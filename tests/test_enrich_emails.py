#!/usr/bin/env python3
"""
Unit Tests - Email Enrichment
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

from test_fixtures import get_sample_email, create_filtered_sample

# Import functions to test
import enrich_emails


class TestRecipientClassification(unittest.TestCase):
    """Test recipient type and audience classification."""
    
    def test_classify_individual(self):
        """Single recipient should be 'individual'."""
        result = enrich_emails.classify_recipient_type(1)
        self.assertEqual(result, "individual")
    
    def test_classify_small_group(self):
        """2-5 recipients should be 'small_group'."""
        self.assertEqual(enrich_emails.classify_recipient_type(2), "small_group")
        self.assertEqual(enrich_emails.classify_recipient_type(5), "small_group")
    
    def test_classify_team(self):
        """6-15 recipients should be 'team'."""
        self.assertEqual(enrich_emails.classify_recipient_type(6), "team")
        self.assertEqual(enrich_emails.classify_recipient_type(15), "team")
    
    def test_classify_broadcast(self):
        """16+ recipients should be 'broadcast'."""
        self.assertEqual(enrich_emails.classify_recipient_type(16), "broadcast")
        self.assertEqual(enrich_emails.classify_recipient_type(100), "broadcast")
    
    def test_classify_audience_internal(self):
        """All same domain should be 'internal'."""
        domains = ["example.com", "example.com", "example.com"]
        result = enrich_emails.classify_audience(domains, "example.com")
        self.assertEqual(result, "internal")
    
    def test_classify_audience_external(self):
        """All different domain should be 'external'."""
        domains = ["client.com", "other.com"]
        result = enrich_emails.classify_audience(domains, "example.com")
        self.assertEqual(result, "external")
    
    def test_classify_audience_mixed(self):
        """Mix of domains should be 'mixed'."""
        domains = ["example.com", "client.com"]
        result = enrich_emails.classify_audience(domains, "example.com")
        self.assertEqual(result, "mixed")


class TestThreadDetection(unittest.TestCase):
    """Test thread position detection."""
    
    def test_detect_initiating(self):
        """Email without Re: or references should be 'initiating'."""
        email = get_sample_email("executive_brief")
        position, depth = enrich_emails.detect_thread_position(email)
        
        self.assertEqual(position, "initiating")
        self.assertEqual(depth, 0)
    
    def test_detect_reply(self):
        """Email with Re: should be 'reply'."""
        email = get_sample_email("client_response")
        position, depth = enrich_emails.detect_thread_position(email)
        
        self.assertEqual(position, "reply")
        self.assertGreater(depth, 0)
    
    def test_detect_forward(self):
        """Email with Fwd: should be 'forward'."""
        email = get_sample_email("forward")
        position, depth = enrich_emails.detect_thread_position(email)
        
        self.assertEqual(position, "forward")


class TestTimeContext(unittest.TestCase):
    """Test time-based context extraction."""
    
    def test_time_of_day_morning(self):
        """Morning hours (5-12) should be 'morning'."""
        # Create email with morning timestamp
        morning_ts = datetime(2025, 1, 7, 9, 0, 0).timestamp() * 1000
        email = {
            "internalDate": str(int(morning_ts))
        }
        
        context = enrich_emails.extract_time_context(email)
        self.assertEqual(context['time_of_day'], "morning")
    
    def test_time_of_day_afternoon(self):
        """Afternoon hours (12-17) should be 'afternoon'."""
        afternoon_ts = datetime(2025, 1, 7, 14, 0, 0).timestamp() * 1000
        email = {
            "internalDate": str(int(afternoon_ts))
        }
        
        context = enrich_emails.extract_time_context(email)
        self.assertEqual(context['time_of_day'], "afternoon")
    
    def test_time_of_day_evening(self):
        """Evening hours (17-21) should be 'evening'."""
        evening_ts = datetime(2025, 1, 7, 19, 0, 0).timestamp() * 1000
        email = {
            "internalDate": str(int(evening_ts))
        }
        
        context = enrich_emails.extract_time_context(email)
        self.assertEqual(context['time_of_day'], "evening")
    
    def test_weekend_detection(self):
        """Saturday/Sunday should be detected as weekend."""
        # Saturday
        sat_ts = datetime(2025, 1, 4, 10, 0, 0).timestamp() * 1000  # Jan 4, 2025 is Saturday
        email = {
            "internalDate": str(int(sat_ts))
        }
        
        context = enrich_emails.extract_time_context(email)
        self.assertTrue(context['is_weekend'])


class TestStructureAnalysis(unittest.TestCase):
    """Test email structure analysis."""
    
    def test_detect_bullets(self):
        """Should detect bullet points in email body."""
        body = """Here are the items:

