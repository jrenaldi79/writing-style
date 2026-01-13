#!/usr/bin/env python3
"""
JSON Repair Utilities - Robust JSON extraction from LLM responses

Handles common LLM JSON output issues:
- Markdown code fences (```json ... ```)
- Preamble/postamble text
- Incomplete responses (truncated JSON)
- Trailing commas
- Unescaped characters in strings
- Missing closing brackets/braces

Usage:
    from json_repair import extract_json, repair_json, safe_parse_json

    result = safe_parse_json(llm_response)
    if result['success']:
        data = result['data']
    else:
        print(f"Failed: {result['error']}")
"""

import re
import json
from typing import Dict, Any, Optional, Tuple


def extract_json_block(text: str) -> str:
    """
    Extract JSON from text that may contain markdown fences or surrounding text.

    Handles:
    - ```json ... ```
    - ``` ... ```
    - JSON embedded in prose
    - Multiple JSON blocks (returns first valid one)

    Returns:
        Extracted JSON string (may still need repair)
    """
    text = text.strip()

    # Pattern 1: ```json ... ``` or ``` ... ```
    fence_pattern = r'```(?:json)?\s*\n?(.*?)```'
    matches = re.findall(fence_pattern, text, re.DOTALL)
    if matches:
        # Try each match to find valid JSON
        for match in matches:
            cleaned = match.strip()
            if cleaned.startswith('{') or cleaned.startswith('['):
                return cleaned

    # Pattern 2: Remove markdown fences at start/end only
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Pattern 3: Find JSON object/array boundaries
    # Look for outermost { } or [ ]
    first_brace = text.find('{')
    first_bracket = text.find('[')

    if first_brace == -1 and first_bracket == -1:
        return text  # No JSON structure found, return as-is

    # Determine which comes first
    if first_brace == -1:
        start = first_bracket
        open_char, close_char = '[', ']'
    elif first_bracket == -1:
        start = first_brace
        open_char, close_char = '{', '}'
    else:
        if first_brace < first_bracket:
            start = first_brace
            open_char, close_char = '{', '}'
        else:
            start = first_bracket
            open_char, close_char = '[', ']'

    # Find matching close (accounting for nesting)
    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end > start:
        return text[start:end]

    # If no matching close found, return from start to end
    return text[start:]


