#!/usr/bin/env python3
"""
Test Validate Personas - TDD tests for RCA fixes

Tests for:
- Issue #1: Health check for persona file naming (personas.json vs persona_registry.json)
- Issue #2: Schema validation for characteristics dict (must have tone vectors)
- Issue #3: Generated reply previews in mismatch review
- Issue #4: Interactive validation loop
- Issue #5: Consistent field naming (id vs pair_id vs email_id)
"""

import json
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))


class TestHealthCheck:
    """Issue #1: Detect wrong persona filename."""

    def test_check_persona_health_detects_wrong_filename(self, tmp_path):
        """Should detect personas.json without persona_registry.json."""
        from validate_personas import check_persona_health

        # Create only personas.json (wrong file)
        wrong_file = tmp_path / "personas.json"
        wrong_file.write_text(json.dumps({"personas": {}}))

        # Create a non-existent path for the correct file
        correct_file = tmp_path / "persona_registry.json"

        with patch('validate_personas.get_data_dir', return_value=tmp_path):
            with patch('validate_personas.PERSONA_REGISTRY_FILE', correct_file):
                result = check_persona_health()

        assert result['healthy'] is False
        assert 'wrong_filename' in result['issues']
        assert 'personas.json exists but persona_registry.json does not' in result['issues']['wrong_filename']

    def test_check_persona_health_passes_correct_filename(self, tmp_path):
        """Should pass when persona_registry.json exists."""
        from validate_personas import check_persona_health

        # Create correct file
        correct_file = tmp_path / "persona_registry.json"
        correct_file.write_text(json.dumps({
            "personas": {
                "Executive": {
                    "description": "Executive communications",
                    "characteristics": {
                        "formality": 7,
                        "warmth": 5,
                        "directness": 8
                    }
                }
            }
        }))

        with patch('validate_personas.get_data_dir', return_value=tmp_path):
            with patch('validate_personas.PERSONA_REGISTRY_FILE', correct_file):
                result = check_persona_health()

        assert result['healthy'] is True
        assert 'wrong_filename' not in result.get('issues', {})


class TestSchemaValidation:
    """Issue #2: Validate characteristics schema."""

    def test_validate_persona_schema_rejects_list_characteristics(self):
        """Should reject characteristics as list (the RCA bug)."""
        from validate_personas import validate_persona_schema

        # BAD: characteristics as list
        bad_persona = {
            "description": "Test persona",
            "characteristics": ["concise", "direct", "warm"]  # WRONG
        }

        result = validate_persona_schema("TestPersona", bad_persona)

        assert result['valid'] is False
        # Check that at least one error mentions 'characteristics must be a dict'
        assert any('characteristics must be a dict' in err for err in result['errors'])

    def test_validate_persona_schema_rejects_missing_tone_vectors(self):
        """Should reject characteristics without required tone vectors."""
        from validate_personas import validate_persona_schema

        # BAD: dict but missing required fields
        bad_persona = {
            "description": "Test persona",
            "characteristics": {
                "typical_greeting": "Hey"
                # Missing: formality, warmth, directness
            }
        }

        result = validate_persona_schema("TestPersona", bad_persona)

        assert result['valid'] is False
        assert any('formality' in e for e in result['errors'])

    def test_validate_persona_schema_accepts_valid_characteristics(self):
        """Should accept properly formatted characteristics dict."""
        from validate_personas import validate_persona_schema

        # GOOD: dict with tone vectors
        good_persona = {
            "description": "Executive communications",
            "characteristics": {
                "formality": 7,
                "warmth": 5,
                "authority": 8,
                "directness": 8,
                "typical_greeting": "Team,",
                "typical_closing": "-JR",
                "uses_contractions": True
            }
        }

        result = validate_persona_schema("Executive", good_persona)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_persona_schema_warns_on_inferred_vectors(self):
        """Should warn if tone vectors appear to be inferred (all same value)."""
        from validate_personas import validate_persona_schema

        # SUSPICIOUS: all same values suggest inference, not analysis
        suspicious_persona = {
            "description": "Test persona",
            "characteristics": {
                "formality": 5,
                "warmth": 5,
                "authority": 5,
                "directness": 5
            }
        }

        result = validate_persona_schema("TestPersona", suspicious_persona)

        assert result['valid'] is True  # Still valid, but...
        assert len(result['warnings']) > 0
        assert any('all same value' in w.lower() or 'inferred' in w.lower() for w in result['warnings'])


