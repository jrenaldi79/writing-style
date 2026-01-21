#!/usr/bin/env python3
"""
LinkedIn Post Fetcher (Direct API) - Fetch LinkedIn posts via BrightData structured APIs

Uses BrightData's web_data_linkedin_* APIs for reliable post discovery,
bypassing the unreliable search-based approach.

This script replaces the search-based fetch_linkedin_mcp.py with a more
reliable direct API approach that:
1. Fetches structured profile data (not HTML scraping)
2. Extracts post URLs from the activity feed
3. Validates ownership using structured data

Usage:
    python fetch_linkedin_direct.py --check                                    # Verify MCP is configured
    python fetch_linkedin_direct.py --profile <url_or_username> [--limit 20]   # Fetch posts
    python fetch_linkedin_direct.py --profile "https://linkedin.com/in/username" --limit 20
    python fetch_linkedin_direct.py --status

    # Search-based discovery (finds more posts via web search):
    python fetch_linkedin_direct.py --profile "username" --search-queries "jiobit,google,northwestern"
    python fetch_linkedin_direct.py --profile "username" --search-queries "topic1,topic2" --search-engines both

    # Auto-search when below threshold (recommended for quality):
    python fetch_linkedin_direct.py --profile "username" --min-posts 15

API Token:
    The script automatically detects your BrightData API token from:
    1. Chatwise MCP configuration (if @brightdata/mcp is configured)
    2. BRIGHTDATA_API_TOKEN environment variable (fallback)
"""

# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import subprocess
import json
import argparse
import re
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
from config import get_data_dir, get_path, get_npx_command
from api_keys import get_brightdata_token, is_mcp_configured_in_chatwise, KNOWN_MCPS

DATA_DIR = get_data_dir()
OUTPUT_DIR = get_path("linkedin_data")
STATE_FILE = get_path("linkedin_fetch_state.json")

# Quality thresholds
RECOMMENDED_MIN_POSTS = 15
IDEAL_MIN_POSTS = 20

# One-click install URL for ChatWise users
CHATWISE_BRIGHTDATA_URL = "https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0="


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
    """Simple MCP client for direct server communication."""

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
            encoding='utf-8',  # Explicit UTF-8 for Windows compatibility
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
            "clientInfo": {"name": "writing-style-clone", "version": "3.5"}
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
            print("[WARNING] BrightData MCP is not configured in Chatwise (will use npx directly)")

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


def print_install_instructions(details=None):
    """Print instructions for installing BrightData MCP."""
    print(f"\n{'=' * 70}")
    print("LINKEDIN PIPELINE PREREQUISITES")
    print(f"{'=' * 70}")

    print("\nThe LinkedIn pipeline requires BrightData MCP Server with structured data APIs.")

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
    print("\n   [WARNING] After clicking, replace YOUR_BRIGHTDATA_TOKEN with your actual token!")

    print(f"\n{'-' * 70}")
    print("ALTERNATIVE: Environment Variable")
    print(f"{'-' * 70}")
    print("\nIf not using Chatwise, set the environment variable:")
    print('   export BRIGHTDATA_API_TOKEN="your-brightdata-api-token"')

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
    state["version"] = "3.5"  # v3.5: Direct API approach
    state["method"] = "direct_api"

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


