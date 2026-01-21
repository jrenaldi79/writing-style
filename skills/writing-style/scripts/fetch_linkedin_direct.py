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


def extract_post_urls_from_activity(profile_data, limit=20):
    """
    Extract post URLs from the profile's activity feed.

    This is much more reliable than Google search as it
    comes directly from LinkedIn's data.

    Args:
        profile_data: Dict from web_data_linkedin_person_profile
        limit: Maximum URLs to return

    Returns:
        list: Post URLs from activity feed
    """
    print("\n" + "=" * 60)
    print("STEP 2: EXTRACT POST URLs FROM ACTIVITY")
    print("=" * 60)

    activity = profile_data.get('activity', [])

    if not activity:
        print("[WARNING] No activity found in profile data.")
        print("   This may be a private profile or the user has no recent posts.")
        return []

    post_urls = []
    skipped = 0

    for item in activity:
        link = item.get('link', '')

        # Filter to only include actual posts (not shares, comments, etc.)
        if '/posts/' in link or '/pulse/' in link:
            post_urls.append(link)
        else:
            skipped += 1

    # Limit results
    post_urls = post_urls[:limit]

    print(f"Total activity items: {len(activity)}")
    print(f"Post URLs extracted: {len(post_urls)}")
    print(f"Skipped (not posts): {skipped}")
    print("=" * 60)

    return post_urls


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


def scrape_posts_parallel(urls, profile_data, token, max_workers=5):
    """
    Scrape LinkedIn posts in parallel using web_data_linkedin_posts.

    Args:
        urls: List of LinkedIn post URLs
        profile_data: Profile data for ownership validation
        token: BrightData API token
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

    # Get the expected user ID from profile
    expected_linkedin_id = profile_data.get('linkedin_id', '')
    expected_username = extract_username(profile_data.get('linkedin_url', ''))

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

        # Validate ownership - compare user_id with expected
        post_user_id = post_data.get('user_id', '')
        post_linkedin_id = post_data.get('linkedin_id', '')

        # Check for match (either username or linkedin_id)
        is_owner = (
            (expected_username and expected_username.lower() in post_user_id.lower()) or
            (expected_linkedin_id and expected_linkedin_id == post_linkedin_id) or
            (expected_username and f"/in/{expected_username}" in url.lower())
        )

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

    print("\n" + "=" * 60)
    print("LINKEDIN POST FETCHER (Direct API)")
    print("=" * 60)
    print(f"Profile: {profile_url}")
    print(f"Username: {username}")
    print(f"Target posts: {args.limit}")
    print(f"Method: BrightData web_data_linkedin_* APIs")

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

        # Step 2: Extract post URLs from activity feed
        post_urls = extract_post_urls_from_activity(profile_data, limit=args.limit)

        if not post_urls:
            print("\n[WARNING] No posts found in activity feed.")
            print("   The profile may be private or have no recent posts.")
            sys.exit(1)

        # Close main client - parallel scraping will use own clients
        client.close()

        # Step 3: Scrape posts in parallel
        posts = scrape_posts_parallel(post_urls, profile_data, token)

        if not posts:
            print("\n[ERROR] No posts could be scraped successfully")
            sys.exit(1)

        # Step 4: Save results
        process_and_save(posts, profile_data)

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
                "urls_scraped": len(post_urls),
                "last_fetch": datetime.now().isoformat(),
                "method": "direct_api"
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
