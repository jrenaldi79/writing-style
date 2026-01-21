#!/usr/bin/env python3
"""
Email Quality Filter - Remove garbage before analysis

Filters out:
- Too short emails (<100 chars)
- Forwards
- Auto-replies (OOO, automatic reply)
- Mass emails (>20 recipients)
- Calendar responses
- Empty bodies

Usage:
    python filter_emails.py                    # Process raw_samples -> filtered_samples
    python filter_emails.py --dry-run          # Preview without saving
    python filter_emails.py --status           # Show filter statistics
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from collections import Counter

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
RAW_DIR = get_path("raw_samples")
FILTERED_DIR = get_path("filtered_samples")
REPORT_FILE = get_path("filter_report.json")

# Quality thresholds
MIN_BODY_LENGTH = 100  # characters
MAX_RECIPIENTS = 20
MIN_QUALITY_SCORE = 0.3

# Detection patterns
FORWARD_PATTERNS = [
    r'^-{5,}\s*Forwarded',
    r'^Begin forwarded message',
    r'^Fwd:',
    r'^FW:',
]

AUTO_REPLY_PATTERNS = [
    r'Out of Office',
    r'Automatic reply',
    r'Auto-Reply',
    r'I am currently out',
    r'Thank you for your email. I am away',
    r'This is an automated response',
    r'I\'m out of the office',
    r'will respond when I return',
]

CALENDAR_PATTERNS = [
    r'^Accepted:',
    r'^Declined:',
    r'^Tentative:',
    r'^Invitation:',
    r'has accepted your meeting',
    r'has declined your meeting',
    r'Calendar:',
]

QUOTED_TEXT_PATTERNS = [
    r'^>+\s*',  # > quoted lines
    r'^On .+ wrote:$',  # "On Mon, Jan 1, John wrote:"
    r'^From:.*\nSent:.*\nTo:',  # Outlook quote header
    r'-{3,}\s*Original Message\s*-{3,}',
]


def extract_body(email_data: dict) -> str:
    """Extract plain text body from email data."""
    # Try payload.body.data (base64) or snippet
    payload = email_data.get('payload', {})
    
    # Try to get body from parts
    def find_text_part(parts):
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    import base64
                    try:
                        return base64.urlsafe_b64decode(body_data).decode('utf-8')
                    except:
                        pass
            if 'parts' in part:
                result = find_text_part(part['parts'])
                if result:
                    return result
        return None
    
    # Check if multipart
    if 'parts' in payload:
        body = find_text_part(payload['parts'])
        if body:
            return body
    
    # Try direct body
    body_data = payload.get('body', {}).get('data', '')
    if body_data:
        import base64
        try:
            return base64.urlsafe_b64decode(body_data).decode('utf-8')
        except:
            pass
    
    # Fallback to snippet
    return email_data.get('snippet', '')


def get_subject(email_data: dict) -> str:
    """Extract subject from email headers."""
    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'subject':
            return header.get('value', '')
    return ''


def get_recipients(email_data: dict) -> List[str]:
    """Extract all recipient emails."""
    headers = email_data.get('payload', {}).get('headers', [])
    recipients = []
    
    for header in headers:
        name = header.get('name', '').lower()
        if name in ['to', 'cc', 'bcc']:
            value = header.get('value', '')
            # Extract emails from header value
            emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', value)
            recipients.extend(emails)
    
    return list(set(recipients))


def remove_quoted_text(body: str) -> str:
    """Remove quoted/forwarded text to get original content only."""
    lines = body.split('\n')
    original_lines = []
    in_quote = False
    
    for line in lines:
        # Check for quote start markers
        if re.match(r'^On .+ wrote:$', line, re.IGNORECASE):
            in_quote = True
            continue
        if re.match(r'-{3,}\s*Original Message\s*-{3,}', line, re.IGNORECASE):
            in_quote = True
            continue
        if re.match(r'^From:.*$', line) and not original_lines:
            # Likely a forwarded email header at the start
            continue
            
        # Skip quoted lines
        if line.startswith('>'):
            continue
            
        if not in_quote:
            original_lines.append(line)
    
    return '\n'.join(original_lines)


def compute_quality_score(body: str, original_body: str) -> float:
    """
    Compute quality score 0-1 based on:
    - Length (longer is better, up to ~500 chars)
    - Originality (ratio of original to total)
    - Vocabulary diversity
    """
    scores = []
    
    # Length score (0-1)
    length = len(original_body)
    if length < 50:
        length_score = 0.1
    elif length < 100:
        length_score = 0.3
    elif length < 200:
        length_score = 0.6
    elif length < 500:
        length_score = 0.8
    else:
        length_score = 1.0
    scores.append(length_score * 0.4)  # 40% weight
    
    # Originality score (0-1)
    total_len = len(body)
    orig_len = len(original_body)
    if total_len > 0:
        originality = orig_len / total_len
    else:
        originality = 0
    scores.append(originality * 0.3)  # 30% weight
    
    # Vocabulary diversity (unique words / total words)
    words = re.findall(r'\b\w+\b', original_body.lower())
    if len(words) > 0:
        diversity = len(set(words)) / len(words)
    else:
        diversity = 0
    scores.append(diversity * 0.3)  # 30% weight
    
    return sum(scores)


def check_patterns(text: str, patterns: List[str]) -> bool:
    """Check if any pattern matches the text."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True
    return False


