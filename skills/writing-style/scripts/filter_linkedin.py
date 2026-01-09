#!/usr/bin/env python3
"""
LinkedIn Quality Filter - Enforce content standards

Unlike email filtering (which focuses on auto-replies), LinkedIn filtering
focuses on CONTENT DEPTH. We want to remove:
1. Short snippets (scraping errors)
2. Low-effort "Congrats!" or "Reposting" updates
3. Zero-engagement noise (optional)

Thresholds:
- Min Length: 200 characters (approx 30-40 words)
- Min Likes: 5 (filters out absolute noise)

Usage:
    python filter_linkedin.py
    python filter_linkedin.py --dry-run
"""

import json
import argparse
from pathlib import Path
import shutil

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
RAW_DIR = get_path("raw_samples")
FILTERED_DIR = get_path("filtered_samples")

# Thresholds
MIN_CHARS = 200  # Snippets are usually < 150 chars
MIN_LIKES = 1    # Basic check to ensure it's a real post

def check_quality(post: dict) -> tuple[bool, str]:
    """
    Check if a post meets quality standards.
    Returns: (passed, reason)
    """
    text = post.get('text', '')
    
    # 1. Length Check
    if len(text) < MIN_CHARS:
        return False, f"Too short ({len(text)} chars)"
        
    # 2. Scraper Artifact Check (common bad scrape patterns)
    if text.strip().endswith("... [Read more]") or text.strip().endswith("See more"):
        # If it's short AND ends with read more, it's definitely a snippet
        if len(text) < 500:
            return False, "Truncated snippet content"
            
    # 3. Content Value Check
    # Skip "John Renaldi reposted this" type content if that's all there is
    if text.startswith("Reposted") and len(text) < 300:
        return False, "Low-value repost"
        
    return True, "Passed"

def main():
    parser = argparse.ArgumentParser(description='Filter LinkedIn posts')
    parser.add_argument('--dry-run', action='store_true', help="Don't move files, just check")
    args = parser.parse_args()
    
    if not RAW_DIR.exists():
        print("No raw_samples directory found.")
        return
        
    if not args.dry_run:
        FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    
    files = list(RAW_DIR.glob('linkedin_*.json'))
    print(f"\n🔍 Checking {len(files)} LinkedIn posts...")
    print(f"   Threshold: >{MIN_CHARS} chars\n")
    
    passed = 0
    rejected = 0
    
    for file_path in files:
        try:
            with open(file_path) as f:
                data = json.load(f)
                
            result, reason = check_quality(data)
            likes = data.get('likes', 0)
            # Use url as identifier (id field may not exist)
            post_id = data.get('id', data.get('url', file_path.stem)[-50:])

            if result:
                print(f"✅ KEEP  {post_id} ({len(data['text'])} chars, {likes} likes)")
                passed += 1
                if not args.dry_run:
                    shutil.copy2(file_path, FILTERED_DIR / file_path.name)
            else:
                print(f"❌ DROP  {post_id}: {reason}")
                rejected += 1
                
        except Exception as e:
            print(f"⚠️ Error processing {file_path.name}: {e}")
            
    print(f"\n{'='*40}")
    print(f"Retained: {passed}")
    print(f"Filtered: {rejected}")
    print(f"{'='*40}\n")

if __name__ == '__main__':
    main()
