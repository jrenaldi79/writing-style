---
name: writing-style
description: Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates the user's authentic voice. Use when cloning writing style, analyzing emails, or building personas.
---

# Writing Style Clone v3.3

Analyze writing samples to discover personas and generate personalized writing assistant prompts.

## 📂 Repository Structure (CRITICAL FOR SETUP)

The GitHub repo has this nested structure after extraction:
```
writing-style/
├── writing-style-main/          # Extracted from zip
│   ├── skills/
│   │   └── writing-style/
│   │       ├── scripts/         # ← Python scripts are HERE
│   │       │   ├── fetch_emails.py
│   │       │   ├── filter_emails.py
│   │       │   └── ... (all .py files)
│   │       └── references/
│   │           └── calibration.md
│   └── docs/
└── (other files at root level)
```

**CRITICAL PATHS:**
- Scripts location: `~/Documents/writing-style/writing-style-main/skills/writing-style/scripts/*.py`
- Calibration guide: `~/Documents/writing-style/writing-style-main/skills/writing-style/references/calibration.md`

**Alternative paths** (if repo cloned directly or manually reorganized):
- May also be at: `~/Documents/writing-style/skills/writing-style/scripts/*.py`

**Recommendation:** Use dynamic path finding (see setup commands below) to handle any structure.

---

## ✅ Pre-flight Checklist (For AI Assistant)

Before starting any pipeline, verify these critical paths:

**Step 1: Verify repo structure discovered**
```bash
find ~/Documents/writing-style -name "fetch_emails.py" 2>/dev/null
```
Expected output: Path containing `/skills/writing-style/scripts/`

**Step 2: Verify scripts accessible**
```bash
SCRIPTS_PATH=$(find ~/Documents/writing-style -type d -name "scripts" -path "*/skills/writing-style/*" 2>/dev/null | head -1)
ls -1 "$SCRIPTS_PATH"/*.py 2>/dev/null | wc -l
```
Expected output: Number > 15 (should find all Python scripts)

**Step 3: Verify work directory state**
```bash
ls ~/Documents/my-writing-style/state.json 2>/dev/null || echo "NEW_PROJECT"
```
Expected output: Shows state.json content OR "NEW_PROJECT"

**If any check fails:** Run recovery commands in troubleshooting section before proceeding.

---

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

# 2. Find and copy scripts dynamically
SCRIPTS_PATH=$(find ~/Documents/writing-style -type d -name "scripts" -path "*/skills/writing-style/*" 2>/dev/null | head -1)
if [ -z "$SCRIPTS_PATH" ]; then
  echo "ERROR: Cannot find scripts directory. Re-downloading repo..."
  cd ~/Documents/writing-style && rm -rf writing-style-main && \
  curl -sL https://github.com/jrenaldi79/writing-style/archive/refs/heads/main.zip -o repo.zip && \
  unzip -q repo.zip
  SCRIPTS_PATH=$(find ~/Documents/writing-style -type d -name "scripts" -path "*/skills/writing-style/*" | head -1)
