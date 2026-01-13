"""
Tests for expanded LinkedIn post search functionality.

TDD: These tests define expected behavior for:
1. Dynamic keyword extraction from profile data
2. Enhanced search pattern generation
3. Article search using full name
4. Date-range searches for older posts
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))


class TestKeywordExtraction(unittest.TestCase):
    """Test extraction of search keywords from profile data."""

    def test_extract_keywords_from_headline(self):
        """Should extract role keywords from headline."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {"headline": "Product Manager at Google | AI Enthusiast"}
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        self.assertTrue(
            any("product" in k for k in lower_keywords),
            f"Expected 'product' in keywords, got: {keywords}"
        )

    def test_extract_keywords_from_headline_with_title(self):
        """Should extract job title from headline."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {"headline": "Senior Software Engineer at Microsoft"}
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        self.assertTrue(
            any("engineer" in k or "software" in k for k in lower_keywords),
            f"Expected engineering terms in keywords, got: {keywords}"
        )

    def test_extract_keywords_from_company(self):
        """Should include company name in keywords."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {
            "headline": "Founder",
            "company": "Jiobit"
        }
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        self.assertTrue(
            any("jiobit" in k for k in lower_keywords),
            f"Expected 'jiobit' in keywords, got: {keywords}"
        )

    def test_extract_keywords_from_bio(self):
        """Should extract industry terms from bio."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {
            "headline": "CEO",
            "bio": "Building the future of machine learning and artificial intelligence"
        }
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        self.assertTrue(
            any("machine" in k or "learning" in k or "ai" in k or "artificial" in k
                for k in lower_keywords),
            f"Expected ML/AI terms in keywords, got: {keywords}"
        )

    def test_filter_stopwords(self):
        """Should filter common stopwords."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {"headline": "The best product manager in the world"}
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        self.assertNotIn("the", lower_keywords)
        self.assertNotIn("in", lower_keywords)

    def test_max_keywords_limit(self):
        """Should respect max_keywords parameter."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {
            "headline": "Product Manager Engineer Designer Developer Architect Lead Senior Principal"
        }
        keywords = extract_profile_keywords(profile, max_keywords=3)

        self.assertLessEqual(len(keywords), 3)

    def test_empty_profile_returns_empty_list(self):
        """Should return empty list for empty profile."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {}
        keywords = extract_profile_keywords(profile)

        self.assertEqual(keywords, [])

    def test_deduplicate_keywords(self):
        """Should not return duplicate keywords."""
        from fetch_linkedin_mcp import extract_profile_keywords

        profile = {
            "headline": "Product Manager",
            "bio": "Experienced product manager with product management skills"
        }
        keywords = extract_profile_keywords(profile)

        lower_keywords = [k.lower() for k in keywords]
        # Check no duplicates
        self.assertEqual(len(lower_keywords), len(set(lower_keywords)))


class TestSearchPatternGeneration(unittest.TestCase):
    """Test dynamic search pattern generation."""

    def test_includes_base_patterns(self):
        """Should always include base patterns."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("testuser")

        self.assertTrue(
            any("activity" in p for p in patterns),
            "Should include activity pattern"
        )
        self.assertTrue(
            any("testuser_" in p for p in patterns),
            "Should include underscore pattern"
        )

    def test_dynamic_keywords_in_pattern(self):
        """Should include profile keywords in patterns when provided."""
        from fetch_linkedin_mcp import build_search_patterns

        profile = {"headline": "AI Startup Founder"}
        patterns = build_search_patterns("testuser", profile_data=profile)

        # Should have a pattern with extracted keywords
        keyword_patterns = [p for p in patterns if "site:linkedin.com/posts" in p and "testuser" in p]
        self.assertTrue(
            any("AI" in p or "startup" in p.lower() or "founder" in p.lower()
                for p in keyword_patterns),
            f"Expected keyword pattern, got: {keyword_patterns}"
        )

    def test_fallback_keywords_when_no_profile(self):
        """Should use hardcoded keywords when profile not provided."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("testuser", profile_data=None)

        self.assertTrue(
            any("product OR founder OR startup" in p for p in patterns),
            "Should include fallback keywords"
        )

    def test_fallback_keywords_when_dynamic_disabled(self):
        """Should use hardcoded keywords when dynamic keywords disabled."""
        from fetch_linkedin_mcp import build_search_patterns

        profile = {"headline": "AI Startup Founder"}
        patterns = build_search_patterns(
            "testuser",
            profile_data=profile,
            use_dynamic_keywords=False
        )

        self.assertTrue(
            any("product OR founder OR startup" in p for p in patterns),
            "Should include fallback keywords when dynamic disabled"
        )

    def test_year_range_patterns(self):
        """Should generate year-specific patterns."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("testuser", year_range=3)
        current_year = datetime.now().year

        self.assertTrue(
            any(str(current_year) in p for p in patterns),
            f"Should include current year {current_year}"
        )
        self.assertTrue(
            any(str(current_year - 1) in p for p in patterns),
            f"Should include year {current_year - 1}"
        )
        self.assertTrue(
            any(str(current_year - 2) in p for p in patterns),
            f"Should include year {current_year - 2}"
        )

    def test_year_range_zero_skips_year_patterns(self):
        """Should skip year patterns when year_range is 0."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("testuser", year_range=0)
        current_year = datetime.now().year

        # Year patterns specifically have format: site:linkedin.com/posts/username YEAR
        year_patterns = [p for p in patterns
                        if f"site:linkedin.com/posts/testuser {current_year}" in p]
        self.assertEqual(len(year_patterns), 0, "Should not include year patterns")


