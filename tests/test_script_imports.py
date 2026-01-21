#!/usr/bin/env python3
"""
Tests for script import validation and basic syntax checking.

Ensures all scripts can be imported without errors and have required
standard library imports for the functions they use.
"""

import unittest
import ast
import sys
from pathlib import Path

# Scripts directory
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"


class TestScriptImports(unittest.TestCase):
    """Test that all scripts have valid imports and syntax."""

    def get_script_files(self):
        """Get all Python scripts in the scripts directory."""
        return list(SCRIPTS_DIR.glob("*.py"))

    def test_all_scripts_parse(self):
        """All scripts should parse without syntax errors."""
        for script_path in self.get_script_files():
            with self.subTest(script=script_path.name):
                try:
                    with open(script_path, 'r') as f:
                        source = f.read()
                    ast.parse(source)
                except SyntaxError as e:
                    self.fail(f"{script_path.name} has syntax error: {e}")

    def test_sys_import_when_sys_exit_used(self):
        """Scripts using sys.exit() must import sys."""
        for script_path in self.get_script_files():
            with self.subTest(script=script_path.name):
                with open(script_path, 'r') as f:
                    source = f.read()

                # Check if sys.exit is used
                if 'sys.exit' in source:
                    # Parse and check imports
                    tree = ast.parse(source)
                    imports = set()

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])

                    self.assertIn('sys', imports,
                        f"{script_path.name} uses sys.exit() but doesn't import sys")

    def test_json_import_when_json_used(self):
        """Scripts using json module must import json."""
        for script_path in self.get_script_files():
            with self.subTest(script=script_path.name):
                with open(script_path, 'r') as f:
                    source = f.read()

                # Check if json is used (json.load, json.dump, json.loads, json.dumps)
                if 'json.load' in source or 'json.dump' in source:
                    tree = ast.parse(source)
                    imports = set()

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])

                    self.assertIn('json', imports,
                        f"{script_path.name} uses json module but doesn't import json")

    def test_scripts_importable(self):
        """All scripts should be importable without errors."""
        # Add scripts directory to path temporarily
        sys.path.insert(0, str(SCRIPTS_DIR))

        try:
            for script_path in self.get_script_files():
                module_name = script_path.stem

                # Skip __init__ if it exists
                if module_name.startswith('__'):
                    continue

                with self.subTest(script=script_path.name):
                    try:
                        # Just check that import doesn't raise
                        __import__(module_name)
                    except ImportError as e:
                        # ImportError for missing dependencies is OK
                        # (e.g., sentence_transformers not installed)
                        if 'No module named' in str(e):
                            pass  # Optional dependency
                        else:
                            self.fail(f"{script_path.name} import failed: {e}")
                    except Exception as e:
                        # Other errors (like NameError) are failures
                        self.fail(f"{script_path.name} failed on import: {type(e).__name__}: {e}")
        finally:
            sys.path.pop(0)


class TestAnalyzeClustersConfig(unittest.TestCase):
    """Test analyze_clusters.py configuration and model handling."""

    def test_default_model_defined(self):
        """DEFAULT_MODEL should be defined in analyze_clusters."""
        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            import analyze_clusters
            self.assertTrue(hasattr(analyze_clusters, 'DEFAULT_MODEL'),
                "analyze_clusters.py should define DEFAULT_MODEL")
            self.assertIsInstance(analyze_clusters.DEFAULT_MODEL, str)
            self.assertIn('/', analyze_clusters.DEFAULT_MODEL,
                "DEFAULT_MODEL should be a valid model ID (org/model format)")
        finally:
            sys.path.pop(0)

    def test_recommended_models_defined(self):
        """RECOMMENDED_MODELS should have required keys."""
        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            import analyze_clusters
            self.assertTrue(hasattr(analyze_clusters, 'RECOMMENDED_MODELS'))

            required_keys = ['cost_effective', 'budget', 'quality']
            for key in required_keys:
                self.assertIn(key, analyze_clusters.RECOMMENDED_MODELS,
                    f"RECOMMENDED_MODELS missing '{key}' key")
        finally:
            sys.path.pop(0)

    def test_model_pricing_has_default(self):
        """MODEL_PRICING should have 'default' fallback entry."""
        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            import analyze_clusters
            self.assertIn('default', analyze_clusters.MODEL_PRICING,
                "MODEL_PRICING should have 'default' fallback")
            self.assertIn('input', analyze_clusters.MODEL_PRICING['default'])
            self.assertIn('output', analyze_clusters.MODEL_PRICING['default'])
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
