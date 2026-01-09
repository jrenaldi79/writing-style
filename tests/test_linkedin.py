#!/usr/bin/env python3
"""
Unit Tests - LinkedIn Pipeline (Articles + Engagement Weighting)

TDD tests for:
1. Article support in fetch_linkedin_mcp.py
2. Engagement weighting in cluster_linkedin.py
"""

import sys
import unittest
import math
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

# =============================================================================
# FIXTURES
# =============================================================================

def create_sample_post(text, likes=0, comments=0, url=None, content_type="post"):
    """Create a sample LinkedIn post for testing."""
    return {
        "text": text,
        "likes": likes,
        "comments": comments,
        "url": url or "https://linkedin.com/posts/testuser_test-activity-123",
        "content_type": content_type,
        "date_posted": "2026-01-01",
        "user_id": "testuser"
    }


# Sample posts with varying engagement
SAMPLE_POSTS = {
    "high_engagement": create_sample_post(
        text="This is a high engagement post about AI and product strategy. " * 10,
        likes=500,
        comments=50
    ),
    "medium_engagement": create_sample_post(
        text="This is a medium engagement post about team collaboration. " * 8,
        likes=50,
        comments=5
    ),
    "low_engagement": create_sample_post(
        text="This is a low engagement post. " * 5,
        likes=2,
        comments=0
    ),
    "zero_engagement": create_sample_post(
        text="This post has zero engagement but is very long and detailed. " * 20,
        likes=0,
        comments=0
    ),
    "short_high_engagement": create_sample_post(
        text="Short but viral!",
        likes=1000,
        comments=100
    ),
}


# Sample URLs for article/post validation
SAMPLE_URLS = {
    "post_standard": "https://www.linkedin.com/posts/renaldi_techstars-chicago-activity-7386491377351733248-9ctr",
    "post_with_params": "https://www.linkedin.com/posts/renaldi_product-activity-123?trk=public_profile",
    "article_pulse": "https://www.linkedin.com/pulse/future-ai-product-management-john-renaldi",
    "article_pulse_with_id": "https://www.linkedin.com/pulse/building-better-teams-renaldi-abc123",
    "wrong_user_post": "https://www.linkedin.com/posts/otheruser_product-activity-456",
    "wrong_user_article": "https://www.linkedin.com/pulse/some-article-otheruser",
}


# =============================================================================
# ARTICLE SUPPORT TESTS
# =============================================================================

class TestArticleURLValidation(unittest.TestCase):
    """Test URL validation for articles vs posts."""

    def test_post_url_is_valid(self):
        """Standard post URLs should be valid."""
        url = SAMPLE_URLS["post_standard"]
        self.assertIn("/posts/", url)
        self.assertIn("activity-", url)

    def test_article_url_pattern(self):
        """Article URLs should contain /pulse/."""
        url = SAMPLE_URLS["article_pulse"]
        self.assertIn("/pulse/", url)

    def test_article_contains_username(self):
        """Article URLs should contain the username."""
        url = SAMPLE_URLS["article_pulse"]
        username = "renaldi"
        self.assertIn(username.lower(), url.lower())

    def test_can_distinguish_post_from_article(self):
        """Should be able to distinguish posts from articles by URL."""
        post_url = SAMPLE_URLS["post_standard"]
        article_url = SAMPLE_URLS["article_pulse"]

        # Posts have /posts/ and activity-
        is_post = "/posts/" in post_url and "activity-" in post_url
        is_article = "/pulse/" in article_url

        self.assertTrue(is_post)
        self.assertTrue(is_article)
        self.assertFalse("/pulse/" in post_url)
        self.assertFalse("activity-" in article_url)


