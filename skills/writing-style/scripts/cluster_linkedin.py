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
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
FILTERED_DIR = get_path("filtered_samples")
RAW_DIR = get_path("raw_samples")
OUTPUT_FILE = get_path("linkedin_persona.json")

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


def calculate_engagement_weight(post: dict) -> float:
    """
    Calculate weight based on engagement. Higher engagement = higher weight.
    Uses log scale to prevent viral posts from dominating.

    Args:
        post: Post dict with 'likes' and 'comments' fields

    Returns:
        float: Weight >= 1.0
    """
    likes = post.get('likes', 0)
    comments = post.get('comments', 0)
    # Comments weighted 2x as they indicate deeper engagement
    engagement_score = likes + (comments * 2)
    # Log scale to prevent viral posts from dominating
    # math.log1p(x) = log(1 + x), handles 0 engagement gracefully
    weight = math.log1p(engagement_score)
    # Minimum weight of 1.0 for zero-engagement posts
    return max(1.0, weight)

def analyze_tone(posts: list) -> dict:
    """
    Infer 1-10 tone vectors from content features.
    Uses engagement-weighted averaging so high-engagement posts influence more.
    """
    # Calculate weights for each post
    weights = [calculate_engagement_weight(p) for p in posts]
    total_weight = sum(weights)

    # Weighted average length
    avg_len = sum(len(p['text']) * w for p, w in zip(posts, weights)) / total_weight

    # Weighted emoji count
    emoji_counts = [len(re.findall(r'[\U0001f600-\U0001f64f]', p['text'])) for p in posts]
    avg_emojis = sum(e * w for e, w in zip(emoji_counts, weights)) / total_weight

    # Weighted question ratio
    question_flags = [1 if '?' in p['text'] else 0 for p in posts]
    has_questions = sum(q * w for q, w in zip(question_flags, weights)) / total_weight
    
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


# =============================================================================
# V2 SCHEMA FUNCTIONS
# =============================================================================

def analyze_linguistic_patterns(posts: list) -> dict:
    """
    Extract sentence-level linguistic patterns for v2 schema.

    Returns:
        dict with sentence_length_avg_words, short_punchy_ratio, uses_contractions,
        uses_em_dash, uses_parentheticals, exclamations_per_post, questions_per_post
    """
    if not posts:
        return {}

    all_sentences = []
    total_exclamations = 0
    total_questions = 0
    has_contractions = False
    has_em_dash = False
    has_parentheticals = False

    # Common contractions pattern
    contraction_pattern = re.compile(r"\b(i'm|i've|i'll|i'd|we're|we've|we'll|we'd|you're|you've|you'll|you'd|they're|they've|they'll|they'd|he's|she's|it's|that's|there's|here's|what's|who's|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|couldn't|wouldn't|shouldn't)\b", re.IGNORECASE)

    for post in posts:
        text = post.get('text', '')

        # Split into sentences (handle ., !, ?)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        all_sentences.extend(sentences)

        # Count punctuation
        total_exclamations += text.count('!')
        total_questions += text.count('?')

        # Check for contractions
        if contraction_pattern.search(text):
            has_contractions = True

        # Check for em-dash (both unicode and double-hyphen)
        if '—' in text or '--' in text:
            has_em_dash = True

        # Check for parentheticals
        if '(' in text and ')' in text:
            has_parentheticals = True

    # Calculate sentence metrics
    num_posts = len(posts)
    sentence_lengths = [len(s.split()) for s in all_sentences]

    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    short_sentences = sum(1 for length in sentence_lengths if length < 8)
    short_punchy_ratio = short_sentences / len(sentence_lengths) if sentence_lengths else 0

    return {
        "sentence_length_avg_words": round(avg_sentence_length, 1),
        "short_punchy_ratio": round(short_punchy_ratio, 2),
        "uses_contractions": has_contractions,
        "uses_em_dash": has_em_dash,
        "uses_parentheticals": has_parentheticals,
        "exclamations_per_post": round(total_exclamations / num_posts, 1),
        "questions_per_post": round(total_questions / num_posts, 1)
    }


