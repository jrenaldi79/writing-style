---
name: writing-style-clone
description: Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates the user's authentic voice using multi-session context management.
---

# Writing Style Clone v3.0

Analyze writing samples to discover personas and generate personalized writing assistant prompts.

## 🆕 v3.0 Multi-Session Architecture

**CRITICAL:** This workflow uses strategic session boundaries to maintain clean context and deliver higher quality outputs.

### Session Structure
```
Session 1: Preprocessing → State saved → STOP (new chat required)
Session 2: Analysis → State saved → STOP (new chat required)
Session 3: LinkedIn (optional) → State saved → STOP (new chat required)
Session 4: Generation → Final output → DONE!
```

**Why?** Preprocessing generates 6,500+ tokens of logs that would clutter context during creative work. Separating phases ensures each task works with only relevant information.

**State Persistence:** All progress saved to `state.json` - resume anytime without data loss.

---

## 🏗️ Architecture: Dual Pipeline

**CRITICAL RULE:** Never mix Email content with LinkedIn content.

### 1. Email Pipeline (Adaptive)
- **Source:** Gmail API
- **Nature:** Context-dependent (Boss vs Team vs Client)
- **Output:** Multiple Personas (3-7 clusters)
- **Sessions:** Preprocessing (Session 1) → Analysis (Session 2)

### 2. LinkedIn Pipeline (Unified)
- **Source:** LinkedIn Scraper
- **Nature:** Public Professional Brand
- **Output:** EXACTLY ONE Persona (Single centroid)
- **Sessions:** Unified processing (Session 3)

---

## 🔄 Complete Workflow: Email Pipeline

### Session 1: Setup & Preprocessing

**Purpose:** Fetch emails, filter quality, enrich metadata, cluster mathematically.

```bash
# 1. Create directories
mkdir -p ~/Documents/my-writing-style/{samples,prompts,raw_samples,batches,filtered_samples,enriched_samples,validation_set}

# 2. Copy scripts
cp ~/Documents/writing-style/skill/scripts/*.py ~/Documents/my-writing-style/
cd ~/Documents/my-writing-style

# 3. Initialize state management
python3 -c 'from state_manager import init_state; init_state(".")'

# 4. Run preprocessing pipeline
python3 fetch_emails.py --count 200 --holdout 0.15
python3 filter_emails.py
python3 enrich_emails.py
python3 embed_emails.py
python3 cluster_emails.py
```

**Output:**
- `clusters.json` - Discovered email clusters
- `state.json` - Workflow state (enables resume)
- `filtered_samples/` - Quality-filtered emails
- `enriched_samples/` - Emails with metadata
- `validation_set/` - Held-out samples for testing

**Next:** Stop here. Start new chat for Session 2 (Analysis).

---

### Session 2: Cluster Analysis

**Purpose:** Analyze each cluster to build persona profiles with calibrated scoring.

```bash
# 1. Check state (should show preprocessing complete)
cat state.json

# 2. Read calibration anchors (CRITICAL for consistent scoring)
cat ~/Documents/writing-style/skill/references/calibration.md

# 3. Prepare first cluster for analysis
python3 prepare_batch.py

# Output: batches/batch_001.json with cluster emails + calibration

# 4. Analyze cluster using LLM
# Use calibration.md as reference for tone scores (1-10)
# Generate persona definition with tone_vectors

# 5. Save analysis results
python3 ingest.py batches/batch_001.json

# 6. Repeat steps 3-5 for each cluster
python3 prepare_batch.py  # Gets next cluster
# ... analyze ...
python3 ingest.py batches/batch_002.json
# Continue until all clusters analyzed
```

**Key Files:**
- `calibration.md` - Anchor examples for consistent scoring
- `prepare_batch.py` - Formats cluster for analysis
- `ingest.py` - Saves persona definitions
- `persona_registry.json` - All discovered personas

**Next:** Stop here. Start new chat for Session 4 (Generation) or Session 3 (LinkedIn).

---

## 🔄 Complete Workflow: LinkedIn Pipeline

### Session 3: LinkedIn Processing (Optional)

**Purpose:** Build unified professional voice from LinkedIn posts.

```bash
cd ~/Documents/my-writing-style

# 1. Fetch posts (token-efficient batch pattern)
# Automatically runs: Search → Scrape Batch → Process Batch
python3 fetch_linkedin_complete.py --profile <username> --limit 20

# 2. Filter (quality gate: min 200 chars)
python3 filter_linkedin.py

# 3. Generate single unified persona (NO clustering)
# Calculates centroid of all posts for consistency
python3 cluster_linkedin.py
```

**Output:**
- `linkedin_persona.json` - Single unified professional voice
- `linkedin_data/` - Scraped posts

**Note:** LinkedIn creates ONE persona (not multiple) for brand consistency.

**Next:** Stop here. Start new chat for Session 4 (Generation).

---

## 🔄 Final Workflow: Generation

### Session 4: Generate Master Prompt

