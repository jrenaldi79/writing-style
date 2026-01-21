#!/usr/bin/env python3
"""
Batch LinkedIn Content Processor - Token-efficient processing

Processes scraped LinkedIn data in one pass.

Usage:
    # From file
    python process_linkedin_batch.py scraped_data.json
    
    # From stdin
    echo '[{"url":"...", "content":"..."}]' | python process_linkedin_batch.py -
    
    # Direct in Python
    python -c 'import process_linkedin_batch; process_linkedin_batch.process_batch(data)'
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
OUTPUT_DIR = DATA_DIR / "raw_samples"
HOLDOUT_DIR = DATA_DIR / "holdout_samples"


def parse_linkedin_post(content: str, url: str) -> dict:
    """Quick parse of LinkedIn post from scraped content."""
    # Extract post ID from URL
    match = re.search(r'activity-(\d+)', url)
    post_id = match.group(1) if match else None
    
    if not post_id:
        return None
    
    # Extract main text (remove LinkedIn UI elements)
    text = content
    
    # Clean up common LinkedIn UI text
    for pattern in ['Report this post', 'Like Comment Share', 'To view or add a comment',
                    'Welcome back', 'Sign in', 'Join for free', 'New to LinkedIn']:
        text = text.replace(pattern, '')
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Extract hashtags
    hashtags = re.findall(r'#\w+', text)
    
    return {
        'id': f'linkedin_post_{post_id}',
        'source': 'linkedin',
        'content_type': 'post',
        'url': url,
        'text': text,
        'hashtags': hashtags,
        'scraped_at': datetime.now().isoformat()
    }


def save_content(content: dict, holdout: bool = False) -> None:
    """Save LinkedIn content to file."""
    output_dir = HOLDOUT_DIR if holdout else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{content['id']}.json"
    
    with open(output_file, 'w') as f:
        json.dump(content, f, indent=2)


def process_batch(scraped_data: list, holdout_fraction: float = 0.0) -> dict:
    """
    Process batch of scraped LinkedIn content.
    
    Args:
        scraped_data: List of dicts with keys: url, content, likes, comments
        holdout_fraction: Fraction to hold out (0-1)
        
    Returns:
        Summary statistics
    """
    import random
    
    stats = {
        'total': len(scraped_data),
        'successful': 0,
        'failed': 0,
        'holdout': 0,
        'engagement': {'total_likes': 0, 'total_comments': 0},
        'posts': []
    }
    
    # Shuffle for random holdout
    if holdout_fraction > 0:
        random.seed(42)
        random.shuffle(scraped_data)
    
    holdout_count = int(len(scraped_data) * holdout_fraction)
    
    for i, item in enumerate(scraped_data):
        try:
            # Parse post
            post = parse_linkedin_post(item['content'], item['url'])
            
            if not post:
                stats['failed'] += 1
                continue
            
            # Add engagement data
            post['engagement'] = {
                'likes': item.get('likes', 0),
                'comments': item.get('comments', 0)
            }
            
            # Determine if holdout
            is_holdout = i < holdout_count
            
            # Save
            save_content(post, holdout=is_holdout)
            
            # Update stats
            stats['successful'] += 1
            if is_holdout:
                stats['holdout'] += 1
            
            stats['engagement']['total_likes'] += post['engagement']['likes']
            stats['engagement']['total_comments'] += post['engagement']['comments']
            
            stats['posts'].append({
                'id': post['id'],
                'likes': post['engagement']['likes'],
                'comments': post['engagement']['comments'],
                'length': len(post['text']),
                'holdout': is_holdout
            })
            
        except Exception as e:
            print(f"Error processing {item.get('url', 'unknown')}: {e}")
            stats['failed'] += 1
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch process LinkedIn content')
    parser.add_argument('input', nargs='?', default='-', 
                       help='JSON file or - for stdin')
    parser.add_argument('--holdout', type=float, default=0.0,
                       help='Holdout fraction (0-1)')
    
    args = parser.parse_args()
    
    # Load data
    if args.input == '-':
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)
    
    # Process
    stats = process_batch(data, holdout_fraction=args.holdout)
    
    # Print summary
    print("\n" + "="*60)
    print("LINKEDIN BATCH PROCESSING COMPLETE")
    print("="*60)
    print(f"Total processed: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Holdout: {stats['holdout']}")
    print(f"\nTotal engagement:")
    print(f"  Likes: {stats['engagement']['total_likes']}")
    print(f"  Comments: {stats['engagement']['total_comments']}")
    print(f"\nPosts by engagement:")
    
    # Sort by likes
    sorted_posts = sorted(stats['posts'], key=lambda x: x['likes'], reverse=True)
    for post in sorted_posts[:5]:
        holdout_tag = " [HOLDOUT]" if post['holdout'] else ""
        print(f"  - {post['id']}: {post['likes']} likes, {post['length']} chars{holdout_tag}")
    
    print("="*60)
    
    # Return for programmatic use
    return stats


if __name__ == '__main__':
    main()