def fetch_profile_direct(client, profile_url):
    """
    Fetch LinkedIn profile using structured data API.

    This bypasses the login wall by using BrightData's
    web_data_linkedin_person_profile API.

    Returns:
        dict: Structured profile data with activity feed
    """
    print("\n" + "=" * 60)
    print("STEP 1: FETCH PROFILE (Direct API)")
    print("=" * 60)
    print(f"URL: {profile_url}")

    try:
        # Use structured data API instead of markdown scraping
        result_json = client.call_tool("web_data_linkedin_person_profile", {
            "url": profile_url
        })

        # Parse response - may be array or single object
        result = json.loads(result_json)

        if isinstance(result, list) and result:
            profile_data = result[0]
        elif isinstance(result, dict):
            profile_data = result
        else:
            print(f"[ERROR] Unexpected response format: {type(result)}")
            return None

        # Check for API rate limiting or errors
        if profile_data.get("status") == "starting":
            print("[WAIT] Data collection in progress, waiting...")
            time.sleep(15)
            # Retry
            result_json = client.call_tool("web_data_linkedin_person_profile", {
                "url": profile_url
            })
            result = json.loads(result_json)
            profile_data = result[0] if isinstance(result, list) else result

        # Display profile info
        print("\n" + "=" * 60)
        print("PROFILE FOUND")
        print("=" * 60)
        print(f"Name:      {profile_data.get('name', 'Unknown')}")
        print(f"Headline:  {profile_data.get('position', 'Unknown')}")
        print(f"Company:   {profile_data.get('current_company_name', 'Unknown')}")
        print(f"Location:  {profile_data.get('city', 'Unknown')}")
        print(f"Followers: {profile_data.get('followers', 'Unknown')}")
        print(f"LinkedIn ID: {profile_data.get('linkedin_id', 'Unknown')}")

        # Show activity count
        activity = profile_data.get('activity', [])
        print(f"Activity Items: {len(activity)}")
        print("=" * 60)

        print("\n[OK] Profile fetched successfully via direct API.\n")

        return profile_data

    except Exception as e:
        print(f"\n[ERROR] Failed to fetch profile: {e}")
        return None


def extract_post_urls_from_activity(profile_data, username, limit=20):
    """
    Extract post URLs from the profile's activity feed.

    This is much more reliable than Google search as it
    comes directly from LinkedIn's data.

    IMPORTANT: The activity feed includes all interactions (likes, shares,
    comments on others' posts). We filter to only include URLs that contain
    the user's username, indicating they authored the post.

    Args:
        profile_data: Dict from web_data_linkedin_person_profile
        username: LinkedIn username for filtering own posts
        limit: Maximum URLs to return

    Returns:
        list: Post URLs authored by the user
    """
    print("\n" + "=" * 60)
    print("STEP 2: EXTRACT POST URLs FROM ACTIVITY")
    print("=" * 60)

    activity = profile_data.get('activity', [])

    if not activity:
        print("[WARNING] No activity found in profile data.")
        print("   This may be a private profile or the user has no recent posts.")
        return []

    username_lower = username.lower() if username else ''
    own_posts = []
    interactions = 0
    skipped = 0

    for item in activity:
        link = item.get('link', '')
        link_lower = link.lower()

        # Check if this is a post/article URL
        if '/posts/' in link or '/pulse/' in link:
            # Check if this is the user's OWN post (URL contains their username)
            # Pattern: /posts/{username}_ or /posts/{username}/
            is_own_post = (
                f"/posts/{username_lower}_" in link_lower or
                f"/posts/{username_lower}/" in link_lower or
                (f"/pulse/" in link_lower and username_lower in link_lower)
            )

            if is_own_post:
                own_posts.append(link)
            else:
                interactions += 1
        else:
            skipped += 1

    # Limit results
    own_posts = own_posts[:limit]

    print(f"Total activity items: {len(activity)}")
    print(f"User's own posts: {len(own_posts)}")
    print(f"Interactions with others: {interactions}")
    print(f"Other activity (skipped): {skipped}")
    print("=" * 60)

    return own_posts


def build_smart_queries(profile_data):
    """
    Build search queries automatically from profile data.

    Extracts company names, job titles, and other relevant terms
    to find posts that may not appear in the activity feed.

    Args:
        profile_data: Dict from web_data_linkedin_person_profile

    Returns:
        list: Search query terms
    """
    queries = []

    # Current company
    company = profile_data.get('current_company_name', '')
    if company and len(company) > 2:
        queries.append(company)

    # Position/headline keywords
    position = profile_data.get('position', '')
    if position:
        # Extract key terms from position
        for term in ['CEO', 'CTO', 'founder', 'director', 'lead', 'head', 'VP']:
            if term.lower() in position.lower():
                queries.append(term)

    # Past companies from experience (if available)
    experience = profile_data.get('experience', [])
    if isinstance(experience, list):
        for exp in experience[:3]:  # Top 3 past roles
            if isinstance(exp, dict):
                past_company = exp.get('company', '') or exp.get('company_name', '')
                if past_company and past_company not in queries:
                    queries.append(past_company)

    # Industry keywords
    industry = profile_data.get('industry', '')
    if industry:
        queries.append(industry)

    # Dedupe and clean
    queries = list(dict.fromkeys([q.strip() for q in queries if q and len(q) > 2]))

    return queries[:6]  # Limit to 6 queries to avoid too many searches


