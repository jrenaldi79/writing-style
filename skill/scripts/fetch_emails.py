#!/usr/bin/env python3
"""
Email Fetcher - Bulk download sent emails via Gmail MCP

Runs outside of Claude to efficiently fetch emails without using tokens.
Saves raw email data to ~/Documents/my-writing-style/raw_samples/

Usage:
    python fetch_emails.py [--count 20]
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path

# Configuration
MCP_COMMAND = ["npx", "-y", "@anthropic-ai/google-workspace-mcp"]
OUTPUT_DIR = Path.home() / "Documents" / "my-writing-style" / "raw_samples"


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


def fetch_emails(count=20):
    """Fetch sent emails and save to raw_samples directory."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MCPClient(MCP_COMMAND)
    
    try:
        client.initialize()

        # Search for sent emails
        print(f"🔍 Searching for last {count} sent emails...")
        search_result_json = client.call_tool("gmail.search", {
            "query": "from:me",
            "maxResults": count
        })
        search_data = json.loads(search_result_json)
        messages = search_data.get("messages", [])
        
        print(f"Found {len(messages)} emails. Downloading...")

        # Fetch each email
        downloaded = 0
        skipped = 0
        
        for msg in messages:
            msg_id = msg["id"]
            file_path = OUTPUT_DIR / f"email_{msg_id}.json"
            
            # Skip if already downloaded
            if file_path.exists():
                skipped += 1
                continue

            # Fetch full email
            email_json_str = client.call_tool("gmail.get", {"messageId": msg_id})
            email_data = json.loads(email_json_str)
            
            # Save raw data
            with open(file_path, "w") as f:
                json.dump(email_data, f, indent=2)
            
            downloaded += 1
            snippet = email_data.get("snippet", "")[:40]
            print(f"  ✓ {msg_id}: {snippet}...")

        print(f"\n{'═' * 40}")
        print(f"FETCH COMPLETE")
        print(f"{'═' * 40}")
        print(f"Downloaded: {downloaded} new emails")
        print(f"Skipped: {skipped} (already existed)")
        print(f"Location: {OUTPUT_DIR}")
        print(f"{'═' * 40}")
        
        return downloaded

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch sent emails via Gmail MCP")
    parser.add_argument("--count", type=int, default=20, help="Number of emails to fetch")
    args = parser.parse_args()
    
    fetch_emails(args.count)