class TestGeneratedReplyPreviews:
    """Issue #3: Generate reply previews for mismatches."""

    def test_generate_persona_reply_creates_sample(self):
        """Should generate a sample reply based on persona characteristics."""
        from validate_personas import generate_persona_reply

        persona = {
            "description": "Executive brief communications",
            "characteristics": {
                "formality": 3,
                "warmth": 5,
                "authority": 7,
                "directness": 8,
                "typical_greeting": "Hey",
                "typical_closing": "-JR",
                "uses_contractions": True,
                "tone": ["direct", "confident"]
            }
        }

        context = {
            "subject": "Q2 Update Request",
            "quoted_text": "Can you provide an update on Q2 priorities?"
        }

        reply = generate_persona_reply(persona, context)

        assert reply is not None
        assert isinstance(reply, str)
        assert len(reply) > 10  # Should have actual content

    def test_generate_persona_reply_reflects_characteristics(self):
        """Generated reply should reflect persona characteristics."""
        from validate_personas import generate_persona_reply

        # Formal persona
        formal_persona = {
            "description": "Formal executive communications",
            "characteristics": {
                "formality": 9,
                "warmth": 3,
                "authority": 8,
                "directness": 6,
                "typical_greeting": "Dear Team,",
                "typical_closing": "Best regards,",
                "uses_contractions": False
            }
        }

        context = {"subject": "Update", "quoted_text": "Status?"}

        reply = generate_persona_reply(formal_persona, context)

        # Should use formal greeting if provided
        assert "Dear" in reply or "Best regards" in reply or reply[0].isupper()

    def test_find_top_mismatches_includes_generated_replies(self):
        """Top mismatches should include generated reply previews."""
        from validate_personas import find_top_mismatches

        personas = {
            "Executive": {
                "description": "Executive communications",
                "characteristics": {
                    "formality": 7,
                    "warmth": 5,
                    "authority": 8,
                    "directness": 8,
                    "typical_greeting": "Team,",
                    "typical_closing": "-JR"
                }
            }
        }

        results = [
            {
                "pair_id": "email_001",
                "inferred_persona": "Executive",
                "composite_score": 0.3,  # Low score = mismatch
                "tone_scores": {"formality": 0.2},
                "structure_scores": {"greeting": 0.3},
                "ground_truth_summary": {
                    "greeting": "Hi there!",
                    "closing": "Cheers",
                    "reply_text": "Thanks for reaching out! Happy to help."
                },
                "context": {
                    "subject": "Question",
                    "quoted_text": "Can you help?"
                }
            }
        ]

        # Pass validation_pairs to get context for generation
        validation_pairs = [
            {
                "id": "email_001",
                "context": {"subject": "Question", "quoted_text": "Can you help?"},
                "ground_truth": {"reply_text": "Thanks for reaching out! Happy to help."}
            }
        ]

        mismatches = find_top_mismatches(results, personas, validation_pairs, limit=5)

        assert len(mismatches) > 0
        assert 'generated_reply' in mismatches[0]
        assert mismatches[0]['generated_reply'] is not None


