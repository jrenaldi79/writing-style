#!/usr/bin/env python3
"""
Tests for Email Persona Schema v2.0

TDD tests for the v2 email persona system including:
- Deterministic analysis (rhythm, formatting, patterns)
- Seniority detection
- Email type inference
- Schema validation
- Backward compatibility
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestRhythmAnalysis(unittest.TestCase):
    """Test rhythm analysis functions (sentence length, word counts, variance)."""

    def setUp(self):
        """Set up test email data."""
        self.sample_emails = [
            {
                "original_data": {
                    "body": "This is a short sentence. Here is another one that is a bit longer than the first. And a third."
                }
            },
            {
                "original_data": {
                    "body": "Quick update. The project is on track. We should finish by Friday."
                }
            },
            {
                "original_data": {
                    "body": "I wanted to follow up on our conversation from yesterday about the new feature requirements and timeline expectations."
                }
            }
        ]

    def test_analyze_rhythm_returns_dict(self):
        """analyze_rhythm should return a dictionary."""
        from email_analysis_v2 import analyze_rhythm
        result = analyze_rhythm(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_analyze_rhythm_has_avg_words_per_sentence(self):
        """Result should include avg_words_per_sentence."""
        from email_analysis_v2 import analyze_rhythm
        result = analyze_rhythm(self.sample_emails)
        self.assertIn("avg_words_per_sentence", result)
        self.assertIsInstance(result["avg_words_per_sentence"], (int, float))
        self.assertGreater(result["avg_words_per_sentence"], 0)

    def test_analyze_rhythm_has_sentence_length_distribution(self):
        """Result should include sentence_length_distribution with short/medium/long ratios."""
        from email_analysis_v2 import analyze_rhythm
        result = analyze_rhythm(self.sample_emails)
        self.assertIn("sentence_length_distribution", result)
        dist = result["sentence_length_distribution"]
        self.assertIn("lt_8_words_ratio", dist)
        self.assertIn("8_to_20_words_ratio", dist)
        self.assertIn("gt_20_words_ratio", dist)
        # Ratios should sum to approximately 1.0
        total = dist["lt_8_words_ratio"] + dist["8_to_20_words_ratio"] + dist["gt_20_words_ratio"]
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_analyze_rhythm_has_paragraphing(self):
        """Result should include paragraphing metrics."""
        from email_analysis_v2 import analyze_rhythm
        result = analyze_rhythm(self.sample_emails)
        self.assertIn("paragraphing", result)
        para = result["paragraphing"]
        self.assertIn("avg_sentences_per_paragraph", para)

    def test_analyze_rhythm_handles_empty_input(self):
        """analyze_rhythm should handle empty email list gracefully."""
        from email_analysis_v2 import analyze_rhythm
        result = analyze_rhythm([])
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("avg_words_per_sentence", 0), 0)


class TestFormattingDetection(unittest.TestCase):
    """Test formatting detection (bullets, numbering, bold/italic)."""

    def setUp(self):
        """Set up test email data with various formatting."""
        self.emails_with_bullets = [
            {"original_data": {"body": "Here are the updates:\n- Item one\n- Item two\n- Item three"}},
            {"original_data": {"body": "Action items:\n* First task\n* Second task"}},
        ]
        self.emails_with_numbers = [
            {"original_data": {"body": "Steps:\n1. Do this first\n2. Then do this\n3. Finally this"}},
        ]
        self.emails_plain = [
            {"original_data": {"body": "Just a simple email with no special formatting at all."}},
        ]

    def test_analyze_formatting_returns_dict(self):
        """analyze_formatting should return a dictionary."""
        from email_analysis_v2 import analyze_formatting
        result = analyze_formatting(self.emails_with_bullets)
        self.assertIsInstance(result, dict)

    def test_analyze_formatting_detects_bullets(self):
        """Should detect bullet usage rate."""
        from email_analysis_v2 import analyze_formatting
        result = analyze_formatting(self.emails_with_bullets)
        self.assertIn("uses_bullets_rate", result)
        self.assertGreater(result["uses_bullets_rate"], 0)

    def test_analyze_formatting_detects_numbering(self):
        """Should detect numbered list usage rate."""
        from email_analysis_v2 import analyze_formatting
        result = analyze_formatting(self.emails_with_numbers)
        self.assertIn("uses_numbering_rate", result)
        self.assertGreater(result["uses_numbering_rate"], 0)

    def test_analyze_formatting_zero_for_plain_text(self):
        """Should return 0 rates for plain text emails."""
        from email_analysis_v2 import analyze_formatting
        result = analyze_formatting(self.emails_plain)
        self.assertEqual(result.get("uses_bullets_rate", 1), 0)
        self.assertEqual(result.get("uses_numbering_rate", 1), 0)

    def test_analyze_formatting_has_paragraph_metrics(self):
        """Should include paragraph count metrics."""
        from email_analysis_v2 import analyze_formatting
        result = analyze_formatting(self.emails_with_bullets)
        self.assertIn("avg_paragraphs_per_email", result)


class TestGreetingClosingExtraction(unittest.TestCase):
    """Test greeting and closing pattern extraction."""

    def setUp(self):
        """Set up test email data with various greetings/closings."""
        self.sample_emails = [
            {"original_data": {"body": "Hi John,\n\nHere is the update.\n\nBest,\nSarah"}},
            {"original_data": {"body": "Hey team,\n\nQuick note.\n\nThanks,\nMike"}},
            {"original_data": {"body": "Hi John,\n\nAnother email.\n\nBest,\nSarah"}},
            {"original_data": {"body": "Hello,\n\nFormal email.\n\nRegards,\nBob"}},
        ]

    def test_extract_greeting_distribution_returns_dict(self):
        """extract_greeting_distribution should return a dictionary."""
        from email_analysis_v2 import extract_greeting_distribution
        result = extract_greeting_distribution(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_extract_greeting_distribution_has_distribution(self):
        """Result should include greeting distribution."""
        from email_analysis_v2 import extract_greeting_distribution
        result = extract_greeting_distribution(self.sample_emails)
        self.assertIn("distribution", result)
        self.assertIsInstance(result["distribution"], dict)
        # Should detect "Hi {name}," pattern
        total = sum(result["distribution"].values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_extract_greeting_distribution_has_primary_style(self):
        """Result should identify primary greeting style."""
        from email_analysis_v2 import extract_greeting_distribution
        result = extract_greeting_distribution(self.sample_emails)
        self.assertIn("primary_style", result)

    def test_extract_closing_distribution_returns_dict(self):
        """extract_closing_distribution should return a dictionary."""
        from email_analysis_v2 import extract_closing_distribution
        result = extract_closing_distribution(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_extract_closing_distribution_has_distribution(self):
        """Result should include sign-off distribution."""
        from email_analysis_v2 import extract_closing_distribution
        result = extract_closing_distribution(self.sample_emails)
        self.assertIn("distribution", result)
        self.assertIsInstance(result["distribution"], dict)

    def test_extract_closing_distribution_detects_signature_block(self):
        """Result should indicate if signature block is used."""
        from email_analysis_v2 import extract_closing_distribution
        result = extract_closing_distribution(self.sample_emails)
        self.assertIn("uses_signature_block", result)
        self.assertIsInstance(result["uses_signature_block"], bool)


class TestSubjectLinePatterns(unittest.TestCase):
    """Test subject line pattern analysis."""

    def setUp(self):
        """Set up test email data with various subjects."""
        self.sample_emails = [
            {"original_data": {"subject": "Quick update on the project"}},
            {"original_data": {"subject": "Re: Meeting tomorrow"}},
            {"original_data": {"subject": "FYI: New policy changes"}},
            {"original_data": {"subject": "[ACTION REQUIRED] Budget approval needed"}},
            {"original_data": {"subject": "Weekly Status Report"}},
        ]

    def test_analyze_subject_lines_returns_dict(self):
        """analyze_subject_lines should return a dictionary."""
        from email_analysis_v2 import analyze_subject_lines
        result = analyze_subject_lines(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_analyze_subject_lines_has_length_range(self):
        """Result should include length_chars_range."""
        from email_analysis_v2 import analyze_subject_lines
        result = analyze_subject_lines(self.sample_emails)
        self.assertIn("length_chars_range", result)
        self.assertIsInstance(result["length_chars_range"], list)
        self.assertEqual(len(result["length_chars_range"]), 2)
        # Min should be <= max
        self.assertLessEqual(result["length_chars_range"][0], result["length_chars_range"][1])

    def test_analyze_subject_lines_has_casing_distribution(self):
        """Result should include casing_distribution."""
        from email_analysis_v2 import analyze_subject_lines
        result = analyze_subject_lines(self.sample_emails)
        self.assertIn("casing_distribution", result)
        dist = result["casing_distribution"]
        self.assertIn("title_case", dist)
        self.assertIn("sentence_case", dist)

    def test_analyze_subject_lines_detects_prefixes(self):
        """Result should detect common prefixes like Re:, FYI:."""
        from email_analysis_v2 import analyze_subject_lines
        result = analyze_subject_lines(self.sample_emails)
        self.assertIn("common_prefixes", result)
        self.assertIsInstance(result["common_prefixes"], list)

    def test_analyze_subject_lines_detects_brackets(self):
        """Result should detect bracket usage rate."""
        from email_analysis_v2 import analyze_subject_lines
        result = analyze_subject_lines(self.sample_emails)
        self.assertIn("uses_brackets_rate", result)
        self.assertGreater(result["uses_brackets_rate"], 0)  # We have one bracketed subject


class TestMechanicsAnalysis(unittest.TestCase):
    """Test punctuation and mechanics analysis."""

    def setUp(self):
        """Set up test email data with various punctuation patterns."""
        self.sample_emails = [
            {"original_data": {"body": "I'll send it over. We're on track -- should be done soon!"}},
            {"original_data": {"body": "Don't forget to check the report. It's important."}},
            {"original_data": {"body": "Can you review this? Let me know if you have questions."}},
        ]

    def test_analyze_mechanics_returns_dict(self):
        """analyze_mechanics should return a dictionary."""
        from email_analysis_v2 import analyze_mechanics
        result = analyze_mechanics(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_analyze_mechanics_detects_contractions(self):
        """Should detect contraction usage."""
        from email_analysis_v2 import analyze_mechanics
        result = analyze_mechanics(self.sample_emails)
        self.assertIn("uses_contractions", result)
        self.assertTrue(result["uses_contractions"])
        self.assertIn("contraction_rate", result)
        self.assertGreater(result["contraction_rate"], 0)

    def test_analyze_mechanics_detects_em_dash(self):
        """Should detect em-dash usage."""
        from email_analysis_v2 import analyze_mechanics
        result = analyze_mechanics(self.sample_emails)
        self.assertIn("uses_em_dash", result)
        self.assertTrue(result["uses_em_dash"])

    def test_analyze_mechanics_has_exclamation_rate(self):
        """Should include exclamation rate."""
        from email_analysis_v2 import analyze_mechanics
        result = analyze_mechanics(self.sample_emails)
        self.assertIn("exclamation_rate", result)
        self.assertGreater(result["exclamation_rate"], 0)

    def test_analyze_mechanics_has_question_rate(self):
        """Should include question rate."""
        from email_analysis_v2 import analyze_mechanics
        result = analyze_mechanics(self.sample_emails)
        self.assertIn("question_rate", result)
        self.assertGreater(result["question_rate"], 0)


class TestSeniorityDetection(unittest.TestCase):
    """Test recipient seniority/role detection."""

    def setUp(self):
        """Set up test email data with various recipient patterns."""
        self.executive_email = {
            "original_data": {
                "to": "john.smith@company.com",
                "body": "Hi John,\n\nI wanted to check with you on the budget approval.\n\nBest,\nSarah"
            },
            "enrichment": {
                "recipient_signatures": ["John Smith, CEO"]
            }
        }
        self.peer_email = {
            "original_data": {
                "to": "jane.doe@company.com",
                "from": "me@company.com",
                "body": "Hey Jane,\n\nQuick sync on the project?\n\nThanks,\nMe"
            },
            "enrichment": {}
        }
        self.external_email = {
            "original_data": {
                "to": "client@external.com",
                "from": "me@company.com",
                "body": "Dear Mr. Johnson,\n\nThank you for your inquiry.\n\nBest regards,\nSarah"
            },
            "enrichment": {
                "audience": "external"
            }
        }

    def test_detect_recipient_seniority_returns_string(self):
        """detect_recipient_seniority should return a string."""
        from email_analysis_v2 import detect_recipient_seniority
        result = detect_recipient_seniority(self.executive_email)
        self.assertIsInstance(result, str)

    def test_detect_recipient_seniority_detects_executive(self):
        """Should detect executive recipients from title patterns."""
        from email_analysis_v2 import detect_recipient_seniority
        result = detect_recipient_seniority(self.executive_email)
        self.assertEqual(result, "executive")

    def test_detect_recipient_seniority_detects_external(self):
        """Should detect external clients from domain/audience."""
        from email_analysis_v2 import detect_recipient_seniority
        result = detect_recipient_seniority(self.external_email)
        self.assertIn(result, ["external_client", "external"])

    def test_detect_recipient_seniority_valid_values(self):
        """Should return one of the valid seniority values."""
        from email_analysis_v2 import detect_recipient_seniority
        valid_values = ["executive", "peer", "report", "external_client", "candidate", "unknown"]
        for email in [self.executive_email, self.peer_email, self.external_email]:
            result = detect_recipient_seniority(email)
            self.assertIn(result, valid_values)


class TestEmailTypeInference(unittest.TestCase):
    """Test email type inference from cluster patterns."""

    def setUp(self):
        """Set up test cluster data."""
        self.status_update_cluster = {
            "id": 1,
            "enrichment_summary": {
                "recipient_types": {"team": 0.8, "individual": 0.2},
                "audiences": {"internal": 1.0}
            }
        }
        self.status_update_emails = [
            {"original_data": {
                "subject": "Weekly Status Update",
                "body": "Team,\n\nHere's this week's update:\n- Completed X\n- In progress Y\n- Blocked on Z\n\nBest,\nMe"
            }},
            {"original_data": {
                "subject": "Project Status",
                "body": "Update on the project:\n\n1. Done\n2. Pending\n\nNext steps..."
            }},
        ]
        self.outreach_cluster = {
            "id": 2,
            "enrichment_summary": {
                "recipient_types": {"individual": 1.0},
                "audiences": {"external": 0.8}
            }
        }
        self.outreach_emails = [
            {"original_data": {
                "subject": "Introduction from Company X",
                "body": "Hi,\n\nI came across your profile and wanted to reach out..."
            }},
        ]

    def test_infer_email_types_returns_dict(self):
        """infer_email_types should return a dictionary."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.status_update_cluster, self.status_update_emails)
        self.assertIsInstance(result, dict)

    def test_infer_email_types_has_detected_type(self):
        """Result should include detected_type."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.status_update_cluster, self.status_update_emails)
        self.assertIn("detected_type", result)
        self.assertIsInstance(result["detected_type"], str)

    def test_infer_email_types_has_confidence(self):
        """Result should include confidence score."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.status_update_cluster, self.status_update_emails)
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)

    def test_infer_email_types_has_required_elements(self):
        """Result should include required_elements list."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.status_update_cluster, self.status_update_emails)
        self.assertIn("required_elements", result)
        self.assertIsInstance(result["required_elements"], list)

    def test_infer_status_update_type(self):
        """Should detect status update type from cluster patterns."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.status_update_cluster, self.status_update_emails)
        self.assertIn("status", result["detected_type"].lower())

    def test_infer_outreach_type(self):
        """Should detect outreach type from cluster patterns."""
        from email_analysis_v2 import infer_email_types
        result = infer_email_types(self.outreach_cluster, self.outreach_emails)
        self.assertIn(result["detected_type"].lower(), ["cold_outreach", "outreach", "introduction"])