def repair_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ]."""
    # Remove trailing commas before closing braces/brackets
    # Handle: ,} or ,] with optional whitespace
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text


def repair_truncated_json(text: str) -> str:
    """
    Attempt to close truncated JSON by adding missing brackets/braces.

    This is a best-effort repair for responses cut off mid-JSON.
    """
    # Count unmatched braces and brackets
    open_braces = 0
    open_brackets = 0
    in_string = False
    escape_next = False

    for char in text:
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
        elif char == '[':
            open_brackets += 1
        elif char == ']':
            open_brackets -= 1

    # Check if we're in an unclosed string
    if in_string:
        text += '"'

    # Add missing closing brackets/braces
    # Order matters: close arrays before objects (inner to outer)
    text += ']' * max(0, open_brackets)
    text += '}' * max(0, open_braces)

    return text


def repair_unescaped_quotes(text: str) -> str:
    """
    Attempt to fix unescaped quotes within JSON strings.

    This is tricky and may not always work correctly.
    """
    # This is a simplified approach - only handles obvious cases
    # For complex cases, manual intervention may be needed

    # Find strings and check for unescaped quotes
    result = []
    i = 0
    in_string = False
    string_start = -1

    while i < len(text):
        char = text[i]

        if char == '\\' and in_string:
            # Skip escaped character
            result.append(text[i:i+2])
            i += 2
            continue

        if char == '"':
            if not in_string:
                in_string = True
                string_start = i
                result.append(char)
            else:
                # Check if this quote is followed by a structural character
                # If so, it's likely a real string end
                next_i = i + 1
                while next_i < len(text) and text[next_i] in ' \t\n\r':
                    next_i += 1

                if next_i >= len(text) or text[next_i] in ':,}]':
                    # Real string end
                    in_string = False
                    result.append(char)
                else:
                    # Possibly unescaped quote inside string - escape it
                    result.append('\\"')
            i += 1
            continue

        result.append(char)
        i += 1

    return ''.join(result)


def repair_json(text: str) -> str:
    """
    Apply all repair strategies to malformed JSON.

    Returns:
        Repaired JSON string (may still be invalid)
    """
    # Step 1: Extract JSON block from surrounding text
    text = extract_json_block(text)

    # Step 2: Remove trailing commas
    text = repair_trailing_commas(text)

    # Step 3: Repair truncated JSON
    text = repair_truncated_json(text)

    return text


def safe_parse_json(text: str, strict: bool = False) -> Dict[str, Any]:
    """
    Safely parse JSON from LLM response with multiple repair attempts.

    Args:
        text: Raw LLM response
        strict: If True, don't attempt repairs (just extract)

    Returns:
        Dict with keys:
        - success: bool
        - data: parsed JSON (if success)
        - error: error message (if not success)
        - repair_applied: bool (if repairs were needed)
        - raw_extracted: the extracted JSON string
    """
    result = {
        'success': False,
        'data': None,
        'error': None,
        'repair_applied': False,
        'raw_extracted': None
    }

    # Attempt 1: Extract and parse without repair
    extracted = extract_json_block(text)
    result['raw_extracted'] = extracted

    try:
        result['data'] = json.loads(extracted)
        result['success'] = True
        return result
    except json.JSONDecodeError as e:
        if strict:
            result['error'] = f"JSON parse error: {str(e)}"
            return result

    # Attempt 2: Apply trailing comma repair
    repaired = repair_trailing_commas(extracted)
    try:
        result['data'] = json.loads(repaired)
        result['success'] = True
        result['repair_applied'] = True
        return result
    except json.JSONDecodeError:
        pass

    # Attempt 3: Apply truncation repair
    repaired = repair_truncated_json(repaired)
    try:
        result['data'] = json.loads(repaired)
        result['success'] = True
        result['repair_applied'] = True
        return result
    except json.JSONDecodeError as e:
        result['error'] = f"JSON parse error after repairs: {str(e)}"

    return result


def validate_analysis_schema(data: Dict) -> Tuple[bool, str]:
    """
    Validate that parsed JSON matches expected analysis schema.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Root must be an object"

    # Check required fields
    if 'samples' not in data:
        return False, "Missing 'samples' array"

    if not isinstance(data['samples'], list):
        return False, "'samples' must be an array"

    if len(data['samples']) == 0:
        return False, "'samples' array is empty"

    # Validate sample structure
    for i, sample in enumerate(data['samples']):
        if not isinstance(sample, dict):
            return False, f"Sample {i} is not an object"
        if 'id' not in sample:
            return False, f"Sample {i} missing 'id'"
        if 'persona' not in sample:
            return False, f"Sample {i} missing 'persona'"

    return True, ""


# Retry prompt for JSON-only output
JSON_RETRY_PROMPT = """Your previous response could not be parsed as valid JSON.

Please output ONLY valid JSON with no additional text, markdown, or explanation.
The response must start with { and end with }.

Here is the required structure again:
{
  "samples": [...],
  "new_personas": [...]
}

IMPORTANT: Output ONLY the JSON object, nothing else."""


def get_retry_prompt(original_prompt: str, error_msg: str) -> str:
    """
    Generate a retry prompt that emphasizes JSON-only output.

    Args:
        original_prompt: The original analysis prompt
        error_msg: The error from the first attempt

    Returns:
        Modified prompt for retry
    """
    # Add JSON-only emphasis to the end of the original prompt
    retry_addition = f"""

---
CRITICAL: Your response MUST be valid JSON only.
Previous attempt failed with: {error_msg}

Output ONLY a JSON object starting with {{ and ending with }}.
No markdown code fences. No explanation text. Just pure JSON.
"""
    return original_prompt + retry_addition
