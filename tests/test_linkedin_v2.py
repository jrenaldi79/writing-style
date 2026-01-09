#!/usr/bin/env python3
"""
Unit Tests - LinkedIn Persona V2 Schema

TDD tests for v2 schema auto-extractable fields:
1. Linguistic patterns (sentence length, contractions, punctuation)
2. Emoji profile (signature emojis, placement, frequency)
3. Platform rules (formatting, hooks, closings, length)
4. Variation controls (distributions and ranges)
5. V2 output structure and confidence scoring
"""

import sys
import unittest
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

# =============================================================================
# FIXTURES
# =============================================================================

def create_sample_post(text, likes=0, comments=0):
    """Create a sample LinkedIn post for testing."""
    return {
        "text": text,
        "likes": likes,
        "comments": comments,
        "url": "https://linkedin.com/posts/testuser_test-activity-123",
        "date_posted": "2026-01-01",
        "user_id": "testuser"
    }


# Sample posts with varying characteristics
SAMPLE_POSTS = {
    "short_punchy": create_sample_post(
        text="AI is changing everything. Fast. Are you ready?",
        likes=100
    ),
    "long_formal": create_sample_post(
        text="I have been reflecting on the significant transformations occurring in the technology sector. "
             "The advancements in artificial intelligence are creating unprecedented opportunities for innovation. "
             "Organizations that embrace these changes will be well-positioned for success in the coming decade.",
        likes=50
    ),
    "with_emojis": create_sample_post(
        text="Just launched our new product! 🚀 The team worked incredibly hard on this. 🎉 "
             "Can't wait to see what you all think! 🍌",
        likes=200
    ),
    "with_contractions": create_sample_post(
        text="I'm excited to share that we've launched something new. It's been a long journey, "
             "but we couldn't have done it without the team. Don't miss out!",
        likes=75
    ),
    "with_em_dash": create_sample_post(
        text="The future of AI—and I mean the real future—is going to be incredible. "
             "We're building something amazing—something that will change everything.",
        likes=60
    ),
    "with_parentheticals": create_sample_post(
        text="Our new feature (which we've been working on for months) is finally ready. "
             "The results (so far) have been incredible. Check it out (link in comments).",
        likes=80
    ),
    "with_hashtags": create_sample_post(
        text="Excited about the future of product management.\n\n#product #AI #startup #innovation",
        likes=45
    ),
    "with_bullets": create_sample_post(
        text="Three things I learned this week:\n\n• Always test your assumptions\n• Ship fast, iterate faster\n• Listen to your users",
        likes=90
    ),
    "question_hook": create_sample_post(
        text="What if AI could write code better than humans? "
             "That's the question we're exploring at our company.",
        likes=120
    ),
    "observation_hook": create_sample_post(
        text="Google's new Gemini 2.0 is absolutely incredible. "
             "I spent the morning testing it and here's what I found.",
        likes=150
    ),
    "cta_closing": create_sample_post(
        text="We're hiring senior engineers. If you know anyone with wearable experience, "
             "please tag them or send them our way!",
        likes=130
    ),
    "question_closing": create_sample_post(
        text="I've been thinking about the future of remote work. "
             "What's your experience been like working from home?",
        likes=70
    ),
}


# =============================================================================
# LINGUISTIC PATTERNS TESTS
# =============================================================================