class TestV2SchemaValidation(unittest.TestCase):
    """Test v2 schema structure validation."""

    def test_v2_schema_required_sections(self):
        """V2 schema should have all required top-level sections."""
        from email_analysis_v2 import get_v2_schema_template
        schema = get_v2_schema_template()
        required_sections = [
            "schema_version",
            "voice_fingerprint",
            "cognitive_load_preferences",
            "subject_line_dna",
            "opening_dna",
            "body_dna",
            "cta_dna",
            "closing_dna",
            "guardrails",
            "variation_controls",
            "example_bank",
            "evaluation_rubric"
        ]
        for section in required_sections:
            self.assertIn(section, schema, f"Missing required section: {section}")

    def test_v2_voice_fingerprint_structure(self):
        """voice_fingerprint should have correct sub-structure."""
        from email_analysis_v2 import get_v2_schema_template
        schema = get_v2_schema_template()
        vf = schema["voice_fingerprint"]
        required_keys = ["formality", "rhythm", "mechanics", "lexicon", "tone_markers", "credibility_markers"]
        for key in required_keys:
            self.assertIn(key, vf, f"Missing voice_fingerprint key: {key}")

    def test_v2_tone_markers_have_instruction(self):
        """Tone markers should have level and instruction fields."""
        from email_analysis_v2 import get_v2_schema_template
        schema = get_v2_schema_template()
        tone_markers = schema["voice_fingerprint"]["tone_markers"]
        for marker in ["warmth", "authority", "directness"]:
            self.assertIn(marker, tone_markers)
            self.assertIn("level", tone_markers[marker])
            self.assertIn("instruction", tone_markers[marker])