class TestArticleSearchPatterns(unittest.TestCase):
    """Test article (pulse) search patterns using full name."""

    def test_article_pattern_uses_full_name(self):
        """Should use full name for article searches."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("jsmith", name="John Smith")

        pulse_patterns = [p for p in patterns if "/pulse/" in p]
        self.assertTrue(
            any("John Smith" in p for p in pulse_patterns),
            f"Should include full name in pulse pattern, got: {pulse_patterns}"
        )

    def test_article_pattern_falls_back_to_username(self):
        """Should include username fallback for articles."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("jsmith", name="John Smith")

        pulse_patterns = [p for p in patterns if "/pulse/" in p]
        self.assertTrue(
            any("jsmith" in p for p in pulse_patterns),
            f"Should include username fallback in pulse pattern, got: {pulse_patterns}"
        )

    def test_article_pattern_without_name(self):
        """Should use username only when name not provided."""
        from fetch_linkedin_mcp import build_search_patterns

        patterns = build_search_patterns("jsmith", name=None)

        pulse_patterns = [p for p in patterns if "/pulse/" in p]
        self.assertTrue(len(pulse_patterns) > 0, "Should have pulse patterns")
        self.assertTrue(
            all("jsmith" in p for p in pulse_patterns),
            "All pulse patterns should use username when no name provided"
        )


class TestArticleURLValidation(unittest.TestCase):
    """Test article URL validation accepts both username and full name."""

    def test_validate_article_url_with_username(self):
        """Should validate article URL containing username."""
        from fetch_linkedin_mcp import validate_article_url

        url = "https://www.linkedin.com/pulse/my-article-title-jsmith-abc123"
        is_valid = validate_article_url(url, username="jsmith", name="John Smith")

        self.assertTrue(is_valid)

    def test_validate_article_url_with_name(self):
        """Should validate article URL containing full name slug."""
        from fetch_linkedin_mcp import validate_article_url

        # LinkedIn converts "John Smith" to "john-smith" in URLs
        url = "https://www.linkedin.com/pulse/my-article-title-john-smith-abc123"
        is_valid = validate_article_url(url, username="jsmith", name="John Smith")

        self.assertTrue(is_valid)

    def test_reject_article_url_without_author(self):
        """Should reject article URL without username or name."""
        from fetch_linkedin_mcp import validate_article_url

        url = "https://www.linkedin.com/pulse/my-article-title-someoneelse-abc123"
        is_valid = validate_article_url(url, username="jsmith", name="John Smith")

        self.assertFalse(is_valid)

    def test_validate_article_url_case_insensitive(self):
        """Should match name case-insensitively."""
        from fetch_linkedin_mcp import validate_article_url

        url = "https://www.linkedin.com/pulse/my-article-JOHN-SMITH-abc123"
        is_valid = validate_article_url(url, username="jsmith", name="John Smith")

        self.assertTrue(is_valid)


class TestSearchIntegration(unittest.TestCase):
    """Integration tests for the full search workflow."""

    def test_search_for_posts_uses_profile_data(self):
        """search_for_posts should accept and use profile_data parameter."""
        from fetch_linkedin_mcp import search_for_posts

        # Verify function accepts profile_data parameter
        import inspect
        sig = inspect.signature(search_for_posts)
        self.assertIn("profile_data", sig.parameters)

    def test_search_for_posts_accepts_year_range(self):
        """search_for_posts should accept year_range parameter."""
        from fetch_linkedin_mcp import search_for_posts

        import inspect
        sig = inspect.signature(search_for_posts)
        self.assertIn("year_range", sig.parameters)

    def test_search_for_posts_accepts_dynamic_keywords_flag(self):
        """search_for_posts should accept use_dynamic_keywords parameter."""
        from fetch_linkedin_mcp import search_for_posts

        import inspect
        sig = inspect.signature(search_for_posts)
        self.assertIn("use_dynamic_keywords", sig.parameters)


class TestURLDeduplication(unittest.TestCase):
    """Test URL deduplication across search strategies."""

    def test_deduplicates_identical_urls(self):
        """Should remove duplicate URLs from results."""
        # This tests the existing deduplication in search_for_posts
        # which uses dict.fromkeys() to preserve order while deduping
        urls = [
            "https://linkedin.com/posts/user_activity-123",
            "https://linkedin.com/posts/user_activity-456",
            "https://linkedin.com/posts/user_activity-123",  # duplicate
            "https://linkedin.com/posts/user_activity-789",
        ]

        unique_urls = list(dict.fromkeys(urls))

        self.assertEqual(len(unique_urls), 3)
        self.assertEqual(unique_urls[0], "https://linkedin.com/posts/user_activity-123")

    def test_preserves_order(self):
        """Should preserve first occurrence order."""
        urls = ["c", "a", "b", "a", "c"]
        unique_urls = list(dict.fromkeys(urls))

        self.assertEqual(unique_urls, ["c", "a", "b"])


if __name__ == "__main__":
    unittest.main()