class TestArticleSearchPatterns(unittest.TestCase):
    """Test that search patterns include articles."""

    def test_search_patterns_exist(self):
        """Import fetch_linkedin_mcp and check search_for_posts exists."""
        try:
            import fetch_linkedin_mcp
            self.assertTrue(hasattr(fetch_linkedin_mcp, 'search_for_posts'))
        except ImportError as e:
            self.skipTest(f"fetch_linkedin_mcp not importable: {e}")

    def test_search_patterns_include_pulse(self):
        """Search patterns should include linkedin.com/pulse/ for articles."""
        try:
            import fetch_linkedin_mcp
            # Get the search patterns from the function
            # This test will fail until we implement the feature
            source = open(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts" / "fetch_linkedin_mcp.py").read()
            self.assertIn("pulse", source.lower(),
                "fetch_linkedin_mcp.py should contain 'pulse' for article searching")
        except Exception as e:
            self.fail(f"Could not verify pulse search pattern: {e}")


# =============================================================================
# ENGAGEMENT WEIGHTING TESTS
# =============================================================================

class TestEngagementWeighting(unittest.TestCase):
    """Test engagement-based weighting in persona analysis."""

    def test_calculate_engagement_weight_exists(self):
        """cluster_linkedin should have calculate_engagement_weight function."""
        try:
            import cluster_linkedin
            self.assertTrue(
                hasattr(cluster_linkedin, 'calculate_engagement_weight'),
                "cluster_linkedin.py should have calculate_engagement_weight function"
            )
        except ImportError as e:
            self.skipTest(f"cluster_linkedin not importable: {e}")

    def test_high_engagement_has_higher_weight(self):
        """Posts with more likes should have higher weight."""
        try:
            from cluster_linkedin import calculate_engagement_weight

            high = SAMPLE_POSTS["high_engagement"]
            low = SAMPLE_POSTS["low_engagement"]

            weight_high = calculate_engagement_weight(high)
            weight_low = calculate_engagement_weight(low)

            self.assertGreater(weight_high, weight_low,
                f"High engagement ({high['likes']} likes) should have higher weight than low ({low['likes']} likes)")
        except ImportError:
            self.fail("calculate_engagement_weight not found - implement this function")

    def test_zero_engagement_has_minimum_weight(self):
        """Posts with 0 likes should still have minimum weight (not 0)."""
        try:
            from cluster_linkedin import calculate_engagement_weight

            zero_engagement = SAMPLE_POSTS["zero_engagement"]
            weight = calculate_engagement_weight(zero_engagement)

            self.assertGreaterEqual(weight, 1.0,
                "Zero engagement posts should have minimum weight of 1.0")
        except ImportError:
            self.fail("calculate_engagement_weight not found - implement this function")

    def test_weight_uses_log_scale(self):
        """Weights should use log scale to prevent viral posts from dominating."""
        try:
            from cluster_linkedin import calculate_engagement_weight

            medium = SAMPLE_POSTS["medium_engagement"]  # 50 likes
            viral = SAMPLE_POSTS["short_high_engagement"]  # 1000 likes

            weight_medium = calculate_engagement_weight(medium)
            weight_viral = calculate_engagement_weight(viral)

            # With log scale, 1000 likes shouldn't be 20x more influential than 50 likes
            ratio = weight_viral / weight_medium
            self.assertLess(ratio, 5.0,
                f"Weight ratio ({ratio:.1f}x) should be < 5x due to log scaling")
        except ImportError:
            self.fail("calculate_engagement_weight not found - implement this function")


class TestBestPostSelection(unittest.TestCase):
    """Test that best post is selected by engagement, not length."""

    def test_best_post_by_engagement_not_length(self):
        """Few-shot example should be highest engagement, not longest."""
        try:
            from cluster_linkedin import create_rich_persona

            posts = [
                SAMPLE_POSTS["zero_engagement"],  # Long but no engagement
                SAMPLE_POSTS["short_high_engagement"],  # Short but viral
            ]

            persona = create_rich_persona(posts)
            best_example = persona["few_shot_examples"][0]["output_text"]

            # Best should be the high engagement one, not the long one
            self.assertEqual(best_example, SAMPLE_POSTS["short_high_engagement"]["text"],
                "Best post should be highest engagement, not longest")
        except ImportError:
            self.fail("create_rich_persona not found")

    def test_length_is_tiebreaker(self):
        """When engagement is equal, longer post should win."""
        try:
            from cluster_linkedin import create_rich_persona

            short = create_sample_post("Short post", likes=100, comments=10)
            long = create_sample_post("This is a much longer post with more content " * 10, likes=100, comments=10)

            persona = create_rich_persona([short, long])
            best_example = persona["few_shot_examples"][0]["output_text"]

            self.assertEqual(best_example, long["text"],
                "With equal engagement, longer post should be selected")
        except ImportError:
            self.fail("create_rich_persona not found")


class TestWeightedToneAnalysis(unittest.TestCase):
    """Test that tone analysis uses engagement-weighted averaging."""

    def test_analyze_tone_uses_weights(self):
        """Tone vectors should be influenced more by high-engagement posts."""
        try:
            from cluster_linkedin import analyze_tone

            # Create posts with different characteristics
            # High engagement post: very formal (long, no emojis)
            formal_high_engagement = create_sample_post(
                text="This is a formal professional post about strategy and business. " * 50,
                likes=500,
                comments=50
            )
            # Low engagement post: informal (short, emojis)
            informal_low_engagement = create_sample_post(
                text="Hey! Quick update! 🎉🚀 Excited!",
                likes=1,
                comments=0
            )

            # With weighting, the formal high-engagement post should dominate
            posts = [formal_high_engagement, informal_low_engagement]
            tone = analyze_tone(posts)

            # Formality should be high (>= 6) because high-engagement post is formal
            self.assertGreaterEqual(tone['formality'], 6,
                "Formality should be high due to weighted influence of formal high-engagement post")
        except ImportError:
            self.fail("analyze_tone not found")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestLinkedInPipelineIntegration(unittest.TestCase):
    """Integration tests for the full pipeline."""

    def test_content_type_field_exists(self):
        """Posts should have content_type field distinguishing posts from articles."""
        post = create_sample_post("Test", content_type="post")
        article = create_sample_post("Test article content", content_type="article")

        self.assertEqual(post["content_type"], "post")
        self.assertEqual(article["content_type"], "article")

    def test_persona_includes_engagement_metadata(self):
        """Generated persona should include info about engagement weighting."""
        try:
            from cluster_linkedin import create_rich_persona

            posts = list(SAMPLE_POSTS.values())
            persona = create_rich_persona(posts)

            # Persona should exist and have required structure
            self.assertIsNotNone(persona)
            self.assertIn("voice_configuration", persona)
            self.assertIn("tone_vectors", persona["voice_configuration"])
        except ImportError:
            self.fail("create_rich_persona not found")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
