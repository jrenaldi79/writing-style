---
name: writing-style-clone
description: Analyze a user's emails and LinkedIn posts to discover their distinct writing personas, then generate a personalized system prompt that enables any LLM to replicate their authentic voice.
---

# Writing Style Clone

Analyze writing samples to discover personas and generate a personalized writing assistant prompt.

## Workflow Overview

Three phases across multiple conversations (to manage context window):

1. **Setup** → Create data directory, download emails in bulk
2. **Analysis** → Analyze downloaded samples, cluster into personas
3. **Generation** → Synthesize patterns into final writing assistant prompt

## Phase 1: Setup

**Goal:** Create workspace, download emails in bulk.

Run setup sequence:
```bash
mkdir -p ~/Documents/my-writing-style/{samples,prompts,raw_samples,batches} && \
cp ~/Documents/writing-style/skill/scripts/*.py ~/Documents/my-writing-style/ && \
cd ~/Documents/my-writing-style && \
python3 -c 'import sys; sys.path.append("."); from state_manager import init_state; init_state(".")'
```

Then ask user how many emails to fetch (recommend 100+):
```bash
cd ~/Documents/my-writing-style && python3 fetch_emails.py --count N
```

After completion, tell user to start a **NEW conversation** for Phase 2.

## Phase 2: Analysis

**Goal:** Analyze downloaded samples, output JSON, run ingest.

### Batch Size
Process **30-40 emails per batch** to maximize efficiency while staying within context limits.

### Workflow (Token-Efficient)

1. **Read raw emails:**
```python
from pathlib import Path
import json

raw_dir = Path.home() / "Documents" / "my-writing-style" / "raw_samples"
emails = sorted(raw_dir.glob("email_*.json"))[:40]  # First 40 unprocessed

for email_file in emails:
    with open(email_file) as f:
        data = json.load(f)
    # Analyze: subject, body, to, snippet
```

2. **Analyze each email** using schema in `references/analysis_schema.md`:
   - Tone, formality, sentence/paragraph style
   - Greeting and closing patterns
   - Punctuation habits, contractions
   - Notable phrases and structure

3. **Cluster into personas:**
   - Group similar samples by tone + formality + structure
   - Create new persona if 3+ samples cluster together
   - Use specific names: "Executive Brief" not "Formal Email"

4. **Output single JSON file** following `references/batch_schema.md`:
```json
{
  "batch_id": "batch_001",
  "new_personas": [...],
  "samples": [...]
}
```
Save to: `~/Documents/my-writing-style/batches/batch_001.json`

5. **Run ingest:**
```bash
cd ~/Documents/my-writing-style && python3 ingest.py batches/batch_001.json
```

### Why JSON Instead of Python Scripts?
- **Saves ~40% output tokens** - no Python boilerplate per batch
- Generic `ingest.py` handles all persistence
- Cleaner version control of analysis results

### Confidence Scoring
| Score | Meaning |
|-------|---------|
| ≥0.70 | Strong match - assign to persona |
| 0.40-0.69 | Tentative - assign but flag for review |
| <0.40 | Weak - hold as unassigned |

### Batch Complete Report
After each ingest, show:
```
════════════════════════════════════════════════════
BATCH COMPLETE
════════════════════════════════════════════════════
Samples analyzed: 35
Personas: Executive Brief (12), Team Update (15), Client Response (8)
Total samples: 35
Ready for generation: No (need 50+ samples)
════════════════════════════════════════════════════
```

### Available Commands
| Command | Action |
|---------|--------|
| `Analyze next batch` | Process next 30-40 raw emails |
| `Show status` | Run `python ingest.py --status` |
| `I'm ready to generate` | Mark ready, prompt for new conversation |

### Completing Analysis
When user has 50+ samples across 3+ personas:
```python
from state_manager import mark_ready_for_generation
mark_ready_for_generation()
```

Tell user to start a **NEW conversation** for Phase 3.

## Phase 3: Generation

**Goal:** Synthesize all persona data into a production-ready writing assistant prompt.

1. **Load all data:**
```python
from pathlib import Path
import json

samples_dir = Path.home() / "Documents" / "my-writing-style" / "samples"
persona_file = Path.home() / "Documents" / "my-writing-style" / "persona_registry.json"

with open(persona_file) as f:
    personas = json.load(f)

samples = []
for f in samples_dir.glob("*.json"):
    with open(f) as file:
        samples.append(json.load(file))
```

2. **Identify patterns:**
   - Universal patterns across all personas (base voice)
   - Per-persona rules (patterns in >80% of samples)
   - Per-persona tendencies (patterns in 50-80%)

3. **Generate prompt** following `references/output_template.md`

4. **Save output:**
```python
output_path = Path.home() / "Documents" / "my-writing-style" / "prompts" / "writing_assistant.md"
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    f.write(generated_prompt)
```

5. **Update state:**
```python
from state_manager import complete_generation
complete_generation(str(output_path))
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `fetch_emails.py` | Bulk download emails via MCP |
| `ingest.py` | Process batch JSON, update personas/samples |
| `state_manager.py` | Phase tracking across conversations |
| `style_manager.py` | Persona management utilities |
| `analysis_utils.py` | Similarity scoring and clustering |

## File Structure

```
~/Documents/my-writing-style/
├── raw_samples/           # Downloaded emails (email_*.json)
├── batches/               # Analysis output (batch_*.json)
├── samples/               # Processed samples (one per email)
├── prompts/               # Generated prompts
│   └── writing_assistant.md
├── persona_registry.json  # Discovered personas
├── state.json            # Workflow state
└── fetch_state.json      # Email fetch tracking
```

## Maintenance

- **Monthly:** Run `python fetch_emails.py` to get new emails, analyze new batch
- **Quarterly:** Regenerate writing_assistant.md with accumulated patterns
