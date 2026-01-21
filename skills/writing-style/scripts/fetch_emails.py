#!/usr/bin/env python3
"""
Email Fetcher - Bulk download sent emails via Gmail MCP

Runs outside of Claude to efficiently fetch emails without using tokens.
Saves raw email data to ~/Documents/my-writing-style/raw_samples/

Usage:
    python fetch_emails.py [--count 100]           # First run: get 100 most recent
    python fetch_emails.py                          # Get new emails since last fetch
    python fetch_emails.py --older [--count 50]    # Get older emails (go back in history)
    python fetch_emails.py --holdout 0.15          # Reserve 15% for validation
    python fetch_emails.py --status                 # Show fetch status
    python fetch_emails.py --check                  # Verify MCP server is installed & authenticated
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import subprocess
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
from config import get_data_dir, get_path, get_npx_command
from api_keys import is_mcp_configured_in_chatwise, KNOWN_MCPS

MCP_COMMAND = [get_npx_command(), "-y", "@presto-ai/google-workspace-mcp"]
DATA_DIR = get_data_dir()
OUTPUT_DIR = get_path("raw_samples")
VALIDATION_DIR = get_path("validation_set")
STATE_FILE = get_path("fetch_state.json")

# One-click install URL for ChatWise users
CHATWISE_INSTALL_URL = "https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9"


class MCPClient:
    """Simple MCP client for direct server communication."""
    
    def __init__(self, command):
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=0
        )
        self.msg_id = 0

    def send_request(self, method, params=None):
        self.msg_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method
        }
        if params:
            message["params"] = params
        
        json_str = json.dumps(message)
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()
        return self.msg_id

    def send_notification(self, method, params=None):
        message = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            message["params"] = params
        
        json_str = json.dumps(message)
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()

    def read_response(self, expected_id):
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise Exception("Server closed connection")
            
            try:
                data = json.loads(line)
                if "id" in data and data["id"] == expected_id:
                    if "error" in data:
                        raise Exception(f"MCP Error: {data['error']}")
                    return data["result"]
            except json.JSONDecodeError:
                continue

    def initialize(self):
        print("[CONNECT] Connecting to Gmail MCP server...")
        req_id = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "writing-style-clone", "version": "1.0"}
        })
        self.read_response(req_id)
        self.send_notification("notifications/initialized")
        print("[OK] Connected.")

    def call_tool(self, name, arguments):
        req_id = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        result = self.read_response(req_id)
        return result.get("content", [{}])[0].get("text", "{}")

    def close(self):
        self.process.terminate()


def check_mcp_auth(verbose=True):
    """
    Verify that the Google Workspace MCP server is installed and authenticated.

    Returns:
        tuple: (success: bool, message: str)
    """
    import shutil

    # Check if MCP is configured in Chatwise
    if verbose:
        if is_mcp_configured_in_chatwise(KNOWN_MCPS["google-workspace"]):
            print("[OK] Google Workspace MCP is configured in Chatwise")
        else:
            print("[WARNING]  Google Workspace MCP is not configured in Chatwise (will use npx directly)")

    # Check if npx is available
    if not shutil.which("npx"):
        return False, "npx not found. Please install Node.js first."

    if verbose:
        print("[SEARCH] Checking Google Workspace MCP server...")

    try:
        client = MCPClient(MCP_COMMAND)
        client.initialize()

        # Try a simple API call to verify authentication
        if verbose:
            print("[AUTH] Verifying Gmail authentication...")

        # Search for just 1 email to test auth
        result_json = client.call_tool("gmail.search", {
            "query": "from:me",
            "maxResults": 1
        })
        result = json.loads(result_json)

        client.close()

        # Check if we got a valid response (even empty is fine)
        if "messages" in result or result == {}:
            return True, "Google Workspace MCP is installed and authenticated."
        elif "error" in result:
            error_msg = result.get("error", {}).get("message", str(result))
            if "auth" in error_msg.lower() or "token" in error_msg.lower() or "credential" in error_msg.lower():
                return False, f"Authentication failed: {error_msg}"
            return False, f"API error: {error_msg}"
        else:
            return True, "Google Workspace MCP is installed and authenticated."

    except FileNotFoundError:
        return False, "Google Workspace MCP server not found. npx failed to run the package."
    except Exception as e:
        error_str = str(e).lower()
        if "auth" in error_str or "token" in error_str or "credential" in error_str or "login" in error_str:
            return False, f"Authentication required: {e}"
        elif "connection" in error_str or "closed" in error_str:
            return False, f"MCP server connection failed: {e}"
        else:
            return False, f"MCP check failed: {e}"


def print_install_instructions():
    """Print instructions for installing the Google Workspace MCP server."""
    print(f"\n{'=' * 60}")
    print("GOOGLE WORKSPACE MCP NOT CONFIGURED")
    print(f"{'=' * 60}")
    print("\nThe email pipeline requires the Google Workspace MCP server")
    print("to be installed and authenticated in your chat client.\n")
    print("[PACKAGE] ONE-CLICK INSTALL (ChatWise users):")
    print(f"   {CHATWISE_INSTALL_URL}\n")
    print("[PACKAGE] MANUAL INSTALL (other clients):")
    print("   Add this to your MCP server configuration:")
    print('   {')
    print('     "google-workspace": {')
    print('       "command": "npx",')
    print('       "args": ["-y", "@presto-ai/google-workspace-mcp"]')
    print('     }')
    print('   }')
    print("\nAfter installing, authenticate with your Google account")
    print("when prompted by the MCP server.")
    print(f"{'=' * 60}\n")


def load_state():
    """Load fetch state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "total_fetched": 0,
        "newest_timestamp": None,
        "oldest_timestamp": None,
        "newest_id": None,
        "oldest_id": None,
        "last_fetch": None,
        "fetched_ids": []
    }