def filter_email(email_data: dict) -> Tuple[bool, str, Dict]:
    """
    Determine if email should be included.
    
    Returns:
        (should_include, rejection_reason, quality_info)
    """
    body = extract_body(email_data)
    subject = get_subject(email_data)
    recipients = get_recipients(email_data)
    
    quality_info = {
        'body_length': len(body),
        'recipient_count': len(recipients),
        'quality_score': 0.0,
        'flags': []
    }
    
    # Check: Empty body
    if not body or len(body.strip()) == 0:
        return False, 'empty_body', quality_info
    
    # Check: Too short
    original_body = remove_quoted_text(body)
    if len(original_body.strip()) < MIN_BODY_LENGTH:
        quality_info['original_length'] = len(original_body)
        return False, 'too_short', quality_info
    
    # Check: Forward
    if check_patterns(body, FORWARD_PATTERNS) or check_patterns(subject, [r'^Fwd:', r'^FW:']):
        return False, 'forward', quality_info
    
    # Check: Auto-reply
    if check_patterns(body, AUTO_REPLY_PATTERNS) or check_patterns(subject, AUTO_REPLY_PATTERNS):
        return False, 'auto_reply', quality_info
    
    # Check: Calendar response
    if check_patterns(subject, CALENDAR_PATTERNS) or check_patterns(body, CALENDAR_PATTERNS):
        return False, 'calendar_response', quality_info
    
    # Check: Mass email
    if len(recipients) > MAX_RECIPIENTS:
        return False, 'mass_email', quality_info
    
    # Compute quality score
    quality_score = compute_quality_score(body, original_body)
    quality_info['quality_score'] = round(quality_score, 3)
    quality_info['original_length'] = len(original_body)
    
    # Check: Below quality threshold
    if quality_score < MIN_QUALITY_SCORE:
        quality_info['flags'].append('low_quality')
        return False, 'low_quality', quality_info
    
    return True, '', quality_info


