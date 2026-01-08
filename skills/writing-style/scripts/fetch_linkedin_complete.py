#!/usr/bin/env python3
"""
Complete LinkedIn Fetcher - Token-efficient end-to-end workflow

This demonstrates the efficient pattern:
1. Search once (get all URLs)
2. Scrape in batch
3. Process in batch
4. Report results

Usage:
    python fetch_linkedin_complete.py --profile renaldi --limit 20
    python fetch_linkedin_complete.py --profile renaldi --limit 50 --holdout 0.15
"""

import json
import argparse
from pathlib import Path
import process_linkedin_batch


def instructions_for_agent(profile: str, limit: int, holdout: float):
    """
    Print instructions for Claude agent to execute workflow efficiently.
    
    This is the TOKEN-EFFICIENT pattern:
    - Minimal tool calls
    - Batch operations
    - Single processing pass
    """
    
    print("\n" + "="*70)
    print("TOKEN-EFFICIENT LINKEDIN FETCHING WORKFLOW")
    print("="*70)
    print("\n📋 AGENT INSTRUCTIONS:\n")
    
    print("STEP 1: Search for LinkedIn posts (ONE MCP call)")
    print("─" * 70)
    print(f'''use_mcp_tool(
  server_name="Social Media Scraper",
  tool_name="search_engine",
  arguments={{
    "query": "site:linkedin.com/posts/{profile}",
    "engine": "google"
  }}
)''')
    print("\nExpected: 10+ post URLs\n")
    
    print("STEP 2: Extract URLs and batch scrape (ONE MCP call)")
    print("─" * 70)
    print(f'''# Extract top {limit} URLs from search results
urls = [result['link'] for result in search_results['organic'][:POST_LIMIT]]

use_mcp_tool(
  server_name="Social Media Scraper",
  tool_name="scrape_batch",
  arguments={{"urls": urls}}
)''')
    print(f"\nExpected: {limit} scraped posts\n")
    
    print("STEP 3: Parse engagement and save to temp file (ONE file write)")
    print("─" * 70)
    print('''# Parse scraped content and extract engagement
scrape_data = []
for item in scraped_results:
    # Extract likes/comments from content
    likes = extract_likes(item['content'])
    comments = extract_comments(item['content'])
    
    scrape_data.append({
        "url": item['url'],
        "content": item['content'],
        "likes": likes,
        "comments": comments
    })

# Write to temp file
with open('/tmp/linkedin_scraped.json', 'w') as f:
    json.dump(scrape_data, f)''')
    print("\nExpected: JSON file with all scraped data\n")
    
    print("STEP 4: Batch process everything (ONE Python execution)")
    print("─" * 70)
    print(f'''use_mcp_tool(
  server_name="Terminal",
  tool_name="start_process",
  arguments={{
    "command": "python /Users/john_renaldi/writing-style/skill/scripts/process_linkedin_batch.py /tmp/linkedin_scraped.json --holdout {holdout}",
    "timeout_ms": 10000
  }}
)''')
    print(f"\nExpected: All {limit} posts processed, {int(limit * holdout)} held out\n")
    
    print("STEP 4.5: Quality Filtering (Critical)")
    print("─" * 70)
    print('''use_mcp_tool(
  server_name="Terminal",
  tool_name="start_process",
  arguments={
    "command": "python /Users/john_renaldi/writing-style/skill/scripts/filter_linkedin.py",
    "timeout_ms": 5000
  }
)''')
    print("\nExpected: Removal of snippet-only or low-quality posts\n")
    
    print("STEP 5: Show status (ONE status check)")
    print("─" * 70)
    print('''use_mcp_tool(
  server_name="Terminal",
  tool_name="start_process",
  arguments={
    "command": "python /Users/john_renaldi/writing-style/skill/scripts/fetch_linkedin.py --status",
    "timeout_ms": 5000
  }
)''')
    print("\nExpected: Summary of all LinkedIn content collected\n")
    
    print("="*70)
    print("\n📊 EFFICIENCY COMPARISON:\n")
    print("OLD APPROACH (Sequential):")
    print("  • 1 search call")
    print("  • 1 batch scrape call")
    print(f"  • {limit} individual parse operations (via REPL)")
    print(f"  • {limit} individual save operations")
    print("  • Multiple status checks")
    print(f"  TOTAL: ~{limit + 5} tool calls\n")
    
    print("NEW APPROACH (Batch):")
    print("  • 1 search call")
    print("  • 1 batch scrape call")
    print("  • 1 file write")
    print("  • 1 batch process")
    print("  • 1 status check")
    print(f"  TOTAL: 5 tool calls (vs ~{limit + 5})\n")
    
    print(f"💰 TOKEN SAVINGS: ~{((limit + 5 - 5) / (limit + 5) * 100):.0f}% reduction\n")
    print("="*70)
    print("\n✅ This pattern applies to ANY batch processing:")
    print("   - Email fetching")
    print("   - File processing")
    print("   - Data transformations")
    print("   - Multi-step workflows")
    print("\n🎯 Key principle: Minimize context switches, maximize batch operations\n")


def main():
    parser = argparse.ArgumentParser(
        description='LinkedIn fetcher with token-efficient workflow'
    )
    parser.add_argument('--profile', required=True, help='LinkedIn username')
    parser.add_argument('--limit', type=int, default=20, help='Max posts to fetch')
    parser.add_argument('--holdout', type=float, default=0.15, help='Holdout fraction')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute workflow (requires agent)')
    
    args = parser.parse_args()
    
    if args.execute:
        print("⚠️  Execution requires agent with MCP tool access")
        print("    Run this script without --execute to see instructions\n")
    
    instructions_for_agent(args.profile, args.limit, args.holdout)


if __name__ == '__main__':
    main()
