#!/usr/bin/env python3
"""
Export LinkedIn posts and current persona for LLM analysis.

Outputs a single markdown file containing:
1. Analysis instructions (embedded from llm_analysis_guide.md)
2. Current persona JSON (auto-extracted fields)
3. All filtered posts with engagement data

Usage:
    python3 prepare_llm_analysis.py
    python3 prepare_llm_analysis.py --output custom_output.md
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import argparse
from pathlib import Path
from datetime import datetime

from config import get_data_dir, get_path

# Paths
DATA_DIR = get_data_dir()
FILTERED_DIR = get_path("filtered_samples")
PERSONA_FILE = get_path("linkedin_persona.json")
OUTPUT_FILE = DATA_DIR / "llm_analysis_input.md"

# Guide is in references/ relative to this script
SCRIPT_DIR = Path(__file__).parent
GUIDE_FILE = SCRIPT_DIR.parent / "references" / "llm_analysis_guide.md"


def load_posts() -> list:
    """Load filtered LinkedIn posts, sorted by date (oldest first)."""
    posts = []
    if not FILTERED_DIR.exists():
        return posts

    for f in sorted(FILTERED_DIR.glob('linkedin_*.json')):
        try:
            with open(f) as file:
                post = json.load(file)
                posts.append(post)
        except Exception as e:
            print(f"Warning: Could not load {f}: {e}")

    # Sort by date (oldest first for chronological reading)
    posts.sort(key=lambda p: p.get('date_posted', ''))
    return posts


def load_persona() -> dict:
    """Load current linkedin_persona.json."""
    if not PERSONA_FILE.exists():
        return {}

    with open(PERSONA_FILE) as f:
        return json.load(f)


def load_guide() -> str:
    """Load llm_analysis_guide.md content."""
    if not GUIDE_FILE.exists():
        return "# Analysis Guide\n\nSee references/llm_analysis_guide.md for instructions."

    with open(GUIDE_FILE) as f:
        return f.read()


def format_post(post: dict, index: int, total: int) -> str:
    """Format a single post for markdown output."""
    lines = []

    # Header
    lines.append(f"### Post {index + 1} of {total} (index: {index})")
    lines.append("")

    # Engagement
    likes = post.get('likes', 0)
    comments = post.get('comments', 0)
    lines.append(f"**Engagement:** {likes} likes, {comments} comments")

    # Date
    date_posted = post.get('date_posted', 'Unknown')
    if date_posted and date_posted != 'Unknown':
        # Parse and format date nicely
        try:
            dt = datetime.fromisoformat(date_posted.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except:
            date_str = date_posted[:10] if len(date_posted) >= 10 else date_posted
    else:
        date_str = 'Unknown'
    lines.append(f"**Date:** {date_str}")

    # Content type
    content_type = post.get('content_type', 'post')
    if content_type != 'post':
        lines.append(f"**Type:** {content_type}")

    lines.append("")

    # Text
    lines.append("**Text:**")
    text = post.get('text', '')
    # Indent the text for readability
    lines.append("```")
    lines.append(text)
    lines.append("```")

    # Top comments (if any)
    top_comments = post.get('top_comments', [])
    if top_comments:
        lines.append("")
        lines.append("**Top Comments:**")
        for comment in top_comments[:3]:  # Max 3 comments
            commenter = comment.get('user_name', 'Anonymous')
            text = comment.get('comment', '')
            if text:
                # Truncate long comments
                if len(text) > 200:
                    text = text[:200] + "..."
                lines.append(f"- \"{text}\" — {commenter}")

    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def generate_output(posts: list, persona: dict, guide: str) -> str:
    """Generate the full markdown output."""
    lines = []

    # Title
    lines.append("# LinkedIn Voice Analysis Input")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Posts: {len(posts)}")
    lines.append("")

    # Instructions section
    lines.append("---")
    lines.append("")
    lines.append(guide)
    lines.append("")

    # Current persona section
    lines.append("---")
    lines.append("")
    lines.append("## Current Persona (Auto-Extracted)")
    lines.append("")
    lines.append("The following has already been extracted automatically. Your task is to complete the empty/placeholder fields.")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(persona, indent=2))
    lines.append("```")
    lines.append("")

    # Posts section
    lines.append("---")
    lines.append("")
    lines.append("## All Posts (Chronological)")
    lines.append("")
    lines.append("Review all posts below to understand the user's voice patterns.")
    lines.append("")

    for i, post in enumerate(posts):
        lines.append(format_post(post, i, len(posts)))

    # Footer with reminder
    lines.append("---")
    lines.append("")
    lines.append("## Your Task")
    lines.append("")
    lines.append("Now that you've reviewed all posts, provide your analysis as a JSON object.")
    lines.append("See the 'Output Format' section in the instructions above for the exact structure.")
    lines.append("")
    lines.append("Remember:")
    lines.append("- Use `index` values (0, 1, 2...) when annotating positive examples")
    lines.append("- Generate 3-5 negative examples that represent anti-patterns")
    lines.append("- Be specific in your observations - generic advice isn't helpful")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Export LinkedIn posts for LLM analysis')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file path (default: llm_analysis_input.md in data dir)')
    args = parser.parse_args()

    # Determine output path
    output_path = Path(args.output) if args.output else OUTPUT_FILE

    # Load data
    print("Loading posts...")
    posts = load_posts()
    if not posts:
        print("Error: No filtered LinkedIn posts found.")
        print(f"Expected location: {FILTERED_DIR}")
        print("Run filter_linkedin.py first.")
        return 1

    print(f"Found {len(posts)} posts")

    print("Loading persona...")
    persona = load_persona()
    if not persona:
        print("Warning: No linkedin_persona.json found.")
        print("Run cluster_linkedin.py first for best results.")
        persona = {"note": "No auto-extracted persona available"}

    print("Loading analysis guide...")
    guide = load_guide()

    # Generate output
    print("Generating analysis input file...")
    output = generate_output(posts, persona, guide)

    # Write output
    with open(output_path, 'w') as f:
        f.write(output)

    print(f"\n[OK] Generated: {output_path}")
    print(f"   Posts included: {len(posts)}")
    print(f"   File size: {len(output):,} characters")
    print("")
    print("Next steps:")
    print("1. Open the generated file")
    print("2. Copy contents to your preferred LLM")
    print("3. Save LLM's JSON output to a file (e.g., llm_output.json)")
    print("4. Run: python3 merge_llm_analysis.py llm_output.json")

    return 0


if __name__ == '__main__':
    exit(main())