def analyze_emoji_profile(posts: list) -> dict:
    """
    Extract emoji usage patterns for v2 schema.

    Returns:
        dict with signature_emojis, placement, per_post_range
    """
    if not posts:
        return {"signature_emojis": [], "placement": "none", "per_post_range": [0, 0]}

    # Comprehensive emoji pattern (covers most common emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Misc symbols & pictographs
        "\U0001F680-\U0001F6FF"  # Transport & map
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002702-\U000027B0"  # Dingbats
        "\U0001F900-\U0001F9FF"  # Supplemental symbols
        "\U0001FA00-\U0001FA6F"  # Chess symbols
        "\U0001FA70-\U0001FAFF"  # Symbols extended
        "\U00002600-\U000026FF"  # Misc symbols
        "]+", re.UNICODE
    )

    all_emojis = []
    emoji_counts_per_post = []
    placement_positions = []  # 'beginning', 'middle', 'end'

    for post in posts:
        text = post.get('text', '')
        emojis_in_post = emoji_pattern.findall(text)

        # Flatten individual emojis (pattern may capture sequences)
        flat_emojis = []
        for e in emojis_in_post:
            flat_emojis.extend(list(e))

        all_emojis.extend(flat_emojis)
        emoji_counts_per_post.append(len(flat_emojis))

        # Analyze placement
        if flat_emojis:
            text_len = len(text)
            for match in emoji_pattern.finditer(text):
                pos = match.start()
                if pos < text_len * 0.2:
                    placement_positions.append('beginning')
                elif pos > text_len * 0.8:
                    placement_positions.append('end')
                else:
                    placement_positions.append('middle')

    # Get signature emojis (top 5 by frequency)
    emoji_counter = Counter(all_emojis)
    signature_emojis = [emoji for emoji, _ in emoji_counter.most_common(5)]

    # Determine primary placement
    if placement_positions:
        placement_counter = Counter(placement_positions)
        primary_placement = placement_counter.most_common(1)[0][0]
        # If mixed (no clear majority), label as "emphasis_points"
        if placement_counter.most_common(1)[0][1] < len(placement_positions) * 0.5:
            primary_placement = "emphasis_points"
    else:
        primary_placement = "none"

    # Calculate range
    min_emoji = min(emoji_counts_per_post) if emoji_counts_per_post else 0
    max_emoji = max(emoji_counts_per_post) if emoji_counts_per_post else 0

    return {
        "signature_emojis": signature_emojis,
        "placement": primary_placement,
        "per_post_range": [min_emoji, max_emoji]
    }


def analyze_platform_rules(posts: list) -> dict:
    """
    Extract LinkedIn-specific formatting and structural rules for v2 schema.

    Returns:
        dict with formatting, hooks, closings, length sections
    """
    if not posts:
        return {}

    # --- Formatting Analysis ---
    line_break_ratios = []
    has_bullets = False
    has_hashtags = False
    hashtag_counts = []
    hashtag_at_end = 0
    single_sentence_paragraphs = 0
    total_paragraphs = 0

    for post in posts:
        text = post.get('text', '')

        # Line break frequency
        double_breaks = text.count('\n\n')
        line_break_ratio = double_breaks / (len(text) / 100) if text else 0
        line_break_ratios.append(line_break_ratio)

        # Bullets
        if re.search(r'^[\s]*[•\-\*]', text, re.MULTILINE):
            has_bullets = True

        # Hashtags
        hashtags = re.findall(r'#\w+', text)
        if hashtags:
            has_hashtags = True
            hashtag_counts.append(len(hashtags))
            # Check if hashtags are at end (last 20% of text)
            last_hashtag_pos = text.rfind('#')
            if last_hashtag_pos > len(text) * 0.8:
                hashtag_at_end += 1

        # Single sentence paragraphs
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if para:
                total_paragraphs += 1
                # Check if single sentence (ends with . ! or ? and no other sentence enders in middle)
                sentence_count = len(re.findall(r'[.!?]+', para))
                if sentence_count <= 1:
                    single_sentence_paragraphs += 1

    # Classify line break frequency
    avg_line_break_ratio = sum(line_break_ratios) / len(line_break_ratios) if line_break_ratios else 0
    if avg_line_break_ratio > 1.5:
        line_break_freq = "high"
    elif avg_line_break_ratio > 0.5:
        line_break_freq = "medium"
    else:
        line_break_freq = "low"

    # Hashtag placement
    hashtag_placement = "end" if hashtag_at_end > len(posts) * 0.5 else "inline"

    # Single sentence paragraph ratio
    single_para_ratio = single_sentence_paragraphs / total_paragraphs if total_paragraphs else 0

    formatting = {
        "line_break_frequency": line_break_freq,
        "single_sentence_paragraphs": single_para_ratio > 0.5,
        "uses_bullets": has_bullets,
        "uses_hashtags": has_hashtags,
        "hashtags_count_range": [min(hashtag_counts, default=0), max(hashtag_counts, default=0)],
        "hashtag_placement": hashtag_placement
    }

    # --- Hooks Analysis ---
    hook_styles = []
    for post in posts:
        text = post.get('text', '')
        first_sentence = re.split(r'[.!?\n]', text)[0].strip() if text else ''

        if '?' in first_sentence:
            hook_styles.append('question')
        elif any(word in first_sentence.lower() for word in ['join', 'apply', 'check out', 'looking for', 'hiring']):
            hook_styles.append('call_to_action')
        else:
            hook_styles.append('observation')

    hook_counter = Counter(hook_styles)
    primary_hook = hook_counter.most_common(1)[0][0] if hook_counter else 'observation'

    hooks = {
        "primary_style": primary_hook,
        "allowed_styles": list(set(hook_styles))
    }

    # --- Closings Analysis ---
    engagement_asks = 0
    link_positions = []

    for post in posts:
        text = post.get('text', '')
        last_sentence = text.strip().split('\n')[-1] if text else ''

        # Check for engagement ask
        if '?' in last_sentence or any(word in last_sentence.lower() for word in ['tag', 'share', 'comment', 'join', 'apply']):
            engagement_asks += 1

        # Link position analysis
        url_match = re.search(r'https?://\S+', text)
        if url_match:
            pos = url_match.start()
            if pos < len(text) * 0.33:
                link_positions.append('beginning')
            elif pos < len(text) * 0.66:
                link_positions.append('middle')
            else:
                link_positions.append('end')

    link_placement = Counter(link_positions).most_common(1)[0][0] if link_positions else "none"

    closings = {
        "primary_style": "invitation" if engagement_asks > len(posts) * 0.3 else "statement",
        "engagement_ask_frequency": round(engagement_asks / len(posts), 2),
        "link_placement": link_placement
    }

    # --- Length Analysis ---
    lengths = [len(post.get('text', '')) for post in posts]
    lengths.sort()

    # Calculate percentiles
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if f != c else data[f]

    length_stats = {
        "target_chars": int(percentile(lengths, 50)),  # median
        "min_chars": int(percentile(lengths, 10)),
        "max_chars": int(percentile(lengths, 90))
    }

    return {
        "formatting": formatting,
        "hooks": hooks,
        "closings": closings,
        "length": length_stats
    }


