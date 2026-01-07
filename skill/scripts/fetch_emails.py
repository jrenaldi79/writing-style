#!/usr/bin/env python3
"""
Email Fetcher - Bulk download sent emails via Gmail MCP

Runs outside of Claude to efficiently fetch emails without using tokens.
Saves raw email data to ~/Documents/my-writing-style/raw_samples/

Usage:
    python fetch_emails.py [--count 100]           # First run: get 100 most recent
    python fetch_emails.py                          # Get new emails since last fetch
    python fetch_emails.py --older [--count 50]    # Get older emails (go back in history)
    python fetch_emails.py --status                 # Show fetch status
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
MCP_COMMAND = ["npx", "-y", "@presto-ai/google-workspace-mcp"]
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
OUTPUT_DIR = DATA_DIR / "raw_samples"
STATE_FILE = DATA_DIR / "fetch_state.json"


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
        print("🔌 Connecting to Gmail MCP server...")
        req_id = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "writing-style-clone", "version": "1.0"}
        })
        self.read_response(req_id)
        self.send_notification("notifications/initialized")
        print("✅ Connected.")

    def call_tool(self, name, arguments):
        req_id = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        result = self.read_response(req_id)
        return result.get("content", [{}])[0].get("text", "{}")

    def close(self):
        self.process.terminate()


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
    
    print(f"\n{'═' * 50}")
    print("EMAIL FETCH STATUS")
    print(f"{'═' * 50}")
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
    
    print(f"{'═' * 50}")
    print("\nCommands:")
    print("  python fetch_emails.py --count 100    # Fetch 100 emails")
    print("  python fetch_emails.py                # Fetch new emails")
    print("  python fetch_emails.py --older        # Fetch older emails")
    print(f"{'═' * 50}\n")


def fetch_emails(count=100, older=False):
    """Fetch sent emails and save to raw_samples directory."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    
    # Build query
    query = "from:me"
    
    if older and state["oldest_timestamp"]:
        # Get emails older than our oldest
        oldest_date = datetime.fromtimestamp(state["oldest_timestamp"] / 1000)
        query += f" before:{oldest_date.strftime('%Y/%m/%d')}"
        print(f"🔍 Fetching emails older than {oldest_date.strftime('%Y-%m-%d')}...")
    elif not older and state["newest_timestamp"]:
        # Get emails newer than our newest
        newest_date = datetime.fromtimestamp(state["newest_timestamp"] / 1000)
        query += f" after:{newest_date.strftime('%Y/%m/%d')}"
        print(f"🔍 Fetching emails newer than {newest_date.strftime('%Y-%m-%d')}...")
    else:
        print(f"🔍 Fetching {count} most recent emails...")
    
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
            print(f"  ✓ {msg_id}: {snippet}...")

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
        print(f"\n{'═' * 50}")
        print(f"FETCH COMPLETE")
        print(f"{'═' * 50}")
        print(f"Downloaded: {downloaded} new emails")
        print(f"Skipped: {skipped} (already existed)")
        print(f"Total in collection: {state['total_fetched']}")
        print(f"Location: {OUTPUT_DIR}")
        print(f"{'═' * 50}")
        
        if downloaded > 0:
            print(f"\n💡 Next steps:")
            print(f"   • Run again with --older to fetch more history")
            print(f"   • Start analysis in ChatWise: 'Continue cloning my writing style'")
        
        return downloaded

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch sent emails via Gmail MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_emails.py --count 100    # First run: get 100 most recent
  python fetch_emails.py                # Get new emails since last fetch  
  python fetch_emails.py --older        # Get older emails (go back in history)
  python fetch_emails.py --status       # Show fetch status
        """
    )
    parser.add_argument("--count", type=int, default=100, 
                        help="Number of emails to fetch (default: 100)")
    parser.add_argument("--older", action="store_true",
                        help="Fetch older emails (go back in history)")
    parser.add_argument("--status", action="store_true",
                        help="Show current fetch status")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        fetch_emails(count=args.count, older=args.older)
