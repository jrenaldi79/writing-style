# Batch Analysis Output Schema

When analyzing emails, output a single JSON file in this format. Save as `batch_NNN.json`.

## Schema

```json
{
  "batch_id": "batch_001",
  "analyzed_at": "2025-01-07T12:00:00Z",
  "email_count": 35,
  "cluster_id": 2,
  
  "calibration_referenced": true,
  "calibration_notes": "Anchored formality against examples 3/5, authority against 7/9",
  
  "new_personas": [
    {
      "name": "Executive Brief",
      "description": "Short, action-oriented updates to leadership team",
      "characteristics": {
        "tone": ["direct", "confident"],
        "formality": 6,
        "warmth": 5,
        "authority": 8,
        "directness": 8,
        "avg_length": "short",
        "typical_greeting": "Team,",
        "typical_closing": "-John",
        "uses_bullets": true,
        "uses_contractions": true
      }
    }
  ],
  
  "samples": [
    {
      "id": "email_abc123def456",
      "source": "email",
      "persona": "Executive Brief",
      "confidence": 0.85,
      "analysis": {
        "tone_vectors": {
          "formality": 6,
          "warmth": 5,
          "authority": 8,
          "directness": 8
        },
        "tone_descriptors": ["direct", "confident", "efficient"],
        "sentence_style": "short, punchy",
        "paragraph_style": "single topic per paragraph",
        "greeting": "Team,",
        "closing": "-John",
        "punctuation": ["em-dashes", "colons for lists"],
        "contractions": true,
        "notable_phrases": ["quick update", "three things", "EOD"],
        "structure": "context → action items → deadline"
      },
      "context": {
        "recipient_type": "team",
        "audience": "internal",
        "thread_position": "initiating"
      }
    }
  ]
}
```

## Field Definitions

### Root Fields

| Field | Required | Description |
|-------|----------|-------------|
| batch_id | Yes | Unique identifier (e.g., "batch_001") |
| analyzed_at | Yes | ISO timestamp of analysis |
| email_count | Yes | Number of emails in batch |
| cluster_id | No | Which cluster this batch analyzes (if using clustering) |
| calibration_referenced | **Yes** | Must be `true` - confirms you read calibration.md |
| calibration_notes | Yes | Brief note on how you anchored your scores |
| new_personas | No | Only if discovering NEW personas |
| samples | Yes | One entry per analyzed email |

### new_personas[]

Only include if this batch discovers a NEW persona not seen before.

| Field | Description |
|-------|-------------|
| name | Specific, descriptive name (e.g., "Executive Brief" not "Formal Email") |
| description | One sentence explaining when this persona is used |
| characteristics | Aggregate patterns including tone_vectors (see below) |

### samples[]

One entry per analyzed email.

| Field | Required | Description |
|-------|----------|-------------|
| id | Yes | The email filename without extension (e.g., "email_abc123") |
| source | Yes | Always "email" for now |
| persona | Yes | Name of assigned persona (must match a persona name) |
| confidence | Yes | 0.0-1.0 how confident in persona assignment |
| analysis | Yes | Detailed style extraction (see below) |
| context | Yes | Recipient/thread context from enrichment |

### analysis object

| Field | Description |
|-------|-------------|
| tone_vectors | **Calibrated scores 1-10** for formality, warmth, authority, directness |
| tone_descriptors | Array of adjectives: direct, warm, formal, casual, urgent, thoughtful |
| sentence_style | short/punchy, flowing, varied, complex |
| paragraph_style | single topic, multi-topic, bullet-heavy |
| greeting | Exact greeting used (or "none") |
| closing | Exact closing/signature used (or "none") |
| punctuation | Notable patterns (em-dashes, ellipses, exclamations) |
| contractions | true/false - does the author use contractions? |
| notable_phrases | Array of characteristic phrases/expressions |
| structure | How the email is organized |

### context object (NEW)

Carried from enrichment data:

| Field | Description |
|-------|-------------|
| recipient_type | individual, small_group, team, broadcast |
| audience | internal, external, mixed |
| thread_position | initiating, reply, forward |

## Tone Vectors (Calibrated)

**IMPORTANT:** Use the calibration.md reference to ensure consistent scoring.

| Dimension | 1 | 5 | 10 |
|-----------|---|---|----|
| Formality | "yo u free?" | "Hi John, following up..." | "Dear Mr. Smith, Please be advised..." |
| Warmth | "Per your request..." | "Happy to help!" | "So great to hear from you!" |
| Authority | "Sorry if wrong..." | "I recommend..." | "This is the approach." |
| Directness | "I was wondering if perhaps..." | "We should discuss..." | "No. Fix it." |

## Confidence Scoring

| Score | Meaning |
|-------|--------|
| ≥0.70 | Strong match to persona |
| 0.40-0.69 | Tentative match, may need review |
| <0.40 | Weak match, consider as unassigned |

## Example Workflow

1. **Read calibration.md** first (required)
2. Read cluster emails from prepare_batch.py output
3. Analyze each for style patterns with **calibrated scores**
4. Cluster into personas (create new if needed)
5. Output single `batch_001.json`
6. Run: `python ingest.py batches/batch_001.json`
7. Repeat for next cluster

## Validation Checklist

Before saving your batch JSON:

- [ ] `calibration_referenced: true` is set
- [ ] `calibration_notes` explains your anchoring approach
- [ ] All tone_vectors are 1-10 integers
- [ ] Every sample has a persona assignment
- [ ] Confidence scores reflect actual certainty
- [ ] Context fields match enrichment data