def print_quality_warning(post_count, context=""):
    """
    Print quality warning if post count is below recommended threshold.

    Args:
        post_count: Number of posts found
        context: Additional context for the warning
    """
    if post_count >= IDEAL_MIN_POSTS:
        print(f"\n[OK] Post count: {post_count} (Good quality sample)")
        return

    print(f"\n{'=' * 60}")
    print(f"[WARNING] LOW POST COUNT: {post_count}")
    print(f"{'=' * 60}")

    if post_count < 5:
        quality = "VERY LOW"
        impact = "Persona will be unreliable"
    elif post_count < 10:
        quality = "LOW"
        impact = "Persona may miss important voice patterns"
    elif post_count < RECOMMENDED_MIN_POSTS:
        quality = "BELOW RECOMMENDED"
        impact = "Persona confidence will be reduced"
    else:
        quality = "ACCEPTABLE"
        impact = "Close to ideal, minor patterns may be missed"

    print(f"   Quality: {quality}")
    print(f"   Impact: {impact}")
    print(f"   Recommended: {RECOMMENDED_MIN_POSTS}-{IDEAL_MIN_POSTS}+ posts")

    if context:
        print(f"   {context}")

    if post_count < RECOMMENDED_MIN_POSTS:
        print(f"\n[SUGGEST] To improve quality:")
        print(f"   --search-queries 'company,topic1,topic2'")
        print(f"   --min-posts {RECOMMENDED_MIN_POSTS}")

    print(f"{'=' * 60}\n")


def extract_linkedin_urls_from_search_results(search_results, username):
    """
    Extract LinkedIn post/article URLs from search engine results.

    Args:
        search_results: Dict with 'organic' key containing search results
        username: LinkedIn username to filter for ownership

    Returns:
        list: LinkedIn post/article URLs belonging to the user
    """
    urls = []
    username_lower = username.lower() if username else ''

    organic = search_results.get('organic', [])
    if not organic:
        return urls

    for result in organic:
        url = result.get('link', '') or result.get('url', '')
        url_lower = url.lower()

        # Check if it's a LinkedIn post or article URL
        is_post = '/posts/' in url_lower
        is_article = '/pulse/' in url_lower

        if not (is_post or is_article):
            continue

        # Check ownership - URL should contain the username
        if is_post:
            # Pattern: /posts/{username}_ or /posts/{username}/
            is_owned = (
                f"/posts/{username_lower}_" in url_lower or
                f"/posts/{username_lower}/" in url_lower
            )
        else:
            # For articles, username appears in the URL slug
            is_owned = username_lower in url_lower

        if is_owned:
            urls.append(url)

    return urls


def run_single_search(query, engine, token):
    """
    Run a single search query with its own MCP client.
    Used for parallel search execution.

    Args:
        query: Search query string
        engine: Search engine (google/bing)
        token: BrightData API token

    Returns:
        tuple: (query, engine, results_dict or None, error_message or None)
    """
    mcp_config = get_mcp_command(token)
    client = MCPClient(mcp_config["command"], mcp_config["env"])

    try:
        client.initialize()
        result_json = client.call_tool("search_engine", {
            "query": query,
            "engine": engine
        })
        results = json.loads(result_json)
        return (query, engine, results, None)
    except Exception as e:
        return (query, engine, None, str(e))
    finally:
        client.close()