def save_state(state):
    """Save fetch state to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_email_timestamp(email_data):
    """Extract timestamp from email data."""
    # Try internalDate first (milliseconds since epoch)
    if "internalDate" in email_data:
        return int(email_data["internalDate"])
    # Fallback to parsing date header
    return 0


def show_status():
    """Display current fetch status."""
    state = load_state()
    
    # Count actual files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_count = len(list(OUTPUT_DIR.glob("email_*.json")))
    
    print(f"\n{'=' * 50}")
    print("EMAIL FETCH STATUS")
    print(f"{'=' * 50}")
    print(f"Emails downloaded: {file_count}")
    print(f"Location: {OUTPUT_DIR}")
    
    if state["last_fetch"]:
        print(f"Last fetch: {state['last_fetch']}")
    
    if state["newest_timestamp"]:
        newest = datetime.fromtimestamp(state["newest_timestamp"] / 1000)
        print(f"Newest email: {newest.strftime('%Y-%m-%d %H:%M')}")
    
    if state["oldest_timestamp"]:
        oldest = datetime.fromtimestamp(state["oldest_timestamp"] / 1000)
        print(f"Oldest email: {oldest.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"{'=' * 50}")
    print("\nCommands:")
    print("  python fetch_emails.py --count 100    # Fetch 100 emails")
    print("  python fetch_emails.py                # Fetch new emails")
    print("  python fetch_emails.py --older        # Fetch older emails")
    print(f"{'=' * 50}\n")


def fetch_emails(count=100, older=False, holdout=0.0):
    """Fetch sent emails and save to raw_samples directory.
    
    Args:
        count: Number of emails to fetch
        older: Fetch older emails instead of newer
        holdout: Fraction of emails to reserve for validation (0.0-0.5)
    """
    import random
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if holdout > 0:
        VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    
    # Build query
    query = "from:me"
    
    if older and state["oldest_timestamp"]:
        # Get emails older than our oldest
        oldest_date = datetime.fromtimestamp(state["oldest_timestamp"] / 1000)
        query += f" before:{oldest_date.strftime('%Y/%m/%d')}"
        print(f"[SEARCH] Fetching emails older than {oldest_date.strftime('%Y-%m-%d')}...")
    elif not older and state["newest_timestamp"]:
        # Get emails newer than our newest
        newest_date = datetime.fromtimestamp(state["newest_timestamp"] / 1000)
        query += f" after:{newest_date.strftime('%Y/%m/%d')}"
        print(f"[SEARCH] Fetching emails newer than {newest_date.strftime('%Y-%m-%d')}...")
    else:
        print(f"[SEARCH] Fetching {count} most recent emails...")
    
    client = MCPClient(MCP_COMMAND)
    
    try:
        client.initialize()

        # Search for sent emails
        search_result_json = client.call_tool("gmail.search", {
            "query": query,
            "maxResults": count
        })
        search_data = json.loads(search_result_json)
        messages = search_data.get("messages", [])
        
        if not messages:
            print("No new emails found.")
            return 0
        
        print(f"Found {len(messages)} emails. Downloading...")

        # Fetch each email
        downloaded = 0
        skipped = 0
        timestamps = []
        
        for msg in messages:
            msg_id = msg["id"]
            file_path = OUTPUT_DIR / f"email_{msg_id}.json"
            
            # Skip if already downloaded
            if file_path.exists() or msg_id in state.get("fetched_ids", []):
                skipped += 1
                continue

            # Fetch full email
            email_json_str = client.call_tool("gmail.get", {"messageId": msg_id})
            email_data = json.loads(email_json_str)
            
            # Determine if this goes to validation set
            is_holdout = holdout > 0 and random.random() < holdout
            
            if is_holdout:
                file_path = VALIDATION_DIR / f"email_{msg_id}.json"
            
            # Save raw data
            with open(file_path, "w") as f:
                json.dump(email_data, f, indent=2)
            
            # Track timestamp
            ts = get_email_timestamp(email_data)
            if ts:
                timestamps.append(ts)
            
            # Track ID
            if "fetched_ids" not in state:
                state["fetched_ids"] = []
            state["fetched_ids"].append(msg_id)
            
            downloaded += 1
            snippet = email_data.get("snippet", "")[:40]
            print(f"  [OK] {msg_id}: {snippet}...")

        # Update state
        if timestamps:
            if state["newest_timestamp"] is None or max(timestamps) > state["newest_timestamp"]:
                state["newest_timestamp"] = max(timestamps)
            if state["oldest_timestamp"] is None or min(timestamps) < state["oldest_timestamp"]:
                state["oldest_timestamp"] = min(timestamps)
        
        state["total_fetched"] = len(state.get("fetched_ids", []))
        state["last_fetch"] = datetime.now().isoformat()
        save_state(state)

        # Report
        print(f"\n{'=' * 50}")
        print(f"FETCH COMPLETE")
        print(f"{'=' * 50}")
        print(f"Downloaded: {downloaded} new emails")
        print(f"Skipped: {skipped} (already existed)")
        print(f"Total in collection: {state['total_fetched']}")
        print(f"Location: {OUTPUT_DIR}")
        print(f"{'=' * 50}")
        
        if downloaded > 0:
            print(f"\n[TIP] Next steps:")
            print(f"   - Run again with --older to fetch more history")
            print(f"   - Start analysis in ChatWise: 'Continue cloning my writing style'")
        
        return downloaded

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch sent emails via Gmail MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_emails.py --check        # Verify MCP server is configured
  python fetch_emails.py --count 100    # First run: get 100 most recent
  python fetch_emails.py                # Get new emails since last fetch
  python fetch_emails.py --older        # Get older emails (go back in history)
  python fetch_emails.py --status       # Show fetch status
        """
    )
    parser.add_argument("--check", action="store_true",
                        help="Verify Google Workspace MCP is installed and authenticated")
    parser.add_argument("--count", type=int, default=300,
                        help="Number of emails to fetch (default: 300)")
    parser.add_argument("--older", action="store_true",
                        help="Fetch older emails (go back in history)")
    parser.add_argument("--holdout", type=float, default=0.0,
                        help="Fraction to reserve for validation (e.g., 0.15 for 15%%)")
    parser.add_argument("--status", action="store_true",
                        help="Show current fetch status")
    parser.add_argument("--skip-check", action="store_true",
                        help="Skip MCP verification before fetching")

    args = parser.parse_args()

    if args.check:
        # Just run the check and exit
        success, message = check_mcp_auth(verbose=True)
        if success:
            print(f"\n[OK] {message}")
            sys.exit(0)
        else:
            print(f"\n[ERROR] {message}")
            print_install_instructions()
            sys.exit(1)
    elif args.status:
        show_status()
    else:
        # Verify MCP auth before fetching (unless skipped)
        if not args.skip_check:
            success, message = check_mcp_auth(verbose=True)
            if not success:
                print(f"\n[ERROR] {message}")
                print_install_instructions()
                sys.exit(1)
            print(f"[OK] {message}\n")

        fetch_emails(count=args.count, older=args.older, holdout=args.holdout)
