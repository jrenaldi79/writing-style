#!/usr/bin/env python3
"""
Prepare Validation - Extract context/reply pairs from validation set

Processes validation_set/ emails and extracts:
- Incoming context (quoted text from the email being replied to)
- Ground truth (the user's actual reply)

This enables blind validation where the LLM sees only context
and must generate a reply, which is then compared to ground truth.

Usage:
    python prepare_validation.py               # Process validation set
    python prepare_validation.py --status      # Show validation set status
    python prepare_validation.py --dry-run     # Preview without saving
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
from typing import Dict, List, Tuple, Optional

from config import get_data_dir, get_path

VALIDATION_DIR = get_path("validation_set")
OUTPUT_FILE = get_path("validation_pairs.json")


def extract_quoted_and_reply(body: str) -> Tuple[str, str]:
    """
    Extract quoted text (incoming context) and non-quoted text (reply).

    Handles common quote formats:
    - Lines starting with '>'
    - Lines starting with '|'
    - "On ... wrote:" blocks

    Returns:
        Tuple of (quoted_context, reply_text)
    """
    if not body:
        return "", ""

    lines = body.split('\n')
    reply_lines = []
    quoted_lines = []
    in_quote_block = False

    # Pattern for "On DATE, NAME wrote:" or similar
    wrote_pattern = re.compile(r'^On .+wrote:?\s*$', re.IGNORECASE)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for quote markers
        if stripped.startswith('>') or stripped.startswith('|'):
            # This is quoted text
            quoted_lines.append(stripped.lstrip('>|').strip())
            in_quote_block = True
        elif wrote_pattern.match(stripped):
            # "On ... wrote:" line - marks start of quote
            in_quote_block = True
            # Don't include the "On ... wrote:" line itself
        elif in_quote_block and stripped == '':
            # Empty line might end quote block or continue it
            # Look ahead to see if more quotes follow
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('>') or next_line.startswith('|'):
                    quoted_lines.append('')
                else:
                    in_quote_block = False
                    reply_lines.append(line)
            else:
                in_quote_block = False
        elif in_quote_block:
            # Continuation of quoted block without marker
            quoted_lines.append(stripped)
        else:
            # This is the user's reply
            reply_lines.append(line)

    quoted_text = '\n'.join(quoted_lines).strip()
    reply_text = '\n'.join(reply_lines).strip()

    return quoted_text, reply_text


def extract_greeting_and_closing(reply_text: str) -> Dict[str, str]:
    """Extract greeting and closing from reply text."""
    if not reply_text:
        return {"greeting": "", "closing": ""}

    lines = [l.strip() for l in reply_text.split('\n') if l.strip()]

    greeting = ""
    closing = ""

    if lines:
        # Check first line for greeting patterns
        first_line = lines[0]
        greeting_patterns = [
            r'^(Hi|Hey|Hello|Dear|Good morning|Good afternoon|Good evening)\b',
            r'^(Thanks|Thank you)\b',
        ]
        for pattern in greeting_patterns:
            if re.match(pattern, first_line, re.IGNORECASE):
                greeting = first_line
                break

    if len(lines) > 1:
        # Check last few lines for closing patterns
        closing_patterns = [
            r'^(Best|Thanks|Thank you|Cheers|Regards|Sincerely|Best regards|Kind regards|Warm regards)',
            r'^(Talk soon|Looking forward|Let me know|Hope this helps)',
            r'^[-–—]?\s*[A-Z][a-z]+$',  # Just a name like "John" or "- John"
        ]
        for line in reversed(lines[-3:]):
            for pattern in closing_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    closing = line
                    break
            if closing:
                break

    return {"greeting": greeting, "closing": closing}


def analyze_tone_hints(reply_text: str) -> List[str]:
    """Extract tone hints from the reply text."""
    hints = []

    if not reply_text:
        return hints

    text_lower = reply_text.lower()

    # Formality indicators
    if any(phrase in text_lower for phrase in ['dear ', 'sincerely', 'kind regards', 'respectfully']):
        hints.append('formal')
    if any(phrase in text_lower for phrase in ['hey ', 'lol', 'haha', '!!']):
        hints.append('casual')

    # Warmth indicators
    if any(phrase in text_lower for phrase in ['hope you', 'thank you so much', 'really appreciate', 'wonderful']):
        hints.append('warm')

    # Directness indicators
    if reply_text.count('?') > 2:
        hints.append('inquisitive')
    if len(reply_text) < 100:
        hints.append('concise')
    if len(reply_text) > 500:
        hints.append('detailed')

    # Contractions - normalize Unicode apostrophes and use comprehensive pattern
    normalized_text = reply_text.replace('\u2019', "'").replace('\u2018', "'")
    contraction_pattern = (
        r"\b(i'm|i've|i'll|i'd|we're|we've|we'll|we'd|you're|you've|you'll|you'd|"
        r"they're|they've|they'll|they'd|he's|she's|it's|that's|there's|here's|"
        r"what's|who's|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|"
        r"weren't|haven't|hasn't|hadn't|couldn't|wouldn't|shouldn't)\b"
    )
    if re.search(contraction_pattern, normalized_text, re.IGNORECASE):
        hints.append('uses_contractions')

    return hints


def process_validation_email(email_file: Path) -> Optional[Dict]:
    """Process a single validation email into a context/reply pair."""
    try:
        with open(email_file) as f:
            email_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  Warning: Could not read {email_file.name}: {e}")
        return None

    body = email_data.get('body', '')

    # Skip if no body
    if not body:
        return None

    # Extract quoted context and reply
    quoted_context, reply_text = extract_quoted_and_reply(body)

    # Skip if no clear reply (might not be a response email)
    if not reply_text:
        # Use snippet as fallback
        reply_text = email_data.get('snippet', '')

    if not reply_text:
        return None

    # Extract structural elements
    greeting_closing = extract_greeting_and_closing(reply_text)
    tone_hints = analyze_tone_hints(reply_text)

    # Build the validation pair
    pair = {
        "id": email_file.stem,  # e.g., "email_abc123"
        "context": {
            "subject": email_data.get('subject', ''),
            "from_original": email_data.get('to', ''),  # Who they were replying to
            "quoted_text": quoted_context,
            "thread_id": email_data.get('thread_id', ''),
            "has_quoted_context": bool(quoted_context)
        },
        "ground_truth": {
            "reply_text": reply_text,
            "greeting": greeting_closing['greeting'],
            "closing": greeting_closing['closing'],
            "tone_hints": tone_hints,
            "word_count": len(reply_text.split()),
            "has_contractions": 'uses_contractions' in tone_hints
        },
        "metadata": {
            "date": email_data.get('date', ''),
            "original_subject": email_data.get('subject', ''),
            "to": email_data.get('to', ''),
            "from": email_data.get('from', '')
        },
        "expected_persona": None  # To be filled by validation
    }

    return pair


def prepare_validation(dry_run: bool = False) -> bool:
    """Process all validation emails and create pairs file."""

    if not VALIDATION_DIR.exists():
        print(f"Validation set not found at: {VALIDATION_DIR}")
        print("\nTo create a validation set, run:")
        print("  python fetch_emails.py --holdout 0.15")
        return False

    email_files = list(VALIDATION_DIR.glob("*.json"))

    if not email_files:
        print("No validation emails found.")
        return False

    print(f"Processing {len(email_files)} validation emails...")
    if dry_run:
        print("(DRY RUN - no files will be written)\n")

    pairs = []
    skipped = 0

    for email_file in sorted(email_files):
        pair = process_validation_email(email_file)
        if pair:
            pairs.append(pair)
            has_context = "+" if pair['context']['has_quoted_context'] else "-"
            print(f"  {has_context} {pair['id'][:25]}... ({pair['ground_truth']['word_count']} words)")
        else:
            skipped += 1

    print(f"\n{'=' * 50}")
    print("VALIDATION PAIRS EXTRACTED")
    print(f"{'=' * 50}")
    print(f"Total emails:     {len(email_files)}")
    print(f"Valid pairs:      {len(pairs)}")
    print(f"Skipped:          {skipped}")

    # Statistics
    with_context = sum(1 for p in pairs if p['context']['has_quoted_context'])
    print(f"With quoted context: {with_context} ({100*with_context/len(pairs):.0f}%)" if pairs else "")

    if not dry_run:
        output_data = {
            "created": datetime.now().isoformat(),
            "source": str(VALIDATION_DIR),
            "total_emails": len(email_files),
            "valid_pairs": len(pairs),
            "pairs": pairs
        }

        with open(OUTPUT_FILE, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\nSaved to: {OUTPUT_FILE}")

    print(f"{'=' * 50}")

    if pairs:
        print(f"\n{'=' * 60}")
        print("READY FOR BLIND VALIDATION")
        print(f"{'=' * 60}")
        print(f"\nNext step:")
        print(f"  python validate_personas.py")
        print(f"\nThis will:")
        print(f"  1. Load your personas (draft)")
        print(f"  2. Show context only (hide ground truth)")
        print(f"  3. Generate replies using personas")
        print(f"  4. Reveal actual replies and score")
        print(f"{'=' * 60}\n")

    return True


def show_status():
    """Show validation set status."""
    print(f"\n{'=' * 50}")
    print("VALIDATION SET STATUS")
    print(f"{'=' * 50}")

    if not VALIDATION_DIR.exists():
        print(f"\nValidation directory not found: {VALIDATION_DIR}")
        print("\nTo create a validation set:")
        print("  python fetch_emails.py --holdout 0.15")
        return

    email_files = list(VALIDATION_DIR.glob("*.json"))
    print(f"\nValidation emails: {len(email_files)}")

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        print(f"Validation pairs:  {data.get('valid_pairs', 0)}")
        print(f"Created:           {data.get('created', 'Unknown')}")

        # Show some sample IDs
        pairs = data.get('pairs', [])
        if pairs:
            print(f"\nSample validation emails:")
            for p in pairs[:5]:
                print(f"  - {p['id']}")
            if len(pairs) > 5:
                print(f"  ... and {len(pairs) - 5} more")
    else:
        print(f"Validation pairs:  Not yet generated")
        print(f"\nRun: python prepare_validation.py")

    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract context/reply pairs from validation set",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prepare_validation.py               # Process validation set
  python prepare_validation.py --status      # Show validation set status
  python prepare_validation.py --dry-run     # Preview without saving
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--status", action="store_true", help="Show validation status")

    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        prepare_validation(dry_run=args.dry_run)