• Item 1
• Item 2
• Item 3"""
        
        structure = enrich_emails.analyze_structure(body)
        self.assertTrue(structure['has_bullets'])
        self.assertEqual(structure['bullet_count'], 3)
    
    def test_count_paragraphs(self):
        """Should count paragraphs correctly."""
        body = """Paragraph one.

Paragraph two.

Paragraph three."""
        
        structure = enrich_emails.analyze_structure(body)
        self.assertEqual(structure['paragraph_count'], 3)
    
    def test_detect_greeting(self):
        """Should detect greeting patterns."""
        body = """Hi John,

This is the email body."""
        
        structure = enrich_emails.analyze_structure(body)
        self.assertIsNotNone(structure['greeting'])
        self.assertIn("Hi", structure['greeting'])
    
    def test_detect_closing(self):
        """Should detect closing patterns."""
        body = """This is the email body.

Best regards,
John"""
        
        structure = enrich_emails.analyze_structure(body)
        self.assertIsNotNone(structure['closing'])
    
    def test_char_count(self):
        """Should count characters correctly."""
        body = "Test"
        structure = enrich_emails.analyze_structure(body)
        self.assertEqual(structure['char_count'], 4)


class TestEnrichmentIntegration(unittest.TestCase):
    """Test full enrichment workflow."""
    
    def test_enrich_executive_brief(self):
        """Executive brief should be enriched with correct metadata."""
        email = get_sample_email("executive_brief")
        filtered = create_filtered_sample(email)
        
        enriched = enrich_emails.enrich_email(filtered, "example.com")
        
        # Check structure
        self.assertIn("enrichment", enriched)
        self.assertIn("recipient_type", enriched["enrichment"])
        self.assertIn("audience", enriched["enrichment"])
        self.assertIn("thread_position", enriched["enrichment"])
        
        # Executive brief specific checks
        self.assertEqual(enriched["enrichment"]["audience"], "internal")
        self.assertTrue(enriched["enrichment"]["has_bullets"])
    
    def test_enrich_client_response(self):
        """Client response should be enriched correctly."""
        email = get_sample_email("client_response")
        filtered = create_filtered_sample(email)
        
        enriched = enrich_emails.enrich_email(filtered, "example.com")
        
        self.assertEqual(enriched["enrichment"]["audience"], "external")
        self.assertEqual(enriched["enrichment"]["thread_position"], "reply")
    
    def test_enrichment_deterministic(self):
        """Enriching same email twice should give same result."""
        email = get_sample_email("executive_brief")
        filtered = create_filtered_sample(email)
        
        enriched1 = enrich_emails.enrich_email(filtered, "example.com")
        enriched2 = enrich_emails.enrich_email(filtered, "example.com")
        
        self.assertEqual(
            enriched1["enrichment"]["recipient_type"],
            enriched2["enrichment"]["recipient_type"]
        )
        self.assertEqual(
            enriched1["enrichment"]["audience"],
            enriched2["enrichment"]["audience"]
        )


if __name__ == '__main__':
    unittest.main()
