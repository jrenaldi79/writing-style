# Email Persona Schema v2.0

## Overview

This schema defines a robust, machine-readable format for capturing a user's email writing voice with context-adaptive capabilities. Key improvements over v1:

| Aspect | v1 | v2 |
|--------|----|----|
| Tone scores | 4 dimensions only | 4 dimensions + `_instruction` siblings |
| Rhythm metrics | None | Statistical analysis (avg, variance, distribution) |
| Greeting/closing | Single value | Full distribution with percentages |
| Subject lines | Not captured | Pattern analysis (length, casing, prefixes) |
| Guardrails | None | Explicit DO/DON'T rules |
| Examples | Not stored | 3-5 redacted verbatim examples with annotations |
| Variation | Fixed values | Ranges to prevent robotic sameness |
| Seniority | Not captured | Relationship calibration by recipient role |

## Schema Structure

```
persona/
├── voice_fingerprint/         # HOW you say things (stable across contexts)
│   ├── formality/
│   ├── rhythm/
│   ├── mechanics/
│   ├── lexicon/
│   ├── tone_markers/
│   └── credibility_markers/
├── cognitive_load_preferences/ # Information structuring
├── email_channel_rules/       # Deliverability, mobile optimization
├── subject_line_dna/          # Subject line patterns
├── opening_dna/               # Greeting/first sentence patterns
├── body_dna/                  # Structure, argumentation, length
├── cta_dna/                   # Ask types, urgency patterns
├── closing_dna/               # Sign-off, signature, PS usage
├── threading_and_reply_dna/   # Reply/follow-up behavior
├── relationship_calibration/  # Recipient-based adjustments
├── guardrails/                # Hard boundaries (NEVER violate)
├── variation_controls/        # Prevents robotic sameness
├── email_types/               # Type-specific required elements
├── example_bank/              # Positive examples with annotations
└── evaluation_rubric/         # Self-check dimensions
```

---

## Full Schema