def analyze_variation_controls(posts: list) -> dict:
    """
    Calculate variation ranges from distributions for v2 schema.

    Returns:
        dict with emoji_per_post_range, question_sentence_ratio_range, hook_style_distribution
    """
    if not posts:
        return {}

    # Emoji per post range
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U00002600-\U000026FF"
        "]+", re.UNICODE
    )

    emoji_counts = []
    question_ratios = []
    hook_styles = []

    for post in posts:
        text = post.get('text', '')

        # Emoji count
        emojis = emoji_pattern.findall(text)
        emoji_count = sum(len(e) for e in emojis)
        emoji_counts.append(emoji_count)

        # Question ratio per post
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        questions = text.count('?')
        question_ratio = questions / len(sentences) if sentences else 0
        question_ratios.append(question_ratio)

        # Hook style
        first_sentence = re.split(r'[.!?\n]', text)[0].strip() if text else ''
        if '?' in first_sentence:
            hook_styles.append('question')
        elif any(word in first_sentence.lower() for word in ['join', 'apply', 'check out', 'hiring']):
            hook_styles.append('call_to_action')
        else:
            hook_styles.append('observation')

    # Hook distribution
    hook_counter = Counter(hook_styles)
    total_hooks = sum(hook_counter.values())
    hook_distribution = {style: round(count / total_hooks, 2) for style, count in hook_counter.items()}

    return {
        "emoji_per_post_range": [min(emoji_counts, default=0), max(emoji_counts, default=0)],
        "question_sentence_ratio_range": [round(min(question_ratios, default=0), 2), round(max(question_ratios, default=0), 2)],
        "hook_style_distribution": hook_distribution
    }


def calculate_confidence(sample_size: int) -> float:
    """
    Calculate confidence score based on sample size.

    Args:
        sample_size: Number of posts analyzed

    Returns:
        float: Confidence score 0.0-1.0
    """
    if sample_size < 3:
        return 0.3
    elif sample_size < 5:
        return 0.5
    elif sample_size < 10:
        return 0.6
    elif sample_size < 15:
        return 0.7
    elif sample_size < 20:
        return 0.8
    elif sample_size < 30:
        return 0.9
    else:
        return 0.95


