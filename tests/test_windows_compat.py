#!/usr/bin/env python3
"""
Tests for Windows compatibility.

Ensures scripts work correctly on Windows by checking:
1. No emoji characters in output (Windows console encoding issues)
2. sys.path fix present in scripts with local imports
3. NPX command uses platform-aware helper function
"""

import unittest
import re
import sys
from pathlib import Path

# Scripts directory
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"


class TestNoEmojisInScripts(unittest.TestCase):
    """Test that scripts use ASCII-only output for Windows compatibility."""

    # Regex pattern for common emojis used in console output
    EMOJI_PATTERN = re.compile(
        r'[\U0001F300-\U0001F9FF]'  # Misc symbols & pictographs
        r'|[\U00002700-\U000027BF]'  # Dingbats
        r'|[\U0001F600-\U0001F64F]'  # Emoticons
        r'|[\U0001F680-\U0001F6FF]'  # Transport & map symbols
        r'|[\U00002600-\U000026FF]'  # Misc symbols
        r'|[\U00002300-\U000023FF]'  # Misc technical
        r'|[\u2705\u2714\u2716\u274C\u26A0]'  # Common checkmarks/crosses/warning
    )

    def get_script_files(self):
        """Get all Python scripts in the scripts directory."""
        return list(SCRIPTS_DIR.glob("*.py"))

    def test_no_emojis_in_scripts(self):
        """Scripts should use ASCII-only output for Windows console compatibility."""
        for script_path in self.get_script_files():
            with self.subTest(script=script_path.name):
                content = script_path.read_text(encoding='utf-8')
                matches = self.EMOJI_PATTERN.findall(content)
                self.assertEqual(
                    len(matches), 0,
                    f"{script_path.name} contains emojis: {matches[:5]}..."
                    if len(matches) > 5 else f"{script_path.name} contains emojis: {matches}"
                )


class TestSysPathFix(unittest.TestCase):
    """Test that scripts with local imports have sys.path fix."""

    # Scripts that import local modules and need sys.path fix
    SCRIPTS_NEEDING_FIX = [
        "analyze_clusters.py",
        "cluster_emails.py",
        "cluster_linkedin.py",
        "embed_emails.py",
        "enrich_emails.py",
        "fetch_emails.py",
        "fetch_linkedin_mcp.py",
        "filter_emails.py",
        "filter_linkedin.py",
        "generate_skill.py",
        "generate_system_prompt.py",
        "ingest.py",
        "merge_llm_analysis.py",
        "prepare_batch.py",
        "prepare_llm_analysis.py",
        "prepare_validation.py",
        "validate_personas.py",
    ]

    def test_scripts_have_syspath_fix(self):
        """Scripts with local imports should have sys.path.insert fix."""
        for script_name in self.SCRIPTS_NEEDING_FIX:
            script_path = SCRIPTS_DIR / script_name
            if not script_path.exists():
                continue  # Skip if script doesn't exist

            with self.subTest(script=script_name):
                content = script_path.read_text(encoding='utf-8')
                # Check for the sys.path.insert pattern
                self.assertIn(
                    "sys.path.insert(0,",
                    content,
                    f"{script_name} missing sys.path.insert fix for Windows imports"
                )


class TestNpxCommand(unittest.TestCase):
    """Test that NPX commands are platform-aware."""

    def test_config_has_get_npx_command(self):
        """config.py should have get_npx_command() helper function."""
        config_path = SCRIPTS_DIR / "config.py"
        content = config_path.read_text(encoding='utf-8')
        self.assertIn(
            "def get_npx_command",
            content,
            "config.py should define get_npx_command() helper"
        )

    def test_get_npx_command_uses_platform(self):
        """get_npx_command should detect Windows platform."""
        config_path = SCRIPTS_DIR / "config.py"
        content = config_path.read_text(encoding='utf-8')
        self.assertIn(
            "platform",
            content,
            "config.py should import/use platform module for OS detection"
        )

    def test_fetch_emails_uses_npx_helper(self):
        """fetch_emails.py should use get_npx_command() helper."""
        script_path = SCRIPTS_DIR / "fetch_emails.py"
        content = script_path.read_text(encoding='utf-8')
        self.assertIn(
            "get_npx_command",
            content,
            "fetch_emails.py should use get_npx_command() for platform compatibility"
        )

    def test_fetch_linkedin_uses_npx_helper(self):
        """fetch_linkedin_mcp.py should use get_npx_command() helper."""
        script_path = SCRIPTS_DIR / "fetch_linkedin_mcp.py"
        content = script_path.read_text(encoding='utf-8')
        self.assertIn(
            "get_npx_command",
            content,
            "fetch_linkedin_mcp.py should use get_npx_command() for platform compatibility"
        )


class TestPreflightCheck(unittest.TestCase):
    """Test that preflight check script exists and is functional."""

    def test_preflight_script_exists(self):
        """preflight_check.py should exist in scripts directory."""
        preflight_path = SCRIPTS_DIR / "preflight_check.py"
        self.assertTrue(
            preflight_path.exists(),
            "preflight_check.py should exist for Windows setup validation"
        )

    def test_preflight_is_importable(self):
        """preflight_check.py should be importable."""
        preflight_path = SCRIPTS_DIR / "preflight_check.py"
        if not preflight_path.exists():
            self.skipTest("preflight_check.py not yet created")

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            import preflight_check
            self.assertTrue(hasattr(preflight_check, 'check_python'))
            self.assertTrue(hasattr(preflight_check, 'check_npx'))
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
