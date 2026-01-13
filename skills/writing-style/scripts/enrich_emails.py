#!/usr/bin/env python3
"""
Email Enrichment - Add recipient and context metadata

Extracts:
- Recipient count and type (individual, small_group, team, broadcast)
- Audience (internal, external, mixed)
- Thread position (initiating, reply, forward)
- Time context (time of day, day of week)
- Email structure metrics

Usage:
    python enrich_emails.py                    # Process filtered_samples → enriched_samples
    python enrich_emails.py --dry-run          # Preview without saving
    python enrich_emails.py --status           # Show enrichment statistics
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter
import base64

# Directories
from config import get_data_dir, get_path
from email_analysis_v2 import detect_recipient_seniority

DATA_DIR = get_data_dir()
FILTERED_DIR = get_path("filtered_samples")
ENRICHED_DIR = get_path("enriched_samples")
REPORT_FILE = get_path("enrichment_report.json")

# Your email domain (for internal detection)
# Will be auto-detected from sender if not set
USER_DOMAIN = None


def get_header(email_data: dict, header_name: str) -> str:
    """Get a specific header value from email.

    Checks payload.headers array first (Gmail API full format),
    then falls back to direct attributes (simplified format).
    """
    # Try payload.headers first (Gmail API format)
    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == header_name.lower():
            return header.get('value', '')

    # Fallback to direct attribute (simplified format)
    # Check lowercase version first, then original case, then case-insensitive search
    direct_value = email_data.get(header_name.lower())
    if direct_value:
        return direct_value
    direct_value = email_data.get(header_name)
    if direct_value:
        return direct_value

    # Case-insensitive search through all keys
    header_lower = header_name.lower()
    for key, value in email_data.items():
        if key.lower() == header_lower and isinstance(value, str):
            return value

    return ''


def extract_emails_from_header(header_value: str) -> List[str]:
    """Extract email addresses from a header value."""
    if not header_value:
        return []
    return re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', header_value.lower())


def get_domain(email: str) -> str:
    """Extract domain from email address."""
    if '@' in email:
        return email.split('@')[1].lower()
    return ''


def detect_user_domain(email_data: dict) -> str:
    """Detect user's domain from the From header."""
    from_header = get_header(email_data, 'from')
    from_emails = extract_emails_from_header(from_header)
    if from_emails:
        return get_domain(from_emails[0])
    return ''


def classify_recipient_type(count: int) -> str:
    """Classify based on recipient count."""
    if count == 1:
        return 'individual'
    elif count <= 5:
        return 'small_group'
    elif count <= 15:
        return 'team'
    else:
        return 'broadcast'


def classify_audience(recipient_domains: List[str], user_domain: str) -> str:
    """Classify audience as internal, external, or mixed."""
    if not recipient_domains:
        return 'unknown'
    
    internal_count = sum(1 for d in recipient_domains if d == user_domain)
    external_count = len(recipient_domains) - internal_count
    
    if external_count == 0:
        return 'internal'
    elif internal_count == 0:
        return 'external'
    else:
        return 'mixed'


def detect_thread_position(email_data: dict) -> Tuple[str, int]:
    """
    Detect if email is initiating, reply, or forward.
    Also estimate thread depth.
    """
    subject = get_header(email_data, 'subject')
    references = get_header(email_data, 'references')
    in_reply_to = get_header(email_data, 'in-reply-to')
    
    # Check subject prefixes
    subject_lower = subject.lower().strip()
    
    if subject_lower.startswith('fwd:') or subject_lower.startswith('fw:'):
        return 'forward', 1
    
    # Count Re: prefixes for thread depth
    re_count = len(re.findall(r'^(re:\s*)+', subject_lower, re.IGNORECASE))
    
    # Check for reply indicators
    if in_reply_to or references:
        # Count message IDs in references for depth
        if references:
            depth = len(references.split()) 
        else:
            depth = 1
        return 'reply', depth
    
    if re_count > 0:
        return 'reply', re_count
    
    return 'initiating', 0


