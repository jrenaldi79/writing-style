#!/usr/bin/env python3
"""
Unit Tests - Email Quality Filtering
"""

import sys
import unittest
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

from test_fixtures import get_sample_email, get_all_valid_samples, get_all_invalid_samples

# Import functions to test
import filter_emails


class TestEmailFiltering(unittest.TestCase):
    """Test email quality filtering."""
    
    def test_filter_executive_brief_passes(self):
        """Executive brief emails should pass filtering."""
        email = get_sample_email("executive_brief")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertTrue(should_include, f"Executive brief should pass but got: {reason}")
        self.assertGreaterEqual(quality['quality_score'], 0.3)
    
    def test_filter_client_response_passes(self):
        """Client response emails should pass filtering."""
        email = get_sample_email("client_response")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertTrue(should_include, f"Client response should pass but got: {reason}")
        self.assertGreaterEqual(quality['quality_score'], 0.3)
    
    def test_filter_forward_rejected(self):
        """Forwarded emails should be rejected."""
        email = get_sample_email("forward")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertFalse(should_include)
        self.assertEqual(reason, "forward")
    
    def test_filter_auto_reply_rejected(self):
        """Auto-reply emails should be rejected."""
        email = get_sample_email("auto_reply")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertFalse(should_include)
        self.assertEqual(reason, "auto_reply")
    
    def test_filter_too_short_rejected(self):
        """Too short emails should be rejected."""
        email = get_sample_email("too_short")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertFalse(should_include)
        self.assertEqual(reason, "too_short")
    
    def test_filter_mass_email_rejected(self):
        """Mass emails should be rejected."""
        email = get_sample_email("mass_email")
        should_include, reason, quality = filter_emails.filter_email(email)
        
        self.assertFalse(should_include)
        self.assertEqual(reason, "mass_email")
    
    def test_quality_score_range(self):
        """Quality scores should be between 0 and 1."""
        for email in get_all_valid_samples():
            should_include, reason, quality = filter_emails.filter_email(email)
            if should_include:
                self.assertGreaterEqual(quality['quality_score'], 0.0)
                self.assertLessEqual(quality['quality_score'], 1.0)
    
    def test_extract_body(self):
        """Should extract body from email data."""
        email = get_sample_email("executive_brief")
        body = filter_emails.extract_body(email)
        
        self.assertIn("Team,", body)
        self.assertIn("Quick update", body)
    
    def test_get_subject(self):
        """Should extract subject from headers."""
        email = get_sample_email("executive_brief")
        subject = filter_emails.get_subject(email)
        
        self.assertEqual(subject, "Q2 Update")
    
    def test_get_recipients(self):
        """Should extract recipient emails."""
        email = get_sample_email("executive_brief")
        recipients = filter_emails.get_recipients(email)
        
        self.assertIn("team@example.com", recipients)
    
    def test_remove_quoted_text(self):
        """Should remove quoted/forwarded text."""
        body_with_quote = """This is my original text.

> Quoted line 1
> Quoted line 2

More original text."""
        
        cleaned = filter_emails.remove_quoted_text(body_with_quote)
        
        self.assertIn("original text", cleaned)
        self.assertNotIn("Quoted line", cleaned)
    
    def test_compute_quality_score(self):
        """Quality score should favor longer, original content."""
        short_body = "Hi"
        medium_body = "Hi John, this is a medium length email with some content and variety."
        long_body = "Hi John, this is a longer email with substantial content. " * 10
        
        score_short = filter_emails.compute_quality_score(short_body, short_body)
        score_medium = filter_emails.compute_quality_score(medium_body, medium_body)
        score_long = filter_emails.compute_quality_score(long_body, long_body)
        
        self.assertLess(score_short, score_medium)
        self.assertLess(score_medium, score_long)


class TestFilteringConsistency(unittest.TestCase):
    """Test filtering consistency and edge cases."""
    
    def test_all_valid_samples_pass(self):
        """All valid sample emails should pass filtering."""
        valid_samples = get_all_valid_samples()
        
        for email in valid_samples:
            should_include, reason, quality = filter_emails.filter_email(email)
            self.assertTrue(should_include, 
                          f"Valid email {email['id']} failed: {reason}")
    
    def test_all_invalid_samples_fail(self):
        """All invalid sample emails should be rejected."""
        invalid_samples = get_all_invalid_samples()
        
        for email in invalid_samples:
            should_include, reason, quality = filter_emails.filter_email(email)
            self.assertFalse(should_include, 
                           f"Invalid email {email['id']} passed filtering")
    
    def test_filtering_deterministic(self):
        """Filtering same email twice should give same result."""
        email = get_sample_email("executive_brief")
        
        result1 = filter_emails.filter_email(email)
        result2 = filter_emails.filter_email(email)
        
        self.assertEqual(result1[0], result2[0])  # should_include
        self.assertEqual(result1[1], result2[1])  # reason
        self.assertAlmostEqual(result1[2]['quality_score'], 
                              result2[2]['quality_score'], places=2)


if __name__ == '__main__':
    unittest.main()
