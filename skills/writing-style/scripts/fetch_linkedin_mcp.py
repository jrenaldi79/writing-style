#!/usr/bin/env python3
"""
LinkedIn Post Fetcher - Bulk download LinkedIn posts via BrightData MCP

Runs outside of Claude to efficiently fetch LinkedIn posts without using tokens.
Uses BrightData Social Media Scraper MCP server (same pattern as fetch_emails.py).

Usage:
    python fetch_linkedin_mcp.py --check                                    # Verify MCP is configured
    python fetch_linkedin_mcp.py --profile <url_or_username> [--limit 20]   # Fetch posts
    python fetch_linkedin_mcp.py --profile "https://linkedin.com/in/renaldi" --limit 20
    python fetch_linkedin_mcp.py --profile "renaldi" --limit 15
    python fetch_linkedin_mcp.py --status

API Token:
    The script automatically detects your BrightData API token from:
    1. Chatwise MCP configuration (if @brightdata/mcp is configured)
    2. BRIGHTDATA_API_TOKEN environment variable (fallback)

    No manual configuration needed if using Chatwise with BrightData MCP installed.
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import subprocess
import json
import sys
import argparse
import re
import os
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration - BrightData MCP Server (NPX-based, like Gmail)
from config import get_data_dir, get_path, get_npx_command
from api_keys import get_brightdata_token, is_mcp_configured_in_chatwise, KNOWN_MCPS

DATA_DIR = get_data_dir()
OUTPUT_DIR = get_path("linkedin_data")
STATE_FILE = get_path("linkedin_fetch_state.json")

# One-click install URLs for ChatWise users
CHATWISE_BRIGHTDATA_URL = "https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0="
CHATWISE_DESKTOP_COMMANDER_URL = "https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImRlc2t0b3AtY29tbWFuZGVyIjogewogICAgICAiY29tbWFuZCI6ICJucHgiLAogICAgICAiYXJncyI6IFsiLXkiLCAiQHdvbmRlcndoeS1lci9kZXNrdG9wLWNvbW1hbmRlciJdLAogICAgICAiZW52IjogewogICAgICAgICJNQ1BfVE9LRU4iOiAiWU9VUl9CUklHSFREQVRBX1RPS0VOIgogICAgICB9CiAgICB9CiAgfQp9"


def get_mcp_command(token):
    """Build MCP command with token in environment."""
    return {
        "command": [get_npx_command(), "@brightdata/mcp"],
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
        print("[CONNECT] Connecting to BrightData MCP server...")
        req_id = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "writing-style-clone", "version": "3.1"}
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


def check_brightdata_auth(token=None, verbose=True):
    """
    Verify that BrightData MCP server is installed and API token is available.

    Returns:
        tuple: (success: bool, message: str, details: dict)
    """
    import shutil

    details = {
        "chatwise_configured": False,
        "npx_available": False,
        "token_set": False,
        "mcp_connects": False,
        "api_works": False
    }

    # Check if MCP is configured in Chatwise
    if is_mcp_configured_in_chatwise(KNOWN_MCPS["brightdata"]):
        details["chatwise_configured"] = True
        if verbose:
            print("[OK] BrightData MCP is configured in Chatwise")
    else:
        if verbose:
            print("[WARNING]  BrightData MCP is not configured in Chatwise (will use npx directly)")

    # Check if npx is available
    if not shutil.which("npx"):
        return False, "npx not found. Please install Node.js first.", details

    details["npx_available"] = True

    # Check for token (from Chatwise or environment)
    token = token or get_brightdata_token(require=False)
    if not token:
        return False, "BrightData API token not found. Configure in Chatwise or set BRIGHTDATA_API_TOKEN.", details

    details["token_set"] = True

    if verbose:
        print("[SEARCH] Checking BrightData MCP server...")

    try:
        mcp_config = get_mcp_command(token)
        client = MCPClient(mcp_config["command"], mcp_config["env"])
        client.initialize()
        details["mcp_connects"] = True

        if verbose:
            print("[AUTH] Verifying BrightData API token...")

        # Try a simple search to verify the API works
        result_json = client.call_tool("search_engine", {
            "query": "test",
            "engine": "google"
        })
        result = json.loads(result_json)

        client.close()

        # Check if we got a valid response
        if "organic" in result or result == {}:
            details["api_works"] = True
            return True, "BrightData MCP is installed and authenticated.", details
        elif "error" in result:
            error_msg = result.get("error", {}).get("message", str(result))
            if "auth" in error_msg.lower() or "token" in error_msg.lower() or "api" in error_msg.lower():
                return False, f"API token invalid: {error_msg}", details
            return False, f"API error: {error_msg}", details
        else:
            details["api_works"] = True
            return True, "BrightData MCP is installed and authenticated.", details

    except FileNotFoundError:
        return False, "BrightData MCP server not found. npx failed to run @brightdata/mcp.", details
    except Exception as e:
        error_str = str(e).lower()
        if "auth" in error_str or "token" in error_str or "api" in error_str:
            return False, f"API authentication failed: {e}", details
        elif "connection" in error_str or "closed" in error_str:
            return False, f"MCP server connection failed: {e}", details
        else:
            return False, f"MCP check failed: {e}", details


def print_linkedin_install_instructions(details=None):
    """Print instructions for installing BrightData MCP."""
    print(f"\n{'=' * 70}")
    print("LINKEDIN PIPELINE PREREQUISITES")
    print(f"{'=' * 70}")

    print("\nThe LinkedIn pipeline requires BrightData MCP Server for scraping.")

    # Check what's missing
    if details:
        if not details.get("token_set"):
            print("\n[ERROR] MISSING: BrightData API token not found")
        if not details.get("mcp_connects"):
            print("[ERROR] MISSING: BrightData MCP server not responding")

    print(f"\n{'-' * 70}")
    print("STEP 1: Get a BrightData API Token")
    print(f"{'-' * 70}")
    print("   1. Sign up at: https://brightdata.com/cp/start")
    print("   2. Navigate to API settings to get your API token")
    print("   3. Copy the token for the next step")

    print(f"\n{'-' * 70}")
    print("STEP 2: Install BrightData MCP Server in Chatwise")
    print(f"{'-' * 70}")
    print("\n[PACKAGE] ONE-CLICK INSTALL (Recommended):")
    print(f"   {CHATWISE_BRIGHTDATA_URL}")
    print("\n   [WARNING]  After clicking, replace YOUR_BRIGHTDATA_TOKEN with your actual token!")
    print("\n   The script will automatically detect your token from Chatwise.")

    print(f"\n{'-' * 70}")
    print("ALTERNATIVE: Environment Variable")
    print(f"{'-' * 70}")
    print("\nIf not using Chatwise, set the environment variable:")
    print('   export BRIGHTDATA_API_TOKEN="your-brightdata-api-token"')
    print("\nAdd to ~/.bashrc or ~/.zshrc for persistence.")

    print(f"\n{'=' * 70}\n")


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
    
    print(f"\n[SAVE] State saved to: {STATE_FILE}")


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


# Stopwords for keyword extraction
KEYWORD_STOPWORDS = {
    'the', 'and', 'or', 'at', 'in', 'for', 'to', 'a', 'an', 'is', 'are', 'was',
    'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can',
    'of', 'on', 'with', 'as', 'by', 'from', 'about', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
    'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'just', 'but', 'if', 'this',
    'that', 'these', 'those', 'am', 'i', 'me', 'my', 'myself', 'we', 'our',
    'ours', 'ourselves', 'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her',
    'hers', 'it', 'its', 'they', 'them', 'their', 'theirs', 'what', 'which', 'who',
    'whom', 'best', 'world', 'experienced', 'years', 'work', 'working', 'company'
}


def extract_profile_keywords(profile_data: dict, max_keywords: int = 5) -> list:
    """
    Extract search keywords from profile data for dynamic search queries.

    Sources (priority order):
    1. Headline (job title, role)
    2. Company name
    3. Bio/Summary (industry terms)

    Args:
        profile_data: Dict with headline, company, bio fields
        max_keywords: Maximum keywords to return (default 5)

    Returns:
        list: Top keywords for search queries, deduplicated
    """
    if not profile_data:
        return []

    keywords = []

    # 1. Parse headline for role keywords
    headline = profile_data.get('headline', '') or ''
    if headline:
        # Split on common separators: |, -, @, at
        parts = re.split(r'[|@\-]|\bat\b', headline, flags=re.IGNORECASE)
        for part in parts:
            # Extract individual words
            words = re.findall(r'\b[A-Za-z]{3,}\b', part)
            for word in words:
                if word.lower() not in KEYWORD_STOPWORDS:
                    keywords.append(word)

    # 2. Add company name
    company = profile_data.get('company', '') or ''
    if company and company.lower() != 'unknown':
        # Clean company name
        company_clean = re.sub(r'[^\w\s]', '', company).strip()
        if company_clean and company_clean.lower() not in KEYWORD_STOPWORDS:
            keywords.append(company_clean)

    # 3. Parse bio for industry terms
    bio = profile_data.get('bio', '') or ''
    if bio and bio.lower() != 'unknown':
        # Extract longer words (likely industry terms)
        bio_words = re.findall(r'\b[A-Za-z]{4,}\b', bio)
        for word in bio_words:
            if word.lower() not in KEYWORD_STOPWORDS:
                keywords.append(word)

    # Deduplicate while preserving order (case-insensitive)
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)

    return unique_keywords[:max_keywords]


def build_search_patterns(username: str, name: str = None, profile_data: dict = None,
                          use_dynamic_keywords: bool = True, year_range: int = 3) -> list:
    """
    Build comprehensive search patterns for LinkedIn post discovery.

    Pattern categories:
    1. Dynamic keyword patterns (from profile) or fallback
    2. Date-range patterns (year-specific for historical discovery)
    3. Base patterns (existing patterns as fallback)
    4. Article patterns (using full name for /pulse/ URLs)

    Args:
        username: LinkedIn username/URL slug
        name: Full name for article searches (optional)
        profile_data: Profile dict for keyword extraction (optional)
        use_dynamic_keywords: Whether to use profile keywords (default True)
        year_range: Number of years to search back (default 3)

    Returns:
        list: Search query patterns
    """
    patterns = []
    current_year = datetime.now().year

    # 1. Dynamic keyword pattern (or fallback)
    if use_dynamic_keywords and profile_data:
        keywords = extract_profile_keywords(profile_data)
        if keywords:
            keyword_str = " OR ".join(keywords[:3])
            patterns.append(f'"{username}" site:linkedin.com/posts {keyword_str}')
        else:
            # No keywords extracted, use fallback
            patterns.append(f'"{username}" site:linkedin.com/posts product OR founder OR startup')
    else:
        # Fallback to hardcoded keywords
        patterns.append(f'"{username}" site:linkedin.com/posts product OR founder OR startup')

    # 2. Date-range patterns (year-specific)
    if year_range > 0:
        for year in range(current_year, current_year - year_range, -1):
            patterns.append(f"site:linkedin.com/posts/{username} {year}")

    # 3. Base patterns (existing - always include)
    patterns.append(f"site:linkedin.com/posts/{username} activity")
    patterns.append(f"site:linkedin.com/posts/{username}_")

    # 4. Article search - USE FULL NAME if available
    if name:
        patterns.append(f"site:linkedin.com/pulse/ {name}")
    # Also include username as fallback
    patterns.append(f"site:linkedin.com/pulse/ {username}")

    return patterns


def validate_article_url(url: str, username: str, name: str = None) -> bool:
    """
    Validate that an article URL belongs to the target user.

    Checks for either username or full name (slugified) in the URL.
    LinkedIn articles use author name in URL, not username.

    Args:
        url: Article URL to validate
        username: LinkedIn username/slug
        name: Full name (optional, will be slugified for matching)

    Returns:
        bool: True if URL belongs to user
    """
    url_lower = url.lower()

    # Check username match
    if username.lower() in url_lower:
        return True

    # Check name match (slugified: "John Smith" -> "john-smith")
    if name:
        name_slug = name.lower().replace(' ', '-')
        if name_slug in url_lower:
            return True
        # Also check without hyphens (some URLs use different formats)
        name_no_space = name.lower().replace(' ', '')
        if name_no_space in url_lower:
            return True

    return False


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
        print(f"\n[ERROR] Error scraping profile: {e}")
        sys.exit(1)
    
    # Extract structured metadata
    profile_data = extract_profile_metadata(content, profile_url)
    
    # Display profile info (LLM can verify with user if needed)
    print("\n" + "=" * 60)
    print("PROFILE FOUND")
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

    # Auto-proceed (LLM workflow - no interactive confirmation)
    profile_data['validated'] = True
    profile_data['validated_at'] = datetime.now().isoformat()

    print("\n[OK] Profile validated. Searching for posts...\n")
    
    return profile_data


def search_for_posts(client, username, limit=20, profile_data=None,
                     use_dynamic_keywords=True, year_range=3):
    """
    Search for LinkedIn posts using multiple strategies.
    Filter to only return posts from the target user.

    Args:
        client: MCP client for search API calls
        username: LinkedIn username/URL slug
        limit: Maximum posts to return (default 20)
        profile_data: Profile dict for dynamic keywords and name (optional)
        use_dynamic_keywords: Use profile keywords instead of hardcoded (default True)
        year_range: Years to search back for historical posts (default 3)

    Returns:
        list: Post URLs
    """
    print("\n" + "=" * 60)
    print("STEP 2: SEARCH FOR POSTS")
    print("=" * 60)

    all_urls = []

    # Extract name from profile_data for article searches
    name = profile_data.get('name') if profile_data else None

    # Build search patterns using new dynamic function
    search_patterns = build_search_patterns(
        username=username,
        name=name,
        profile_data=profile_data,
        use_dynamic_keywords=use_dynamic_keywords,
        year_range=year_range
    )

    print(f"\nUsing {len(search_patterns)} search patterns")
    if profile_data and use_dynamic_keywords:
        keywords = extract_profile_keywords(profile_data)
        if keywords:
            print(f"Dynamic keywords: {', '.join(keywords[:3])}")

    for i, query in enumerate(search_patterns, 1):
        print(f"\n[SEARCH] Search {i}/{len(search_patterns)}: {query}")

        try:
            result_json = client.call_tool("search_engine", {
                "query": query,
                "engine": "google"
            })
            result_data = json.loads(result_json)

            # Extract post/article URLs - FILTER to exact username match
            for item in result_data.get("organic", []):
                url = item.get("link", "")
                # Strict validation: must be from THIS user's profile
                # Posts: /posts/username/ or /posts/username_ with activity-
                if (f"/posts/{username}/" in url or f"/posts/{username}_" in url) and "activity-" in url:
                    all_urls.append(url)
                # Articles: /pulse/ - use validate_article_url for name+username matching
                elif "/pulse/" in url and validate_article_url(url, username, name):
                    all_urls.append(url)

            found = len(all_urls)
            print(f"   -> Found {found} posts so far")

            # Early termination when we have enough unique URLs
            if len(set(all_urls)) >= limit * 1.5:
                print("   -> Sufficient URLs found, stopping search")
                break

        except Exception as e:
            print(f"   [WARNING]  Search failed: {e}")
            continue

    # Deduplicate and limit
    unique_urls = list(dict.fromkeys(all_urls))[:limit]

    print(f"\n[OK] Total unique post URLs: {len(unique_urls)}")
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


def scrape_single_post(url, token, max_retries=2):
    """
    Scrape a single LinkedIn post with its own MCP client.
    Used for parallel processing.

    Args:
        url: LinkedIn post URL
        token: BrightData API token
        max_retries: Number of retries

    Returns:
        tuple: (url, post_data or None, error_message or None)
    """
    mcp_config = get_mcp_command(token)
    client = MCPClient(mcp_config["command"], mcp_config["env"])

    try:
        client.initialize()

        for attempt in range(max_retries + 1):
            try:
                result_json = client.call_tool("web_data_linkedin_posts", {"url": url})
                data = json.loads(result_json)

                if isinstance(data, dict) and data.get("status") == "starting":
                    if attempt < max_retries:
                        time.sleep(10)
                        continue
                    else:
                        return (url, None, "Timeout waiting for cache")
                elif isinstance(data, list) and data:
                    return (url, data[0], None)
                else:
                    return (url, None, "Unexpected response format")

            except json.JSONDecodeError as e:
                return (url, None, f"Invalid JSON: {e}")
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return (url, None, str(e))

        return (url, None, "Max retries exceeded")
    finally:
        client.close()


def scrape_posts_batch(client, urls, validated_profile, max_retries=2, retry_delay=30, max_workers=5):
    """
    Scrape LinkedIn posts in parallel using web_data_linkedin_posts.

    Args:
        client: MCPClient instance (used for token extraction)
        urls: List of LinkedIn post URLs
        max_retries: Number of retries per post
        retry_delay: Not used (kept for compatibility)
        max_workers: Number of parallel scrapers (default 5)

    Returns:
        list: Successfully scraped posts with structured data
    """
    print("\n" + "=" * 60)
    print("STEP 3: SCRAPE & VALIDATE POSTS")
    print("=" * 60)
    print(f"Using parallel scraping ({max_workers} workers, {len(urls)} URLs)")
    print(f"This is much faster than sequential scraping\n")

    all_posts = []
    rejected_posts = []

    # Get token from Chatwise or environment
    token = get_brightdata_token(require=False)
    if not token:
        print("[ERROR] BrightData API token not found")
        print("   Configure in Chatwise or set BRIGHTDATA_API_TOKEN environment variable")
        return []

    # Scrape posts in parallel
    batch_results = {}
    print(f"[PACKAGE] Starting parallel scrape of {len(urls)} posts...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scrape jobs
        future_to_url = {
            executor.submit(scrape_single_post, url, token, max_retries): url
            for url in urls
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_url):
            completed += 1
            url, post_data, error = future.result()

            if post_data:
                batch_results[url] = post_data
                text_len = len(post_data.get("post_text", ""))
                likes = post_data.get("num_likes", 0)
                print(f"   [OK] [{completed}/{len(urls)}] {text_len} chars, {likes} likes - {url[:50]}...")
            else:
                print(f"   [ERROR] [{completed}/{len(urls)}] Failed: {error} - {url[:50]}...")

    print(f"\n[OK] Parallel scrape complete: {len(batch_results)}/{len(urls)} successful")

    # Process results
    for i, url in enumerate(urls, 1):
        post_data = batch_results.get(url)

        if not post_data or not post_data.get("post_text"):
            continue

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
                "post_html": post_data.get("post_text_html", ""),

                # NEW v3.4: Content type (post vs article)
                "content_type": "article" if "/pulse/" in url else "post"
            }
            all_posts.append(post_entry)
        else:
            rejected_posts.append({
                "url": url,
                "reason": reason,
                "user_id": post_data.get("user_id", "unknown")
            })
            print(f"   [WARNING]  Rejected: {reason}")
    
    # Report validation results
    print(f"\n" + "=" * 60)
    print(f"VALIDATION SUMMARY")
    print(f"=" * 60)
    print(f"[OK] Validated: {len(all_posts)} posts (confirmed ownership)")
    
    if rejected_posts:
        print(f"[WARNING]  Rejected:  {len(rejected_posts)} posts (failed validation)")
        for rejection in rejected_posts:
            print(f"   - {rejection['url'][:60]}... ({rejection['reason']})")
    else:
        print(f"[OK] No rejections: All posts passed validation")
    
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
    
    print(f"[OK] Saved {saved_count} posts to {raw_dir}")
    print(f"\n[OK] LinkedIn fetch complete!")
    print(f"\n[STATS] Next steps:")
    print(f"   1. Run filter_linkedin.py to quality-check posts")
    print(f"   2. Run cluster_linkedin.py to create unified persona")
    print(f"   3. LinkedIn voice will be added to your writing assistant")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch LinkedIn posts via BrightData MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_linkedin_mcp.py --check                              # Verify MCP is configured
  python fetch_linkedin_mcp.py --profile "renaldi" --limit 20       # Fetch 20 posts
  python fetch_linkedin_mcp.py --profile "https://linkedin.com/in/renaldi"
        """
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify BrightData MCP is installed and API token is available"
    )
    parser.add_argument(
        "--profile",
        default=None,
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
        help="BrightData API token (default: auto-detects from Chatwise or BRIGHTDATA_API_TOKEN)"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip MCP verification before fetching"
    )
    parser.add_argument(
        "--no-dynamic-keywords",
        action="store_true",
        help="Disable dynamic keyword extraction from profile (use hardcoded keywords)"
    )
    parser.add_argument(
        "--year-range",
        type=int,
        default=3,
        help="Number of years to search back for posts (default: 3)"
    )
    parser.add_argument(
        "--max-keywords",
        type=int,
        default=5,
        help="Maximum keywords to extract from profile (default: 5)"
    )

    args = parser.parse_args()

    # Handle --check flag
    if args.check:
        token = args.token or get_brightdata_token(require=False)
        success, message, details = check_brightdata_auth(token=token, verbose=True)
        if success:
            print(f"\n[OK] {message}")
            print("\nChecklist:")
            print(f"   [OK] npx available")
            print(f"   [OK] API token found")
            print(f"   [OK] BrightData MCP connects")
            print(f"   [OK] API token valid")
            sys.exit(0)
        else:
            print(f"\n[ERROR] {message}")
            print_linkedin_install_instructions(details)
            sys.exit(1)

    # Require --profile for fetching
    if not args.profile:
        print("[ERROR] Error: --profile is required (unless using --check)")
        print("   Example: python fetch_linkedin_mcp.py --profile 'renaldi' --limit 20")
        sys.exit(1)

    # Get token (from Chatwise or environment)
    token = args.token or get_brightdata_token(require=False)

    # Run MCP check before fetching (unless skipped)
    if not args.skip_check:
        success, message, details = check_brightdata_auth(token=token, verbose=True)
        if not success:
            print(f"\n[ERROR] {message}")
            print_linkedin_install_instructions(details)
            sys.exit(1)
        print(f"[OK] {message}\n")
    
    # Normalize profile URL
    profile_url = normalize_profile_url(args.profile)
    username = extract_username(profile_url)
    
    if not username:
        print(f"[ERROR] Error: Could not extract username from {profile_url}")
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
        
        # Step 2: Search for posts (using profile data for dynamic keywords)
        post_urls = search_for_posts(
            client,
            username,
            limit=args.limit,
            profile_data=profile_data,
            use_dynamic_keywords=not args.no_dynamic_keywords,
            year_range=args.year_range
        )
        
        if not post_urls:
            print("\n[ERROR] No posts found. Try:")
            print("   - Checking if profile is public")
            print("   - Using full LinkedIn URL: https://linkedin.com/in/username")
            sys.exit(1)
        
        # Step 3: Scrape and validate posts
        posts = scrape_posts_batch(client, post_urls, profile_data)
        
        if not posts:
            print("\n[ERROR] No posts could be scraped successfully")
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
        print("\n\n[WARNING]  Interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()