```json
{
  "schema_version": "2.0",
  "profile_type": "email_persona",
  "persona_id": "generated_uuid",
  "cluster_name": "Internal Strategic",
  "language": "en-US",
  "created_at": "2026-01-09",

  "source_corpus": {
    "email_count": 45,
    "time_range": {"start": "2025-06-01", "end": "2026-01-01"},
    "domains": ["internal", "external"],
    "data_hygiene_status": "pii_redacted_signatures_removed"
  },

  "voice_fingerprint": {
    "formality": {
      "level": 6,
      "instruction": "Professional but conversational; roughly peer-to-peer standard. Use contractions freely, avoid overly formal phrases like 'Please be advised'.",
      "politeness": 7,
      "directness": 8,
      "hedging_rate_per_100_words": 1.2,
      "hedging_instruction": "Use occasional softeners ('I think', 'possibly') but default to definitive statements.",
      "certainty_language_rate_per_100_words": 2.0
    },
    "rhythm": {
      "avg_words_per_sentence": 14.2,
      "sentence_length_distribution": {
        "lt_8_words_ratio": 0.25,
        "8_to_20_words_ratio": 0.60,
        "gt_20_words_ratio": 0.15
      },
      "paragraphing": {
        "avg_sentences_per_paragraph": 2.5,
        "uses_single_sentence_paragraphs": true,
        "visual_density": "low"
      }
    },
    "mechanics": {
      "contractions": "often",
      "uses_contractions": true,
      "contraction_rate": 0.82,
      "common_contractions": ["I'm", "don't", "we're", "I'll"],
      "punctuation": {
        "exclamations_per_email_avg": 0.3,
        "questions_per_email_avg": 1.1,
        "uses_ellipsis": false,
        "uses_em_dash": true,
        "uses_parentheticals": true,
        "oxford_comma": "consistent"
      },
      "emoji": {
        "allowed": false,
        "avg_per_email": 0.0,
        "allowed_contexts": []
      }
    },
    "lexicon": {
      "signature_phrases": ["quick update", "circling back", "sounds good"],
      "common_transitions": ["but", "and", "so", "however"],
      "preferred_verbs": ["share", "confirm", "align", "send", "review"],
      "banned_words_or_phrases": ["synergy", "touch base", "leverage", "deep dive"],
      "jargon_level": "medium",
      "acronym_handling": "assume_internal_explained_external"
    },
    "tone_markers": {
      "warmth": {
        "level": 5,
        "instruction": "Polite and appreciative, but efficient. Not overly chatty. Acknowledge others' work without excessive praise."
      },
      "authority": {
        "level": 7,
        "instruction": "Project confidence without arrogance. Use 'I recommend' rather than 'I think maybe'. Avoid hedging on decisions."
      },
      "directness": {
        "level": 8,
        "instruction": "Get to the point quickly. Lead with the ask or key information. Minimize preamble."
      },
      "humor": {"enabled": false, "style": "none"},
      "empathy_markers": ["I understand", "That makes sense", "Appreciate you"],
      "gratitude_frequency_per_email_avg": 1.0
    },
    "credibility_markers": {
      "uses_specifics_over_vague": true,
      "uses_numbers_when_available": true,
      "source_citation_style": "link_inline_or_named_source",
      "states_assumptions_explicitly": true
    }
  },

  "cognitive_load_preferences": {
    "bottom_line_up_front": true,
    "action_item_isolation": "bold_and_separate",
    "information_density": "low",
    "scannability_instruction": "Assume reader is skimming on mobile. Use formatting to break up walls of text."
  },

  "email_channel_rules": {
    "deliverability": {
      "avoid_spam_triggers": true,
      "max_links_per_email": 2,
      "attachment_policy": {
        "allowed": true,
        "default_behavior": "offer_link_or_attach_if_requested",
        "file_naming_style": "descriptive_date_optional"
      }
    },
    "mobile_readability": {
      "max_paragraph_lines_preference": 3,
      "prefers_scannable_formatting": true
    }
  },

  "subject_line_dna": {
    "length_chars_range": [15, 55],
    "avg_word_count": 5.2,
    "style_distribution": {
      "direct_topic": 0.50,
      "ask": 0.25,
      "status_update": 0.15,
      "context_plus_request": 0.10
    },
    "casing_distribution": {
      "title_case": 0.60,
      "sentence_case": 0.30,
      "all_caps": 0.05,
      "lowercase": 0.05
    },
    "punctuation": {
      "uses_question_mark_rate": 0.25,
      "uses_exclamation_rate": 0.02,
      "uses_brackets_rate": 0.08,
      "uses_re_prefix_handling": "preserve_thread"
    },
    "common_prefixes": ["Re:", "Fwd:", "FYI:"],
    "templates": [
      "Quick update on [topic]",
      "[Project]: [status/request]",
      "Re: [topic] - [action needed]"
    ],
    "forbidden_patterns": ["ALL CAPS", "clickbait", "excessive urgency", "URGENT!!!"]
  },

  "opening_dna": {
    "greeting_distribution": {
      "Hi {first_name},": 0.55,
      "Hey {first_name},": 0.25,
      "Hello {first_name},": 0.10,
      "Team,": 0.05,
      "No greeting (thread reply)": 0.05
    },
    "primary_style": "Hi {first_name},",
    "first_sentence_functions_distribution": {
      "context_reference": 0.40,
      "purpose_statement": 0.35,
      "gratitude": 0.15,
      "rapport_small_talk": 0.10
    },
    "context_reference_templates": [
      "Following up on our conversation about...",
      "Per your request, here's...",
      "Quick update on..."
    ]
  },

  "body_dna": {
    "structure_preferences": {
      "default_pattern": ["context", "point", "request_or_next_step", "timeframe", "close"],
      "uses_bullets_rate": 0.60,
      "bullet_style": "hyphen",
      "uses_numbered_lists_rate": 0.25,
      "uses_headings_rate": 0.10
    },
    "argumentation_style": {
      "primary_style": "logical_sequential",
      "makes_ask_explicit": true,
      "includes_why_it_matters_rate": 0.35,
      "includes_options_when_blocked_rate": 0.40
    },
    "clarity_habits": {
      "defines_owner_and_deadline": true,
      "restates_decisions": true,
      "summarizes_action_items": {"enabled": true, "when": "multi_point_emails"}
    },
    "typical_length": {
      "target_word_range": [90, 220],
      "short_email_word_max": 80,
      "long_email_word_min": 260,
      "avg_chars": 450,
      "category": "medium"
    }
  },

  "cta_dna": {
    "ask_types_distribution": {
      "confirm": 0.30,
      "schedule": 0.25,
      "approve": 0.15,
      "provide_info": 0.20,
      "introduce_someone": 0.10
    },
    "urgency_style": {
      "uses_deadlines": true,
      "deadline_phrasing": "soft",
      "deadline_instruction": "Frame deadlines as 'needs' rather than demands. e.g. 'Can we target EOD?'",
      "default_timeframes": ["today", "tomorrow", "this week", "by EOD"],
      "avoids_pressure_language": true
    },
    "closing_question_rate": 0.40,
    "calendar_links": {"allowed": true, "placement": "near_cta"}
  },

  "closing_dna": {
    "sign_off_distribution": {
      "Thanks,": 0.45,
      "Best,": 0.25,
      "Appreciate it,": 0.15,
      "-{name}": 0.10,
      "No sign-off (thread reply)": 0.05
    },
    "primary_style": "Thanks,",
    "signature_block": {
      "includes_full_name": true,
      "includes_title": true,
      "includes_company": true,
      "includes_phone": "sometimes",
      "includes_pronouns": "never",
      "includes_disclaimer": "never",
      "format": "compact_multiline"
    },
    "uses_signature_block": true,
    "ps_usage": {"enabled": false, "rate": 0.0}
  },

  "threading_and_reply_dna": {
    "reply_style": {
      "acknowledges_request_first": true,
      "answers_inline": {"enabled": true, "rate": 0.35},
      "quotes_previous_message": {"enabled": true, "rate": 0.50, "style": "minimal"}
    },
    "context_echoing": "minimal",
    "context_instruction": "Assume recipient remembers their last email. Do not summarize previous thread unless >1 week old.",
    "follow_up_behavior": {
      "follow_up_if_no_reply": true,
      "timing_days": [2, 5],
      "max_follow_ups": 2,
      "follow_up_tone": "polite_brief",
      "follow_up_templates": [
        "Just wanted to bump this up...",
        "Following up on the below..."
      ]
    }
  },

  "relationship_calibration": {
    "recipient_segments": {
      "executive": {
        "seniority": "executive",
        "formality_adjustment": 1,
        "length_adjustment": -0.30,
        "more_concise": true,
        "more_direct": true,
        "extra_context": false,
        "greeting_override": "Hi {first_name},"
      },
      "peer": {
        "seniority": "peer",
        "formality_adjustment": 0,
        "length_adjustment": 0,
        "more_concise": false,
        "more_direct": false,
        "extra_context": true
      },
      "report": {
        "seniority": "report",
        "formality_adjustment": -1,
        "supportive": true,
        "coaching_tone": true
      },
      "external_client": {
        "seniority": "external_client",
        "formality_adjustment": 2,
        "more_empathy": true,
        "more_explanation": true,
        "avoid_jargon": true
      },
      "candidate": {
        "seniority": "candidate",
        "warmth_adjustment": 2,
        "clarity_on_next_steps": true
      }
    },
    "power_distance_handling": {
      "to_senior": {"deference": 2, "directness": 7},
      "to_junior": {"supportive": true, "coaching_tone": true}
    }
  },

  "content_modules": {
    "reusable_blocks": {
      "scheduling": [
        "Let me know what works for you.",
        "Happy to find a time that works."
      ],
      "status_update": [
        "Here's where we stand:",
        "Quick update on..."
      ],
      "apology_and_repair": [
        "Apologies for the delay.",
        "Thanks for your patience."
      ]
    }
  },

  "guardrails": {
    "structural_anti_patterns": [
      "Never start with 'I hope this email finds you well'",
      "Never use the word 'delve'",
      "Never apologize for a delay < 24 hours",
      "Never use passive voice for action items"
    ],
    "never_do": [
      "invent prior conversations",
      "use aggressive sales language",
      "use guilt or pressure to force response",
      "overpromise timelines or results",
      "use emoji in formal emails",
      "reply-all unnecessarily"
    ],
    "sensitive_topics": {
      "politics": "avoid",
      "health": "avoid",
      "legal": "avoid_or_refer_to_counsel",
      "salary": "avoid_in_writing",
      "personnel_issues": "handle_privately"
    },
    "confidentiality": {
      "do_not_share_internal_info_externally": true,
      "redact_customer_data": true
    }
  },

  "variation_controls": {
    "allowed_deviation": {
      "sentence_length": 0.15,
      "warmth": 0.10,
      "directness": 0.10
    },
    "deviation_ranges": {
      "sentence_length": [0.85, 1.15],
      "formality": [-1, 1]
    },
    "signature_phrase_max_per_email": 1,
    "bullet_usage_range": [0.30, 0.80],
    "avoid_repetition_window_emails": 5,
    "greeting_rotation": true,
    "phrase_cooldown": 3
  },

  "email_types": {
    "internal_status_update": {
      "goal": "inform_and_align",
      "target_word_range": [120, 260],
      "required_elements": ["status", "blockers", "next_steps", "timeline"],
      "structure": "bullet_heavy",
      "formality_override": null
    },
    "cold_outreach": {
      "goal": "start_conversation",
      "target_word_range": [70, 140],
      "required_elements": ["hook", "credibility", "clear_ask", "easy_out"],
      "max_length": 200,
      "formality_override": 7
    },
    "reply_to_request": {
      "goal": "fulfill_request",
      "target_word_range": [80, 200],
      "required_elements": ["acknowledgment", "answer", "follow_up_offer"]
    },
    "meeting_request": {
      "goal": "schedule_meeting",
      "target_word_range": [60, 120],
      "required_elements": ["purpose", "proposed_times", "duration", "location_or_link"]
    },
    "customer_support_reply": {
      "goal": "resolve_issue",
      "target_word_range": [120, 240],
      "required_elements": ["acknowledge", "apology_if_needed", "steps", "timeline", "close_loop_question"]
    },
    "recruiting_candidate": {
      "goal": "move_process_forward",
      "target_word_range": [110, 220],
      "required_elements": ["context", "next_step", "time_options", "expectations"]
    }
  },

  "example_bank": {
    "usage_guidance": {
      "instruction": "Match the rhythm, tone, and structural patterns of these examples. Adapt content to new topics without forcing the original subject matter.",
      "what_to_match": [
        "Sentence length variation",
        "Opening hook style",
        "Closing/CTA pattern",
        "Level of directness",
        "Use of bullets/formatting"
      ],
      "what_to_adapt": [
        "Topic and subject matter",
        "Specific names, products, companies",
        "Call-to-action details",
        "Links and references"
      ],
      "warning": "Do NOT copy examples verbatim. Extract the voice patterns, apply them to new content."
    },
    "examples": [
      {
        "type": "internal_status_update",
        "subject": "[REDACTED]",
        "body": "Team,\n\nQuick update on [project]:\n\n- Completed: [items]\n- In progress: [items]\n- Blocked: [item] - need [resource]\n\nTarget completion: [date]\n\nLet me know if questions.\n\n-[Name]",
        "context": "Weekly status to direct reports",
        "confidence": 0.92,
        "what_makes_it_work": [
          "BLUF: purpose clear from first line",
          "Bullets for scannability",
          "Explicit blockers and needs",
          "Clear deadline"
        ]
      }
    ]
  },

  "evaluation_rubric": {
    "voice_match_dimensions": [
      {"name": "tone_match", "scale": [1, 5], "description": "Does the tone feel like me?"},
      {"name": "clarity_and_structure", "scale": [1, 5], "description": "Is information organized clearly?"},
      {"name": "ask_specificity", "scale": [1, 5], "description": "Is the ask explicit with owner/deadline?"},
      {"name": "politeness_without_fluff", "scale": [1, 5], "description": "Polite but not wordy?"},
      {"name": "persona_distinctiveness", "scale": [1, 5], "description": "Does this feel distinct, not generic?"}
    ],
    "self_checklist": [
      "Did I state the purpose in the first 1-2 sentences?",
      "Is the ask explicit, with an owner and timeframe if relevant?",
      "Did I avoid inventing facts and avoid banned phrases?",
      "Is the length within target range for this email type?",
      "Would I actually send this?"
    ]
  }
}
```