def discover_posts_via_search(token, username, full_name, search_queries, engines=None, max_workers=8):
    """
    Discover LinkedIn posts using web search engines (parallel execution).

    This supplements the activity feed by searching for posts that may not
    appear in recent activity. Uses multiple search queries and engines
    for comprehensive discovery.

    Args:
        token: BrightData API token (for parallel clients)
        username: LinkedIn username
        full_name: User's full name (from profile)
        search_queries: List of additional search terms (e.g., ["jiobit", "google"])
        engines: List of search engines to use (default: ["google"])
        max_workers: Number of parallel search workers (default: 8)

    Returns:
        list: Discovered LinkedIn post URLs
    """
    if engines is None:
        engines = ["google"]

    print("\n" + "=" * 60)
    print("SEARCH-BASED POST DISCOVERY (Parallel)")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Search queries: {search_queries}")
    print(f"Engines: {engines}")
    print(f"Workers: {max_workers}")

    # Build search queries
    base_queries = [
        f'site:linkedin.com/posts/{username}',
        f'site:linkedin.com/posts/{username}_',
    ]

    # Add name-based searches if we have the full name
    if full_name:
        name_queries = [
            f'site:linkedin.com "{full_name}" posts',
            f'site:linkedin.com/pulse "{full_name}"',
        ]
        base_queries.extend(name_queries)

    # Add custom search queries (e.g., topics, companies)
    for query in search_queries:
        query = query.strip()
        if query:
            base_queries.append(f'site:linkedin.com/posts/{username} {query}')
            if full_name:
                base_queries.append(f'site:linkedin.com "{full_name}" {query}')

    # Dedupe queries
    unique_queries = list(dict.fromkeys(base_queries))

    # Build all search tasks (query, engine pairs)
    search_tasks = [(q, e) for e in engines for q in unique_queries]
    total_searches = len(search_tasks)

    print(f"\nRunning {total_searches} searches in parallel...")

    all_urls = set()
    completed = 0
    errors = 0

    # Run searches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(run_single_search, query, engine, token): (query, engine)
            for query, engine in search_tasks
        }

        for future in as_completed(future_to_task):
            completed += 1
            query, engine, results, error = future.result()

            if error:
                errors += 1
                print(f"   [{completed}/{total_searches}] ERROR ({engine}): {error[:30]}...")
            elif results:
                urls = extract_linkedin_urls_from_search_results(results, username)
                new_urls = [u for u in urls if u not in all_urls]
                if new_urls:
                    all_urls.update(new_urls)
                    print(f"   [{completed}/{total_searches}] +{len(new_urls)} URLs ({engine})")
                else:
                    print(f"   [{completed}/{total_searches}] 0 new ({engine})")
            else:
                print(f"   [{completed}/{total_searches}] empty ({engine})")

    print(f"\n" + "=" * 60)
    print(f"SEARCH DISCOVERY COMPLETE")
    print(f"=" * 60)
    print(f"Total searches: {total_searches}")
    print(f"Errors: {errors}")
    print(f"Unique URLs found: {len(all_urls)}")
    print(f"=" * 60)

    return list(all_urls)


def dedupe_urls(activity_urls, search_urls):
    """
    Combine and deduplicate URLs from activity feed and search discovery.

    Normalizes URLs to handle variations (http vs https, trailing slashes, etc.)

    Args:
        activity_urls: URLs from profile activity feed
        search_urls: URLs from search discovery

    Returns:
        list: Deduplicated list of URLs
    """
    def normalize_url(url):
        """Normalize URL for comparison."""
        url = url.lower().strip()
        url = url.replace('http://', 'https://')
        url = url.rstrip('/')
        # Remove tracking parameters
        if '?' in url:
            url = url.split('?')[0]
        return url

    seen = set()
    unique_urls = []

    # Process activity URLs first (higher priority)
    for url in activity_urls:
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)

    # Add search URLs that aren't duplicates
    search_added = 0
    for url in search_urls:
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)
            search_added += 1

    if search_added > 0:
        print(f"[OK] Added {search_added} unique URLs from search discovery")

    return unique_urls


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
                elif isinstance(data, dict) and data.get("post_text"):
                    return (url, data, None)
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


