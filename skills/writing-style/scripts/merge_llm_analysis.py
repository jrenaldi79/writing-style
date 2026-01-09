#!/usr/bin/env python3
"""
Merge LLM analysis output into linkedin_persona.json.

Usage:
    python3 merge_llm_analysis.py llm_output.json
    echo '{"guardrails":...}' | python3 merge_llm_analysis.py -
    python3 merge_llm_analysis.py --dry-run llm_output.json

Features:
- Deep merges arrays and objects
- Only overwrites placeholder/empty fields by default
- Validates result structure
- Prints diff of changes
- Supports dry-run mode
"""

import json
import sys
import argparse
from pathlib import Path
from copy import deepcopy

from config import get_path

PERSONA_FILE = get_path("linkedin_persona.json")


def load_persona() -> dict:
    """Load current linkedin_persona.json."""
    if not PERSONA_FILE.exists():
        print(f"Error: Persona file not found: {PERSONA_FILE}")
        print("Run cluster_linkedin.py first.")
        sys.exit(1)

    with open(PERSONA_FILE) as f:
        return json.load(f)


def load_llm_output(source: str) -> dict:
    """Load LLM output from file or stdin."""
    if source == '-':
        content = sys.stdin.read()
    else:
        path = Path(source)
        if not path.exists():
            print(f"Error: File not found: {source}")
            sys.exit(1)
        with open(path) as f:
            content = f.read()

    # Handle markdown code blocks (common when copying from LLMs)
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in LLM output: {e}")
        print("First 500 chars of content:")
        print(content[:500])
        sys.exit(1)


