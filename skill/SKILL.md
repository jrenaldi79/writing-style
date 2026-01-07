---
name: writing-style-clone
version: 2.0
description: Analyze a user's emails to discover distinct writing personas using mathematical clustering, then generate a validated personalized system prompt.
---

# Writing Style Clone v2

Analyze writing samples to discover personas and generate a personalized writing assistant prompt.

## What's New in v2

- **Mathematical clustering** - Embeddings + HDBSCAN/K-Means instead of "vibes"
- **Calibration anchoring** - Consistent scoring across batches
- **Quality filtering** - Remove garbage emails before analysis
- **Recipient awareness** - Context-sensitive persona detection
- **Validation loop** - Test generated prompts against held-out samples

## Architecture Overview

```
Phase 0: Preprocessing (automated)
├── fetch_emails.py      → raw_samples/
├── filter_emails.py     → filtered_samples/ (quality gate)
├── enrich_emails.py     → enriched_samples/ (recipient metadata)
├── embed_emails.py      → embeddings.npy (vector representations)
└── cluster_emails.py    → clusters.json (math-based grouping)

Phase 1: Analysis (agent + human)
├── prepare_batch.py     → formatted cluster for analysis
├── Agent analyzes       → batches/batch_NNN.json
└── ingest.py            → persona_registry.json + samples/

Phase 2: Generation (agent)
└── Agent synthesizes    → writing_assistant.md

Phase 3: Validation (automated + human)
├── validate.py          → validation_report.json
└── Iterate if needed    → back to Phase 2
```

## Phase 0: Preprocessing

**Goal:** Prepare high-quality, clustered email data.

### Step 0.1: Fetch Emails
```bash
cd ~/Documents/my-writing-style
python fetch_emails.py --count 150 --holdout 0.15
```

This downloads emails and reserves 15% for validation.

### Step 0.2: Filter Quality
```bash
python filter_emails.py
```

Removes:
- Too short (<100 chars)
- Forwards, auto-replies
- Calendar responses
- Mass emails (>20 recipients)

### Step 0.3: Enrich Metadata
```bash
python enrich_emails.py
```

Adds:
- Recipient type (individual, team, broadcast)
- Audience (internal, external, mixed)
- Thread position (initiating, reply)
- Time context

### Step 0.4: Generate Embeddings
```bash
python embed_emails.py
```

Creates vector representations using sentence-transformers.

### Step 0.5: Cluster
```bash
python cluster_emails.py
```

Groups similar emails mathematically. Agent will describe clusters, not define them.

### Full Pipeline (One Command)
```bash
cd ~/Documents/my-writing-style && \
python fetch_emails.py --count 150 --holdout 0.15 && \
python filter_emails.py && \
python enrich_emails.py && \
python embed_emails.py && \
python cluster_emails.py
```

After preprocessing, tell user to start a **NEW conversation** for Phase 1.

---

## Phase 1: Calibrated Analysis

**Goal:** Analyze pre-clustered emails with consistent scoring.

### Step 1.1: Read Calibration

**CRITICAL:** Before analyzing ANY emails, read `references/calibration.md`. This ensures consistent tone_vectors scoring across all batches.

### Step 1.2: Get Cluster Batch
```bash
cd ~/Documents/my-writing-style
python prepare_batch.py
```

This outputs:
1. Calibration reference (anchoring examples)
2. Cluster metadata
3. Emails to analyze
4. Analysis instructions

### Step 1.3: Analyze & Output JSON

For each email:
1. Assign calibrated tone_vectors (1-10 scales)
2. Extract patterns (greeting, closing, structure)
3. Assign to persona (create new if needed)
4. Include context from enrichment

Output format: See `references/batch_schema.md`

**Required fields:**
```json
{
  "calibration_referenced": true,
  "calibration_notes": "Anchored formality against examples 3/5"
}
```

### Step 1.4: Ingest
```bash
python ingest.py batches/batch_001.json
```

### Step 1.5: Repeat

Continue until all clusters analyzed:
```bash
python prepare_batch.py --all  # Show cluster status
```

### Batch Complete Report
```
════════════════════════════════════════════════════
BATCH COMPLETE
════════════════════════════════════════════════════
Samples analyzed: 35
Personas: Executive Brief (12), Team Update (15), Client Response (8)
Clusters remaining: 2
Ready for generation: No (need all clusters done)
════════════════════════════════════════════════════
```

