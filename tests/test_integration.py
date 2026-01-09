#!/usr/bin/env python3
"""
Integration Tests - End-to-end workflow testing
"""

import sys
import unittest
import tempfile
import json
import shutil
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

from test_fixtures import get_sample_email, get_all_valid_samples

import filter_emails
import enrich_emails


class TestFilterEnrichPipeline(unittest.TestCase):
    """Test the filter → enrich pipeline."""
    
    def test_filter_then_enrich(self):
        """Filtered email should be enrichable."""
        # Get valid email
        email = get_sample_email("executive_brief")
        
        # Filter
        should_include, reason, quality = filter_emails.filter_email(email)
        self.assertTrue(should_include)
        
        # Create filtered sample
        filtered_data = {
            "id": email["id"],
            "original_data": email,
            "quality": quality
        }
        
        # Enrich
        enriched = enrich_emails.enrich_email(filtered_data, "example.com")
        
        # Verify enrichment structure
        self.assertIn("enrichment", enriched)
        self.assertIn("quality", enriched)
        self.assertIn("original_data", enriched)
        
        # Verify enrichment fields
        e = enriched["enrichment"]
        self.assertIn("recipient_type", e)
        self.assertIn("audience", e)
        self.assertIn("thread_position", e)
    
    def test_invalid_emails_not_enriched(self):
        """Invalid emails should be filtered before enrichment."""
        invalid_types = ["forward", "auto_reply", "too_short", "mass_email"]
        
        for email_type in invalid_types:
            email = get_sample_email(email_type)
            should_include, reason, quality = filter_emails.filter_email(email)
            
            self.assertFalse(should_include, 
                           f"{email_type} should be filtered out")
    
    def test_all_valid_samples_through_pipeline(self):
        """All valid samples should pass through filter → enrich."""
        for email in get_all_valid_samples():
            # Filter
            should_include, reason, quality = filter_emails.filter_email(email)
            self.assertTrue(should_include, f"Email {email['id']} failed filter: {reason}")
            
            # Create filtered
            filtered_data = {
                "id": email["id"],
                "original_data": email,
                "quality": quality
            }
            
            # Enrich
            enriched = enrich_emails.enrich_email(filtered_data, "example.com")
            
            # Verify complete
            self.assertIn("enrichment", enriched)
            self.assertGreater(len(enriched["enrichment"]), 0)