**Purpose:** Combine all personas into final copy-paste artifact.

```bash
cd ~/Documents/my-writing-style

# 1. Check state (should show analysis complete)
cat state.json

# 2. Generate final prompt
# Combines: persona_registry.json + linkedin_persona.json (if exists)
python3 generate_system_prompt.py

# 3. (Optional) Validate output
python3 validate.py
```

**Output:**
- `prompts/writing_assistant.md` - **FINAL ARTIFACT**
- Copy this into ChatGPT, Claude, or any AI tool

**Done!** You now have a personalized writing assistant.

---

## 📁 File Structure

```
~/Documents/
├── writing-style/              # The skill (auto-downloaded)
│   ├── skill/
│   │   ├── scripts/           # All processing scripts (18 files)
│   │   │   ├── state_manager.py          # State persistence
│   │   │   ├── fetch_emails.py           # Gmail fetching
│   │   │   ├── filter_emails.py          # Quality filtering
│   │   │   ├── enrich_emails.py          # Metadata extraction
│   │   │   ├── embed_emails.py           # Vector embeddings
│   │   │   ├── cluster_emails.py         # Mathematical clustering
│   │   │   ├── prepare_batch.py          # Format for analysis
│   │   │   ├── ingest.py                 # Save analysis results
│   │   │   ├── validate.py               # Quality validation
│   │   │   ├── fetch_linkedin_complete.py # LinkedIn batch fetch
│   │   │   ├── filter_linkedin.py        # LinkedIn filtering
│   │   │   ├── cluster_linkedin.py       # LinkedIn unification
│   │   │   ├── generate_system_prompt.py # Final generation
│   │   │   └── [5 more utility scripts]
│   │   │
│   │   └── references/        # Documentation (4 files)
│   │       ├── calibration.md            # Tone scoring anchors
│   │       ├── batch_schema.md           # Analysis format
│   │       ├── analysis_schema.md        # Output schema
│   │       └── output_template.md        # Template reference
│   │
│   └── SYSTEM_PROMPT.md       # v3.0 multi-session logic
│
└── my-writing-style/          # Your personal data (created by scripts)
    ├── state.json             # Workflow state (enables resume)
    ├── raw_samples/           # Fetched emails/posts (200+)
    ├── filtered_samples/      # Quality-filtered (170+)
    ├── enriched_samples/      # With metadata (170+)
    ├── validation_set/        # Held-out for testing (30)
    ├── batches/               # Prepared for analysis
    │   ├── batch_001.json     # Cluster 1 emails
    │   ├── batch_002.json     # Cluster 2 emails
    │   └── ...
    ├── clusters.json          # Email cluster definitions
    ├── persona_registry.json  # All email personas
    ├── linkedin_persona.json  # LinkedIn voice (if used)
    └── prompts/
        └── writing_assistant.md  # ← FINAL OUTPUT
```

---

## 📊 Data Schemas

### Email Cluster Schema (clusters.json)
```json
{
  "clustering_run": "2026-01-07T15:00:00Z",
  "algorithm": "hdbscan",
  "n_clusters": 4,
  "clusters": [
    {
      "id": 0,
      "size": 45,
      "centroid_emails": ["email_abc", "email_def"],
      "sample_ids": ["email_abc", "email_def", ...]
    }
  ]
}
```

### Persona Registry Schema (persona_registry.json)
```json
{
  "personas": [
    {
      "name": "Formal Executive",
      "cluster_id": 0,
      "tone_vectors": {
        "formality": 8,
        "warmth": 5,
        "authority": 7,
        "directness": 6
      },
      "context": {
        "typical_recipients": ["boss", "executive"],
        "typical_threads": ["initiating", "reply"]
      },
      "structural_patterns": {
        "avg_length": 342,
        "uses_bullets": true,
        "greeting_style": "formal"
      }
    }
  ]
}
```

### LinkedIn Persona Schema (linkedin_persona.json)
```json
{
  "source": "linkedin",
  "persona_count": 1,
  "persona": {
    "name": "Professional LinkedIn Voice",
    "post_count": 47,
    "consistency_score": 0.87,
    "characteristics": {
      "avg_post_length": 285,
      "uses_emojis": true,
      "emoji_types": ["🎯", "🍌", "🤯"],
      "technical_content_ratio": 0.65,
      "top_hashtags": ["#ai", "#agents", "#product"]
    },
    "tone_profile": {
      "formality": 6,
      "warmth": 7,
      "technical_depth": 8,
      "humor": 6
    }
  }
}
```

### State Management Schema (state.json)
```json
{
  "current_phase": "analysis",
  "data_dir": "/Users/john/Documents/my-writing-style",
  "created_at": "2026-01-07T10:00:00Z",
  "last_updated": "2026-01-07T10:30:00Z",
  "setup": {
    "completed_at": "2026-01-07T10:05:00Z"
  },
  "analysis": {
    "started_at": "2026-01-07T10:30:00Z",
    "batches_completed": 4,
    "total_samples": 172,
    "ready_for_generation": true
  },
  "generation": {
    "completed_at": null,
    "output_file": null
  }
}
```