---

## Section Details

### `voice_fingerprint` - How You Sound

**Purpose:** Core voice patterns that define your unique email style. Should remain stable across different email types.

| Subsection | Source | Description |
|------------|--------|-------------|
| `formality` | LLM | Level + instruction for register |
| `rhythm` | Deterministic | Sentence/paragraph statistics |
| `mechanics` | Deterministic | Contractions, punctuation patterns |
| `lexicon` | LLM | Signature phrases, banned words |
| `tone_markers` | LLM | Warmth/authority/directness with instructions |
| `credibility_markers` | LLM | How you establish credibility |

**Key insight:** Every numeric score (1-10) should have a sibling `_instruction` field explaining what that score means in practice.

---

### `cognitive_load_preferences` - Information Structuring

**Purpose:** How you structure information to reduce reader cognitive load.

| Field | Description |
|-------|-------------|
| `bottom_line_up_front` | Do you lead with the conclusion? |
| `action_item_isolation` | How action items are separated (bold, numbered, etc.) |
| `information_density` | low/medium/high - how packed is each paragraph? |
| `scannability_instruction` | Prose guidance for formatting |

---

### `email_channel_rules` - Platform-Specific

**Purpose:** Rules specific to email as a medium (vs Slack, LinkedIn, etc.)

| Field | Description |
|-------|-------------|
| `deliverability` | Spam trigger avoidance, link limits |
| `mobile_readability` | Short paragraphs, line length |

