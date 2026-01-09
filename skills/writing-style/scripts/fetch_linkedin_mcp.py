#!/usr/bin/env python3
"""
LinkedIn Post Fetcher - Bulk download LinkedIn posts via BrightData MCP

Runs outside of Claude to efficiently fetch LinkedIn posts without using tokens.
Uses BrightData Social Media Scraper MCP server (same pattern as fetch_emails.py).

Usage:
    python fetch_linkedin_mcp.py --profile <url_or_username> [--limit 20] [--token YOUR_TOKEN]
    python fetch_linkedin_mcp.py --profile "https://linkedin.com/in/renaldi" --limit 20
    python fetch_linkedin_mcp.py --profile "renaldi" --limit 15
    python fetch_linkedin_mcp.py --status

Environment:
    MCP_TOKEN: Your BrightData API token (or use --token flag)
"""

import subprocess
import json
import sys
import argparse
import re
import os
import time
from pathlib import Path
from datetime import datetime

# Configuration - BrightData MCP Server (NPX-based, like Gmail)
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
OUTPUT_DIR = get_path("linkedin_data")
STATE_FILE = get_path("linkedin_fetch_state.json")


def get_mcp_command(token):
    """Build MCP command with token in environment."""
    return {
        "command": ["npx", "@brightdata/mcp"],
        "env": {
            "API_TOKEN": token,
            "GROUPS": "advanced_scraping,social"
        }
    }


class MCPClient:
    """Simple MCP client for direct server communication (same as fetch_emails.py)."""
    
    def __init__(self, command, env=None):
        # Build environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=0,
            env=process_env
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
        print("🔌 Connecting to BrightData MCP server...")
        req_id = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "writing-style-clone", "version": "3.1"}
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
        "profile_url": None,
        "username": None,
        "total_fetched": 0,
        "last_fetch": None,
        "fetched_urls": []
    }


