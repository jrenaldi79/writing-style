#!/usr/bin/env python3
"""
API Key Management - Fetches API keys from Chatwise or environment variables.

Priority order:
1. Chatwise application database (if available)
2. Environment variable
3. Error with setup instructions

Supported services:
- OpenRouter (for LLM validation)
- BrightData (for LinkedIn scraping via MCP)
"""

import sqlite3
import json
import os
import sys
from pathlib import Path


def get_chatwise_db_path() -> Path:
    """Get the Chatwise database path for the current platform."""
    if sys.platform == "darwin":
        # macOS
        return Path.home() / "Library" / "Application Support" / "app.chatwise" / "app.db"
    elif sys.platform == "win32":
        # Windows (AppData\Roaming)
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "app.chatwise" / "app.db"
    else:
        # Linux (~/.config)
        return Path.home() / ".config" / "app.chatwise" / "app.db"

    return None


# =============================================================================
# OpenRouter API Key
# =============================================================================

def get_openrouter_key_from_chatwise() -> str | None:
    """
    Reads the OpenRouter API key from the local Chatwise database.
    Returns the key as a string, or None if not found.
    """
    db_path = get_chatwise_db_path()

    if not db_path or not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM kv WHERE key = 'config'")
        row = cursor.fetchone()
        conn.close()

        if row:
            config = json.loads(row[0])
            return config.get("openrouter_api_key")

    except Exception:
        # Silently fail - will fall back to environment variable
        return None

    return None


def get_openrouter_key(require: bool = True) -> str | None:
    """
    Get OpenRouter API key from Chatwise or environment variable.

    Priority:
    1. Chatwise application database
    2. OPENROUTER_API_KEY environment variable

    Args:
        require: If True, exit with error if key not found. If False, return None.

    Returns:
        API key string, or None if not found and require=False
    """
    # Try Chatwise first
    key = get_openrouter_key_from_chatwise()
    if key:
        return key

    # Fall back to environment variable
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    # Not found
    if require:
        print("=" * 60)
        print("ERROR: OpenRouter API key not found")
        print("=" * 60)
        print()
        print("Option 1: Configure in Chatwise")
        print("  Open Chatwise settings and add your OpenRouter API key")
        print()
        print("Option 2: Set environment variable")
        print("  export OPENROUTER_API_KEY='your-key-here'")
        print()
        print("Get your key at: https://openrouter.ai/keys")
        print("=" * 60)
        sys.exit(1)

    return None


# =============================================================================
# MCP Server Configuration Check
# =============================================================================

# Known MCP packages used by this project
KNOWN_MCPS = {
    "brightdata": "@brightdata/mcp",
    "google-workspace": "@presto-ai/google-workspace-mcp"
}


def get_mcp_status(mcp_package: str) -> dict | None:
    """
    Get detailed status of a specific MCP server in Chatwise.

    Args:
        mcp_package: The npm package name to look for (e.g., '@brightdata/mcp')

    Returns:
        Dict with 'installed', 'enabled', 'display_name', 'command' or None if not found
    """
    db_path = get_chatwise_db_path()

    if not db_path or not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get all tool configs with enabled status and display name
        cursor.execute("SELECT config, enabled, displayName FROM tool")
        rows = cursor.fetchall()
        conn.close()

        for config_str, enabled, display_name in rows:
            if not config_str:
                continue

            try:
                config = json.loads(config_str)

                # Only check stdio tools (MCP servers)
                if config.get("type") != "stdio":
                    continue

                command = config.get("command", "")

                # Check if this is the MCP we're looking for
                if mcp_package in command:
                    return {
                        "installed": True,
                        "enabled": bool(enabled),
                        "display_name": display_name or "Unknown",
                        "command": command
                    }

                # Also check args (some configs use args array)
                args = config.get("args", [])
                if isinstance(args, list):
                    for arg in args:
                        if mcp_package in str(arg):
                            return {
                                "installed": True,
                                "enabled": bool(enabled),
                                "display_name": display_name or "Unknown",
                                "command": command
                            }

            except json.JSONDecodeError:
                continue

    except Exception:
        return None

    return None


def is_mcp_configured_in_chatwise(mcp_package: str, require_enabled: bool = True) -> bool:
    """
    Check if a specific MCP server is configured (and optionally enabled) in Chatwise.

    Args:
        mcp_package: The npm package name to look for (e.g., '@brightdata/mcp')
        require_enabled: If True, also check that the MCP is enabled (default: True)

    Returns:
        True if the MCP is configured (and enabled if required), False otherwise
    """
    status = get_mcp_status(mcp_package)

    if status is None:
        return False

    if require_enabled:
        return status["installed"] and status["enabled"]

    return status["installed"]


