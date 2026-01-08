#!/usr/bin/env python3
"""
LinkedIn Persona Creator - Full Fidelity Version

Upgraded to match the Email Persona schema (output_template.md).
Produces a rich JSON profile with tone vectors, structural DNA, and formatting rules.

Usage:
    python cluster_linkedin.py
"""

import json
import re
import math
from pathlib import Path
from datetime import datetime
from collections import Counter

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
FILTERED_DIR = DATA_DIR / "filtered_samples"
RAW_DIR = DATA_DIR / "raw_samples"
OUTPUT_FILE = DATA_DIR / "linkedin_persona.json"

def load_posts() -> list:
    """Load filtered posts."""
    source_dir = FILTERED_DIR if FILTERED_DIR.exists() else RAW_DIR
    posts = []
    for f in source_dir.glob('linkedin_*.json'):
        try:
            with open(f) as file:
                posts.append(json.load(file))
        except: pass
    return posts

def analyze_tone(posts: list) -> dict:
    """
    Infer 1-10 tone vectors from content features.
    This is heuristic-based since we don't have an LLM in the loop for this script.
    """
    avg_len = sum(len(p['text']) for p in posts) / len(posts)
    emoji_count = sum(len(re.findall(r'[\U0001f600-\U0001f64f]', p['text'])) for p in posts)
    avg_emojis = emoji_count / len(posts)
    has_questions = sum(1 for p in posts if '?' in p['text']) / len(posts)
    
    # Formality (1-10)
    # More emojis = less formal. Longer text = usually more formal.
    formality = 7.0
    if avg_emojis > 2: formality -= 2
    if avg_len < 200: formality -= 1
    if avg_len > 1000: formality += 1
    
    # Warmth (1-10)
    # Emojis and questions (engagement) increase warmth
    warmth = 5.0
    if avg_emojis > 0.5: warmth += 2
    if has_questions > 0.3: warmth += 1
    
    # Authority (1-10)
    # Technical terms and length increase authority
    authority = 6.0
    tech_terms = ['ai', 'strategy', 'product', 'future', 'scale', 'model']
    tech_density = sum(sum(p['text'].lower().count(t) for t in tech_terms) for p in posts) / len(posts)
    if tech_density > 2: authority += 2
    if avg_len > 800: authority += 1
    
    # Directness (1-10)
    # Short sentences = more direct
    directness = 7.0
    
    return {
        # Clamp to 1-10
        'formality': max(1, min(10, int(formality))),
        'warmth': max(1, min(10, int(warmth))),
        'authority': max(1, min(10, int(authority))),
        'directness': max(1, min(10, int(directness)))
    }

def analyze_structure(posts: list) -> dict:
    """Analyze structural DNA."""
    # Openers (First line)
    openers = [p['text'].split('\n')[0][:50] for p in posts]
    # Closers (Last line)
    closers = [p['text'].strip().split('\n')[-1][:50] for p in posts]
    
    # Check patterns
    has_hook = any('?' in o or '!' in o for o in openers)
    has_cta = any('?' in c for c in closers)
    
    return {
        "opener_pattern": "Hook-based (Questions or strong statements)" if has_hook else "Context-first",
        "closer_pattern": "Engagement question or Call to Action" if has_cta else "Professional sign-off",
        "sentence_variance": "High (Mix of short punchy lines and detailed paragraphs)",
        "paragraph_structure": "Concept → Evidence → Insight → Engagement"
    }

def analyze_formatting(posts: list) -> dict:
    """Analyze formatting rules."""
    has_bullets = any('•' in p['text'] or '-' in p['text'] for p in posts)
    has_hashtags = any('#' in p['text'] for p in posts)
    emoji_freq = "Frequent" if sum(p['text'].count('🍌') + p['text'].count('🚀') for p in posts) > 5 else "Sparingly"
    
    return {
        "bullet_points": "Used for lists and emphasis" if has_bullets else "Rarely used",
        "bolding": "Used for key terms and headers",
        "emojis": f"{emoji_freq} (Strategic placement for tone)",
        "hashtags": "3-5 relevant tags at the end" if has_hashtags else "Minimal"
    }

def extract_keywords(posts: list) -> list:
    """Extract common technical keywords."""
    text = " ".join(p['text'].lower() for p in posts)
    words = re.findall(r'\b\w{4,}\b', text)
    common = Counter(words).most_common(20)
    # Filter for domain-specific
    domain_terms = {'product', 'ai', 'team', 'model', 'agent', 'discovery', 'scale', 'context', 'workflow'}
    return [w for w, c in common if w in domain_terms]

def create_rich_persona(posts: list) -> dict:
    """Create full-fidelity persona object."""
    if not posts: return None
    
    tone = analyze_tone(posts)
    structure = analyze_structure(posts)
    formatting = analyze_formatting(posts)
    keywords = extract_keywords(posts)
    
    # Most representative post (longest for now, good proxy for depth)
    best_post = max(posts, key=lambda p: len(p['text']))
    
    return {
        "id": "linkedin_professional",
        "meta": {
            "name": "Professional LinkedIn Voice",
            "description": "Unified thought-leader voice for public broadcasting. Authoritative yet accessible.",
            "triggers": ["linkedin", "social_post", "announcement", "thought_leadership"],
            "anti_patterns": ["Low-effort reposts", "Overly casual slang", "Wall of text without formatting"]
        },
        "voice_configuration": {
            "tone_vectors": tone,
            "keywords_preferred": keywords,
            "keywords_forbidden": ["synergy", "leverage", "deep dive"], # Generic corp-speak
        },
        "structural_dna": structure,
        "formatting_rules": formatting,
        "few_shot_examples": [
            {
                "input_context": "Announcement/Thought Leadership",
                "output_text": best_post['text']
            }
        ]
    }

def main():
    print("Loading posts...")
    posts = load_posts()
    if not posts:
        print("No posts found! Run fetch/filter first.")
        return
        
    print(f"Analyzing {len(posts)} posts for Rich Persona generation...")
    persona = create_rich_persona(posts)
    
    # Wrap in the expected registry structure
    output = {
        "source": "linkedin",
        "generated_at": datetime.now().isoformat(),
        "persona": persona
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
        
    print(f"✅ Generated Rich LinkedIn Persona: {OUTPUT_FILE}")
    print(json.dumps(persona['voice_configuration']['tone_vectors'], indent=2))

if __name__ == '__main__':
    main()
