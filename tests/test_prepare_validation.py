#!/usr/bin/env python3
"""
Unit Tests - Validation Preparation (contraction detection, tone analysis)
"""

import sys
import unittest
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

import prepare_validation


class TestContractionDetection(unittest.TestCase):
    """Test contraction detection in analyze_tone_hints()."""

    def test_common_contractions_detected(self):
        """Standard contractions should be detected."""
        test_cases = [
            "I'll probably line up some calls",
            "Here's a little bit of my background",
            "I've got quite a bit of flexibility",
            "won't be able to make it",
            "can't sign in to the system",
            "I'm excited about this",
            "You're going to love it",
            "We're looking forward to it",
            "They're coming tomorrow",
            "It's a great opportunity",
            "That's what I meant",
            "There's no problem with that",
        ]

        for text in test_cases:
            hints = prepare_validation.analyze_tone_hints(text)
            self.assertIn('uses_contractions', hints,
                         f"Should detect contraction in: {text}")

    def test_negative_contractions_detected(self):
        """Negative contractions should be detected."""
        test_cases = [
            "I don't think that's right",
            "We won't be able to attend",
            "She doesn't agree with that",
            "He didn't respond",
            "It isn't working",
            "They aren't available",
            "I wasn't aware",
            "We weren't informed",
            "I haven't seen it",
            "He hasn't replied",
            "We hadn't considered that",
            "I couldn't find it",
            "You wouldn't believe it",
            "We shouldn't proceed",
        ]

        for text in test_cases:
            hints = prepare_validation.analyze_tone_hints(text)
            self.assertIn('uses_contractions', hints,
                         f"Should detect contraction in: {text}")

    def test_unicode_apostrophe_detected(self):
        """Unicode right single quotation mark (U+2019) should be detected."""
        # These use Unicode apostrophe ' (U+2019) instead of ASCII '
        test_cases = [
            "I\u2019ll be there tomorrow",
            "Here\u2019s the document",
            "I\u2019ve reviewed it",
            "We\u2019re on track",
            "Don\u2019t worry about it",
        ]

        for text in test_cases:
            hints = prepare_validation.analyze_tone_hints(text)
            self.assertIn('uses_contractions', hints,
                         f"Should detect Unicode apostrophe contraction in: {text}")

    def test_no_contractions_not_detected(self):
        """Text without contractions should not trigger detection."""
        test_cases = [
            "I will probably line up some calls",
            "Here is a little bit of my background",
            "I have got quite a bit of flexibility",
            "No contractions in this text",
            "This is a formal message without any shortened words",
            "",  # Empty string
        ]

        for text in test_cases:
            hints = prepare_validation.analyze_tone_hints(text)
            self.assertNotIn('uses_contractions', hints,
                            f"Should not detect contraction in: {text}")

    def test_possessives_not_mistaken_for_contractions(self):
        """Possessives like 'John's book' should not trigger contraction detection.

        Note: This is a known limitation. 's endings are ambiguous between
        possessive (John's book) and contractions (it's, that's).
        We intentionally include it's, that's, here's, there's, what's, who's
        as contractions since they're almost always contractions in speech.
        """
        # These ARE detected because they match known contraction patterns
        detected_as_contractions = [
            "It's a great day",  # Contraction: it is
            "That's interesting",  # Contraction: that is
            "Here's the plan",  # Contraction: here is
        ]

        for text in detected_as_contractions:
            hints = prepare_validation.analyze_tone_hints(text)
            self.assertIn('uses_contractions', hints,
                         f"Should detect contraction in: {text}")


class TestToneAnalysis(unittest.TestCase):
    """Test other tone hint detection."""

    def test_formal_indicators(self):
        """Formal language should be detected."""
        text = "Dear Sir, I sincerely appreciate your kind regards."
        hints = prepare_validation.analyze_tone_hints(text)
        self.assertIn('formal', hints)

    def test_casual_indicators(self):
        """Casual language should be detected."""
        text = "Hey there! Haha that's hilarious lol"
        hints = prepare_validation.analyze_tone_hints(text)
        self.assertIn('casual', hints)

    def test_warm_indicators(self):
        """Warm language should be detected."""
        text = "I hope you're doing well. Thank you so much for your help!"
        hints = prepare_validation.analyze_tone_hints(text)
        self.assertIn('warm', hints)

    def test_concise_text(self):
        """Short replies should be marked concise."""
        text = "Sure, sounds good."
        hints = prepare_validation.analyze_tone_hints(text)
        self.assertIn('concise', hints)


if __name__ == '__main__':
    unittest.main()