---

### `subject_line_dna` - First Impression

**Purpose:** Patterns for crafting subject lines that match your style.

| Field | Source | Description |
|-------|--------|-------------|
| `length_chars_range` | Deterministic | Min/max character count |
| `casing_distribution` | Deterministic | Title case vs sentence case |
| `common_prefixes` | Deterministic | Re:, FYI:, [ACTION], etc. |
| `templates` | LLM | Common patterns extracted |
| `forbidden_patterns` | LLM | Anti-patterns to avoid |

---

### `opening_dna` - Starting Strong

**Purpose:** How you begin emails.

| Field | Source | Description |
|-------|--------|-------------|
| `greeting_distribution` | Deterministic | Frequency of each greeting style |
| `first_sentence_functions` | LLM | What the first sentence does |
| `context_reference_templates` | LLM | How you reference prior context |

---

### `body_dna` - Core Content

**Purpose:** How you structure the main content.

| Field | Description |
|-------|-------------|
| `structure_preferences` | Default pattern, bullet usage |
| `argumentation_style` | How you build arguments |
| `clarity_habits` | Restating decisions, summarizing |
| `typical_length` | Word count ranges |

---

### `cta_dna` - Calls to Action

**Purpose:** How you make asks.

| Field | Description |
|-------|-------------|
| `ask_types_distribution` | Types of asks you make |
| `urgency_style` | How you communicate deadlines |
| `closing_question_rate` | % of emails ending with a question |