def create_v2_persona(posts: list) -> dict:
    """
    Create full v2 schema persona with all auto-extractable fields.

    Returns:
        dict matching linkedin_persona_schema_v2.md structure
    """
    if not posts:
        return None

    # Extract all patterns
    tone = analyze_tone(posts)
    linguistic = analyze_linguistic_patterns(posts)
    emoji_profile = analyze_emoji_profile(posts)
    platform_rules = analyze_platform_rules(posts)
    variation = analyze_variation_controls(posts)

    # Calculate enthusiasm level (1-10)
    exclamations = linguistic.get('exclamations_per_post', 0)
    questions = linguistic.get('questions_per_post', 0)
    emoji_density = sum(emoji_profile.get('per_post_range', [0, 0])) / 2
    enthusiasm_raw = (exclamations * 2 + questions + emoji_density) / 2
    enthusiasm_level = max(1, min(10, int(5 + enthusiasm_raw)))

    # Select top examples by engagement
    sorted_posts = sorted(posts, key=lambda p: (p.get('likes', 0), len(p.get('text', ''))), reverse=True)
    top_examples = sorted_posts[:3]  # Top 3 by engagement

    positive_examples = []
    for post in top_examples:
        positive_examples.append({
            "category": "",  # Placeholder for LLM
            "goal": "",  # Placeholder for LLM
            "audience": "",  # Placeholder for LLM
            "engagement": {
                "likes": post.get('likes', 0),
                "comments": post.get('comments', 0)
            },
            "text": post.get('text', ''),
            "what_makes_it_work": []  # Placeholder for LLM
        })

    return {
        "schema_version": "2.0",
        "generated_at": datetime.now().isoformat(),
        "sample_size": len(posts),
        "confidence": calculate_confidence(len(posts)),

        "voice": {
            "tone_vectors": tone,
            "linguistic_patterns": linguistic,
            "emoji_profile": emoji_profile,
            "enthusiasm_level": enthusiasm_level
        },

        "guardrails": {
            # Placeholder - requires LLM assistance
            "never_do": [],
            "forbidden_phrases": ["synergy", "leverage", "deep dive", "game-changer", "circle back"],
            "off_limits_topics": [],
            "compliance": {
                "no_confidential_info": True,
                "no_unverified_claims": True
            }
        },

        "platform_rules": platform_rules,

        "variation_controls": variation,

        "example_bank": {
            "usage_guidance": {
                "instruction": "Match the rhythm, tone, and structural patterns of these examples. Adapt content to new topics without forcing the original subject matter.",
                "what_to_match": [
                    "Sentence length variation",
                    "Opening hook style",
                    "Closing/CTA pattern",
                    "Emoji placement and frequency",
                    "Level of specificity"
                ],
                "what_to_adapt": [
                    "Topic and subject matter",
                    "Specific names, products, companies",
                    "Call-to-action details",
                    "Links and references"
                ],
                "warning": "Do NOT copy examples verbatim. Extract the voice patterns, apply them to new content."
            },
            "positive": positive_examples,
            "negative": []  # Placeholder for LLM
        }
    }

def create_rich_persona(posts: list) -> dict:
    """Create full-fidelity persona object."""
    if not posts: return None
    
    tone = analyze_tone(posts)
    structure = analyze_structure(posts)
    formatting = analyze_formatting(posts)
    keywords = extract_keywords(posts)
    
    # Most representative post (highest engagement, length as tiebreaker)
    best_post = max(posts, key=lambda p: (p.get('likes', 0), len(p['text'])))
    
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

    print(f"Analyzing {len(posts)} posts for V2 Persona generation...")

    # Use V2 schema
    v2_persona = create_v2_persona(posts)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(v2_persona, f, indent=2)

    print(f"\n{'═' * 60}")
    print("✅ LINKEDIN PERSONA GENERATED")
    print(f"{'═' * 60}")
    print(f"   Schema version: {v2_persona['schema_version']}")
    print(f"   Confidence: {v2_persona['confidence']}")
    print(f"   Sample size: {v2_persona['sample_size']}")
    print(f"\nTone vectors:")
    print(json.dumps(v2_persona['voice']['tone_vectors'], indent=2))
    print(f"\n💾 Saved to: {OUTPUT_FILE}")

    print(f"\n{'═' * 60}")
    print("🛑 SESSION 3 COMPLETE - LINKEDIN DONE")
    print(f"{'═' * 60}")
    print("\nLinkedIn voice profile is ready.")
    print("\n👉 NEXT STEP: Generate your writing clone skill")
    print("   Run: python generate_skill.py --name <your-name>")
    print()
    print("This will combine your Email personas + LinkedIn voice")
    print("into an installable skill package.")
    print(f"{'═' * 60}\n")


if __name__ == '__main__':
    main()