def extract_time_context(email_data: dict) -> Dict:
    """Extract time-based context from email."""
    # Try internalDate (milliseconds since epoch)
    internal_date = email_data.get('internalDate')
    
    if internal_date:
        try:
            dt = datetime.fromtimestamp(int(internal_date) / 1000)
            hour = dt.hour
            
            if 5 <= hour < 12:
                time_of_day = 'morning'
            elif 12 <= hour < 17:
                time_of_day = 'afternoon'
            elif 17 <= hour < 21:
                time_of_day = 'evening'
            else:
                time_of_day = 'night'
            
            return {
                'timestamp': dt.isoformat(),
                'time_of_day': time_of_day,
                'day_of_week': dt.strftime('%A').lower(),
                'hour': hour,
                'is_weekend': dt.weekday() >= 5
            }
        except (ValueError, TypeError):
            pass
    
    return {
        'timestamp': None,
        'time_of_day': 'unknown',
        'day_of_week': 'unknown',
        'hour': None,
        'is_weekend': None
    }


def extract_body(email_data: dict) -> str:
    """Extract plain text body from email data."""
    payload = email_data.get('payload', {})
    
    def find_text_part(parts):
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    try:
                        return base64.urlsafe_b64decode(body_data).decode('utf-8')
                    except:
                        pass
            if 'parts' in part:
                result = find_text_part(part['parts'])
                if result:
                    return result
        return None
    
    if 'parts' in payload:
        body = find_text_part(payload['parts'])
        if body:
            return body
    
    body_data = payload.get('body', {}).get('data', '')
    if body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode('utf-8')
        except:
            pass
    
    return email_data.get('snippet', '')


def analyze_structure(body: str) -> Dict:
    """Analyze email structure metrics."""
    lines = body.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    
    # Count paragraphs (separated by blank lines)
    paragraphs = []
    current_para = []
    for line in lines:
        if line.strip():
            current_para.append(line)
        elif current_para:
            paragraphs.append('\n'.join(current_para))
            current_para = []
    if current_para:
        paragraphs.append('\n'.join(current_para))
    
    # Detect bullet points
    bullet_patterns = [r'^\s*[•\-\*]\s+', r'^\s*\d+[.)\-]\s+']
    bullet_count = sum(
        1 for line in lines 
        if any(re.match(p, line) for p in bullet_patterns)
    )
    
    # Detect greeting and closing
    greeting = None
    closing = None
    
    greeting_patterns = [
        r'^(Hey|Hi|Hello|Dear|Good morning|Good afternoon)\b',
        r'^\w+,?$',  # Just a name
        r'^Team,?$',
    ]
    
    closing_patterns = [
        r'^(Best|Thanks|Cheers|Regards|Sincerely|Talk soon)',
        r'^-\s*\w+$',  # -John
        r'^\w{1,3}$',  # JR, J
    ]
    
    for line in non_empty_lines[:3]:
        for pattern in greeting_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                greeting = line.strip()
                break
        if greeting:
            break
    
    for line in reversed(non_empty_lines[-5:]):
        for pattern in closing_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                closing = line.strip()
                break
        if closing:
            break
    
    return {
        'char_count': len(body),
        'line_count': len(lines),
        'paragraph_count': len(paragraphs),
        'bullet_count': bullet_count,
        'has_bullets': bullet_count > 0,
        'greeting': greeting,
        'closing': closing,
        'avg_paragraph_length': sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
    }


def has_attachments(email_data: dict) -> bool:
    """Check if email has attachments."""
    payload = email_data.get('payload', {})
    
    def check_parts(parts):
        for part in parts:
            if part.get('filename'):
                return True
            if 'parts' in part:
                if check_parts(part['parts']):
                    return True
        return False
    
    if 'parts' in payload:
        return check_parts(payload['parts'])
    
    return False


