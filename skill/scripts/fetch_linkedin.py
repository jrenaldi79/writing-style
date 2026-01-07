#!/usr/bin/env python3
"""
LinkedIn Content Fetcher - Search and scrape posts + articles

Fetches both short-form posts and long-form articles from LinkedIn profiles
for writing style analysis.

Usage:
    python fetch_linkedin.py --profile renaldi --limit 50
    python fetch_linkedin.py --profile renaldi --limit 50 --holdout 0.15
    python fetch_linkedin.py --status
"""

import json
import re
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import random

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
OUTPUT_DIR = DATA_DIR / "raw_samples"
HOLDOUT_DIR = DATA_DIR / "holdout_samples"
STATE_FILE = DATA_DIR / "linkedin_fetch_state.json"


def parse_linkedin_post(markdown: str, url: str) -> Optional[Dict]:
    """
    Parse scraped LinkedIn post markdown into structured format.
    
    Handles short-form posts with:
    - Post text
    - Engagement (likes, comments)
    - Hashtags
    - Date posted
    """
    lines = [l.strip() for l in markdown.split('\n') if l.strip()]
    
    # Extract post ID from URL
    # Format: linkedin.com/posts/username_topic-activity-{id}-hash
    match = re.search(r'activity-(\d+)', url)
    post_id = match.group(1) if match else None
    
    if not post_id:
        return None
    
    # Find main post text (between author name and engagement section)
    post_text = []
    in_post = False
    
    for i, line in enumerate(lines):
        # Start after author name/header
        if 'Renaldi' in line or 'John' in line:
            in_post = True
            continue
        
        # Stop at engagement/comments
        if any(x in line for x in ['Comment', 'Like', 'To view or add a comment', 'Report this']):
            break
        
        # Capture post content
        if in_post:
            # Skip metadata
            if any(skip in line for skip in ['followers', 'connections', 'View Profile', 'Edited']):
                continue
            post_text.append(line)
    
    text = ' '.join(post_text).strip()
    
    # Extract engagement
    likes = 0
    comments = 0
    for line in lines:
        # Patterns: "[47]" or "47 reactions"
        likes_match = re.search(r'\[(\d+)\]', line)
        if likes_match:
            likes = int(likes_match.group(1))
        
        reactions_match = re.search(r'(\d+)\s+reactions?', line, re.IGNORECASE)
        if reactions_match:
            likes = int(reactions_match.group(1))
        
        comments_match = re.search(r'(\d+)\s+comments?', line, re.IGNORECASE)
        if comments_match:
            comments = int(comments_match.group(1))
    
    # Extract relative date
    date_str = None
    for line in lines:
        date_match = re.search(r'(\d+)(mo|y|w|d)\s*(ago)?', line)
        if date_match:
            date_str = date_match.group(0)
            break
    
    # Extract hashtags
    hashtags = re.findall(r'#\w+', text)
    
    return {
        'id': f'linkedin_post_{post_id}',
        'source': 'linkedin',
        'content_type': 'post',
        'url': url,
        'text': text,
        'date_relative': date_str,
        'engagement': {
            'likes': likes,
            'comments': comments
        },
        'hashtags': hashtags,
        'scraped_at': datetime.now().isoformat()
    }


def parse_linkedin_article(markdown: str, url: str) -> Optional[Dict]:
    """
    Parse scraped LinkedIn article markdown into structured format.
    
    Handles long-form articles with:
    - Title
    - Full text content
    - Published date
    - Engagement
    """
    lines = [l.strip() for l in markdown.split('\n') if l.strip()]
    
    # Extract article ID from URL
    # Format: linkedin.com/pulse/{title}-{author}-{hash}
    match = re.search(r'/pulse/([^/]+)', url)
    article_slug = match.group(1) if match else None
    
    if not article_slug:
        return None
    
    # First non-empty line is usually the title
    title = lines[0] if lines else 'Untitled'
    
    # Article text starts after title and author info
    article_text = []
    skip_patterns = ['Renaldi', 'Published', 'Follow', 'reactions', 'comments', 'View Profile']
    
    for line in lines[1:]:
        # Skip metadata/UI elements
        if any(skip in line for skip in skip_patterns):
            continue
        article_text.append(line)
    
    text = ' '.join(article_text).strip()
    
    # Extract engagement
    likes = 0
    comments = 0
    for line in lines:
        likes_match = re.search(r'(\d+)\s+reactions?', line, re.IGNORECASE)
        if likes_match:
            likes = int(likes_match.group(1))
        
        comments_match = re.search(r'(\d+)\s+comments?', line, re.IGNORECASE)
        if comments_match:
            comments = int(comments_match.group(1))
    
    # Extract publish date
    date_str = None
    for line in lines:
        # Look for "Published on Month Day, Year" or relative dates
        date_match = re.search(r'Published.*?(\w+ \d+, \d{4})', line)
        if date_match:
            date_str = date_match.group(1)
            break
        
        # Also check relative
        rel_match = re.search(r'(\d+)(mo|y|w|d)\s*(ago)?', line)
        if rel_match:
            date_str = rel_match.group(0)
            break
    
    return {
        'id': f'linkedin_article_{article_slug[:20]}',
        'source': 'linkedin',
        'content_type': 'article',
        'url': url,
        'title': title,
        'text': text,
        'date': date_str,
        'engagement': {
            'likes': likes,
            'comments': comments
        },
        'scraped_at': datetime.now().isoformat()
    }