---

### `closing_dna` - Sign-offs

**Purpose:** How you end emails.

| Field | Source | Description |
|-------|--------|-------------|
| `sign_off_distribution` | Deterministic | Frequency of each sign-off |
| `signature_block` | Deterministic | What's included in signature |
| `ps_usage` | Deterministic | Frequency of P.S. |

---

### `relationship_calibration` - Context Adaptation

**Purpose:** How voice adjusts based on recipient seniority/role.

| Segment | Adjustments |
|---------|-------------|
| `executive` | More concise, more direct |
| `peer` | Baseline style |
| `report` | Supportive, coaching tone |
| `external_client` | More formal, more empathy |
| `candidate` | Warmer, clear next steps |

**Seniority Detection:** Inferred from:
- To/CC field patterns (CEO, VP, Director)
- Email signature analysis
- Domain matching (internal vs external)
- Language deference markers

---

### `guardrails` - Hard Boundaries

**Purpose:** Explicit rules the model must NEVER violate.

| Field | Description |
|-------|-------------|
| `structural_anti_patterns` | Formatting/structure don'ts |
| `never_do` | Behavioral prohibitions |
| `sensitive_topics` | Topics to avoid or handle carefully |
| `confidentiality` | Data protection rules |

---

### `variation_controls` - Anti-Robotic