When all clusters done, tell user to start a **NEW conversation** for Phase 2.

---

## Phase 2: Generation

**Goal:** Synthesize all persona data into a production-ready writing assistant prompt.

### Step 2.1: Load Data
```python
from pathlib import Path
import json

data_dir = Path.home() / "Documents" / "my-writing-style"

with open(data_dir / "persona_registry.json") as f:
    personas = json.load(f)

samples = []
for f in (data_dir / "samples").glob("*.json"):
    with open(f) as file:
        samples.append(json.load(file))
```

### Step 2.2: Identify Patterns

- **Universal patterns** across all personas (base voice)
- **Per-persona rules** (patterns in >80% of samples)
- **Per-persona tendencies** (patterns in 50-80%)

### Step 2.3: Select Few-Shot Examples

- Filter for **confidence ≥ 0.85**
- Select 3-4 diverse examples per persona
- Vary by length, topic, recipient type

### Step 2.4: Generate Prompt

Follow `references/output_template.md`.

**Include:**
- Universal voice rules
- Per-persona sections with tone_vectors
- Few-shot examples
- Anti-patterns (what to avoid)
- JSON knowledge block (persona_registry.json)

### Step 2.5: Save
```python
output_path = data_dir / "prompts" / "writing_assistant.md"
with open(output_path, "w") as f:
    f.write(generated_prompt)
```

### Step 2.6: Update State
```python
from state_manager import complete_generation
complete_generation(str(output_path), ".")
```

---

## Phase 3: Validation

**Goal:** Verify the generated prompt actually works.

### Step 3.1: Run Validation
```bash
cd ~/Documents/my-writing-style
python validate.py --samples 15 --threshold 0.7
```

This:
1. Loads held-out email samples
2. Generates test emails using the prompt
3. Scores generated vs. original (embedding similarity)
4. Reports pass/fail and suggestions

### Step 3.2: Review Report
```
════════════════════════════════════════════════════
VALIDATION PASSED ✓
════════════════════════════════════════════════════
Samples tested: 15
Overall score: 0.78 (threshold: 0.70)

Per-persona scores:
  ✓ individual_external: 0.82 (5 samples)
  ✓ team_internal: 0.76 (7 samples)
  ⚠ individual_internal: 0.68 (3 samples)

💡 Suggestions:
  • individual_internal needs more casual examples
════════════════════════════════════════════════════
```

### Step 3.3: Iterate if Needed

If validation fails:
1. Review suggestions
2. Add examples to weak personas
3. Regenerate prompt (Phase 2)
4. Re-validate

---

## Scripts Reference

| Script | Purpose | Phase |
|--------|---------|-------|
| `fetch_emails.py` | Download emails, optional holdout | 0 |
| `filter_emails.py` | Quality gate, remove garbage | 0 |
| `enrich_emails.py` | Add recipient/context metadata | 0 |
| `embed_emails.py` | Generate sentence embeddings | 0 |
| `cluster_emails.py` | Mathematical clustering | 0 |
| `prepare_batch.py` | Format cluster for analysis | 1 |
| `ingest.py` | Process batch JSON | 1 |
| `validate.py` | Test prompt against holdout | 3 |
| `state_manager.py` | Phase tracking | All |

## File Structure

```
~/Documents/my-writing-style/
├── raw_samples/           # Downloaded emails
├── filtered_samples/      # Quality-filtered emails
├── enriched_samples/      # Emails with metadata
├── validation_set/        # Held-out emails for testing
├── batches/               # Analysis output (batch_*.json)
├── samples/               # Processed samples (per email)
├── prompts/               # Generated prompts
│   └── writing_assistant.md
├── embeddings.npy         # Vector representations
├── embedding_index.json   # Maps indices to email IDs
├── clusters.json          # Cluster assignments
├── persona_registry.json  # Discovered personas
├── state.json             # Workflow state
├── filter_report.json     # Quality filter results
├── enrichment_report.json # Enrichment statistics
└── validation_report.json # Validation results
```

## Dependencies

```bash
pip install sentence-transformers scikit-learn numpy hdbscan
```

For validation (optional):
```bash
pip install anthropic  # or openai
export ANTHROPIC_API_KEY=your_key  # or OPENAI_API_KEY
```

## Maintenance

- **Monthly:** Fetch new emails, run preprocessing, analyze new clusters
- **Quarterly:** Regenerate prompt, run validation, refine personas
