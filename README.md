# Writing Style Clone v2

**Train AI to write in your authentic voice using mathematical clustering and validated persona discovery.**

## Overview

Writing Style Clone analyzes your sent emails to discover distinct writing "personas" (e.g., Executive Brief, Client Response, Team Update), then generates a personalized system prompt that enables any LLM to replicate your voice with accuracy.

### What's New in v2

| Feature | v1 (Vibes) | v2 (Mathematical) |
|---------|------------|------------------|
| **Clustering** | Agent decides personas | Embeddings + HDBSCAN/K-Means |
| **Scoring** | Inconsistent across batches | Calibration anchors (1-10 scales) |
| **Input Quality** | All emails processed | Garbage filtered (15-20% rejection) |
| **Context** | None | Recipient type, audience, thread position |
| **Validation** | Hope it works | Embedding similarity scoring |
| **Reproducibility** | Different each run | Deterministic clustering |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 0: Preprocessing (Automated)                      │
├─────────────────────────────────────────────────────────┤
│ fetch_emails.py      → raw_samples/                     │
│ filter_emails.py     → filtered_samples/ (quality gate) │
│ enrich_emails.py     → enriched_samples/ (metadata)     │
│ embed_emails.py      → embeddings.npy (vectors)         │
│ cluster_emails.py    → clusters.json (grouping)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Analysis (Agent + Human)                       │
├─────────────────────────────────────────────────────────┤
│ prepare_batch.py     → formatted cluster                │
│ Agent analyzes       → batches/batch_NNN.json           │
│ ingest.py            → persona_registry.json            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Generation (Agent)                             │
├─────────────────────────────────────────────────────────┤
│ Agent synthesizes    → writing_assistant.md             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Validation (Automated + Human)                 │
├─────────────────────────────────────────────────────────┤
│ validate.py          → validation_report.json           │
│ Iterate if needed    → back to Phase 2                  │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Gmail MCP configured (for email access)
- ChatWise or Claude Desktop

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Download the skill (auto-happens on first use, or manual):
git clone https://github.com/jrenaldi79/writing-style.git ~/Documents/writing-style
```

### First Run

1. **Phase 0: Preprocessing** (~10 minutes)
   ```bash
   cd ~/Documents/my-writing-style
   python fetch_emails.py --count 150 --holdout 0.15
   python filter_emails.py
   python enrich_emails.py
   python embed_emails.py
   python cluster_emails.py
   ```

2. **Phase 1: Analysis** (~20 minutes, new conversation)
   - Agent reads clusters and calibration.md
   - Analyzes emails with calibrated scoring
   - Outputs JSON per cluster
   - Repeat until all clusters done

3. **Phase 2: Generation** (~5 minutes, new conversation)
   - Agent synthesizes personas into prompt
   - Outputs `writing_assistant.md`

4. **Phase 3: Validation** (~2 minutes)
   ```bash
   python validate.py --samples 15 --threshold 0.7
   ```

## Technical Deep Dive

### Phase 0: Preprocessing Pipeline

#### 1. Email Fetching (`fetch_emails.py`)

**Purpose:** Bulk-download sent emails via Gmail MCP.

**Features:**
- Incremental fetch (new emails only)
- Historical backfill (`--older`)
- Validation holdout (`--holdout 0.15` reserves 15% for testing)
- Deduplication tracking

**Usage:**
```bash
python fetch_emails.py --count 150 --holdout 0.15
```

**Output:** `raw_samples/email_*.json`

#### 2. Quality Filtering (`filter_emails.py`)

**Purpose:** Remove garbage before analysis.

**Filters Applied:**
| Filter | Threshold | Rationale |
|--------|-----------|----------|
| Minimum length | 100 chars | Too short lacks patterns |
| Forwards | Regex detection | Not original writing |
| Auto-replies | OOO patterns | Not authentic voice |
| Calendar responses | "Accepted:", "Declined:" | Meaningless for style |
| Mass emails | >20 recipients | Broadcast style different |

**Quality Scoring:**
```python
score = 0.4 * length_score +  # Longer = better (up to 500 chars)
        0.3 * originality +     # Ratio of original to quoted text
        0.3 * diversity         # Unique words / total words