def process_emails(dry_run: bool = False) -> Dict:
    """
    Process all raw emails through quality filter.
    
    Returns filter report.
    """
    if not RAW_DIR.exists():
        print(f"[ERROR] Raw samples directory not found: {RAW_DIR}")
        return {}
    
    if not dry_run:
        FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    
    raw_files = list(RAW_DIR.glob('email_*.json'))
    print(f"[EMAIL] Processing {len(raw_files)} raw emails...")
    
    if dry_run:
        print("\n[SEARCH] DRY RUN - no files will be written\n")
    
    # Track results
    accepted = []
    rejected = []
    rejection_reasons = Counter()
    quality_scores = []
    
    for filepath in raw_files:
        email_id = filepath.stem
        
        try:
            with open(filepath) as f:
                email_data = json.load(f)
        except json.JSONDecodeError:
            rejected.append((email_id, 'invalid_json', {}))
            rejection_reasons['invalid_json'] += 1
            continue
        
        should_include, reason, quality_info = filter_email(email_data)
        
        if should_include:
            accepted.append(email_id)
            quality_scores.append(quality_info['quality_score'])
            
            # Save filtered email with quality metadata
            if not dry_run:
                output_data = {
                    'id': email_id,
                    'original_data': email_data,
                    'quality': quality_info,
                    'filtered_at': datetime.now().isoformat()
                }
                output_path = FILTERED_DIR / f"{email_id}.json"
                with open(output_path, 'w') as f:
                    json.dump(output_data, f, indent=2)
            
            status = '[OK]' if quality_info['quality_score'] >= 0.6 else '~'
            print(f"  {status} {email_id} (quality: {quality_info['quality_score']:.2f})")
        else:
            rejected.append((email_id, reason, quality_info))
            rejection_reasons[reason] += 1
            print(f"  [ERROR] {email_id} -> {reason}")
    
    # Generate report
    report = {
        'filter_run': datetime.now().isoformat(),
        'input_count': len(raw_files),
        'output_count': len(accepted),
        'rejected_count': len(rejected),
        'rejection_breakdown': dict(rejection_reasons),
        'avg_quality_score': round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0,
        'quality_distribution': {
            'high': len([s for s in quality_scores if s >= 0.7]),
            'medium': len([s for s in quality_scores if 0.4 <= s < 0.7]),
            'low': len([s for s in quality_scores if s < 0.4])
        }
    }
    
    if not dry_run:
        with open(REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'=' * 50}")
    print("FILTER COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    print(f"{'=' * 50}")
    print(f"Input:    {report['input_count']} emails")
    print(f"Accepted: {report['output_count']} ({report['output_count']/max(report['input_count'],1)*100:.1f}%)")
    print(f"Rejected: {report['rejected_count']} ({report['rejected_count']/max(report['input_count'],1)*100:.1f}%)")
    print(f"\nRejection breakdown:")
    for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
        print(f"  - {reason}: {count}")
    print(f"\nAverage quality score: {report['avg_quality_score']:.2f}")
    print(f"Quality distribution: {report['quality_distribution']}")
    print(f"{'=' * 50}")
    
    if not dry_run:
        print(f"\n[FILE] Filtered emails saved to: {FILTERED_DIR}")
        print(f"[STATS] Report saved to: {REPORT_FILE}")
    
    return report


def show_status():
    """Show current filter status."""
    raw_count = len(list(RAW_DIR.glob('email_*.json'))) if RAW_DIR.exists() else 0
    filtered_count = len(list(FILTERED_DIR.glob('email_*.json'))) if FILTERED_DIR.exists() else 0
    
    print(f"\n{'=' * 50}")
    print("FILTER STATUS")
    print(f"{'=' * 50}")
    print(f"Raw emails:      {raw_count}")
    print(f"Filtered emails: {filtered_count}")
    
    if REPORT_FILE.exists():
        with open(REPORT_FILE) as f:
            report = json.load(f)
        print(f"\nLast run: {report.get('filter_run', 'unknown')}")
        print(f"Avg quality: {report.get('avg_quality_score', 0):.2f}")
        print(f"\nRejection breakdown:")
        for reason, count in report.get('rejection_breakdown', {}).items():
            print(f"  - {reason}: {count}")
    else:
        print("\nNo filter report found. Run filter first.")
    
    print(f"{'=' * 50}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Filter emails for quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python filter_emails.py              # Process all raw emails
  python filter_emails.py --dry-run    # Preview without saving
  python filter_emails.py --status     # Show current status
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--status', action='store_true', help='Show filter status')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        process_emails(dry_run=args.dry_run)