---

## 🛠️ Script Reference

### Core Processing Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `state_manager.py` | Track workflow progress | - | state.json |
| `fetch_emails.py` | Pull from Gmail | Gmail API | raw_samples/*.json |
| `filter_emails.py` | Quality gate | raw_samples/ | filtered_samples/ |
| `enrich_emails.py` | Add metadata | filtered_samples/ | enriched_samples/ |
| `embed_emails.py` | Generate vectors | enriched_samples/ | embeddings.npy |
| `cluster_emails.py` | Math clustering | embeddings.npy | clusters.json |
| `prepare_batch.py` | Format for analysis | clusters.json | batches/*.json |
| `ingest.py` | Save persona | batches/*.json | persona_registry.json |
| `validate.py` | Test quality | persona_registry.json | validation_report.json |

### LinkedIn Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `fetch_linkedin_complete.py` | Batch scrape | Username | linkedin_data/*.json |
| `filter_linkedin.py` | Quality gate | linkedin_data/ | filtered/ |
| `cluster_linkedin.py` | Unify voice | filtered/ | linkedin_persona.json |

### Utility Scripts

| Script | Purpose |
|--------|----------|
| `generate_system_prompt.py` | Create final artifact |
| `analysis_utils.py` | Helper functions |
| `style_manager.py` | Style utilities |
| `extract_linkedin_engagement.py` | Parse engagement data |
| `process_linkedin_batch.py` | Batch processing helpers |

### Reference Files

| File | Purpose |
|------|----------|
| `calibration.md` | Tone scoring anchor examples (1-10 scales) |
| `batch_schema.md` | Analysis format specification |
| `analysis_schema.md` | Persona output schema |
| `output_template.md` | Final prompt template |

---

## 🎯 Best Practices

### For Token Efficiency

1. **Use Batch Scripts:** Don't loop in REPL - use provided batch processors
2. **Offline Preprocessing:** Math operations (filter/enrich/embed/cluster) cost 0 tokens
3. **Session Boundaries:** Keep phases separate for clean context
4. **State Persistence:** Resume anytime without re-work

### For Quality

1. **Always Use Calibration:** Reference `calibration.md` when scoring
2. **Holdout Validation:** Use `--holdout 0.15` to test accuracy
3. **Quality Filter:** Remove garbage before analysis (15-20% rejection rate is good)
4. **Multiple Clusters:** Email should discover 3-7 personas, LinkedIn exactly 1

### For Workflow

1. **Check State First:** Always `cat state.json` before continuing
2. **Follow Session Structure:** Don't skip session boundaries
3. **Save Progress:** State is automatically saved after each phase
4. **Separate Pipelines:** Email and LinkedIn data stay separate

---

## 🔧 Troubleshooting

### Common Issues

**"State not found"**
- Run: `python3 -c 'from state_manager import init_state; init_state(".")'`

**"No clusters found"**
- Check: `filter_emails.py` may have rejected too many (adjust thresholds)
- Check: Need at least 50 quality emails for clustering

**"Persona scores inconsistent"**
- Solution: Always reference `calibration.md` anchor examples
- Solution: Use same calibration across all batches

**"LinkedIn returns empty"**
- Check: Profile must be public
- Check: Need at least 10 posts with 200+ chars each

**"Missing dependencies"**
- Run: `pip install sentence-transformers scikit-learn numpy hdbscan`

---

## 📖 Additional Resources

- **SYSTEM_PROMPT.md** - AI assistant instructions for v3.0
- **README.md** - Complete project overview
- **docs/ARCHITECTURE_MULTI_SOURCE.md** - Dual pipeline design
- **docs/CONTEXT_ENGINEERING_SUMMARY.md** - v3.0 multi-session explanation
- **index.html** - User guide with clickable workflows

---

## 🎓 Summary

### What This Skill Does

1. **Fetches** your writing samples (emails, LinkedIn posts)
2. **Filters** for quality (removes garbage)
3. **Enriches** with metadata (recipient, context, structure)
4. **Clusters** mathematically (discovers natural groupings)
5. **Analyzes** with calibrated scoring (1-10 tone vectors)
6. **Validates** against holdout set (proves accuracy)
7. **Generates** final prompt (copy-paste ready)

### What Makes It Different

- ✅ **Mathematical:** Not vibes - actual clustering algorithms
- ✅ **Validated:** Tests itself against held-out samples
- ✅ **Context-Aware:** Email personas adapt to recipient
- ✅ **Brand-Consistent:** LinkedIn maintains unified voice
- ✅ **State-Managed:** Resume anytime without data loss
- ✅ **Production-Grade:** 55 tests, comprehensive error handling

### Result

A system prompt that makes any AI write **exactly like you**, with:
- Context-sensitive tone adaptation (emails)
- Consistent professional voice (LinkedIn)
- Your actual patterns, not generic templates
- Proven accuracy via validation loop
