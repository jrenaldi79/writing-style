# Batch Analysis Output Schema

When analyzing emails, output a single JSON file in this format. Save as `batch_NNN.json`.

## Schema

```json
{
  "batch_id": "batch_001",
  "analyzed_at": "2025-01-07T12:00:00Z",
  "email_count": 35,
  
  "new_personas": [
    {
      "name": "Executive Brief",
      "description": "Short, action-oriented updates to leadership team",
      "characteristics": {
        "tone": "direct",
        "formality": "high",
        "avg_length": "short",
        "typical_greeting": "Team,",
        "typical_closing": "-John"
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
        "tone": "direct",
        "formality": "high",
        "sentence_style": "short, punchy",
        "paragraph_style": "single topic per paragraph",
        "greeting": "Team,",
        "closing": "-John",
        "punctuation": "em-dashes, colons for lists",
        "contractions": true,
        "notable_phrases": ["quick update", "three things", "EOD"],
        "structure": "context → action items → deadline"
      }
    }
  ]
}
```

## Field Definitions

### new_personas[]
Only include if this batch discovers a NEW persona not seen before.

| Field | Description |
|-------|-------------|
| name | Specific, descriptive name (e.g., "Executive Brief" not "Formal Email") |
| description | One sentence explaining when this persona is used |
| characteristics | Aggregate patterns for this persona |

### samples[]
One entry per analyzed email.

| Field | Description |
|-------|-------------|
| id | The email filename without extension (e.g., "email_abc123") |
| source | Always "email" for now |
| persona | Name of assigned persona (must match a persona name) |
| confidence | 0.0-1.0 how confident in persona assignment |
| analysis | Detailed style extraction (see below) |

### analysis object

| Field | Description |
|-------|-------------|
| tone | direct, warm, formal, casual, urgent, thoughtful |
| formality | high, medium, low |
| sentence_style | short/punchy, flowing, varied, complex |
| paragraph_style | single topic, multi-topic, bullet-heavy |
| greeting | Exact greeting used (or "none") |
| closing | Exact closing/signature used (or "none") |
| punctuation | Notable patterns (em-dashes, ellipses, exclamations) |
| contractions | true/false - does the author use contractions? |
| notable_phrases | Array of characteristic phrases/expressions |
| structure | How the email is organized |

## Confidence Scoring

| Score | Meaning |
|-------|---------|
| ≥0.70 | Strong match to persona |
| 0.40-0.69 | Tentative match, may need review |
| <0.40 | Weak match, consider as unassigned |

## Example Workflow

1. Read 30-40 raw emails from `raw_samples/`
2. Analyze each for style patterns
3. Cluster into personas (create new if needed)
4. Output single `batch_001.json`
5. Run: `python ingest.py batch_001.json`
6. Repeat for next batch

## Token Efficiency

This approach saves ~40% output tokens by:
- No Python boilerplate per batch
- Single JSON file vs multiple script files
- Generic `ingest.py` handles all persistence