def is_empty_or_placeholder(value) -> bool:
    """Check if a value is empty/placeholder and should be overwritten."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def merge_positive_examples(base_examples: list, llm_examples: list) -> list:
    """Merge LLM annotations into positive examples using index matching."""
    result = deepcopy(base_examples)

    for llm_ex in llm_examples:
        idx = llm_ex.get('index')
        if idx is None:
            print(f"Warning: LLM example missing 'index', skipping: {llm_ex}")
            continue

        if idx < 0 or idx >= len(result):
            print(f"Warning: Index {idx} out of range (0-{len(result)-1}), skipping")
            continue

        # Merge fields into the existing example
        target = result[idx]
        for field in ['category', 'goal', 'audience', 'what_makes_it_work']:
            if field in llm_ex and not is_empty_or_placeholder(llm_ex[field]):
                if is_empty_or_placeholder(target.get(field)):
                    target[field] = llm_ex[field]
                    print(f"  + example[{idx}].{field} = {json.dumps(llm_ex[field])[:60]}...")

    return result


def deep_merge(base: dict, overlay: dict, path: str = "") -> dict:
    """
    Merge overlay into base, preferring overlay for non-empty values.
    Only overwrites if base value is empty/placeholder.
    """
    result = deepcopy(base)

    for key, overlay_value in overlay.items():
        current_path = f"{path}.{key}" if path else key
        base_value = result.get(key)

        # Skip the index field in example_bank.positive (used for matching)
        if key == 'index':
            continue

        # Special handling for example_bank.positive (uses index-based matching)
        if current_path == 'example_bank.positive':
            if isinstance(overlay_value, list) and isinstance(base_value, list):
                result[key] = merge_positive_examples(base_value, overlay_value)
            continue

        # Special handling for example_bank.negative (append/replace empty array)
        if current_path == 'example_bank.negative':
            if isinstance(overlay_value, list) and len(overlay_value) > 0:
                if is_empty_or_placeholder(base_value):
                    result[key] = overlay_value
                    print(f"  + {current_path} = [{len(overlay_value)} items]")
            continue

        # If overlay value is empty, skip it
        if is_empty_or_placeholder(overlay_value):
            continue

        # If both are dicts, recurse
        if isinstance(base_value, dict) and isinstance(overlay_value, dict):
            result[key] = deep_merge(base_value, overlay_value, current_path)

        # If base is empty/placeholder, replace with overlay
        elif is_empty_or_placeholder(base_value):
            result[key] = overlay_value
            if isinstance(overlay_value, list):
                print(f"  + {current_path} = [{len(overlay_value)} items]")
            elif isinstance(overlay_value, str) and len(overlay_value) > 50:
                print(f"  + {current_path} = \"{overlay_value[:47]}...\"")
            else:
                print(f"  + {current_path} = {json.dumps(overlay_value)}")

        # If base has value and overlay has value, log but don't overwrite
        else:
            print(f"  ~ {current_path}: keeping existing value (use --force to overwrite)")

    return result


def validate_structure(persona: dict) -> list:
    """Validate persona has expected v2 structure. Returns list of warnings."""
    warnings = []

    # Check required top-level fields
    required = ['schema_version', 'voice', 'guardrails', 'platform_rules', 'example_bank']
    for field in required:
        if field not in persona:
            warnings.append(f"Missing required field: {field}")

    # Check voice structure
    if 'voice' in persona:
        voice = persona['voice']
        if 'signature_phrases' in voice and not isinstance(voice['signature_phrases'], list):
            warnings.append("voice.signature_phrases should be an array")

    # Check guardrails structure
    if 'guardrails' in persona:
        guardrails = persona['guardrails']
        if 'never_do' in guardrails and not isinstance(guardrails['never_do'], list):
            warnings.append("guardrails.never_do should be an array")

    # Check example_bank structure
    if 'example_bank' in persona:
        bank = persona['example_bank']
        if 'positive' in bank:
            for i, ex in enumerate(bank['positive']):
                if not ex.get('text'):
                    warnings.append(f"example_bank.positive[{i}] missing 'text'")
        if 'negative' in bank:
            for i, ex in enumerate(bank['negative']):
                if not ex.get('text'):
                    warnings.append(f"example_bank.negative[{i}] missing 'text'")
                if not ex.get('why_not_me'):
                    warnings.append(f"example_bank.negative[{i}] missing 'why_not_me'")

    return warnings


def count_completed_fields(persona: dict) -> dict:
    """Count how many LLM-assisted fields are now completed."""
    counts = {
        'never_do': len(persona.get('guardrails', {}).get('never_do', [])),
        'off_limits_topics': len(persona.get('guardrails', {}).get('off_limits_topics', [])),
        'signature_phrases': len(persona.get('voice', {}).get('signature_phrases', [])),
        'negative_examples': len(persona.get('example_bank', {}).get('negative', [])),
    }

    # Count completed positive example annotations
    positive = persona.get('example_bank', {}).get('positive', [])
    counts['positive_categorized'] = sum(1 for ex in positive if ex.get('category'))
    counts['positive_annotated'] = sum(1 for ex in positive if ex.get('what_makes_it_work'))
    counts['positive_total'] = len(positive)

    return counts


def main():
    parser = argparse.ArgumentParser(description='Merge LLM analysis into linkedin_persona.json')
    parser.add_argument('input', type=str,
                        help='LLM output JSON file (use "-" for stdin)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would change without modifying the file')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Overwrite existing non-empty values')
    args = parser.parse_args()

    # Load data
    print("Loading current persona...")
    persona = load_persona()
    original = deepcopy(persona)

    print(f"Loading LLM output from {'stdin' if args.input == '-' else args.input}...")
    llm_output = load_llm_output(args.input)

    # Merge
    print("\nMerging LLM analysis:")
    merged = deep_merge(persona, llm_output)

    # Validate
    warnings = validate_structure(merged)
    if warnings:
        print("\nValidation warnings:")
        for w in warnings:
            print(f"  ⚠️  {w}")

    # Count completions
    counts = count_completed_fields(merged)
    print("\nField completion status:")
    print(f"  guardrails.never_do: {counts['never_do']} rules")
    print(f"  guardrails.off_limits_topics: {counts['off_limits_topics']} topics")
    print(f"  voice.signature_phrases: {counts['signature_phrases']} phrases")
    print(f"  example_bank.negative: {counts['negative_examples']} examples")
    print(f"  example_bank.positive: {counts['positive_categorized']}/{counts['positive_total']} categorized, "
          f"{counts['positive_annotated']}/{counts['positive_total']} annotated")

    # Save or show dry-run
    if args.dry_run:
        print("\n[DRY RUN] Would write to:", PERSONA_FILE)
        print("Run without --dry-run to apply changes.")
    else:
        with open(PERSONA_FILE, 'w') as f:
            json.dump(merged, f, indent=2)
        print(f"\n✅ Saved merged persona to: {PERSONA_FILE}")

    return 0


if __name__ == '__main__':
    exit(main())