def enrich_email(filtered_data: dict, user_domain: str) -> Dict:
    """
    Add enrichment metadata to a filtered email.
    """
    email_data = filtered_data.get('original_data', filtered_data)
    email_id = filtered_data.get('id', 'unknown')
    
    # Extract recipients
    to_emails = extract_emails_from_header(get_header(email_data, 'to'))
    cc_emails = extract_emails_from_header(get_header(email_data, 'cc'))
    all_recipients = list(set(to_emails + cc_emails))
    recipient_domains = [get_domain(e) for e in all_recipients]
    
    # Thread position
    thread_position, thread_depth = detect_thread_position(email_data)
    
    # Time context
    time_context = extract_time_context(email_data)
    
    # Body analysis
    body = extract_body(email_data)
    structure = analyze_structure(body)
    
    # Detect recipient seniority for relationship calibration
    audience = classify_audience(recipient_domains, user_domain)
    temp_enrichment = {
        'audience': audience,
        'recipient_signatures': []  # Placeholder - could be populated from email parsing
    }
    seniority = detect_recipient_seniority({
        'original_data': email_data,
        'enrichment': temp_enrichment
    })

    enrichment = {
        # Recipient info
        'recipient_count': len(all_recipients),
        'recipient_type': classify_recipient_type(len(all_recipients)),
        'audience': audience,
        'recipient_domains': list(set(recipient_domains)),
        'recipient_seniority': seniority,  # NEW: v2 seniority detection
        'has_cc': len(cc_emails) > 0,

        # Thread info
        'thread_position': thread_position,
        'thread_depth': thread_depth,

        # Attachments
        'has_attachments': has_attachments(email_data),

        # Time context
        'time_of_day': time_context['time_of_day'],
        'day_of_week': time_context['day_of_week'],
        'is_weekend': time_context['is_weekend'],
        'timestamp': time_context['timestamp'],

        # Structure
        'char_count': structure['char_count'],
        'paragraph_count': structure['paragraph_count'],
        'has_bullets': structure['has_bullets'],
        'greeting': structure['greeting'],
        'closing': structure['closing']
    }
    
    return {
        'id': email_id,
        'original_data': email_data,
        'quality': filtered_data.get('quality', {}),
        'enrichment': enrichment,
        'enriched_at': datetime.now().isoformat()
    }


