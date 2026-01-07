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

### Workflow (Optimized)

1. **Fetch and Format Data (1 Step):**
   Run this script to auto-discover unprocessed emails and format them cleanly:
```bash
cd ~/Documents/my-writing-style && python3 prepare_batch.py --count 40
```

2. **Analyze & Cluster:**
   - Read the output from Step 1.
   - Analyze tone, formality, sentence structure, and signature.
   - Cluster into personas (create new ones or match existing).

3. **Output Analysis (1 Step):**
   Create a single JSON file following `references/batch_schema.md`:
```json
{
  "batch_id": "batch_001",
  "new_personas": [...],
  "samples": [...]
}
```
   Save to: `~/Documents/my-writing-style/batches/batch_NNN.json`

4. **Ingest (1 Step):**
```bash
cd ~/Documents/my-writing-style && python3 ingest.py batches/batch_NNN.json
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
| `Analyze next batch` | Run `prepare_batch.py` again |
| `Show status` | Run `python ingest.py --status` |
| `I'm ready to generate` | Mark ready, prompt for new conversation |

### Completing Analysis
When user has 50+ samples across 3+ personas:
```python
from state_manager import mark_ready_for_generation
mark_ready_for_generation(".")
```

Tell user to start a **NEW conversation** for Phase 3.

## Phase 3: Generation

**Goal:** Synthesize all persona data into a production-ready writing assistant prompt.

### Step 1: Load All Data
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

**Note:** As of the latest update, `ingest.py` now includes the full email content (subject, body, snippet, from, to, date) in each sample file under the `content` field. This means you can access all email content directly from the `samples/` directory without needing to cross-reference `raw_samples/`.

### Step 2: Identify Patterns
For each persona, extract:
- **Universal patterns** across all personas (base voice)
- **Rules** (patterns in >80% of samples) - state as commands
- **Tendencies** (patterns in 50-80%) - softer guidance
- **Anti-patterns** - what to explicitly avoid

### Step 3: Select Few-Shot Examples (CRITICAL)
Filter samples for **confidence ≥ 0.9** to ensure only the best examples:
```python
high_confidence = [s for s in samples if s.get('confidence', 0) >= 0.9]
```

For each persona, select **2-4 diverse examples**:
- Different lengths (short vs. detailed)
- Different topics/contexts
- Representative of the persona's range

If insufficient high-confidence samples exist, use the highest available.

### Step 4: Generate Prompt with Rich JSON
Follow `references/output_template.md`. **CRITICAL:** 

1. **Embed persona-specific JSON profiles** directly within each persona's markdown section (voice_configuration, structural_dna, formatting_rules)

2. **Append the full `persona_registry.json`** at the end in a JSON code block - this serves as the machine-readable knowledge base

### Step 5: Save Output
```python
output_path = Path.home() / "Documents" / "my-writing-style" / "prompts" / "writing_assistant.md"
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    f.write(generated_prompt)
```

### Step 6: Update State
```python
from state_manager import complete_generation
complete_generation(str(output_path), ".")
```

## Persona Registry Schema

The `persona_registry.json` should follow this rich structure:

```json
{
  "personas": [
    {
      "id": "persona_id",
      "meta": {
        "name": "Display Name",
        "description": "When/how this voice is used",
        "triggers": ["context1", "context2"],
        "anti_patterns": ["avoid1", "avoid2"]
      },
      "voice_configuration": {
        "tone_vectors": {
          "formality": 7,
          "warmth": 8,
          "authority": 6,
          "directness": 9
        },
        "keywords_preferred": ["phrase1", "word2"],
        "keywords_forbidden": ["avoid1", "avoid2"]
      },
      "structural_dna": {
        "opener_pattern": "How messages start",
        "closer_pattern": "Sign-off style",
        "sentence_variance": "High/Medium/Low",
        "paragraph_structure": "Pattern description"
      },
      "formatting_rules": {
        "bullet_points": "Usage pattern",
        "bolding": "Usage pattern",
        "emojis": "Allowed/Forbidden/Sparingly"
      },
      "few_shot_examples": [
        {
          "input_context": "What prompted this",
          "output_text": "Actual example text"
        }
      ]
    }
  ],
  "generated_at": "ISO timestamp"
}
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `fetch_emails.py` | Bulk download emails via MCP |
| `prepare_batch.py` | Smart fetch & format of raw emails for analysis |
| `ingest.py` | Process batch JSON, update personas/samples |
| `state_manager.py` | Phase tracking across conversations |
| `style_manager.py` | Persona management utilities |
| `analysis_utils.py` | Similarity scoring and clustering |

## File Structure

```
~/Documents/my-writing-style/
├── raw_samples/           # Downloaded emails (email_*.json) - original format
├── batches/               # Analysis output (batch_*.json) - Claude's analysis
├── samples/               # Processed samples with persona assignments + full content
├── prompts/               # Generated prompts
│   └── writing_assistant.md
├── persona_registry.json  # Discovered personas (rich schema)
├── state.json            # Workflow state
└── fetch_state.json      # Email fetch tracking
```

**Key Change (2026-01-07):** The `samples/` directory now contains full email content (subject, body, etc.) under a `content` field, not just metadata. This eliminates the need to cross-reference `raw_samples/` during generation phase.

## Maintenance

- **Monthly:** Run `python fetch_emails.py` to get new emails, analyze new batch
- **Quarterly:** Regenerate writing_assistant.md with accumulated patterns
