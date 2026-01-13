#!/usr/bin/env python3
"""Tests for JSON repair utilities."""

import unittest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

from json_repair import (
    extract_json_block,
    repair_trailing_commas,
    repair_truncated_json,
    repair_json,
    safe_parse_json,
    validate_analysis_schema,
    get_retry_prompt
)


class TestExtractJsonBlock(unittest.TestCase):
    """Tests for JSON block extraction."""

    def test_extract_clean_json(self):
        """Clean JSON should be returned as-is."""
        text = '{"key": "value"}'
        result = extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_from_markdown_fence_json(self):
        """Extract JSON from ```json ... ``` fence."""
        text = '```json\n{"key": "value"}\n```'
        result = extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_from_markdown_fence_plain(self):
        """Extract JSON from plain ``` ... ``` fence."""
        text = '```\n{"key": "value"}\n```'
        result = extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_with_preamble(self):
        """Extract JSON with text before it."""
        text = 'Here is the JSON:\n{"key": "value"}'
        result = extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_with_postamble(self):
        """Extract JSON with text after it."""
        text = '{"key": "value"}\n\nI hope this helps!'
        result = extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_nested_braces(self):
        """Handle nested braces correctly."""
        text = '{"outer": {"inner": "value"}}'
        result = extract_json_block(text)
        self.assertEqual(result, '{"outer": {"inner": "value"}}')

    def test_extract_array(self):
        """Extract JSON array."""
        text = '[1, 2, 3]'
        result = extract_json_block(text)
        self.assertEqual(result, '[1, 2, 3]')

    def test_extract_braces_in_string(self):
        """Braces inside strings should not confuse extraction."""
        text = '{"message": "Use {name} for template"}'
        result = extract_json_block(text)
        self.assertEqual(result, '{"message": "Use {name} for template"}')


class TestRepairTrailingCommas(unittest.TestCase):
    """Tests for trailing comma repair."""

    def test_trailing_comma_object(self):
        """Remove trailing comma before }."""
        text = '{"key": "value",}'
        result = repair_trailing_commas(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_trailing_comma_array(self):
        """Remove trailing comma before ]."""
        text = '["a", "b",]'
        result = repair_trailing_commas(text)
        self.assertEqual(result, '["a", "b"]')

    def test_trailing_comma_with_whitespace(self):
        """Remove trailing comma with whitespace - whitespace is preserved."""
        text = '{"key": "value",  \n}'
        result = repair_trailing_commas(text)
        # Comma removed, whitespace preserved (valid JSON)
        self.assertNotIn(',  \n}', result)
        self.assertIn('"value"', result)
        # Verify it parses as valid JSON
        import json
        parsed = json.loads(result)
        self.assertEqual(parsed, {"key": "value"})

    def test_nested_trailing_commas(self):
        """Handle multiple trailing commas."""
        text = '{"arr": [1, 2,], "obj": {"a": 1,},}'
        result = repair_trailing_commas(text)
        self.assertEqual(result, '{"arr": [1, 2], "obj": {"a": 1}}')

    def test_no_trailing_comma(self):
        """Valid JSON should be unchanged."""
        text = '{"key": "value"}'
        result = repair_trailing_commas(text)
        self.assertEqual(result, '{"key": "value"}')


class TestRepairTruncatedJson(unittest.TestCase):
    """Tests for truncated JSON repair."""

    def test_missing_closing_brace(self):
        """Add missing closing brace."""
        text = '{"key": "value"'
        result = repair_truncated_json(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_missing_closing_bracket(self):
        """Add missing closing bracket."""
        text = '["a", "b"'
        result = repair_truncated_json(text)
        self.assertEqual(result, '["a", "b"]')

    def test_missing_multiple_closings(self):
        """Add multiple missing closings."""
        text = '{"arr": [1, 2'
        result = repair_truncated_json(text)
        self.assertEqual(result, '{"arr": [1, 2]}')

    def test_unclosed_string(self):
        """Close unclosed string."""
        text = '{"key": "value'
        result = repair_truncated_json(text)
        self.assertIn('"', result[-3:])  # Should have added closing quote

    def test_complete_json_unchanged(self):
        """Complete JSON should have no extra closings."""
        text = '{"key": "value"}'
        result = repair_truncated_json(text)
        self.assertEqual(result, '{"key": "value"}')


class TestSafeParseJson(unittest.TestCase):
    """Tests for safe JSON parsing."""

    def test_parse_valid_json(self):
        """Valid JSON should parse successfully."""
        text = '{"key": "value"}'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {"key": "value"})
        self.assertFalse(result['repair_applied'])

    def test_parse_with_fence(self):
        """JSON with markdown fence should parse."""
        text = '```json\n{"key": "value"}\n```'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {"key": "value"})

    def test_parse_with_trailing_comma(self):
        """JSON with trailing comma should be repaired."""
        text = '{"key": "value",}'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {"key": "value"})
        self.assertTrue(result['repair_applied'])

    def test_parse_truncated_json(self):
        """Truncated JSON should be repaired."""
        text = '{"key": "value"'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertTrue(result['repair_applied'])

    def test_parse_invalid_json(self):
        """Completely invalid JSON should fail."""
        text = 'This is not JSON at all'
        result = safe_parse_json(text)
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])

    def test_parse_strict_mode(self):
        """Strict mode should not apply repairs."""
        text = '{"key": "value",}'
        result = safe_parse_json(text, strict=True)
        self.assertFalse(result['success'])