def scrape_posts_parallel(urls, profile_data, token, username, max_workers=5):
    """
    Scrape LinkedIn posts in parallel using web_data_linkedin_posts.

    Args:
        urls: List of LinkedIn post URLs
        profile_data: Profile data for ownership validation
        token: BrightData API token
        username: LinkedIn username (from URL) for ownership validation
        max_workers: Number of parallel scrapers

    Returns:
        list: Successfully scraped posts with structured data
    """
    print("\n" + "=" * 60)
    print("STEP 3: SCRAPE POSTS (Parallel)")
    print("=" * 60)
    print(f"Using {max_workers} parallel workers for {len(urls)} URLs")

    all_posts = []
    rejected_posts = []

    # Get the expected user ID from profile and passed username
    expected_linkedin_id = profile_data.get('linkedin_id', '')
    expected_username = username  # Use passed username directly

    # Scrape posts in parallel
    batch_results = {}
    print(f"\n[PACKAGE] Starting parallel scrape...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(scrape_single_post, url, token, 2): url
            for url in urls
        }

        completed = 0
        for future in as_completed(future_to_url):
            completed += 1
            url, post_data, error = future.result()

            if post_data:
                batch_results[url] = post_data
                text_len = len(post_data.get("post_text", ""))
                likes = post_data.get("num_likes", 0)
                print(f"   [OK] [{completed}/{len(urls)}] {text_len} chars, {likes} likes")
            else:
                print(f"   [ERROR] [{completed}/{len(urls)}] {error}")

    print(f"\n[OK] Parallel scrape complete: {len(batch_results)}/{len(urls)} successful")

    # Process and validate results
    for url in urls:
        post_data = batch_results.get(url)

        if not post_data or not post_data.get("post_text"):
            continue

        # Validate ownership - check if this is the user's own post
        post_user_id = post_data.get('user_id', '')
        post_linkedin_id = post_data.get('linkedin_id', '')

        # The most reliable check is if the post URL contains the user's username
        # Activity feed includes interactions (likes, shares) with others' posts
        # Only posts authored by the user will have their username in the URL
        url_lower = url.lower()
        username_lower = expected_username.lower() if expected_username else ''

        # Check for ownership:
        # 1. URL contains /posts/{username}_ pattern (authored posts)
        # 2. URL contains /pulse/ and username (articles)
        # 3. post_user_id matches username (direct match)
        # 4. linkedin_id matches
        is_authored_post = (
            f"/posts/{username_lower}_" in url_lower or
            f"/posts/{username_lower}/" in url_lower
        )
        is_authored_article = (
            "/pulse/" in url_lower and username_lower in url_lower
        )
        is_user_id_match = (
            post_user_id and username_lower and
            username_lower in post_user_id.lower()
        )
        is_linkedin_id_match = (
            expected_linkedin_id and post_linkedin_id and
            expected_linkedin_id.lower() == post_linkedin_id.lower()
        )

        is_owner = is_authored_post or is_authored_article or is_user_id_match or is_linkedin_id_match

        if is_owner:
            post_entry = {
                "url": url,
                "text": post_data.get("post_text", ""),
                "likes": post_data.get("num_likes", 0),
                "comments": post_data.get("num_comments", 0),
                "date_posted": post_data.get("date_posted", ""),
                "user_id": post_data.get("user_id", ""),
                "linkedin_id": post_data.get("linkedin_id", ""),
                "validation_status": "confirmed",
                "fetch_method": "direct_api",

                # Additional metadata
                "headline": post_data.get("headline", ""),
                "post_type": post_data.get("post_type", "original"),
                "images": post_data.get("images", []),
                "content_type": "article" if "/pulse/" in url else "post"
            }
            all_posts.append(post_entry)
        else:
            rejected_posts.append({
                "url": url,
                "reason": f"Owner mismatch: {post_user_id} != {expected_username}",
                "user_id": post_user_id
            })

    # Report validation results
    print(f"\n" + "=" * 60)
    print(f"VALIDATION SUMMARY")
    print(f"=" * 60)
    print(f"[OK] Validated: {len(all_posts)} posts (confirmed ownership)")

    if rejected_posts:
        print(f"[WARNING] Rejected: {len(rejected_posts)} posts (failed validation)")
        for rejection in rejected_posts[:3]:  # Show first 3
            print(f"   - {rejection['reason']}")
    else:
        print(f"[OK] No rejections")

    print(f"=" * 60 + "\n")

    return all_posts