class TestComputeDeterministicMetrics(unittest.TestCase):
    """Test the master compute_deterministic_metrics function."""

    def setUp(self):
        """Set up comprehensive test email data."""
        self.sample_emails = [
            {
                "original_data": {
                    "subject": "Quick update on project",
                    "body": "Hi Team,\n\nHere's the update:\n- Item 1\n- Item 2\n\nBest,\nJohn"
                }
            },
            {
                "original_data": {
                    "subject": "Re: Meeting tomorrow",
                    "body": "Hey Sarah,\n\nSounds good. I'll be there.\n\nThanks,\nMike"
                }
            }
        ]

    def test_compute_deterministic_metrics_returns_dict(self):
        """compute_deterministic_metrics should return a dictionary."""
        from email_analysis_v2 import compute_deterministic_metrics
        result = compute_deterministic_metrics(self.sample_emails)
        self.assertIsInstance(result, dict)

    def test_compute_deterministic_metrics_has_all_sections(self):
        """Result should include all deterministic sections."""
        from email_analysis_v2 import compute_deterministic_metrics
        result = compute_deterministic_metrics(self.sample_emails)
        expected_keys = [
            "rhythm",
            "formatting",
            "greeting_distribution",
            "closing_distribution",
            "subject_line_patterns",
            "mechanics"
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing section: {key}")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with v1 batches."""

    def setUp(self):
        """Set up v1 format persona data."""
        self.v1_persona = {
            "name": "Executive Brief",
            "description": "Short updates to leadership",
            "characteristics": {
                "formality": 6,
                "warmth": 5,
                "authority": 8,
                "directness": 8,
                "tone": ["direct", "confident"],
                "typical_greeting": "Team,",
                "typical_closing": "-John",
                "uses_contractions": True,
                "uses_bullets": True
            }
        }
        self.v1_batch = {
            "batch_id": "batch_001",
            "new_personas": [self.v1_persona],
            "samples": []
        }

    def test_detect_schema_version_v1(self):
        """Should detect v1 schema from batch without schema_version."""
        from email_analysis_v2 import detect_schema_version
        result = detect_schema_version(self.v1_batch)
        self.assertEqual(result, "1.0")

    def test_detect_schema_version_v2(self):
        """Should detect v2 schema from batch with schema_version."""
        from email_analysis_v2 import detect_schema_version
        v2_batch = {"schema_version": "2.0", "new_personas": []}
        result = detect_schema_version(v2_batch)
        self.assertEqual(result, "2.0")

    def test_migrate_v1_to_v2_returns_dict(self):
        """migrate_v1_to_v2 should return a dictionary."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        self.assertIsInstance(result, dict)

    def test_migrate_v1_to_v2_has_schema_version(self):
        """Migrated persona should have schema_version 2.0."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        self.assertEqual(result.get("schema_version"), "2.0")

    def test_migrate_v1_to_v2_preserves_name(self):
        """Migrated persona should preserve name."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        self.assertEqual(result.get("name"), "Executive Brief")

    def test_migrate_v1_to_v2_has_voice_fingerprint(self):
        """Migrated persona should have voice_fingerprint structure."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        self.assertIn("voice_fingerprint", result)
        vf = result["voice_fingerprint"]
        # Should map old formality to new structure
        self.assertIn("formality", vf)
        self.assertEqual(vf["formality"].get("level"), 6)

    def test_migrate_v1_to_v2_maps_tone_markers(self):
        """Migrated persona should map old tone scores to tone_markers."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        tone_markers = result["voice_fingerprint"]["tone_markers"]
        self.assertEqual(tone_markers["warmth"]["level"], 5)
        self.assertEqual(tone_markers["authority"]["level"], 8)
        self.assertEqual(tone_markers["directness"]["level"], 8)

    def test_migrate_v1_to_v2_has_placeholder_guardrails(self):
        """Migrated persona should have placeholder guardrails."""
        from email_analysis_v2 import migrate_v1_to_v2
        result = migrate_v1_to_v2(self.v1_persona)
        self.assertIn("guardrails", result)
        self.assertIn("never_do", result["guardrails"])


class TestExampleBankSelection(unittest.TestCase):
    """Test example bank selection based on confidence scores."""

    def setUp(self):
        """Set up sample data with confidence scores."""
        self.samples = [
            {"id": "email_001", "confidence": 0.95, "content": {"subject": "Test 1", "body": "Body 1"}},
            {"id": "email_002", "confidence": 0.75, "content": {"subject": "Test 2", "body": "Body 2"}},
            {"id": "email_003", "confidence": 0.90, "content": {"subject": "Test 3", "body": "Body 3"}},
            {"id": "email_004", "confidence": 0.60, "content": {"subject": "Test 4", "body": "Body 4"}},
            {"id": "email_005", "confidence": 0.88, "content": {"subject": "Test 5", "body": "Body 5"}},
            {"id": "email_006", "confidence": 0.92, "content": {"subject": "Test 6", "body": "Body 6"}},
        ]

    def test_select_example_bank_returns_list(self):
        """select_example_bank should return a list."""
        from email_analysis_v2 import select_example_bank
        result = select_example_bank(self.samples)
        self.assertIsInstance(result, list)

    def test_select_example_bank_respects_limit(self):
        """Should respect the limit parameter."""
        from email_analysis_v2 import select_example_bank
        result = select_example_bank(self.samples, limit=3)
        self.assertEqual(len(result), 3)

    def test_select_example_bank_selects_high_confidence(self):
        """Should select highest confidence samples."""
        from email_analysis_v2 import select_example_bank
        result = select_example_bank(self.samples, limit=3)
        # Top 3 by confidence should be 0.95, 0.92, 0.90
        confidences = [s["confidence"] for s in result]
        self.assertIn(0.95, confidences)
        self.assertIn(0.92, confidences)
        self.assertIn(0.90, confidences)

    def test_select_example_bank_filters_low_confidence(self):
        """Should filter out samples below 0.85 threshold by default."""
        from email_analysis_v2 import select_example_bank
        result = select_example_bank(self.samples, limit=10, min_confidence=0.85)
        for sample in result:
            self.assertGreaterEqual(sample["confidence"], 0.85)


if __name__ == "__main__":
    unittest.main()