class TestValidateAnalysisSchema(unittest.TestCase):
    """Tests for schema validation."""

    def test_valid_schema(self):
        """Valid analysis schema should pass."""
        data = {
            "samples": [
                {"id": "email_1", "persona": "Formal"}
            ]
        }
        is_valid, error = validate_analysis_schema(data)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_missing_samples(self):
        """Missing samples field should fail."""
        data = {"personas": []}
        is_valid, error = validate_analysis_schema(data)
        self.assertFalse(is_valid)
        self.assertIn("samples", error)

    def test_empty_samples(self):
        """Empty samples array should fail."""
        data = {"samples": []}
        is_valid, error = validate_analysis_schema(data)
        self.assertFalse(is_valid)
        self.assertIn("empty", error)

    def test_sample_missing_id(self):
        """Sample without id should fail."""
        data = {"samples": [{"persona": "Test"}]}
        is_valid, error = validate_analysis_schema(data)
        self.assertFalse(is_valid)
        self.assertIn("id", error)

    def test_sample_missing_persona(self):
        """Sample without persona should fail."""
        data = {"samples": [{"id": "email_1"}]}
        is_valid, error = validate_analysis_schema(data)
        self.assertFalse(is_valid)
        self.assertIn("persona", error)

    def test_non_dict_root(self):
        """Non-dict root should fail."""
        data = [{"samples": []}]
        is_valid, error = validate_analysis_schema(data)
        self.assertFalse(is_valid)
        self.assertIn("object", error)


class TestGetRetryPrompt(unittest.TestCase):
    """Tests for retry prompt generation."""

    def test_retry_prompt_includes_error(self):
        """Retry prompt should include error message."""
        original = "Analyze this email"
        error = "JSON parse error: Expecting ',' at position 50"
        result = get_retry_prompt(original, error)
        self.assertIn(error, result)
        self.assertIn(original, result)

    def test_retry_prompt_emphasizes_json(self):
        """Retry prompt should emphasize JSON-only output."""
        original = "Analyze this"
        result = get_retry_prompt(original, "some error")
        self.assertIn("JSON", result)
        self.assertIn("valid", result.lower())


class TestComplexScenarios(unittest.TestCase):
    """Tests for complex real-world scenarios."""

    def test_llm_response_with_explanation(self):
        """Handle LLM response with explanation text."""
        text = """Here's the analysis you requested:

```json
{
  "samples": [
    {"id": "email_1", "persona": "Professional", "confidence": 0.85}
  ],
  "new_personas": []
}
```

Let me know if you need any clarification!"""
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']['samples']), 1)

    def test_deeply_nested_json(self):
        """Handle deeply nested JSON structures."""
        text = '{"a": {"b": {"c": {"d": "value"}}}}'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['a']['b']['c']['d'], 'value')

    def test_json_with_special_characters(self):
        """Handle JSON with special characters in strings."""
        text = '{"message": "Hello\\nWorld\\t\\"quoted\\""}'
        result = safe_parse_json(text)
        self.assertTrue(result['success'])

    def test_large_truncated_response(self):
        """Handle large truncated response."""
        # Simulate a response cut off mid-way
        text = '{"samples": [{"id": "1", "persona": "Test"}, {"id": "2", "persona":'
        result = safe_parse_json(text)
        # Should attempt repair but may not fully succeed
        # At minimum, should not crash


if __name__ == "__main__":
    unittest.main()