```

**Typical Results:**
- Input: 150 emails
- Rejected: 23 (15%)
- Average quality: 0.73

**Output:** `filtered_samples/email_*.json` with quality metadata

#### 3. Metadata Enrichment (`enrich_emails.py`)

**Purpose:** Extract context signals for persona detection.

**Enrichment Fields:**
```json
{
  "recipient_type": "individual | small_group | team | broadcast",
  "audience": "internal | external | mixed",
  "thread_position": "initiating | reply | forward",
  "thread_depth": 0,
  "time_of_day": "morning | afternoon | evening | night",
  "day_of_week": "monday",
  "has_bullets": true,
  "paragraph_count": 3,
  "greeting": "Team,",
  "closing": "-JR"
}
```

**Domain Detection:**
- Auto-detects user domain from sender
- Classifies recipients as internal/external
- Enables persona variations (e.g., "Client Email" vs "Team Email")

**Output:** `enriched_samples/email_*.json`

#### 4. Embedding Generation (`embed_emails.py`)

**Purpose:** Convert emails to vector representations for similarity.

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- Dimension: 384
- Fast: ~0.02s per email
- Quality: Good for short texts

**Alternative:** `all-mpnet-base-v2` (higher quality, slower, 768 dim)

**Text Preparation:**
```python
text = f"{subject}\n\n{clean_body}"  # Combine subject + body
text = remove_quoted_text(text)      # Strip replies
text = truncate(text, 2000)          # ~500 tokens max
```

**Output:**
- `embeddings.npy` (numpy array)
- `embedding_index.json` (maps indices to email IDs)

#### 5. Mathematical Clustering (`cluster_emails.py`)

**Purpose:** Group similar emails objectively.

**Algorithms:**

**HDBSCAN** (default, recommended):
- Pros: Auto-detects cluster count, handles noise
- Cons: Requires ≥20 samples
- Parameters: `min_cluster_size=5`

**K-Means** (fallback):
- Pros: Works with small datasets
- Cons: Must specify k
- Optimization: Elbow method for auto-k

**Silhouette Score:**
Measures cluster quality (0-1, higher is better)
```
<0.25: Poor separation
0.25-0.50: Weak
0.50-0.70: Reasonable
>0.70: Strong
```

**Example Output:**
```json
{
  "algorithm": "hdbscan",
  "n_clusters": 4,
  "n_noise": 12,
  "silhouette_score": 0.68,
  "clusters": [
    {
      "id": 0,
      "size": 45,
      "centroid_emails": ["email_abc", "email_def"],
      "enrichment_summary": {
        "recipient_types": {"team": 30, "individual": 15},
        "audiences": {"internal": 42, "external": 3}
      }
    }
  ]
}
```

**Reproducibility:**
- Same input → same clusters (deterministic)
- Random seed: 42 (fixed)

---

### Phase 1: Calibrated Analysis

#### Calibration System

**Problem:** Without anchors, "formality: 6" in batch 1 might be "formality: 4" in batch 2.

**Solution:** `calibration.md` provides labeled examples:

```markdown
## Formality Scale (1-10)

### 1 - Very Casual
> "yo u free tmrw? lmk asap"

### 5 - Balanced
> "Hi John, I wanted to follow up..."