class TestInteractiveValidation:
    """Issue #4: LLM-driven validation (non-interactive CLI)."""

    def test_review_validation_mode_exists(self):
        """Should have a review validation mode for LLM use."""
        from validate_personas import run_interactive_validation

        # Function should exist (now outputs data for LLM, no stdin)
        assert callable(run_interactive_validation)

    def test_format_mismatch_comparison_shows_both_replies(self):
        """Format function should show actual vs generated reply."""
        from validate_personas import format_mismatch_comparison

        mismatch = {
            "pair_id": "email_001",
            "inferred_persona": "Executive",
            "composite_score": 0.4,
            "ground_truth": {
                "reply_text": "Thanks for reaching out! Happy to help with this.",
                "greeting": "Hi!",
                "closing": "Cheers"
            },
            "generated_reply": "Team, Here's the update. -JR",
            "context": {
                "subject": "Question",
                "quoted_text": "Can you help with this?"
            }
        }

        output = format_mismatch_comparison(mismatch)

        # Should show both actual and generated
        assert "Actual" in output or "Ground Truth" in output
        assert "Generated" in output or "Persona Would Write" in output
        assert "Thanks for reaching out" in output  # actual
        assert "Team" in output or "-JR" in output  # generated (from persona)

    def test_feedback_cli_function_exists(self):
        """Should have CLI function to record feedback without stdin."""
        from validate_personas import record_feedback_cli

        # Function should exist
        assert callable(record_feedback_cli)

    def test_interactive_validator_collects_feedback(self):
        """InteractiveValidator should collect and process feedback."""
        from validate_personas import InteractiveValidator

        validator = InteractiveValidator()

        # Should have methods for feedback
        assert hasattr(validator, 'record_feedback')
        assert hasattr(validator, 'get_refinement_suggestions')

    def test_interactive_validator_tracks_does_this_sound_like_me(self):
        """Should track 'does this sound like me' responses."""
        from validate_personas import InteractiveValidator

        validator = InteractiveValidator()

        # Record some feedback
        validator.record_feedback(
            pair_id="email_001",
            persona="Executive",
            sounds_like_me=False,
            user_notes="I would never write this formally"
        )

        validator.record_feedback(
            pair_id="email_002",
            persona="Executive",
            sounds_like_me=True,
            user_notes=None
        )

        # Get suggestions based on feedback
        suggestions = validator.get_refinement_suggestions()

        # Should suggest adjustments based on feedback
        assert isinstance(suggestions, list)

    def test_show_suggestions_function_exists(self):
        """Should have function to show suggestions from accumulated feedback."""
        from validate_personas import show_suggestions

        assert callable(show_suggestions)


class TestFieldNameConsistency:
    """Issue #5: Consistent field naming."""

    def test_validation_pair_uses_consistent_id_field(self):
        """Validation pairs should use consistent 'id' field."""
        from validate_personas import normalize_validation_pair

        # Various input formats
        pair_with_id = {"id": "email_001", "context": {}}
        pair_with_pair_id = {"pair_id": "email_001", "context": {}}
        pair_with_email_id = {"email_id": "email_001", "context": {}}

        # All should normalize to 'id'
        assert normalize_validation_pair(pair_with_id)['id'] == "email_001"
        assert normalize_validation_pair(pair_with_pair_id)['id'] == "email_001"
        assert normalize_validation_pair(pair_with_email_id)['id'] == "email_001"

    def test_score_result_uses_consistent_id_field(self):
        """Score results should use consistent 'id' field."""
        from validate_personas import score_validation_pair

        pair = {
            "id": "test_email_001",
            "context": {"subject": "Test", "quoted_text": ""},
            "ground_truth": {
                "reply_text": "Test reply",
                "greeting": "Hi",
                "closing": "Thanks",
                "tone_hints": [],
                "has_contractions": True
            }
        }

        personas = {
            "Default": {
                "description": "Default persona",
                "characteristics": {
                    "formality": 5,
                    "warmth": 5,
                    "uses_contractions": True
                }
            }
        }

        result = score_validation_pair(pair, personas)

        # Result should have 'id' (not 'pair_id')
        assert 'id' in result
        assert result['id'] == "test_email_001"

    def test_mismatch_extraction_handles_all_id_formats(self):
        """Mismatch extraction should handle all ID field formats."""
        from validate_personas import extract_mismatch_details

        # Results might have 'pair_id' from old code
        result_with_pair_id = {
            "pair_id": "email_001",
            "composite_score": 0.3,
            "inferred_persona": "Executive"
        }

        # Pairs use 'id'
        pairs = [{"id": "email_001", "context": {}, "ground_truth": {"reply_text": "test"}}]

        details = extract_mismatch_details(result_with_pair_id, pairs)

        assert details is not None
        assert details['id'] == "email_001"


class TestLoadPersonasWithValidation:
    """Test that load_personas validates schema."""

    def test_load_personas_validates_on_load(self, tmp_path):
        """load_personas should validate schema and report issues."""
        from validate_personas import load_personas_with_validation

        # Create persona file with bad schema (list instead of dict)
        bad_personas = {
            "personas": {
                "Executive": {
                    "description": "Test",
                    "characteristics": ["concise", "direct"]  # WRONG
                }
            }
        }

        persona_file = tmp_path / "persona_registry.json"
        persona_file.write_text(json.dumps(bad_personas))

        with patch('validate_personas.PERSONA_REGISTRY_FILE', persona_file):
            personas, issues = load_personas_with_validation()

        # Should load but report issues
        assert len(issues) > 0
        assert any('Executive' in str(issue) for issue in issues)
        assert any('characteristics' in str(issue).lower() for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