def load_state() -> Dict:
    """Load fetch state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        'total_fetched': 0,
        'posts_fetched': 0,
        'articles_fetched': 0,
        'last_fetch': None,
        'fetched_urls': []
    }


def save_state(state: Dict) -> None:
    """Save fetch state."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def save_linkedin_content(content: Dict, holdout: bool = False) -> None:
    """Save LinkedIn content to raw_samples or holdout."""
    output_dir = HOLDOUT_DIR if holdout else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{content['id']}.json"
    
    with open(output_file, 'w') as f:
        json.dump(content, f, indent=2)
    
    content_type = content.get('content_type', 'unknown')
    likes = content.get('engagement', {}).get('likes', 0)
    location = "holdout" if holdout else "raw_samples"
    
    print(f"✓ Saved {content['id']} ({content_type}, {likes} likes) → {location}")


def show_status():
    """Show LinkedIn fetch status."""
    state = load_state()
    
    linkedin_files = list(OUTPUT_DIR.glob('linkedin_*.json')) if OUTPUT_DIR.exists() else []
    holdout_files = list(HOLDOUT_DIR.glob('linkedin_*.json')) if HOLDOUT_DIR.exists() else []
    
    posts = [f for f in linkedin_files if 'post' in f.name]
    articles = [f for f in linkedin_files if 'article' in f.name]
    
    print(f"\n{'═' * 60}")
    print("LINKEDIN FETCH STATUS")
    print(f"{'═' * 60}")
    print(f"Total content: {len(linkedin_files)} ({len(posts)} posts, {len(articles)} articles)")
    print(f"Holdout set: {len(holdout_files)}")
    
    if state.get('last_fetch'):
        print(f"Last fetch: {state['last_fetch']}")
    
    if linkedin_files:
        print(f"\nRecent content:")
        for f in sorted(linkedin_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            with open(f) as fp:
                data = json.load(fp)
            text_preview = (data.get('title') or data.get('text', ''))[:50]
            likes = data.get('engagement', {}).get('likes', 0)
            content_type = data.get('content_type', 'unknown')
            print(f"  • [{content_type:7}] {text_preview}... ({likes} likes)")
    
    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description='Fetch LinkedIn posts and articles')
    parser.add_argument('--profile', type=str, help='LinkedIn username (e.g., renaldi)')
    parser.add_argument('--limit', type=int, default=50, help='Max items to fetch per type')
    parser.add_argument('--holdout', type=float, default=0.0, help='Holdout fraction (0-1)')
    parser.add_argument('--status', action='store_true', help='Show fetch status')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if not args.profile:
        print("Error: --profile required (e.g., --profile renaldi)")
        sys.exit(1)
    
    print(f"\n🔍 LinkedIn Content Fetcher")
    print(f"{'─' * 60}")
    print(f"Profile: {args.profile}")
    print(f"Limit: {args.limit} per type")
    print(f"Holdout: {args.holdout:.0%}")
    print(f"{'─' * 60}\n")
    
    # Load existing state
    state = load_state()
    
    print("⚠️  AGENT INSTRUCTIONS:")
    print("\nThis script provides the framework for LinkedIn fetching.")
    print("The Claude agent should use MCP tools to:")
    print("\n1. Search for POSTS:")
    print(f"   use_mcp_tool('Social Media Scraper', 'search_engine',")
    print(f"     query='site:linkedin.com/posts/{args.profile}', engine='google')")
    print("\n2. Search for ARTICLES:")
    print(f"   use_mcp_tool('Social Media Scraper', 'search_engine',")
    print(f"     query='site:linkedin.com/pulse {args.profile}', engine='google')")
    print("\n3. For each URL found, scrape content:")
    print(f"   use_mcp_tool('Social Media Scraper', 'scrape_as_markdown',")
    print(f"     url='https://linkedin.com/posts/...')")
    print("\n4. Parse and save using this script's functions:")
    print("   - parse_linkedin_post(markdown, url)")
    print("   - parse_linkedin_article(markdown, url)")
    print("   - save_linkedin_content(content_dict, holdout=False/True)")
    print("\n5. Update state and show summary")
    print(f"\n{'─' * 60}\n")
    
    if not args.dry_run:
        print("To execute, the agent needs to call MCP tools above.\n")


if __name__ == '__main__':
    main()
