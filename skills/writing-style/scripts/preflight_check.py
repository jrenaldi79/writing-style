#!/usr/bin/env python3
"""
Pre-flight validation for Writing Style Clone setup.

Checks Python environment, dependencies, and platform-specific requirements
before running the main pipeline.

Usage:
    python preflight_check.py           # Run all checks
    python preflight_check.py --quiet   # Only show failures
"""

import sys
import platform
import subprocess
import importlib.util
import argparse
from pathlib import Path


def check_python():
    """
    Verify Python version and core modules.

    Returns:
        tuple: (success: bool, message: str)
    """
    version = sys.version_info
    if version < (3, 10):
        return False, f"Python {version.major}.{version.minor} (need 3.10+)"

    # Check core modules that should always be present
    required_modules = ['encodings', 'json', 'pathlib', 'argparse']
    for mod in required_modules:
        if importlib.util.find_spec(mod) is None:
            return False, f"Missing core module: {mod}"

    return True, f"Python {sys.version.split()[0]} OK"


def check_npx():
    """
    Verify npx is available and working.

    Returns:
        tuple: (success: bool, message: str)
    """
    cmd = "npx.cmd" if platform.system() == "Windows" else "npx"
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"npx {version} OK"
        else:
            return False, f"npx returned error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "npx not found - install Node.js from https://nodejs.org"
    except subprocess.TimeoutExpired:
        return False, "npx timed out"
    except Exception as e:
        return False, f"npx check failed: {e}"


def check_venv():
    """
    Verify virtual environment is active.

    Returns:
        tuple: (success: bool, message: str)
    """
    venv_path = sys.prefix
    base_path = getattr(sys, 'base_prefix', sys.prefix)

    if venv_path != base_path:
        return True, f"Virtual env active: {Path(venv_path).name}"
    else:
        return False, "No virtual environment active - run: python -m venv venv && source venv/bin/activate"


def check_dependencies():
    """
    Verify required Python packages are installed.

    Returns:
        tuple: (success: bool, message: str)
    """
    required = ['requests', 'numpy']
    optional = ['sentence_transformers', 'sklearn']

    missing_required = []
    missing_optional = []

    for pkg in required:
        if importlib.util.find_spec(pkg) is None:
            missing_required.append(pkg)

    for pkg in optional:
        if importlib.util.find_spec(pkg) is None:
            missing_optional.append(pkg)

    if missing_required:
        return False, f"Missing required packages: {', '.join(missing_required)}"

    if missing_optional:
        return True, f"OK (optional missing: {', '.join(missing_optional)})"

    return True, "All dependencies installed"


def check_data_dir():
    """
    Verify data directory is accessible.

    Returns:
        tuple: (success: bool, message: str)
    """
    # Import config to get data directory
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    try:
        from config import get_data_dir
        data_dir = get_data_dir()

        # Try to create if it doesn't exist
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            return True, f"Data dir: {data_dir}"
        except PermissionError:
            return False, f"Cannot create data directory: {data_dir}"
        except Exception as e:
            return False, f"Data directory error: {e}"
    finally:
        sys.path.pop(0)


def run_preflight(quiet=False):
    """
    Run all preflight checks.

    Args:
        quiet: Only show failures

    Returns:
        bool: True if all checks passed
    """
    checks = [
        ("Python", check_python),
        ("Virtual Env", check_venv),
        ("NPX", check_npx),
        ("Dependencies", check_dependencies),
        ("Data Directory", check_data_dir),
    ]

    print("=" * 50)
    print("WRITING STYLE CLONE - PREFLIGHT CHECK")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("=" * 50)

    all_passed = True

    for name, check_fn in checks:
        try:
            passed, message = check_fn()
        except Exception as e:
            passed = False
            message = f"Check failed: {e}"

        if not passed:
            all_passed = False
            print(f"[ERROR] {name}: {message}")
        elif not quiet:
            print(f"[OK] {name}: {message}")

    print("=" * 50)

    if all_passed:
        print("All checks passed. Ready to run pipeline.")
    else:
        print("Some checks failed. Fix issues before running pipeline.")
        print("\nFor help, see: references/troubleshooting.md")

    print("=" * 50)

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pre-flight validation for Writing Style Clone"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show failures"
    )

    args = parser.parse_args()
    success = run_preflight(quiet=args.quiet)
    sys.exit(0 if success else 1)