def _extract_package_from_command(command: str) -> str | None:
    """
    Extract npm package name from a command string.

    Examples:
        'npx @brightdata/mcp' -> '@brightdata/mcp'
        'npx -y @presto-ai/google-workspace-mcp' -> '@presto-ai/google-workspace-mcp'
        'node /path/to/script.js' -> None
    """
    import re

    # Look for @scope/package pattern anywhere in the command
    match = re.search(r'@[\w-]+/[\w-]+', command)
    if match:
        return match.group(0)

    # Look for package-mcp or mcp-package patterns
    match = re.search(r'\b[\w-]+-mcp\b|\bmcp-[\w-]+\b', command)
    if match:
        return match.group(0)

    return None


def get_configured_mcps() -> list[dict]:
    """
    Get a list of all MCP servers configured in Chatwise with their status.

    Returns:
        List of dicts with 'package', 'enabled', 'display_name', 'command'
    """
    db_path = get_chatwise_db_path()

    if not db_path or not db_path.exists():
        return []

    mcps = []

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT config, enabled, displayName FROM tool")
        rows = cursor.fetchall()
        conn.close()

        for config_str, enabled, display_name in rows:
            if not config_str:
                continue

            try:
                config = json.loads(config_str)

                # Only check stdio tools (MCP servers)
                if config.get("type") != "stdio":
                    continue

                command = config.get("command", "")

                # Extract package name from command
                package = _extract_package_from_command(command)

                # Also check args if no package found in command
                if not package:
                    args = config.get("args", [])
                    if isinstance(args, list):
                        for arg in args:
                            package = _extract_package_from_command(str(arg))
                            if package:
                                break

                if package:
                    mcps.append({
                        "package": package,
                        "enabled": bool(enabled),
                        "display_name": display_name or "Unknown",
                        "command": command
                    })

            except json.JSONDecodeError:
                continue

    except Exception:
        pass

    return mcps


def check_required_mcps() -> dict:
    """
    Check status of all MCP servers required by this project.

    Returns:
        Dict with results for each known MCP
    """
    results = {}

    for name, package in KNOWN_MCPS.items():
        status = get_mcp_status(package)
        if status:
            results[name] = {
                "package": package,
                "installed": True,
                "enabled": status["enabled"],
                "display_name": status["display_name"]
            }
        else:
            results[name] = {
                "package": package,
                "installed": False,
                "enabled": False,
                "display_name": None
            }

    return results


# =============================================================================
# BrightData API Token (for LinkedIn MCP)
# =============================================================================

def get_brightdata_token_from_chatwise() -> str | None:
    """
    Scans the Chatwise tool database for the Bright Data MCP server
    (identified by its launch command 'npx @brightdata/mcp')
    and returns the API_TOKEN.
    """
    db_path = get_chatwise_db_path()

    if not db_path or not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Fetch all tool configurations
        cursor.execute("SELECT config FROM tool")
        rows = cursor.fetchall()
        conn.close()

        for (config_str,) in rows:
            if not config_str:
                continue

            try:
                config = json.loads(config_str)
                command = config.get("command", "")

                # Validate: Ensure it is the Bright Data MCP
                if "@brightdata/mcp" in command:

                    # The 'env' field is stored as a newline-separated string
                    # e.g., "API_TOKEN=123\nGROUPS=..."
                    env_str = config.get("env", "")

                    if isinstance(env_str, str):
                        # Parse the env string line by line
                        for line in env_str.split('\n'):
                            if line.startswith("API_TOKEN="):
                                return line.split("=", 1)[1].strip()

                    # Fallback: sometimes env might be a dict in other versions
                    elif isinstance(env_str, dict):
                        return env_str.get("API_TOKEN")

            except json.JSONDecodeError:
                continue

    except Exception:
        # Silently fail - will fall back to environment variable
        return None

    return None


def get_brightdata_token(require: bool = True) -> str | None:
    """
    Get BrightData API token from Chatwise or environment variable.

    Priority:
    1. Chatwise MCP tool configuration (looks for @brightdata/mcp)
    2. BRIGHTDATA_API_TOKEN environment variable

    Args:
        require: If True, exit with error if token not found. If False, return None.

    Returns:
        API token string, or None if not found and require=False
    """
    # Try Chatwise first
    token = get_brightdata_token_from_chatwise()
    if token:
        return token

    # Fall back to environment variable
    token = os.environ.get("BRIGHTDATA_API_TOKEN")
    if token:
        return token

    # Not found
    if require:
        print("=" * 60)
        print("ERROR: BrightData API token not found")
        print("=" * 60)
        print()
        print("Option 1: Configure BrightData MCP in Chatwise")
        print("  Add the @brightdata/mcp tool with your API_TOKEN")
        print()
        print("Option 2: Set environment variable")
        print("  export BRIGHTDATA_API_TOKEN='your-token-here'")
        print()
        print("Get your token at: https://brightdata.com/")
        print("=" * 60)
        sys.exit(1)

    return None