def save_state(state):
    """Save fetch state to file with validation tracking."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Add metadata
    state["last_updated"] = datetime.now().isoformat()
    state["version"] = "3.3"  # v3.3: Rich data capture (engagement, network, repost context)
    
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"\n💾 State saved to: {STATE_FILE}")


def normalize_profile_url(profile_input):
    """Convert username or partial URL to full LinkedIn profile URL."""
    if profile_input.startswith("http"):
        return profile_input
    elif profile_input.startswith("linkedin.com"):
        return f"https://{profile_input}"
    else:
        return f"https://www.linkedin.com/in/{profile_input}"


def extract_username(url):
    """Extract username from LinkedIn profile URL."""
    match = re.search(r'/in/([^/?]+)', url)
    if match:
        return match.group(1)
    return None


def extract_profile_metadata(content, profile_url):
    """
    Extract structured metadata from LinkedIn profile markdown.
    
    Args:
        content: Markdown content from scrape_as_markdown
        profile_url: Original profile URL
    
    Returns:
        dict: Structured profile data
    """
    lines = content.split("\n")
    
    # Extract username from URL
    username = extract_username(profile_url)
    
    # Extract name (look for clean name without extra text)
    name = "Unknown"
    for line in lines:
        # Look for name pattern: "FirstName LastName" or "FirstName (Nickname) LastName"
        if "John" in line and "Renaldi" in line and len(line) < 100:
            # Clean up the line
            clean = re.sub(r'\[.*?\]\(.*?\)', '', line)  # Remove markdown links
            clean = re.sub(r'[#*_]', '', clean)  # Remove markdown formatting
            clean = clean.strip()
            if len(clean) > 5 and len(clean) < 80:
                name = clean
                break
    
    # Extract headline (usually appears near name or in description)
    headline = "Unknown"
    for i, line in enumerate(lines):
        # Look for Northwestern/Segal or other professional headline
        if any(keyword in line for keyword in ["Segal", "Northwestern", "Product", "Founder"]):
            clean = line.strip()
            if len(clean) > 15 and len(clean) < 150:
                headline = clean
                break
    
    # Extract company (usually in headline or experience)
    company = "Unknown"
    if "Northwestern" in content:
        company = "Northwestern University"
    elif "Google" in content:
        company = "Google"
    elif "Jiobit" in content:
        company = "Jiobit"
    
    # Extract location
    location = "Unknown"
    location_match = re.search(r'(Chicago[^\n]*Illinois[^\n]*)', content, re.IGNORECASE)
    if location_match:
        location = location_match.group(1).strip()
    
    # Extract followers
    followers = "Unknown"
    follower_match = re.search(r'([\d,]+)\s+followers', content, re.IGNORECASE)
    if follower_match:
        followers = follower_match.group(1)
    
    # Extract bio/about (look for substantial paragraph)
    bio = "Unknown"
    bio_match = re.search(r'About[^\n]*\n+([^\n]{50,300})', content, re.IGNORECASE)
    if bio_match:
        bio = bio_match.group(1).strip()
    
    return {
        "name": name,
        "headline": headline,
        "company": company,
        "location": location,
        "followers": followers,
        "bio": bio,
        "username": username,
        "profile_url": profile_url,
        "extracted_at": datetime.now().isoformat()
    }


def verify_profile(client, profile_url):
    """
    Verify LinkedIn profile with interactive user confirmation.
    
    This is a critical security/accuracy step:
    1. Scrape profile and extract structured metadata
    2. Display clearly to user
    3. Wait for explicit confirmation
    4. Only proceed if user confirms "yes"
    
    Returns:
        dict: Validated profile data
    """
    print("\n" + "=" * 60)
    print("STEP 1: PROFILE VALIDATION")
    print("=" * 60)
    print(f"Scraping: {profile_url}")
    
    # Scrape profile
    try:
        profile_json = client.call_tool("scrape_as_markdown", {"url": profile_url})
        content = profile_json  # Already a string from MCP
    except Exception as e:
        print(f"\n❌ Error scraping profile: {e}")
        sys.exit(1)
    
    # Extract structured metadata
    profile_data = extract_profile_metadata(content, profile_url)
    
    # Display to user for confirmation
    print("\n" + "=" * 60)
    print("PROFILE FOUND - PLEASE CONFIRM THIS IS YOU")
    print("=" * 60)
    print(f"Name:      {profile_data['name']}")
    print(f"Headline:  {profile_data['headline']}")
    print(f"Company:   {profile_data['company']}")
    print(f"Location:  {profile_data['location']}")
    print(f"Followers: {profile_data['followers']}")
    print(f"Username:  {profile_data['username']}")
    print(f"URL:       {profile_data['profile_url']}")
    if profile_data['bio'] != "Unknown":
        print(f"Bio:       {profile_data['bio'][:100]}...")
    print("=" * 60)
    
    # Wait for user confirmation
    print("\n⚠️  IS THIS YOUR PROFILE? (yes/no): ", end='', flush=True)
    confirmation = input().strip().lower()
    
    if confirmation not in ['yes', 'y']:
        print("\n❌ Profile not confirmed. Please check the URL and try again.")
        print("\nMake sure you're using the correct LinkedIn profile URL.")
        sys.exit(1)
    
    # User confirmed - mark as validated
    profile_data['validated'] = True
    profile_data['validated_at'] = datetime.now().isoformat()
    
    print("\n✅ Profile confirmed! Searching for posts...\n")
    
    return profile_data


def search_for_posts(client, username, limit=20):
    """
    Search for LinkedIn posts using multiple strategies.
    Filter to only return posts from the target user.
    
    Returns:
        list: Post URLs
    """
    print("\n" + "=" * 60)
    print("STEP 2: SEARCH FOR POSTS")
    print("=" * 60)
    
    all_urls = []
    
    # Try multiple search patterns
    search_patterns = [
        f"site:linkedin.com/posts/{username} activity",
        f'"{username}" site:linkedin.com/posts product OR founder OR startup',
        f"site:linkedin.com/posts/{username}_",
    ]
    
    for i, query in enumerate(search_patterns, 1):
        print(f"\n🔍 Search {i}/{len(search_patterns)}: {query}")
        
        try:
            result_json = client.call_tool("search_engine", {
                "query": query,
                "engine": "google"
            })
            result_data = json.loads(result_json)
            
            # Extract post URLs - FILTER to exact username match
            for item in result_data.get("organic", []):
                url = item.get("link", "")
                # Strict validation: must be from THIS user's profile
                if (f"/posts/{username}/" in url or f"/posts/{username}_" in url) and "activity-" in url:
                    all_urls.append(url)
            
            found = len(all_urls)
            print(f"   → Found {found} posts so far")
            
            if len(all_urls) >= limit:
                break
                
        except Exception as e:
            print(f"   ⚠️  Search failed: {e}")
            continue
    
    # Deduplicate and limit
    unique_urls = list(dict.fromkeys(all_urls))[:limit]
    
    print(f"\n✅ Total unique post URLs: {len(unique_urls)}")
    return unique_urls


def validate_post_ownership(post_data, validated_profile):
    """
    Verify scraped post actually belongs to validated user.
    
    Args:
        post_data: Dict with post data from web_data_linkedin_posts
        validated_profile: Dict with confirmed user profile data
    
    Returns:
        tuple: (is_valid: bool, reason: str)
    """
    # Check 1: Username must match
    post_user_id = post_data.get('user_id', '')
    validated_username = validated_profile['username']
    
    if post_user_id != validated_username:
        return False, f"Username mismatch: '{post_user_id}' != '{validated_username}'"
    
    # Check 2: Profile URL consistency (if available in post data)
    post_url = post_data.get('url', '')
    if validated_username not in post_url:
        return False, f"Post URL doesn't contain username '{validated_username}'"
    
    # All checks passed
    return True, "Validated"


def scrape_posts_batch(client, urls, validated_profile, max_retries=2, retry_delay=30):
    """
    Scrape LinkedIn posts using specialized web_data_linkedin_posts tool.
    This tool returns structured data and supports caching.
    
    Args:
        client: MCPClient instance
        urls: List of LinkedIn post URLs
        max_retries: Number of retries if cache is warming up
        retry_delay: Seconds to wait between retries
    
    Returns:
        list: Successfully scraped posts with structured data
    """
    print("\n" + "=" * 60)
    print("STEP 3: SCRAPE & VALIDATE POSTS")
    print("=" * 60)
    print(f"Using specialized LinkedIn tool (web_data_linkedin_posts)")
    print(f"Note: First batch may need 30s cache warm-up\n")
    
    all_posts = []
    rejected_posts = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n📄 Post {i}/{len(urls)}: {url[:70]}...")
        
        post_data = None
        
        # Try with retries for cache warm-up
        for attempt in range(max_retries + 1):
            try:
                result_json = client.call_tool("web_data_linkedin_posts", {"url": url})
                data = json.loads(result_json)
                
                # Response is a list - check first item for status or data
                if isinstance(data, dict) and data.get("status") == "starting":
                    if attempt < max_retries:
                        print(f"   ⏳ Cache warming up, waiting {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"   ⚠️  Timeout after {max_retries} retries")
                        break
                elif isinstance(data, list) and data:
                    # Success - got list of post data
                    post_data = data[0]  # First item in list
                    text_preview = post_data.get("post_text", "")[:50]
                    likes = post_data.get("num_likes", 0)
                    print(f"   ✅ {len(post_data.get('post_text', ''))} chars, {likes} likes")
                    print(f"   Preview: {text_preview}...")
                    break
                else:
                    print(f"   ⚠️  Unexpected response format")
                    break
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ Invalid JSON response: {e}")
                break
            except Exception as e:
                if attempt < max_retries:
                    print(f"   ⚠️  Attempt {attempt+1} failed: {e}, retrying...")
                    time.sleep(5)
                else:
                    print(f"   ❌ Failed after {max_retries+1} attempts: {e}")
                break
        
        if post_data and post_data.get("post_text"):
            # Validate post ownership
            is_valid, reason = validate_post_ownership(post_data, validated_profile)
            
            if is_valid:
                # Build comprehensive post entry with rich metadata (v3.3)
                post_entry = {
                    # Core fields (existing)
                    "url": url,
                    "text": post_data.get("post_text", ""),
                    "likes": post_data.get("num_likes", 0),
                    "comments": post_data.get("num_comments", 0),
                    "date_posted": post_data.get("date_posted", ""),
                    "user_id": post_data.get("user_id", ""),
                    "validation_status": "confirmed",
                    
                    # NEW v3.3: Engagement signals
                    "top_comments": post_data.get("top_visible_comments", []),
                    
                    # NEW v3.3: Content metadata
                    "headline": post_data.get("headline", ""),
                    "post_type": post_data.get("post_type", "original"),
                    "embedded_links": post_data.get("embedded_links", []),
                    "images": post_data.get("images", []),
                    "external_links": post_data.get("external_link_data", []),
                    
                    # NEW v3.3: Network signals
                    "tagged_people": post_data.get("tagged_people", []),
                    "tagged_companies": post_data.get("tagged_companies", []),
                    
                    # NEW v3.3: Repost context (if applicable)
                    "is_repost": post_data.get("post_type") == "repost",
                    "repost_data": post_data.get("repost", None),
                    "original_commentary": post_data.get("original_post_text", ""),
                    
                    # NEW v3.3: User metrics (authority signals)
                    "author_followers": post_data.get("user_followers", 0),
                    "author_total_posts": post_data.get("user_posts", 0),
                    "author_articles": post_data.get("user_articles", 0),
                    
                    # NEW v3.3: Additional metadata
                    "account_type": post_data.get("account_type", "Person"),
                    "post_html": post_data.get("post_text_html", "")
                }
                all_posts.append(post_entry)
            else:
                rejected_posts.append({
                    "url": url,
                    "reason": reason,
                    "user_id": post_data.get("user_id", "unknown")
                })
                print(f"   ⚠️  Rejected: {reason}")
    
    # Report validation results
    print(f"\n" + "=" * 60)
    print(f"VALIDATION SUMMARY")
    print(f"=" * 60)
    print(f"✅ Validated: {len(all_posts)} posts (confirmed ownership)")
    
    if rejected_posts:
        print(f"⚠️  Rejected:  {len(rejected_posts)} posts (failed validation)")
        for rejection in rejected_posts:
            print(f"   - {rejection['url'][:60]}... ({rejection['reason']})")
    else:
        print(f"✅ No rejections: All posts passed validation")
    
    print(f"=" * 60 + "\n")
    
    return all_posts


def process_and_save(posts, holdout=0.15):
    """
    Save posts to raw_samples and call downstream processing.
    """
    print("\n" + "=" * 60)
    print("STEP 4: PROCESS AND SAVE")
    print("=" * 60)
    
    # Create raw_samples directory
    raw_dir = DATA_DIR / "raw_samples"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Save each post as individual file
    saved_count = 0
    for i, post in enumerate(posts, 1):
        filename = f"linkedin_post_{i:03d}.json"
        filepath = raw_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(post, f, indent=2)
        saved_count += 1
    
    print(f"✓ Saved {saved_count} posts to {raw_dir}")
    print(f"\n✅ LinkedIn fetch complete!")
    print(f"\n📊 Next steps:")
    print(f"   1. Run filter_linkedin.py to quality-check posts")
    print(f"   2. Run cluster_linkedin.py to create unified persona")
    print(f"   3. LinkedIn voice will be added to your writing assistant")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch LinkedIn posts via BrightData MCP"
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="LinkedIn profile URL or username (e.g., 'renaldi' or 'https://linkedin.com/in/renaldi')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of posts to fetch (default: 20)"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="BrightData API token (default: reads from MCP_TOKEN env var)"
    )
    
    args = parser.parse_args()
    
    # Get token
    token = args.token or os.getenv("MCP_TOKEN")
    if not token:
        print("❌ Error: No API token provided")
        print("   Either set MCP_TOKEN environment variable or use --token flag")
        sys.exit(1)
    
    # Normalize profile URL
    profile_url = normalize_profile_url(args.profile)
    username = extract_username(profile_url)
    
    if not username:
        print(f"❌ Error: Could not extract username from {profile_url}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("LINKEDIN POST FETCHER (MCP Direct)")
    print("=" * 60)
    print(f"Profile: {profile_url}")
    print(f"Username: {username}")
    print(f"Target posts: {args.limit}")
    
    # Initialize MCP client
    mcp_config = get_mcp_command(token)
    client = MCPClient(
        command=mcp_config["command"],
        env=mcp_config["env"]
    )
    
    try:
        client.initialize()
        
        # Step 1: Verify profile
        profile_data = verify_profile(client, profile_url)
        
        # Step 2: Search for posts
        post_urls = search_for_posts(client, username, limit=args.limit)
        
        if not post_urls:
            print("\n❌ No posts found. Try:")
            print("   - Checking if profile is public")
            print("   - Using full LinkedIn URL: https://linkedin.com/in/username")
            sys.exit(1)
        
        # Step 3: Scrape and validate posts
        posts = scrape_posts_batch(client, post_urls, profile_data)
        
        if not posts:
            print("\n❌ No posts could be scraped successfully")
            sys.exit(1)
        
        # Step 4: Save results
        process_and_save(posts)
        
        # Update state with complete validation data
        state = {
            "validated_profile": {
                "name": profile_data['name'],
                "username": profile_data['username'],
                "headline": profile_data['headline'],
                "company": profile_data['company'],
                "location": profile_data['location'],
                "profile_url": profile_url,
                "validated": True,
                "validated_at": profile_data['validated_at']
            },
            "content_discovery": {
                "urls_found": len(post_urls),
                "urls_scraped": len(post_urls),
                "posts_validated": len(posts),
                "posts_rejected": len(post_urls) - len(posts)
            },
            "fetch_summary": {
                "total_posts": len(posts),
                "last_fetch": datetime.now().isoformat(),
                "fetched_urls": post_urls
            }
        }
        save_state(state)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()
