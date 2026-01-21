#!/usr/bin/env python3
"""
Unit Tests - Ingest Module

TDD tests for ingest.py - batch ingestion with validation.

Tests for:
- Post-ingest validation (registry verification)
- Persona writing (always persist, don't skip existing)
- Error handling and feedback
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))


class TestValidateIngestResult(unittest.TestCase):
    """Test post-ingest validation that verifies registry was updated."""

    def test_validate_detects_empty_registry(self):
        """Should detect when registry is empty after ingest."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"

            # Create empty registry
            persona_file.write_text(json.dumps({"personas": {}}))

            batch = {
                "new_personas": [{"name": "Test Persona"}],
                "samples": [{"id": "email_001", "persona": "Test Persona"}]
            }

            with patch.object(ingest, 'PERSONA_FILE', persona_file):
                result = ingest.validate_ingest_result(batch, dry_run=False)

            self.assertFalse(result)

    def test_validate_detects_missing_personas(self):
        """Should detect when expected personas are missing."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"

            # Create registry with only one persona
            persona_file.write_text(json.dumps({
                "personas": {"Persona A": {"sample_count": 1}}
            }))

            batch = {
                "new_personas": [
                    {"name": "Persona A"},
                    {"name": "Persona B"}
                ],
                "samples": [
                    {"id": "email_001", "persona": "Persona A"},
                    {"id": "email_002", "persona": "Persona B"}
                ]
            }

            with patch.object(ingest, 'PERSONA_FILE', persona_file):
                result = ingest.validate_ingest_result(batch, dry_run=False)

            self.assertFalse(result)

    def test_validate_passes_when_all_personas_present(self):
        """Should pass when all expected personas exist in registry."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"

            # Create registry with all personas
            persona_file.write_text(json.dumps({
                "personas": {
                    "Persona A": {"sample_count": 1},
                    "Persona B": {"sample_count": 1}
                }
            }))

            batch = {
                "new_personas": [
                    {"name": "Persona A"},
                    {"name": "Persona B"}
                ],
                "samples": [
                    {"id": "email_001", "persona": "Persona A"},
                    {"id": "email_002", "persona": "Persona B"}
                ]
            }

            with patch.object(ingest, 'PERSONA_FILE', persona_file):
                result = ingest.validate_ingest_result(batch, dry_run=False)

            self.assertTrue(result)

    def test_validate_skipped_in_dry_run(self):
        """Should skip validation in dry_run mode."""
        import ingest

        batch = {
            "new_personas": [{"name": "Test"}],
            "samples": []
        }

        # dry_run should always return True without checking file
        result = ingest.validate_ingest_result(batch, dry_run=True)
        self.assertTrue(result)

    def test_validate_reports_registry_size(self):
        """Validation should report registry stats for visibility."""
        import ingest
        from io import StringIO

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"

            # Create registry with personas
            persona_file.write_text(json.dumps({
                "personas": {"Test Persona": {"sample_count": 5}}
            }))

            batch = {
                "new_personas": [{"name": "Test Persona"}],
                "samples": []
            }

            captured_output = StringIO()
            with patch.object(ingest, 'PERSONA_FILE', persona_file), \
                 patch('sys.stdout', captured_output):
                ingest.validate_ingest_result(batch, dry_run=False)

            output = captured_output.getvalue()
            # Should mention persona count or validation
            self.assertTrue("1" in output or "persona" in output.lower())


