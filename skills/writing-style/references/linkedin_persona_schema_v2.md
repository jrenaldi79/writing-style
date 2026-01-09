# LinkedIn Persona Schema v2.0

## Overview

This schema defines a robust, machine-readable format for capturing a user's LinkedIn voice. Key improvements over v1:

| Aspect | v1 | v2 |
|--------|----|----|
| JSON validity | Comments, placeholders | Strict valid JSON |
| Voice vs Content | Mixed together | Separated (voice is topic-agnostic) |
| Guardrails | Weak `keywords_forbidden` | Explicit DO/DON'T rules |
| Examples | Single example | Multiple + negative examples |
| Variation | Fixed values | Ranges to prevent robotic sameness |
| Metrics | Mixed qualitative/numeric | Consistent numeric throughout |

## Schema Structure

```
persona/
├── voice/                 # HOW you say things (stable across topics)
├── guardrails/            # Hard boundaries (NEVER violate)
├── platform_rules/        # LinkedIn-specific formatting
├── variation_controls/    # Prevents robotic sameness
├── example_bank/          # Positive + negative examples
└── post_templates/        # Executable structure patterns
```

---

## Full Schema

```json
{
  "schema_version": "2.0",
  "generated_at": "2026-01-08T20:43:15Z",
  "sample_size": 5,
  "confidence": 0.72,

  "voice": {
    "tone_vectors": {
      "formality": 7,
      "warmth": 5,
      "authority": 6,
      "directness": 7
    },

    "linguistic_patterns": {
      "sentence_length_avg_words": 16,
      "short_punchy_ratio": 0.35,
      "uses_contractions": true,
      "uses_em_dash": true,
      "uses_parentheticals": true,
      "exclamations_per_post": 0.8,
      "questions_per_post": 1.2
    },

    "signature_phrases": [
      "give it a whirl",
      "come join me/us"
    ],

    "emoji_profile": {
      "signature_emojis": ["🍌", "🤯", "🚀"],
      "placement": "emphasis_points",
      "per_post_range": [0, 3]
    },

    "enthusiasm_level": 8
  },

  "guardrails": {
    "never_do": [
      "use cringe motivational clichés",
      "sound salesy or guru-like",
      "use corporate boilerplate",
      "start with 'I'm excited to announce'",
      "use engagement bait ('agree?')"
    ],

    "forbidden_phrases": [
      "game-changer",
      "synergy",
      "leverage",
      "deep dive",
      "circle back",
      "thought leader"
    ],

    "off_limits_topics": [
      "politics",
      "religion",
      "medical advice"
    ],

    "compliance": {
      "no_confidential_info": true,
      "no_unverified_claims": true,
      "disclose_ai_if_asked": true
    }
  },

  "platform_rules": {
    "formatting": {
      "line_break_frequency": "high",
      "single_sentence_paragraphs": true,
      "uses_bullets": false,
      "uses_hashtags": true,
      "hashtags_count_range": [2, 5],
      "hashtag_placement": "end"
    },

    "hooks": {
      "primary_style": "observation",
      "allowed_styles": ["observation", "question", "call_to_action"],
      "forbidden_styles": ["clickbait", "controversial_hot_take"],
      "forbidden_openers": [
        "In today's fast-paced world",
        "I'm excited to announce",
        "I'm thrilled to share",
        "Hot take:",
        "Unpopular opinion:"
      ]
    },

    "closings": {
      "primary_style": "invitation",
      "engagement_ask_frequency": 0.6,
      "link_placement": "mid_or_end",
      "forbidden_closers": [
        "Thoughts?",
        "Agree?",
        "Drop a comment below",
        "Like and share if you agree",
        "Follow for more"
      ]
    },

    "length": {
      "target_chars": 500,
      "min_chars": 250,
      "max_chars": 900
    }
  },

  "variation_controls": {
    "signature_phrase_max_per_post": 1,
    "signature_phrase_usage_rate": 0.35,
    "emoji_per_post_range": [0, 3],
    "question_sentence_ratio_range": [0.1, 0.4],
    "hook_style_distribution": {
      "observation": 0.5,
      "question": 0.3,
      "call_to_action": 0.2
    }
  },

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

    "positive": [
      {
        "category": "hiring_announcement",
        "goal": "recruit",
        "audience": "product_managers",
        "engagement": {"likes": 129, "comments": 3},
        "text": "I know there's a lot of super talented folks right now in tech looking for new opportunities...",
        "what_makes_it_work": [
          "Opens with empathy not self-promotion",
          "Specific technical requirements (credibility)",
          "Names actual products (social proof)",
          "Inclusive closing 'me/us'"
        ]
      }
    ],

    "negative": [
      {
        "text": "🚨 10x your productivity with this ONE hack...",
        "why_not_me": ["clickbait opener", "exaggerated claims", "guru energy"]
      },
      {
        "text": "Excited to announce that I'm thrilled to share...",
        "why_not_me": ["corporate boilerplate", "says nothing", "empty enthusiasm"]
      },
      {
        "text": "Thoughts? 👇 Drop a comment if you agree!",
        "why_not_me": ["engagement bait", "desperate energy", "no substance"]
      }
    ]
  },

  "post_templates": [
    {
      "name": "observation_to_invitation",
      "use_when": "sharing a new tool/product/insight",
      "structure": [
        "Punchy observation with opinion (1 line)",
        "Why it matters / what you tried (2-4 lines)",
        "Concrete example or result (2-3 lines)",
        "Invitation to try / question (1-2 lines)"
      ]
    },
    {
      "name": "hiring_call",
      "use_when": "recruiting",
      "structure": [
        "Empathy opener acknowledging market (1 line)",
        "Specific role requirements (2-3 lines)",
        "Why this opportunity is real (credibility markers)",
        "Inclusive call to action"
      ]
    }
  ]
}
```