**Purpose:** Prevents every email from sounding identical.

| Field | Description |
|-------|-------------|
| `deviation_ranges` | Acceptable variance from baseline |
| `signature_phrase_max_per_email` | Avoid overusing phrases |
| `greeting_rotation` | Vary greetings |
| `phrase_cooldown` | Emails before reusing a phrase |

---

### `email_types` - Contextual Templates

**Purpose:** Type-specific requirements inferred from cluster patterns.

Each type includes:
- `goal` - What the email aims to achieve
- `target_word_range` - Appropriate length
- `required_elements` - Must-have components
- `structure` - Structural pattern

---

### `example_bank` - Few-Shot Learning

**Purpose:** Real examples that drive voice accuracy.

**Selection Criteria:**
- Confidence score >= 0.85
- Include subject + full body
- PII redacted
- Annotated with `what_makes_it_work`

---

### `evaluation_rubric` - Self-Check

**Purpose:** Dimensions for evaluating output quality.

| Dimension | Description |
|-----------|-------------|
| `tone_match` | Does it sound like me? |
| `clarity_and_structure` | Is it well-organized? |
| `ask_specificity` | Is the ask clear? |
| `politeness_without_fluff` | Polite but concise? |
| `persona_distinctiveness` | Not generic AI? |

---

## Extraction Difficulty by Section

| Section | Method | Notes |
|---------|--------|-------|
| `voice_fingerprint.rhythm` | Deterministic | NLTK sentence tokenization |
| `voice_fingerprint.mechanics` | Deterministic | Regex patterns |
| `voice_fingerprint.formality` | LLM | Needs level + instruction |
| `voice_fingerprint.tone_markers` | LLM | Needs level + instruction |
| `opening_dna.greeting_distribution` | Deterministic | Regex first line extraction |
| `closing_dna.sign_off_distribution` | Deterministic | Regex last line extraction |
| `subject_line_dna` | Deterministic | Length, casing analysis |
| `guardrails` | LLM | Requires interpretation |
| `relationship_calibration` | LLM | Requires semantic analysis |
| `example_bank` | Hybrid | Selection deterministic, annotation LLM |

---

## Migration from v1

| v1 Field | v2 Location |
|----------|-------------|
| `formality` (1-10) | `voice_fingerprint.formality.level` |
| `warmth` (1-10) | `voice_fingerprint.tone_markers.warmth.level` |
| `authority` (1-10) | `voice_fingerprint.tone_markers.authority.level` |
| `directness` (1-10) | `voice_fingerprint.tone_markers.directness.level` |
| `typical_greeting` | `opening_dna.greeting_distribution` (single entry at 1.0) |
| `typical_closing` | `closing_dna.sign_off_distribution` (single entry at 1.0) |
| `uses_contractions` | `voice_fingerprint.mechanics.uses_contractions` |
| `uses_bullets` | `body_dna.structure_preferences.uses_bullets_rate` |
| `tone` array | `voice_fingerprint.tone_markers` (expanded) |

**Note:** Migrated v1 personas will have placeholder `_instruction` fields and empty `rhythm`/`mechanics` sections (require re-analysis with source emails).