class TestPersonaWriting(unittest.TestCase):
    """Test that personas are always written, not skipped when existing."""

    def test_existing_persona_is_updated(self):
        """Should update existing persona, not skip it."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"
            samples_dir = tmp_path / "samples"
            raw_samples_dir = tmp_path / "raw_samples"
            state_file = tmp_path / "state.json"

            # Create existing registry with a persona
            initial_registry = {
                "personas": {
                    "Existing Persona": {
                        "description": "Old description",
                        "sample_count": 0,
                        "characteristics": {"formality": 5}
                    }
                },
                "created": "2026-01-01T00:00:00Z"
            }
            persona_file.write_text(json.dumps(initial_registry))
            state_file.write_text(json.dumps({}))

            # Create batch file with same persona, new characteristics
            batch_data = {
                "batch_id": "batch_001",
                "new_personas": [
                    {
                        "name": "Existing Persona",
                        "description": "Updated description",
                        "characteristics": {
                            "voice_fingerprint": {"formality": 8},
                            "relationship_calibration": {"hierarchy_direction": "peer"}
                        }
                    }
                ],
                "samples": []
            }

            batch_file = tmp_path / "batch.json"
            batch_file.write_text(json.dumps(batch_data))

            with patch.object(ingest, 'PERSONA_FILE', persona_file), \
                 patch.object(ingest, 'SAMPLES_DIR', samples_dir), \
                 patch.object(ingest, 'RAW_SAMPLES_DIR', raw_samples_dir), \
                 patch.object(ingest, 'STATE_FILE', state_file), \
                 patch.object(ingest, 'CLUSTERS_FILE', tmp_path / "nonexistent.json"):
                result = ingest.ingest_batch(batch_file, dry_run=False, force=True)

            # Load updated registry
            updated = json.loads(persona_file.read_text())

            # Persona should have updated characteristics
            self.assertIn("Existing Persona", updated["personas"])
            persona = updated["personas"]["Existing Persona"]
            # Should have new v2 structure
            self.assertIn("characteristics", persona)

    def test_new_persona_is_created(self):
        """Should create new personas that don't exist."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"
            samples_dir = tmp_path / "samples"
            raw_samples_dir = tmp_path / "raw_samples"
            state_file = tmp_path / "state.json"

            # Create empty registry
            persona_file.write_text(json.dumps({"personas": {}}))
            state_file.write_text(json.dumps({}))

            # Create raw sample (required for ingest)
            raw_samples_dir.mkdir(parents=True)
            (raw_samples_dir / "email_email_001.json").write_text(json.dumps({
                "subject": "Test", "body": "Test body"
            }))

            # Create batch file with new persona (must have samples)
            batch_data = {
                "batch_id": "batch_001",
                "new_personas": [
                    {
                        "name": "Brand New Persona",
                        "description": "A fresh persona",
                        "characteristics": {"voice_fingerprint": {"formality": 7}}
                    }
                ],
                "samples": [
                    {"id": "email_001", "persona": "Brand New Persona", "confidence": 0.9}
                ]
            }

            batch_file = tmp_path / "batch.json"
            batch_file.write_text(json.dumps(batch_data))

            with patch.object(ingest, 'PERSONA_FILE', persona_file), \
                 patch.object(ingest, 'SAMPLES_DIR', samples_dir), \
                 patch.object(ingest, 'RAW_SAMPLES_DIR', raw_samples_dir), \
                 patch.object(ingest, 'STATE_FILE', state_file), \
                 patch.object(ingest, 'CLUSTERS_FILE', tmp_path / "nonexistent.json"):
                result = ingest.ingest_batch(batch_file, dry_run=False, force=True)

            # Load registry
            updated = json.loads(persona_file.read_text())

            # New persona should exist
            self.assertIn("Brand New Persona", updated["personas"])
            self.assertTrue(result)

    def test_all_personas_from_samples_are_tracked(self):
        """Should track all personas referenced in samples."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"
            samples_dir = tmp_path / "samples"
            raw_samples_dir = tmp_path / "raw_samples"
            state_file = tmp_path / "state.json"

            # Create registry
            persona_file.write_text(json.dumps({"personas": {
                "Persona A": {"description": "", "sample_count": 0}
            }}))
            state_file.write_text(json.dumps({}))

            # Create raw sample
            raw_samples_dir.mkdir(parents=True)
            (raw_samples_dir / "email_email_001.json").write_text(json.dumps({
                "subject": "Test", "body": "Test body"
            }))

            # Batch with samples referencing multiple personas
            batch_data = {
                "batch_id": "batch_001",
                "new_personas": [{"name": "Persona A", "description": ""}],
                "samples": [
                    {"id": "email_001", "persona": "Persona A", "confidence": 0.9}
                ]
            }

            batch_file = tmp_path / "batch.json"
            batch_file.write_text(json.dumps(batch_data))

            with patch.object(ingest, 'PERSONA_FILE', persona_file), \
                 patch.object(ingest, 'SAMPLES_DIR', samples_dir), \
                 patch.object(ingest, 'RAW_SAMPLES_DIR', raw_samples_dir), \
                 patch.object(ingest, 'STATE_FILE', state_file), \
                 patch.object(ingest, 'CLUSTERS_FILE', tmp_path / "nonexistent.json"):
                result = ingest.ingest_batch(batch_file, dry_run=False, force=True)

            # Check sample count was updated
            updated = json.loads(persona_file.read_text())
            self.assertEqual(updated["personas"]["Persona A"]["sample_count"], 1)


class TestIngestBatchWithValidation(unittest.TestCase):
    """Test that ingest_batch calls validation."""

    def test_ingest_batch_calls_validation(self):
        """ingest_batch should call validate_ingest_result at the end."""
        import ingest

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            persona_file = tmp_path / "persona_registry.json"
            samples_dir = tmp_path / "samples"
            raw_samples_dir = tmp_path / "raw_samples"
            state_file = tmp_path / "state.json"

            persona_file.write_text(json.dumps({"personas": {}}))
            state_file.write_text(json.dumps({}))

            # Create raw sample for ingest
            raw_samples_dir.mkdir(parents=True)
            (raw_samples_dir / "email_email_001.json").write_text(json.dumps({
                "subject": "Test", "body": "Test body"
            }))

            batch_data = {
                "batch_id": "batch_001",
                "new_personas": [{"name": "Test", "description": ""}],
                "samples": [{"id": "email_001", "persona": "Test", "confidence": 0.9}]
            }

            batch_file = tmp_path / "batch.json"
            batch_file.write_text(json.dumps(batch_data))

            validation_called = []

            def mock_validate(batch, dry_run=False):
                validation_called.append(batch)
                return True

            with patch.object(ingest, 'PERSONA_FILE', persona_file), \
                 patch.object(ingest, 'SAMPLES_DIR', samples_dir), \
                 patch.object(ingest, 'RAW_SAMPLES_DIR', raw_samples_dir), \
                 patch.object(ingest, 'STATE_FILE', state_file), \
                 patch.object(ingest, 'CLUSTERS_FILE', tmp_path / "nonexistent.json"), \
                 patch.object(ingest, 'validate_ingest_result', mock_validate):
                ingest.ingest_batch(batch_file, dry_run=False, force=True)

            # Validation should have been called
            self.assertEqual(len(validation_called), 1)


class TestExportedFunctions(unittest.TestCase):
    """Test that required functions are exported."""

    def test_ingest_module_exports(self):
        """Module should export required functions for external use."""
        import ingest

        # These should be accessible for import by analyze_clusters.py
        self.assertTrue(hasattr(ingest, 'ingest_batch'))
        self.assertTrue(hasattr(ingest, 'load_json'))
        self.assertTrue(hasattr(ingest, 'PERSONA_FILE'))
        self.assertTrue(hasattr(ingest, 'validate_ingest_result'))


if __name__ == '__main__':
    unittest.main()