def process_and_save(posts, profile_data):
    """
    Save posts to linkedin_data directory.
    """
    print("\n" + "=" * 60)
    print("STEP 4: SAVE RESULTS")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save each post as individual file
    saved_count = 0
    for i, post in enumerate(posts, 1):
        filename = f"linkedin_post_{i:03d}.json"
        filepath = OUTPUT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post, f, indent=2, ensure_ascii=False)
        saved_count += 1

    # Save profile summary
    profile_summary = {
        "name": profile_data.get("name"),
        "linkedin_id": profile_data.get("linkedin_id"),
        "linkedin_url": profile_data.get("linkedin_url"),
        "followers": profile_data.get("followers"),
        "position": profile_data.get("position"),
        "company": profile_data.get("current_company_name"),
        "fetched_at": datetime.now().isoformat(),
        "post_count": len(posts)
    }

    with open(OUTPUT_DIR / "profile_summary.json", 'w', encoding='utf-8') as f:
        json.dump(profile_summary, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {saved_count} posts to {OUTPUT_DIR}")
    print(f"[OK] Profile summary saved")
    print(f"\n[OK] LinkedIn fetch complete!")
    print(f"\n[STATS] Next steps:")
    print(f"   1. Run filter_linkedin.py to quality-check posts")
    print(f"   2. Run cluster_linkedin.py to create unified persona")
    print(f"   3. LinkedIn voice will be added to your writing assistant")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch LinkedIn posts via BrightData Direct API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_linkedin_direct.py --check                              # Verify MCP is configured
  python fetch_linkedin_direct.py --profile "username" --limit 20      # Fetch 20 posts
  python fetch_linkedin_direct.py --profile "https://linkedin.com/in/username"
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
        help="LinkedIn profile URL or username"
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
        help="BrightData API token (default: auto-detects from Chatwise or env)"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip MCP verification before fetching"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current fetch status"
    )
    parser.add_argument(
        "--search-queries",
        default=None,
        help="Comma-separated search terms for discovery (e.g., 'jiobit,google,wearables')"
    )
    parser.add_argument(
        "--search-engines",
        default="google",
        choices=["google", "bing", "both"],
        help="Search engine(s) to use for discovery (default: google)"
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Skip activity feed, only use search-based discovery"
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=0,
        help=f"Auto-search if below this threshold (recommended: {RECOMMENDED_MIN_POSTS})"
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
            print_install_instructions(details)
            sys.exit(1)

    # Handle --status flag
    if args.status:
        state = load_state()
        print(f"\n{'=' * 50}")
        print("LINKEDIN FETCH STATUS (Direct API)")
        print(f"{'=' * 50}")
        print(f"Last fetch: {state.get('last_fetch', 'Never')}")
        print(f"Method: {state.get('method', 'unknown')}")
        print(f"Total posts: {state.get('total_fetched', 0)}")
        print(f"Data location: {OUTPUT_DIR}")
        print(f"{'=' * 50}\n")
        sys.exit(0)

    # Require --profile for fetching
    if not args.profile:
        print("[ERROR] --profile is required (unless using --check or --status)")
        print("   Example: python fetch_linkedin_direct.py --profile 'username' --limit 20")
        sys.exit(1)

    # Get token
    token = args.token or get_brightdata_token(require=False)

    # Run MCP check before fetching (unless skipped)
    if not args.skip_check:
        success, message, details = check_brightdata_auth(token=token, verbose=True)
        if not success:
            print(f"\n[ERROR] {message}")
            print_install_instructions(details)
            sys.exit(1)
        print(f"[OK] {message}\n")

    # Normalize profile URL
    profile_url = normalize_profile_url(args.profile)
    username = extract_username(profile_url)

    if not username:
        print(f"[ERROR] Could not extract username from {profile_url}")
        sys.exit(1)

    # Parse search options
    search_queries = []
    if args.search_queries:
        search_queries = [q.strip() for q in args.search_queries.split(',') if q.strip()]

    search_engines = []
    if args.search_engines == "both":
        search_engines = ["google", "bing"]
    else:
        search_engines = [args.search_engines]

    print("\n" + "=" * 60)
    print("LINKEDIN POST FETCHER (Direct API)")
    print("=" * 60)
    print(f"Profile: {profile_url}")
    print(f"Username: {username}")
    print(f"Target posts: {args.limit}")
    print(f"Method: BrightData web_data_linkedin_* APIs")
    if search_queries:
        print(f"Search queries: {', '.join(search_queries)}")
        print(f"Search engines: {', '.join(search_engines)}")
    if args.search_only:
        print(f"Mode: Search-only (skipping activity feed)")

    # Initialize MCP client
    mcp_config = get_mcp_command(token)
    client = MCPClient(
        command=mcp_config["command"],
        env=mcp_config["env"]
    )

    try:
        client.initialize()

        # Step 1: Fetch profile using direct API
        profile_data = fetch_profile_direct(client, profile_url)

        if not profile_data:
            print("\n[ERROR] Failed to fetch profile. Try:")
            print("   - Checking if profile URL is correct")
            print("   - Verifying BrightData API token is valid")
            sys.exit(1)

        # Step 2a: Extract post URLs from activity feed (unless --search-only)
        activity_urls = []
        if not args.search_only:
            activity_urls = extract_post_urls_from_activity(profile_data, username, limit=args.limit)

        # Step 2b: Auto-search if below --min-posts threshold
        # This triggers smart query generation from profile data
        auto_search_triggered = False
        if args.min_posts > 0 and len(activity_urls) < args.min_posts and not search_queries:
            print(f"\n[AUTO-SEARCH] Activity feed returned {len(activity_urls)} posts, below threshold of {args.min_posts}")
            print("[AUTO-SEARCH] Generating smart search queries from profile...")
            search_queries = build_smart_queries(profile_data)
            if search_queries:
                print(f"[AUTO-SEARCH] Using queries: {', '.join(search_queries)}")
                auto_search_triggered = True
            else:
                print("[AUTO-SEARCH] Could not extract search terms from profile")

        # Step 2c: Search-based discovery (if --search-queries provided or auto-triggered)
        # Runs in parallel with separate MCP clients for speed
        search_urls = []
        if search_queries:
            full_name = profile_data.get('name', '')
            search_urls = discover_posts_via_search(
                token, username, full_name, search_queries, search_engines, max_workers=8
            )

        # Combine and dedupe URLs from both sources
        if activity_urls or search_urls:
            post_urls = dedupe_urls(activity_urls, search_urls)
            print(f"\n[STATS] Total unique URLs: {len(post_urls)}")
            print(f"   From activity feed: {len(activity_urls)}")
            print(f"   From search discovery: {len(search_urls)}")
            if auto_search_triggered:
                print(f"   (auto-search was triggered)")
        else:
            post_urls = []

        if not post_urls:
            print("\n[WARNING] No posts found.")
            if not search_queries:
                print("   Try adding --search-queries to discover more posts via web search.")
                print("   Example: --search-queries 'topic1,topic2,company'")
                print("   Or use --min-posts 15 for automatic search discovery.")
            print("   The activity may only contain interactions (likes/shares) with others' posts.")
            sys.exit(1)

        # Limit to requested count
        if len(post_urls) > args.limit:
            print(f"[INFO] Limiting to {args.limit} posts (found {len(post_urls)})")
            post_urls = post_urls[:args.limit]

        # Close main client - parallel scraping will use own clients
        client.close()

        # Step 3: Scrape posts in parallel
        posts = scrape_posts_parallel(post_urls, profile_data, token, username)

        if not posts:
            print("\n[ERROR] No posts could be scraped successfully")
            sys.exit(1)

        # Step 4: Save results
        process_and_save(posts, profile_data)

        # Step 5: Quality assessment
        print_quality_warning(len(posts))

        # Update state
        state = {
            "validated_profile": {
                "name": profile_data.get('name'),
                "username": username,
                "linkedin_id": profile_data.get('linkedin_id'),
                "linkedin_url": profile_url,
                "followers": profile_data.get('followers'),
                "validated": True,
                "validated_at": datetime.now().isoformat()
            },
            "fetch_summary": {
                "total_posts": len(posts),
                "urls_found": len(post_urls),
                "urls_from_activity": len(activity_urls),
                "urls_from_search": len(search_urls),
                "urls_scraped": len(post_urls),
                "last_fetch": datetime.now().isoformat(),
                "method": "direct_api" + ("+search" if search_queries else ""),
                "search_queries": search_queries if search_queries else None,
                "search_engines": search_engines if search_queries else None
            }
        }
        save_state(state)

    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client.close()
        except:
            pass


if __name__ == "__main__":
    main()