fi
cp "$SCRIPTS_PATH"/*.py ~/Documents/my-writing-style/
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
# Find calibration.md dynamically
CALIB_PATH=$(find ~/Documents/writing-style -name "calibration.md" -path "*/references/*" 2>/dev/null | head -1)
cat "$CALIB_PATH"

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

---

### 📊 Data Captured from LinkedIn Posts (v3.3 Enhancement)

The LinkedIn pipeline captures **20+ fields per post** for rich persona development:

#### Core Content
- **Text**: Full post content (your actual words)
- **Headline**: Opening hook/summary
- **Post Type**: Original vs Repost/Share
- **Date**: When published
- **HTML Version**: Formatted text with links

#### 🆕 Engagement Signals (v3.3)
**Why this matters:** High-engagement posts = strongest voice examples

- **Likes/Comments Count**: Quantitative engagement (47 likes, 3 comments)
- **Top Comments**: Actual audience responses
  - **Reveals:** What resonates with your audience
  - **Shows:** How others perceive you (authority signals)
  - **Identifies:** Content gaps (questions people ask)
  - **Example:** "One of the absolute best founders, mentors..." ← Authority signal

**Use Case:** Filter to posts with 50+ likes or 5+ comments for strongest voice

#### 🆕 Network Context (v3.3)
**Why this matters:** Shows collaboration patterns and relationship style

- **Tagged People**: Who you mention/collaborate with
- **Tagged Companies**: Organizations you reference
- **Your Metrics**: Follower count (4,715), total posts (265), articles (4)

**Use Case:** Generate "frequently mentions X" or "collaborates with Y" patterns

#### 🆕 Repost Analysis (v3.3)
**Why this matters:** Separates your editorial voice from creation voice

When you share others' content:
- **Your Commentary**: What you add/emphasize (your framing)
- **Original Content**: What you're amplifying (their words)
- **Attribution**: Who you credit
- **Network**: Tagged users/companies in original post

**Use Case:** Understand your "curation voice" distinct from "creation voice"

#### Content Structure
- **Embedded Links**: External references you include
- **Images**: Visual content used
- **External Link Data**: Previews of shared URLs

**Use Case:** Capture "includes links to..." or "shares visuals" patterns

#### Authority Signals
- **Follower Count**: Your platform reach
- **Total Posts**: Publishing frequency
- **Articles**: Long-form vs short-form ratio

**Use Case:** Context for persona ("active thought leader with 4.7K followers")

---

### How This Improves Persona Quality

**Before v3.3 (5 fields):**
- Could only analyze text content
- No idea what resonated (engagement unknown)
- Couldn't distinguish original vs curated
- Missing authority context

**After v3.3 (20+ fields):**
- ✅ **Voice Validation**: High-engagement = strong voice
- ✅ **Content Balance**: Know original vs curated ratio
- ✅ **Editorial Voice**: How you frame others' work
- ✅ **Network Patterns**: Collaboration style
- ✅ **Authority Context**: Platform engagement level

**Example Insight:**
> "70% reposts with thoughtful commentary. Frequently tags startup founders. Top posts average 80+ likes. Authority signals in comments: 'best mentor', 'thought leader'."

---

#### Option A: Automated (Recommended - Coming Soon)

```bash
cd ~/Documents/my-writing-style

# Single command - handles everything automatically
python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 20

# Then filter and cluster
python3 filter_linkedin.py
python3 cluster_linkedin.py
```

**Note:** `fetch_linkedin_mcp.py` is a template - MCP integration pending.

#### Option B: Manual Workflow (Current)

**CRITICAL: Always verify profile FIRST to avoid confusion!**

Common names return many profiles. Follow this workflow:

```bash
cd ~/Documents/my-writing-style

# STEP 1: Get FULL profile URL from user
# Ask: "Please provide your complete LinkedIn URL"
# Example: https://www.linkedin.com/in/renaldi

# STEP 2: Verify identity (via System Prompt MCP calls)
# - Scrape profile to extract name, headline
# - Show user for confirmation: "Found: John Renaldi, Product Leader..."
# - Confirm: "Is this correct?"

# STEP 3: Only after confirmation, run batch fetch
# This script coordinates the AI to make MCP calls
python3 fetch_linkedin_complete.py --profile <username> --limit 20

# STEP 4: Filter (quality gate: min 200 chars)
python3 filter_linkedin.py

# STEP 5: Generate single unified persona (NO clustering)
python3 cluster_linkedin.py
```

**Profile Verification Workflow (via System Prompt):**

1. **Get full URL:** Don't accept just a username - ask for complete profile URL
2. **Scrape profile:** Use `scrape_as_markdown` to verify identity
3. **Show preview:** Display name, headline, follower count to user
4. **Confirm:** "Is this you?" before proceeding to batch operations
5. **Proceed:** Only then run post search and scraping

**Why This Matters:**
- Common names like "Renaldi" return 10+ different profiles
- Wrong profile = wasted tokens and incorrect persona
- Verification takes 1 tool call, saves 10+ trial-and-error searches

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
| `fetch_linkedin_mcp.py` | Automated fetch (v2.0) | Full profile URL | /tmp/linkedin_scraped.json |
| `fetch_linkedin_complete.py` | Manual instructions | Username | (guides AI) |
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

**"No such file or directory" for scripts**
- Cause: Scripts location varies based on how repo was downloaded/extracted
- Fix: Use dynamic path finding
```bash
# Find where scripts actually are
find ~/Documents/writing-style -name "fetch_emails.py" -exec dirname {} \;

# Then copy from discovered location
cp /path/from/above/*.py ~/Documents/my-writing-style/
```
- Common locations:
  - `~/Documents/writing-style/writing-style-main/skills/writing-style/scripts/`
  - `~/Documents/writing-style/skills/writing-style/scripts/`
- Prevention: Use the dynamic setup command in Session 1 which auto-locates scripts

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