class TestLinguisticPatterns(unittest.TestCase):
    """Test linguistic pattern extraction."""

    def test_analyze_linguistic_patterns_exists(self):
        """Function should exist in cluster_linkedin module."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns
            self.assertTrue(callable(analyze_linguistic_patterns))
        except ImportError:
            self.fail("analyze_linguistic_patterns not found - implement this function")

    def test_sentence_length_calculation(self):
        """Should calculate average words per sentence."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["short_punchy"]]  # "AI is changing everything. Fast. Are you ready?"
            result = analyze_linguistic_patterns(posts)

            self.assertIn("sentence_length_avg_words", result)
            # 3 sentences: 4 words, 1 word, 3 words = avg ~2.67
            self.assertIsInstance(result["sentence_length_avg_words"], (int, float))
            self.assertGreater(result["sentence_length_avg_words"], 0)
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_short_punchy_ratio(self):
        """Should identify percentage of short sentences (<8 words)."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["short_punchy"]]
            result = analyze_linguistic_patterns(posts)

            self.assertIn("short_punchy_ratio", result)
            # All sentences in this post are short
            self.assertGreater(result["short_punchy_ratio"], 0.5)
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_contraction_detection(self):
        """Should detect contractions usage."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            # Post with contractions
            posts_with = [SAMPLE_POSTS["with_contractions"]]
            result_with = analyze_linguistic_patterns(posts_with)

            # Post without contractions
            posts_without = [SAMPLE_POSTS["long_formal"]]
            result_without = analyze_linguistic_patterns(posts_without)

            self.assertIn("uses_contractions", result_with)
            self.assertTrue(result_with["uses_contractions"])
            self.assertFalse(result_without["uses_contractions"])
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_em_dash_detection(self):
        """Should detect em-dash usage."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["with_em_dash"]]
            result = analyze_linguistic_patterns(posts)

            self.assertIn("uses_em_dash", result)
            self.assertTrue(result["uses_em_dash"])
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_parenthetical_detection(self):
        """Should detect parenthetical usage."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["with_parentheticals"]]
            result = analyze_linguistic_patterns(posts)

            self.assertIn("uses_parentheticals", result)
            self.assertTrue(result["uses_parentheticals"])
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_exclamation_frequency(self):
        """Should count exclamations per post."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["with_emojis"]]  # Has multiple !
            result = analyze_linguistic_patterns(posts)

            self.assertIn("exclamations_per_post", result)
            self.assertGreater(result["exclamations_per_post"], 0)
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")

    def test_question_frequency(self):
        """Should count questions per post."""
        try:
            from cluster_linkedin import analyze_linguistic_patterns

            posts = [SAMPLE_POSTS["short_punchy"]]  # "Are you ready?"
            result = analyze_linguistic_patterns(posts)

            self.assertIn("questions_per_post", result)
            self.assertGreater(result["questions_per_post"], 0)
        except ImportError:
            self.fail("analyze_linguistic_patterns not found")


# =============================================================================
# EMOJI PROFILE TESTS
# =============================================================================

class TestEmojiProfile(unittest.TestCase):
    """Test emoji profile extraction."""

    def test_analyze_emoji_profile_exists(self):
        """Function should exist in cluster_linkedin module."""
        try:
            from cluster_linkedin import analyze_emoji_profile
            self.assertTrue(callable(analyze_emoji_profile))
        except ImportError:
            self.fail("analyze_emoji_profile not found - implement this function")

    def test_signature_emoji_extraction(self):
        """Should identify top emojis by frequency."""
        try:
            from cluster_linkedin import analyze_emoji_profile

            posts = [SAMPLE_POSTS["with_emojis"]]  # Has 🚀 🎉 🍌
            result = analyze_emoji_profile(posts)

            self.assertIn("signature_emojis", result)
            self.assertIsInstance(result["signature_emojis"], list)
            self.assertGreater(len(result["signature_emojis"]), 0)
        except ImportError:
            self.fail("analyze_emoji_profile not found")

    def test_emoji_placement_analysis(self):
        """Should classify emoji placement patterns."""
        try:
            from cluster_linkedin import analyze_emoji_profile

            posts = [SAMPLE_POSTS["with_emojis"]]
            result = analyze_emoji_profile(posts)

            self.assertIn("placement", result)
            self.assertIn(result["placement"], ["beginning", "middle", "end", "emphasis_points", "mixed"])
        except ImportError:
            self.fail("analyze_emoji_profile not found")

    def test_emoji_per_post_range(self):
        """Should calculate min/max emoji counts."""
        try:
            from cluster_linkedin import analyze_emoji_profile

            posts = [
                SAMPLE_POSTS["with_emojis"],  # 3 emojis
                SAMPLE_POSTS["short_punchy"],  # 0 emojis
            ]
            result = analyze_emoji_profile(posts)

            self.assertIn("per_post_range", result)
            self.assertIsInstance(result["per_post_range"], list)
            self.assertEqual(len(result["per_post_range"]), 2)
            self.assertEqual(result["per_post_range"][0], 0)  # min
            self.assertGreater(result["per_post_range"][1], 0)  # max
        except ImportError:
            self.fail("analyze_emoji_profile not found")

    def test_no_emojis_handled(self):
        """Should handle posts with no emojis gracefully."""
        try:
            from cluster_linkedin import analyze_emoji_profile

            posts = [SAMPLE_POSTS["long_formal"]]  # No emojis
            result = analyze_emoji_profile(posts)

            self.assertIn("signature_emojis", result)
            self.assertEqual(result["signature_emojis"], [])
        except ImportError:
            self.fail("analyze_emoji_profile not found")


# =============================================================================
# PLATFORM RULES TESTS
# =============================================================================

class TestPlatformRules(unittest.TestCase):
    """Test platform rules extraction."""

    def test_analyze_platform_rules_exists(self):
        """Function should exist in cluster_linkedin module."""
        try:
            from cluster_linkedin import analyze_platform_rules
            self.assertTrue(callable(analyze_platform_rules))
        except ImportError:
            self.fail("analyze_platform_rules not found - implement this function")

    def test_line_break_frequency(self):
        """Should classify line break density."""
        try:
            from cluster_linkedin import analyze_platform_rules

            posts = [SAMPLE_POSTS["with_hashtags"]]  # Has \n\n
            result = analyze_platform_rules(posts)

            self.assertIn("formatting", result)
            self.assertIn("line_break_frequency", result["formatting"])
            self.assertIn(result["formatting"]["line_break_frequency"], ["high", "medium", "low"])
        except ImportError:
            self.fail("analyze_platform_rules not found")

    def test_bullet_detection(self):
        """Should detect bullet point usage."""
        try:
            from cluster_linkedin import analyze_platform_rules

            posts = [SAMPLE_POSTS["with_bullets"]]
            result = analyze_platform_rules(posts)

            self.assertIn("formatting", result)
            self.assertIn("uses_bullets", result["formatting"])
            self.assertTrue(result["formatting"]["uses_bullets"])
        except ImportError:
            self.fail("analyze_platform_rules not found")

    def test_hashtag_analysis(self):
        """Should extract hashtag patterns."""
        try:
            from cluster_linkedin import analyze_platform_rules

            posts = [SAMPLE_POSTS["with_hashtags"]]  # Has 4 hashtags at end
            result = analyze_platform_rules(posts)

            self.assertIn("formatting", result)
            self.assertIn("uses_hashtags", result["formatting"])
            self.assertTrue(result["formatting"]["uses_hashtags"])
            self.assertIn("hashtag_placement", result["formatting"])
        except ImportError:
            self.fail("analyze_platform_rules not found")

    def test_hook_classification(self):
        """Should classify first sentence style."""
        try:
            from cluster_linkedin import analyze_platform_rules

            # Question hook
            posts_question = [SAMPLE_POSTS["question_hook"]]
            result_question = analyze_platform_rules(posts_question)

            # Observation hook
            posts_observation = [SAMPLE_POSTS["observation_hook"]]
            result_observation = analyze_platform_rules(posts_observation)

            self.assertIn("hooks", result_question)
            self.assertIn("primary_style", result_question["hooks"])
        except ImportError:
            self.fail("analyze_platform_rules not found")

    def test_closing_classification(self):
        """Should classify last sentence style."""
        try:
            from cluster_linkedin import analyze_platform_rules

            posts = [SAMPLE_POSTS["cta_closing"]]
            result = analyze_platform_rules(posts)

            self.assertIn("closings", result)
            self.assertIn("engagement_ask_frequency", result["closings"])
        except ImportError:
            self.fail("analyze_platform_rules not found")

    def test_length_statistics(self):
        """Should calculate length statistics."""
        try:
            from cluster_linkedin import analyze_platform_rules

            posts = list(SAMPLE_POSTS.values())
            result = analyze_platform_rules(posts)

            self.assertIn("length", result)
            self.assertIn("target_chars", result["length"])
            self.assertIn("min_chars", result["length"])
            self.assertIn("max_chars", result["length"])
            self.assertLess(result["length"]["min_chars"], result["length"]["max_chars"])
        except ImportError:
            self.fail("analyze_platform_rules not found")


# =============================================================================
# VARIATION CONTROLS TESTS
# =============================================================================

class TestVariationControls(unittest.TestCase):
    """Test variation controls calculation."""

    def test_analyze_variation_controls_exists(self):
        """Function should exist in cluster_linkedin module."""
        try:
            from cluster_linkedin import analyze_variation_controls
            self.assertTrue(callable(analyze_variation_controls))
        except ImportError:
            self.fail("analyze_variation_controls not found - implement this function")

    def test_emoji_range_calculation(self):
        """Should calculate emoji per post range."""
        try:
            from cluster_linkedin import analyze_variation_controls

            posts = list(SAMPLE_POSTS.values())
            result = analyze_variation_controls(posts)

            self.assertIn("emoji_per_post_range", result)
            self.assertIsInstance(result["emoji_per_post_range"], list)
            self.assertEqual(len(result["emoji_per_post_range"]), 2)
        except ImportError:
            self.fail("analyze_variation_controls not found")

    def test_hook_style_distribution(self):
        """Should calculate hook style distribution."""
        try:
            from cluster_linkedin import analyze_variation_controls

            posts = list(SAMPLE_POSTS.values())
            result = analyze_variation_controls(posts)

            self.assertIn("hook_style_distribution", result)
            self.assertIsInstance(result["hook_style_distribution"], dict)
        except ImportError:
            self.fail("analyze_variation_controls not found")


# =============================================================================
# V2 OUTPUT STRUCTURE TESTS
# =============================================================================

class TestV2OutputStructure(unittest.TestCase):
    """Test V2 schema output structure."""

    def test_create_v2_persona_exists(self):
        """Function should exist in cluster_linkedin module."""
        try:
            from cluster_linkedin import create_v2_persona
            self.assertTrue(callable(create_v2_persona))
        except ImportError:
            self.fail("create_v2_persona not found - implement this function")

    def test_v2_schema_structure(self):
        """Output should match v2 schema with all sections."""
        try:
            from cluster_linkedin import create_v2_persona

            posts = list(SAMPLE_POSTS.values())
            result = create_v2_persona(posts)

            # Check top-level fields
            self.assertIn("schema_version", result)
            self.assertEqual(result["schema_version"], "2.0")
            self.assertIn("confidence", result)

            # Check voice section
            self.assertIn("voice", result)
            self.assertIn("tone_vectors", result["voice"])
            self.assertIn("linguistic_patterns", result["voice"])
            self.assertIn("emoji_profile", result["voice"])
            self.assertIn("enthusiasm_level", result["voice"])

            # Check platform_rules section
            self.assertIn("platform_rules", result)
            self.assertIn("formatting", result["platform_rules"])
            self.assertIn("hooks", result["platform_rules"])
            self.assertIn("closings", result["platform_rules"])
            self.assertIn("length", result["platform_rules"])

            # Check variation_controls section
            self.assertIn("variation_controls", result)

            # Check example_bank section
            self.assertIn("example_bank", result)
            self.assertIn("usage_guidance", result["example_bank"])
            self.assertIn("positive", result["example_bank"])

            # Check guardrails placeholder
            self.assertIn("guardrails", result)
        except ImportError:
            self.fail("create_v2_persona not found")

    def test_confidence_calculation(self):
        """Confidence should scale with sample size."""
        try:
            from cluster_linkedin import calculate_confidence

            # Small sample
            conf_small = calculate_confidence(3)
            # Medium sample
            conf_medium = calculate_confidence(10)
            # Large sample
            conf_large = calculate_confidence(25)

            self.assertLess(conf_small, conf_medium)
            self.assertLess(conf_medium, conf_large)
            self.assertLessEqual(conf_large, 1.0)
            self.assertGreaterEqual(conf_small, 0.0)
        except ImportError:
            self.fail("calculate_confidence not found - implement this function")

    def test_enthusiasm_level_range(self):
        """Enthusiasm level should be 1-10."""
        try:
            from cluster_linkedin import create_v2_persona

            posts = list(SAMPLE_POSTS.values())
            result = create_v2_persona(posts)

            enthusiasm = result["voice"]["enthusiasm_level"]
            self.assertGreaterEqual(enthusiasm, 1)
            self.assertLessEqual(enthusiasm, 10)
        except ImportError:
            self.fail("create_v2_persona not found")

    def test_example_bank_has_usage_guidance(self):
        """Example bank should include usage guidance."""
        try:
            from cluster_linkedin import create_v2_persona

            posts = list(SAMPLE_POSTS.values())
            result = create_v2_persona(posts)

            guidance = result["example_bank"]["usage_guidance"]
            self.assertIn("instruction", guidance)
            self.assertIn("what_to_match", guidance)
            self.assertIn("what_to_adapt", guidance)
            self.assertIn("warning", guidance)
        except ImportError:
            self.fail("create_v2_persona not found")

    def test_positive_examples_have_engagement(self):
        """Positive examples should include engagement data."""
        try:
            from cluster_linkedin import create_v2_persona

            posts = list(SAMPLE_POSTS.values())
            result = create_v2_persona(posts)

            positive = result["example_bank"]["positive"]
            self.assertGreater(len(positive), 0)

            first_example = positive[0]
            self.assertIn("engagement", first_example)
            self.assertIn("likes", first_example["engagement"])
            self.assertIn("text", first_example)
        except ImportError:
            self.fail("create_v2_persona not found")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