def process_emails(dry_run: bool = False) -> Dict:
    """
    Process all filtered emails through enrichment.
    """
    global USER_DOMAIN
    
    if not FILTERED_DIR.exists():
        print(f"❌ Filtered samples directory not found: {FILTERED_DIR}")
        print("   Run filter_emails.py first.")
        return {}
    
    if not dry_run:
        ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    
    filtered_files = list(FILTERED_DIR.glob('email_*.json'))
    print(f"📧 Enriching {len(filtered_files)} filtered emails...")
    
    if dry_run:
        print("\n🔍 DRY RUN - no files will be written\n")
    
    # Auto-detect user domain from first email
    if not USER_DOMAIN and filtered_files:
        with open(filtered_files[0]) as f:
            sample = json.load(f)
        USER_DOMAIN = detect_user_domain(sample.get('original_data', sample))
        print(f"📍 Detected user domain: {USER_DOMAIN}\n")
    
    # Track statistics
    stats = {
        'recipient_types': Counter(),
        'audiences': Counter(),
        'recipient_seniorities': Counter(),  # NEW: v2 seniority tracking
        'thread_positions': Counter(),
        'times_of_day': Counter(),
        'days_of_week': Counter()
    }
    
    processed = 0
    for filepath in filtered_files:
        try:
            with open(filepath) as f:
                filtered_data = json.load(f)
        except json.JSONDecodeError:
            print(f"  ✗ {filepath.stem} → invalid JSON")
            continue
        
        enriched = enrich_email(filtered_data, USER_DOMAIN)
        e = enriched['enrichment']
        
        # Update stats
        stats['recipient_types'][e['recipient_type']] += 1
        stats['audiences'][e['audience']] += 1
        stats['recipient_seniorities'][e.get('recipient_seniority', 'unknown')] += 1
        stats['thread_positions'][e['thread_position']] += 1
        stats['times_of_day'][e['time_of_day']] += 1
        if e['day_of_week'] != 'unknown':
            stats['days_of_week'][e['day_of_week']] += 1
        
        # Save enriched email
        if not dry_run:
            output_path = ENRICHED_DIR / f"{enriched['id']}.json"
            with open(output_path, 'w') as f:
                json.dump(enriched, f, indent=2)
        
        # Brief status
        audience_icon = {'internal': '🏠', 'external': '🌍', 'mixed': '🔀'}.get(e['audience'], '❓')
        print(f"  ✓ {enriched['id']} → {e['recipient_type']} {audience_icon} ({e['thread_position']})")
        processed += 1
    
    # Generate report
    report = {
        'enrichment_run': datetime.now().isoformat(),
        'user_domain': USER_DOMAIN,
        'input_count': len(filtered_files),
        'output_count': processed,
        'statistics': {
            'recipient_types': dict(stats['recipient_types']),
            'audiences': dict(stats['audiences']),
            'recipient_seniorities': dict(stats['recipient_seniorities']),
            'thread_positions': dict(stats['thread_positions']),
            'times_of_day': dict(stats['times_of_day']),
            'days_of_week': dict(stats['days_of_week'])
        }
    }
    
    if not dry_run:
        with open(REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'═' * 50}")
    print("ENRICHMENT COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    print(f"{'═' * 50}")
    print(f"Processed: {processed} emails")
    print(f"\nRecipient Types:")
    for rtype, count in stats['recipient_types'].most_common():
        print(f"  • {rtype}: {count}")
    print(f"\nAudience:")
    for audience, count in stats['audiences'].most_common():
        print(f"  • {audience}: {count}")
    print(f"\nThread Position:")
    for pos, count in stats['thread_positions'].most_common():
        print(f"  • {pos}: {count}")
    print(f"{'═' * 50}")
    
    if not dry_run:
        print(f"\n📁 Enriched emails saved to: {ENRICHED_DIR}")
        print(f"📊 Report saved to: {REPORT_FILE}")
    
    return report


def show_status():
    """Show current enrichment status."""
    filtered_count = len(list(FILTERED_DIR.glob('email_*.json'))) if FILTERED_DIR.exists() else 0
    enriched_count = len(list(ENRICHED_DIR.glob('email_*.json'))) if ENRICHED_DIR.exists() else 0
    
    print(f"\n{'═' * 50}")
    print("ENRICHMENT STATUS")
    print(f"{'═' * 50}")
    print(f"Filtered emails:  {filtered_count}")
    print(f"Enriched emails:  {enriched_count}")
    
    if REPORT_FILE.exists():
        with open(REPORT_FILE) as f:
            report = json.load(f)
        print(f"\nLast run: {report.get('enrichment_run', 'unknown')}")
        print(f"User domain: {report.get('user_domain', 'unknown')}")
        
        stats = report.get('statistics', {})
        if stats.get('audiences'):
            print(f"\nAudience breakdown:")
            for audience, count in stats['audiences'].items():
                print(f"  • {audience}: {count}")
    else:
        print("\nNo enrichment report found. Run enrichment first.")
    
    print(f"{'═' * 50}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Enrich emails with recipient and context metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enrich_emails.py              # Process all filtered emails
  python enrich_emails.py --dry-run    # Preview without saving
  python enrich_emails.py --status     # Show current status
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--status', action='store_true', help='Show enrichment status')
    parser.add_argument('--domain', type=str, help='Override user domain detection')
    
    args = parser.parse_args()
    
    if args.domain:
        USER_DOMAIN = args.domain
    
    if args.status:
        show_status()
    else:
        process_emails(dry_run=args.dry_run)