# =============================================================================
# Generic API Key Function
# =============================================================================

def get_api_key(service: str, require: bool = True) -> str | None:
    """
    Get API key for a service.

    Supported services:
    - openrouter: OpenRouter API key (for LLM validation)
    - brightdata: BrightData API token (for LinkedIn scraping)

    Args:
        service: Service name (e.g., 'openrouter', 'brightdata')
        require: If True, exit with error if key not found

    Returns:
        API key string, or None if not found and require=False
    """
    service_lower = service.lower()

    if service_lower == "openrouter":
        return get_openrouter_key(require=require)
    elif service_lower == "brightdata":
        return get_brightdata_token(require=require)
    else:
        raise ValueError(f"Unknown service: {service}. Supported: openrouter, brightdata")


# =============================================================================
# CLI
# =============================================================================

def _mask_key(key: str) -> str:
    """Mask a key for display, showing only first 8 and last 4 chars."""
    if len(key) > 12:
        return f"{key[:8]}...{key[-4:]}"
    return "[hidden]"


def _check_service(service: str, show_source: bool = False) -> bool:
    """Check if a service key is available. Returns True if found."""
    if service == "openrouter":
        chatwise_key = get_openrouter_key_from_chatwise()
        env_key = os.environ.get("OPENROUTER_API_KEY")
        env_var_name = "OPENROUTER_API_KEY"
    elif service == "brightdata":
        chatwise_key = get_brightdata_token_from_chatwise()
        env_key = os.environ.get("BRIGHTDATA_API_TOKEN")
        env_var_name = "BRIGHTDATA_API_TOKEN"
    else:
        print(f"Unknown service: {service}")
        return False

    if show_source:
        if chatwise_key:
            print(f"{service.upper()}")
            print(f"  Source: Chatwise application database")
            print(f"  Key: {_mask_key(chatwise_key)}")
            return True
        elif env_key:
            print(f"{service.upper()}")
            print(f"  Source: {env_var_name} environment variable")
            print(f"  Key: {_mask_key(env_key)}")
            return True
        else:
            print(f"{service.upper()}")
            print(f"  Source: Not found")
            return False
    else:
        if chatwise_key or env_key:
            print(f"{service.upper()}: Available")
            return True
        else:
            print(f"{service.upper()}: Not configured")
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="API Key and MCP Configuration Management")
    parser.add_argument("--check", action="store_true",
                        help="Check if API keys are available")
    parser.add_argument("--source", action="store_true",
                        help="Show where each key was found")
    parser.add_argument("--service", choices=["openrouter", "brightdata", "all"],
                        default="all", help="Which service to check (default: all)")
    parser.add_argument("--mcps", action="store_true",
                        help="List MCP servers configured in Chatwise")
    parser.add_argument("--check-mcp", metavar="PACKAGE",
                        help="Check if specific MCP is configured (e.g., '@brightdata/mcp')")
    parser.add_argument("--check-required", action="store_true",
                        help="Check all MCP servers required by this project")

    args = parser.parse_args()

    if args.mcps:
        mcps = get_configured_mcps()
        if mcps:
            print("MCP Servers configured in Chatwise:")
            for mcp in mcps:
                status = "Enabled" if mcp["enabled"] else "Disabled"
                print(f"  - {mcp['package']}")
                print(f"      Name: {mcp['display_name']}")
                print(f"      Status: {status}")
        else:
            print("No MCP servers found in Chatwise configuration")
        sys.exit(0)

    if args.check_required:
        print("Required MCP Servers:")
        print("-" * 40)
        results = check_required_mcps()
        all_ok = True

        for name, info in results.items():
            if info["installed"]:
                status = "Enabled" if info["enabled"] else "Disabled"
                icon = "[OK]" if info["enabled"] else "[WARNING]"
                print(f"{icon} {name}: {info['display_name']} ({status})")
            else:
                print(f"[ERROR] {name}: NOT INSTALLED")
                all_ok = False

        sys.exit(0 if all_ok else 1)

    if args.check_mcp:
        status = get_mcp_status(args.check_mcp)
        if status:
            enabled_str = "Enabled" if status["enabled"] else "Disabled"
            print(f"[OK] {args.check_mcp} is configured in Chatwise")
            print(f"   Name: {status['display_name']}")
            print(f"   Status: {enabled_str}")
            sys.exit(0 if status["enabled"] else 1)
        else:
            print(f"[ERROR] {args.check_mcp} is NOT configured in Chatwise")
            sys.exit(1)

    if args.check or args.source:
        services = ["openrouter", "brightdata"] if args.service == "all" else [args.service]
        all_found = True

        for service in services:
            if not _check_service(service, show_source=args.source):
                all_found = False
            if args.source and service != services[-1]:
                print()  # Blank line between services

        sys.exit(0 if all_found else 1)
    else:
        parser.print_help()