class TestBatchWorkflow(unittest.TestCase):
    """Test batch analysis workflow."""
    
    def test_batch_json_structure(self):
        """Batch JSON should follow schema."""
        # Simulate agent output
        batch = {
            "batch_id": "batch_test_001",
            "analyzed_at": "2025-01-07T12:00:00Z",
            "email_count": 2,
            "calibration_referenced": True,
            "calibration_notes": "Anchored against provided examples",
            "new_personas": [
                {
                    "name": "Test Persona",
                    "description": "Test persona for unit testing",
                    "characteristics": {
                        "tone": ["direct"],
                        "formality": 6,
                        "warmth": 5,
                        "authority": 7,
                        "directness": 8
                    }
                }
            ],
            "samples": [
                {
                    "id": "exec_001",
                    "source": "email",
                    "persona": "Test Persona",
                    "confidence": 0.85,
                    "analysis": {
                        "tone_vectors": {
                            "formality": 6,
                            "warmth": 5,
                            "authority": 7,
                            "directness": 8
                        },
                        "greeting": "Team,",
                        "closing": "-John"
                    },
                    "context": {
                        "recipient_type": "team",
                        "audience": "internal",
                        "thread_position": "initiating"
                    }
                }
            ]
        }
        
        # Validate structure
        required_fields = ["batch_id", "calibration_referenced", "samples"]
        for field in required_fields:
            self.assertIn(field, batch, f"Missing required field: {field}")
        
        # Validate calibration
        self.assertTrue(batch["calibration_referenced"])
        self.assertIsNotNone(batch["calibration_notes"])
        
        # Validate samples
        self.assertGreater(len(batch["samples"]), 0)
        
        sample = batch["samples"][0]
        self.assertIn("tone_vectors", sample["analysis"])
        self.assertIn("context", sample)
        
        # Validate tone_vectors range (1-10)
        for dimension, score in sample["analysis"]["tone_vectors"].items():
            self.assertGreaterEqual(score, 1, f"{dimension} score too low")
            self.assertLessEqual(score, 10, f"{dimension} score too high")
        
        # Validate confidence range (0-1)
        self.assertGreaterEqual(sample["confidence"], 0.0)
        self.assertLessEqual(sample["confidence"], 1.0)
    
    def test_persona_consistency(self):
        """All samples assigned to a persona should have that persona's name."""
        batch = {
            "batch_id": "batch_test_002",
            "analyzed_at": "2025-01-07T12:00:00Z",
            "email_count": 2,
            "calibration_referenced": True,
            "calibration_notes": "Test",
            "new_personas": [
                {
                    "name": "Persona A",
                    "description": "Test",
                    "characteristics": {}
                }
            ],
            "samples": [
                {
                    "id": "test_001",
                    "source": "email",
                    "persona": "Persona A",
                    "confidence": 0.8,
                    "analysis": {"tone_vectors": {"formality": 5, "warmth": 5, "authority": 5, "directness": 5}},
                    "context": {"recipient_type": "individual", "audience": "external"}
                },
                {
                    "id": "test_002",
                    "source": "email",
                    "persona": "Persona A",
                    "confidence": 0.75,
                    "analysis": {"tone_vectors": {"formality": 5, "warmth": 5, "authority": 5, "directness": 5}},
                    "context": {"recipient_type": "individual", "audience": "external"}
                }
            ]
        }
        
        # All samples should reference existing persona
        persona_names = {p["name"] for p in batch["new_personas"]}
        
        for sample in batch["samples"]:
            self.assertIn(sample["persona"], persona_names,
                         f"Sample references unknown persona: {sample['persona']}")


class TestDataConsistency(unittest.TestCase):
    """Test data consistency across pipeline stages."""
    
    def test_email_id_preserved(self):
        """Email ID should be preserved through all stages."""
        email = get_sample_email("executive_brief")
        original_id = email["id"]
        
        # Through filtering
        should_include, reason, quality = filter_emails.filter_email(email)
        filtered_data = {
            "id": original_id,
            "original_data": email,
            "quality": quality
        }
        self.assertEqual(filtered_data["id"], original_id)
        
        # Through enrichment
        enriched = enrich_emails.enrich_email(filtered_data, "example.com")
        self.assertEqual(enriched["id"], original_id)
    
    def test_original_data_preserved(self):
        """Original email data should be preserved."""
        email = get_sample_email("executive_brief")
        
        # Filter
        should_include, reason, quality = filter_emails.filter_email(email)
        filtered_data = {
            "id": email["id"],
            "original_data": email,
            "quality": quality
        }
        
        # Enrich
        enriched = enrich_emails.enrich_email(filtered_data, "example.com")
        
        # Original data should be unchanged
        self.assertEqual(enriched["original_data"], email)
    
    def test_metadata_accumulates(self):
        """Metadata should accumulate through pipeline."""
        email = get_sample_email("executive_brief")
        
        # Filter adds quality
        should_include, reason, quality = filter_emails.filter_email(email)
        filtered_data = {
            "id": email["id"],
            "original_data": email,
            "quality": quality
        }
        
        # Enrich adds enrichment
        enriched = enrich_emails.enrich_email(filtered_data, "example.com")
        
        # Both should be present
        self.assertIn("quality", enriched)
        self.assertIn("enrichment", enriched)
        self.assertIn("original_data", enriched)


if __name__ == '__main__':
    unittest.main()