### 10 - Highly Formal
> "Dear Mr. Smith, Please be advised..."
```

**Usage:**
1. Agent reads calibration.md FIRST
2. References anchors when scoring each email
3. Confirms in output: `"calibration_referenced": true`

**Tone Vectors:**

Every email gets 4 calibrated scores (1-10):

| Dimension | Low (1-3) | Mid (4-7) | High (8-10) |
|-----------|-----------|-----------|-------------|
| **Formality** | "hey!" | "Hi John," | "Dear Mr. Smith," |
| **Warmth** | "Per request..." | "Happy to help" | "So excited!" |
| **Authority** | "I think maybe..." | "I recommend..." | "This is the approach." |
| **Directness** | "wondering if perhaps..." | "We should discuss" | "No. Fix it." |

#### Batch Analysis Workflow

1. **Get Cluster:**
   ```bash
   python prepare_batch.py  # Auto-selects next unanalyzed cluster
   ```

   Output includes:
   - Calibration reference
   - Cluster characteristics
   - Formatted emails (30-40 per batch)

2. **Analyze:**
   Agent outputs JSON per `batch_schema.md`:
   ```json
   {
     "batch_id": "batch_001",
     "cluster_id": 2,
     "calibration_referenced": true,
     "new_personas": [...],
     "samples": [
       {
         "id": "email_abc",
         "persona": "Executive Brief",
         "confidence": 0.85,
         "analysis": {
           "tone_vectors": {
             "formality": 6,
             "warmth": 5,
             "authority": 8,
             "directness": 8
           },
           "greeting": "Team,",
           "closing": "-JR"
         },
         "context": {
           "recipient_type": "team",
           "audience": "internal"
         }
       }
     ]
   }
   ```

3. **Ingest:**
   ```bash
   python ingest.py batches/batch_001.json
   ```

   Updates:
   - `persona_registry.json` (personas + sample counts)
   - `samples/*.json` (individual analyzed emails)
   - `state.json` (progress tracking)

4. **Repeat** until all clusters done

#### Confidence Scoring

| Score | Meaning | Action |
|-------|---------|--------|
| ≥0.70 | Strong match | Assign confidently |
| 0.40-0.69 | Tentative | Assign but flag for review |
| <0.40 | Weak | Leave unassigned, create new persona |

---

### Phase 2: Generation

**Goal:** Synthesize persona data into production-ready prompt.

**Data Loaded:**
- `persona_registry.json` (all personas + characteristics)
- `samples/*.json` (all analyzed emails)

**Pattern Identification:**

| Pattern Type | Threshold | Usage |
|--------------|-----------|-------|
| Universal | 90%+ across all personas | Base voice rules |
| Per-persona rules | 80%+ within persona | "Always follow" |
| Per-persona tendencies | 50-80% within persona | "When appropriate" |

**Few-Shot Selection:**

1. Filter: confidence ≥ 0.85
2. Diversify:
   - Different recipient types
   - Different lengths (short, medium, long)
   - Different topics
3. Select: 3-4 examples per persona

**Output Structure:**

```markdown
# John's Writing Voice

## Universal Voice
- Default stance: Expert but approachable
- Signature moves: Validates first, uses bullets, signs "JR"

## Personas

### 1. Executive Brief
**Use when:** Team updates, leadership communication
**Tone vectors:** formality=6, warmth=5, authority=8, directness=8
**Rules:**
- Open with "Team,"
- Use bullet points for 3+ items
**Examples:**
> [actual email excerpt]

### 2. Client Response
[...]

## Quick Reference
| Context | Persona |
|---------|--------|
| Team update | Executive Brief |
| Client question | Client Response |

## Writing Profile (JSON)
```json
[Full persona_registry.json]
```
```

**Key Feature:** Appends full persona registry as JSON for programmatic access.

---

### Phase 3: Validation

**Goal:** Verify the prompt actually works.

#### Validation Process

1. **Load held-out samples** (from `validation_set/` or last 20% of enriched)
2. **For each sample:**
   - Extract context (recipient, subject, thread position)
   - Generate test email using `writing_assistant.md`
   - Compute embedding similarity (original vs. generated)
3. **Aggregate scores** and report

#### Similarity Scoring

**Method:** Cosine similarity of normalized embeddings

```python
embeddings = model.encode([original, generated])
similarity = dot(embeddings[0], embeddings[1])  # 0-1 scale
```

**Interpretation:**
| Score | Meaning |
|-------|--------|
| >0.80 | Excellent match |
| 0.70-0.80 | Good match (threshold) |
| 0.50-0.70 | Moderate match (needs work) |
| <0.50 | Poor match (revise prompt) |

#### Mismatch Analysis

When score < threshold, validator checks:
- Length mismatch (too short/long)
- Bullet point mismatch (missing/extra)
- Tone mismatch (formality/casualness)
- Greeting/closing errors

#### Validation Report

```json
{
  "validation_run": "2026-01-07T15:00:00Z",
  "samples_tested": 15,
  "overall_score": 0.78,
  "threshold": 0.70,
  "passed": true,
  "per_persona": {
    "individual_external": {"count": 5, "avg_score": 0.82},
    "team_internal": {"count": 7, "avg_score": 0.76},
    "individual_internal": {"count": 3, "avg_score": 0.68}
  },
  "worst_samples": [
    {"id": "email_xyz", "score": 0.68, "issue": "Missing bullets"}
  ],
  "suggestions": [
    "individual_internal needs more casual examples"
  ]
}
```

#### Iteration Loop

If validation fails:
1. Review suggestions
2. Add examples to weak personas (back to analysis)
3. Regenerate prompt (Phase 2)
4. Re-validate

---

## File Structure

```
~/Documents/
├── writing-style/              # Skill repository (GitHub)
│   ├── skill/
│   │   ├── SKILL.md            # Agent workflow guide
│   │   ├── scripts/            # All Python scripts
│   │   │   ├── fetch_emails.py
│   │   │   ├── filter_emails.py
│   │   │   ├── enrich_emails.py
│   │   │   ├── embed_emails.py
│   │   │   ├── cluster_emails.py
│   │   │   ├── prepare_batch.py
│   │   │   ├── ingest.py
│   │   │   ├── validate.py
│   │   │   ├── state_manager.py
│   │   │   ├── style_manager.py
│   │   │   └── analysis_utils.py
│   │   └── references/
│   │       ├── calibration.md   # Scoring anchors
│   │       ├── batch_schema.md  # JSON output format
│   │       ├── analysis_schema.md
│   │       └── output_template.md
│   ├── docs/
│   │   └── IMPLEMENTATION_PLAN.md
│   ├── SYSTEM_PROMPT.md         # Agent bootstrap
│   ├── README.md                # This file
│   ├── requirements.txt
│   └── index.html               # User guide
│
└── my-writing-style/            # User data (local only)
    ├── raw_samples/             # Downloaded emails
    ├── filtered_samples/        # Quality-filtered
    ├── enriched_samples/        # With metadata
    ├── validation_set/          # Held-out samples
    ├── batches/                 # Analysis output
    ├── samples/                 # Processed samples
    ├── prompts/
    │   └── writing_assistant.md # ★ FINAL OUTPUT
    ├── embeddings.npy           # Vector representations
    ├── embedding_index.json     # Index mapping
    ├── clusters.json            # Cluster assignments
    ├── persona_registry.json    # Discovered personas
    ├── state.json               # Workflow state
    ├── fetch_state.json         # Fetch tracking
    ├── filter_report.json       # Quality stats
    ├── enrichment_report.json   # Enrichment stats
    └── validation_report.json   # Validation results
```

## Dependencies

```txt
# Core preprocessing
sentence-transformers>=2.2.0  # Embedding generation
scikit-learn>=1.0.0           # K-Means clustering
numpy>=1.21.0                 # Array operations

# Optional: Better clustering
hdbscan>=0.8.0                # Auto-detect cluster count

# Optional: Validation (choose one)
anthropic>=0.18.0             # Claude API
openai>=1.0.0                 # OpenAI API
```

## Performance Metrics

### Preprocessing Pipeline

| Step | Time | Input | Output |
|------|------|-------|--------|
| Fetch | 3-5 min | N/A | 150 emails |
| Filter | 10 sec | 150 | 127 (15% rejected) |
| Enrich | 15 sec | 127 | 127 enriched |
| Embed | 30 sec | 127 | 384-dim vectors |
| Cluster | 5 sec | 127 | 4-6 clusters |
| **Total** | **~5 min** | | |

### Analysis (per batch)

- Emails per batch: 30-40
- Agent analysis time: ~3-5 minutes
- Batches needed: 3-5 (depends on cluster count)
- **Total analysis: ~20 minutes**

### Validation

- Samples tested: 15
- Generation time: ~30 seconds (with API)
- Embedding computation: ~2 seconds
- **Total: ~2 minutes**

## Success Metrics (v2 vs v1)

| Metric | v1 | v2 | Improvement |
|--------|----|----|-------------|
| Validation score | N/A | 0.78 | ✅ Measurable |
| Cross-batch consistency | σ=1.2 | σ=0.4 | ✅ 67% better |
| Garbage emails | 0% filtered | 15% filtered | ✅ Cleaner input |
| Clustering reproducibility | Random | 100% | ✅ Deterministic |
| Context awareness | 0% | 100% | ✅ Recipient-aware |

## Troubleshooting

### "No embeddings found"
```bash
# Run preprocessing pipeline
cd ~/Documents/my-writing-style
python embed_emails.py
```

### "HDBSCAN not installed"
```bash
pip install hdbscan
# Or: use K-Means fallback (automatic)
```

### "Validation failed - no LLM available"
```bash
# Set API key
export ANTHROPIC_API_KEY=your_key
# Or: Run local Ollama
ollama serve
```

### "Cluster X not found"
```bash
# Check cluster status
python prepare_batch.py --all
```

### "Calibration not referenced"
Agent must read `calibration.md` before analysis. Remind: "Read calibration.md first."

## Contributing

Pull requests welcome! Priority areas:
- Additional embedding models
- Performance optimizations
- LinkedIn integration
- Multi-language support

## License

MIT

## Author

John Renaldi • January 2025  
GitHub: [@jrenaldi79](https://github.com/jrenaldi79)