---

## Section Details

### `voice` - How You Sound

**Purpose:** Topic-agnostic patterns that define your unique voice. Should remain stable whether you're posting about AI, hiring, or personal insights.

| Field | Type | Description |
|-------|------|-------------|
| `tone_vectors` | object | 1-10 scores for formality, warmth, authority, directness |
| `linguistic_patterns` | object | Measurable text patterns (sentence length, punctuation habits) |
| `signature_phrases` | array | Phrases unique to you that appear across posts |
| `emoji_profile` | object | Which emojis, where placed, frequency range |
| `enthusiasm_level` | number | 1-10 overall energy level |

**Key insight:** Voice should NOT include topics. "Mentions AI frequently" is content, not voice.

---

### `guardrails` - Hard Boundaries

**Purpose:** Explicit rules the model must NEVER violate. These prevent "LinkedIn cringe" drift.

| Field | Type | Description |
|-------|------|-------------|
| `never_do` | array | Actions to avoid (behavioral) |
| `forbidden_phrases` | array | Exact phrases to never use |
| `off_limits_topics` | array | Topics to avoid entirely |
| `compliance` | object | Legal/ethical constraints |

**Why this matters:** LLMs tend to drift toward generic patterns. Explicit "never do" is more effective than just showing positive examples.

---

### `platform_rules` - LinkedIn-Specific

**Purpose:** Formatting and structural rules specific to LinkedIn. Would differ for Twitter, email, etc.

| Field | Type | Description |
|-------|------|-------------|
| `formatting` | object | Line breaks, bullets, hashtags |
| `hooks` | object | First-line patterns (allowed/forbidden styles) |
| `closings` | object | CTA patterns, link placement |
| `length` | object | Target/min/max character counts |

---

### `variation_controls` - Anti-Robotic

**Purpose:** Prevents every post from sounding identical. Defines acceptable ranges, not fixed values.

| Field | Type | Description |
|-------|------|-------------|
| `signature_phrase_max_per_post` | number | Don't overuse signature phrases |
| `signature_phrase_usage_rate` | number | % of posts that should include one |
| `emoji_per_post_range` | array | [min, max] emojis per post |
| `hook_style_distribution` | object | Target mix of hook types |

---

### `example_bank` - Few-Shot Learning

**Purpose:** Real examples that drive 60-80% of voice accuracy.

#### Positive Examples

Each positive example includes:
- `category` - Type of post (hiring, commentary, insight)
- `goal` - What the post aims to achieve
- `audience` - Who it's written for
- `engagement` - Proof it worked (likes/comments)
- `text` - Full text (never truncated)
- `what_makes_it_work` - Annotated analysis

#### Negative Examples

Each negative example includes:
- `text` - Anti-pattern example
- `why_not_me` - Specific reasons this violates your voice

**Why negatives matter:** "This is NOT my voice" is extremely effective for LLM prompting.

---

### `post_templates` - Executable Structures

**Purpose:** Lightweight templates that can be followed without becoming formulaic.

Each template includes:
- `name` - Template identifier
- `use_when` - Context trigger
- `structure` - Ordered steps with guidance

---

## Implementation Notes

### Extraction Difficulty by Section

| Section | Auto-Extractable? | Notes |
|---------|-------------------|-------|
| `voice.tone_vectors` | Yes | Current implementation works |
| `voice.linguistic_patterns` | Yes | Requires text analysis |
| `voice.signature_phrases` | Partial | Need n-gram analysis + manual review |
| `guardrails` | No | Requires manual/LLM-assisted creation |
| `platform_rules` | Yes | Most can be extracted from posts |
| `variation_controls` | Yes | Calculate from distributions |
| `example_bank.positive` | Yes | Select top engagement posts |
| `example_bank.negative` | No | Must be generated/curated |

### Confidence Scoring

Top-level `confidence` reflects data quality:
- `< 0.5` - Insufficient data, use defaults
- `0.5-0.7` - Reasonable patterns, some inference
- `0.7-0.9` - Strong patterns, high reliability
- `> 0.9` - Very high confidence (20+ quality posts)

---

## Migration from v1

Current v1 fields map to v2 as follows:

| v1 Field | v2 Location |
|----------|-------------|
| `tone_vectors` | `voice.tone_vectors` |
| `keywords_preferred` | Removed (content, not voice) |
| `keywords_forbidden` | `guardrails.forbidden_phrases` |
| `structural_dna` | Split into `voice.linguistic_patterns` + `platform_rules` |
| `formatting_rules` | `platform_rules.formatting` |
| `few_shot_examples` | `example_bank.positive` |

---

## Usage in System Prompts

When embedding in a system prompt:

1. **Voice section** - Include fully, always applies
2. **Guardrails** - Include fully, emphasize "NEVER" rules
3. **Platform rules** - Include for LinkedIn posts, omit for other contexts
4. **Variation controls** - Include to prevent robotic output
5. **Example bank** - Include 2-3 positive + 2-3 negative examples
6. **Templates** - Include relevant template based on post goal
