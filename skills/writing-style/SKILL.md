---
name: writing-style
description: Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates the user's authentic voice. Use when cloning writing style, analyzing emails, or building personas.
triggers:
  - "Clone my email style"
  - "Clone my writing voice"
  - "Run Email Pipeline"
  - "Run LinkedIn Pipeline"
  - "Generate writing assistant"
  - "Continue email analysis"
  - "Analyze clusters"
  - "Show project status"
---

# Writing Style Clone v3.3

Analyze writing samples to discover personas and generate personalized writing assistant prompts.

## ⚠️ Critical Workflows (Read First)

**LinkedIn Profile Verification:** Common names return multiple profiles. ALWAYS verify profile identity BEFORE batch operations to avoid wrong-person errors and wasted tokens. See [LinkedIn Search Strategies](#-linkedin-search-strategies-critical) section.

**Search Query Strategy:** Use disambiguating terms (full name, company, products) in ALL LinkedIn searches. Bad: `site:linkedin.com/posts/username 2024`. Good: `site:linkedin.com/posts/username "Full Name" Company OR Product`.

**Script Location:** Use dynamic path finding (see setup commands) to handle nested GitHub repo structures. Scripts may be at different depths depending on how the repo was extracted.

## 📂 Directory Architecture

Skills (code) and data (outputs) are intentionally separated:

```
~/skills/writing-style/          # Skill installation (read-only code)
├── SKILL.md                     # This file - workflow documentation
├── scripts/                     # Python automation scripts
│   ├── fetch_emails.py
│   ├── filter_emails.py
│   └── ... (all .py files)
└── references/                  # Supporting documentation
    └── calibration.md

~/Documents/my-writing-style/    # User data (generated outputs)
├── state.json                   # Workflow state
├── venv/                        # Python virtual environment
├── clusters.json                # Email personas
├── linkedin_persona.json        # LinkedIn persona
└── prompts/                     # Final outputs
    └── writing_assistant.md
```

**Primary skill location:** `~/skills/writing-style/`

**Fallback locations** (checked in order if primary not found):
1. `~/Documents/skills/writing-style/`
2. `~/.local/share/skills/writing-style/`

**Why separate?** Skills are "programs" (rarely modified), data is user-specific. Clean uninstall without losing outputs.

---

## ✅ Pre-flight Checklist (For AI Assistant)

Before starting any pipeline, verify these critical paths:

**Step 1: Find skill installation**
```bash
# Check primary and fallback locations
SKILL_DIR=""
for dir in ~/skills/writing-style ~/Documents/skills/writing-style ~/.local/share/skills/writing-style; do
  [ -f "$dir/SKILL.md" ] && SKILL_DIR="$dir" && break
done
echo "SKILL_DIR: ${SKILL_DIR:-NOT_FOUND}"
```
Expected output: Path to skill directory

**Step 2: Verify scripts accessible**
```bash
ls -1 "$SKILL_DIR/scripts"/*.py 2>/dev/null | wc -l
```
Expected output: Number > 15 (should find all Python scripts)

**Step 3: Verify data directory state**
```bash
cat ~/Documents/my-writing-style/state.json 2>/dev/null || echo "NEW_PROJECT"
```
Expected output: Shows state.json content OR "NEW_PROJECT"

**If skill not found:** Install to `~/skills/writing-style/` or run recovery commands in troubleshooting section.

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
# 1. Find skill installation
SKILL_DIR=""
for dir in ~/skills/writing-style ~/Documents/skills/writing-style ~/.local/share/skills/writing-style; do
  [ -f "$dir/SKILL.md" ] && SKILL_DIR="$dir" && break
done

if [ -z "$SKILL_DIR" ]; then
  echo "ERROR: Skill not installed. Installing to ~/skills/writing-style..."
  mkdir -p ~/skills/writing-style
  curl -sL https://github.com/jrenaldi79/writing-style/archive/refs/heads/main.zip -o /tmp/skill.zip
  unzip -q /tmp/skill.zip -d /tmp
  cp -r /tmp/writing-style-main/skills/writing-style/* ~/skills/writing-style/
  rm -rf /tmp/skill.zip /tmp/writing-style-main
  SKILL_DIR=~/skills/writing-style
fi

# 2. Create data directories
DATA_DIR=~/Documents/my-writing-style
mkdir -p "$DATA_DIR"/{samples,prompts,raw_samples,batches,filtered_samples,enriched_samples,validation_set}

# 3. Copy scripts to data directory and setup venv
cp "$SKILL_DIR"/scripts/*.py "$DATA_DIR"/
cd "$DATA_DIR"
python3 -m venv venv
venv/bin/python3 -m pip install -r "$SKILL_DIR"/requirements.txt

# 4. Initialize state management
venv/bin/python3 -c 'from state_manager import init_state; init_state(".")'

# 5. Run preprocessing pipeline
venv/bin/python3 fetch_emails.py --count 200 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
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

#### 🆕 Content Types Supported (v3.3)
- **Short-form posts** (`/posts/`): Regular LinkedIn updates
- **Long-form articles** (`/pulse/`): Blog-style articles you've published

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

**Engagement-Weighted Analysis:** Posts with higher engagement influence tone vectors more heavily using log-scale weighting. This prevents viral posts from dominating while still prioritizing what resonates with your audience.

**Best Example Selection:** The few-shot example in the persona is automatically selected by highest engagement (likes), with length as tiebreaker for equal engagement.

**Use Case:** Persona automatically emphasizes your strongest voice patterns

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
- ✅ **Voice Validation**: High-engagement posts automatically weighted higher
- ✅ **Content Balance**: Know original vs curated ratio
- ✅ **Editorial Voice**: How you frame others' work
- ✅ **Network Patterns**: Collaboration style
- ✅ **Authority Context**: Platform engagement level
- ✅ **Article Support**: Long-form `/pulse/` articles included alongside posts
- ✅ **Engagement Weighting**: Log-scale weighting prevents viral posts from dominating

**Example Insight:**
> "70% reposts with thoughtful commentary. Frequently tags startup founders. Top posts average 80+ likes. Authority signals in comments: 'best mentor', 'thought leader'."

---

### LinkedIn Fetching (Automated)

**CRITICAL: Always provide full profile URL to avoid wrong-person errors!**

```bash
cd ~/Documents/my-writing-style

# Fetch posts (fully automated with built-in verification)
python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 20

# Filter quality posts (min 200 chars)
python3 filter_linkedin.py

# Generate unified persona (NO clustering - single voice)
python3 cluster_linkedin.py
```

**How it works:**
1. **Profile Verification:** Scrapes profile to verify identity (name, headline, company)
2. **Smart Search:** Uses disambiguating terms to find correct person's posts AND articles
3. **Parallel Scraping:** Fetches posts in parallel (5 concurrent) for faster processing
4. **Content Types:** Captures both short-form posts (`/posts/`) and long-form articles (`/pulse/`)
5. **Validation:** Filters out posts from wrong people
6. **State Tracking:** Saves progress for resume/debugging

**Requirements:**
- BrightData API token in `MCP_TOKEN` environment variable
- Full LinkedIn URL (not just username)

**Why full URL matters:**
- Common names return multiple profiles
- URL ensures correct person from the start
- Saves tokens by avoiding wrong-person errors

---

## 🔍 LinkedIn Search Strategies (CRITICAL)

### The Wrong-Person Problem

Common names return many profiles from Google searches.

**BAD searches (will return wrong people):**
```
site:linkedin.com/posts/username 2024
site:linkedin.com/posts/username CompanyName
```

**GOOD searches (filtered by identity):**
```
site:linkedin.com/posts/username "Full Name" Company
site:linkedin.com/posts/username Product OR TechStack OR Location
```

### After Profile Verification

Once you've verified the profile, extract identity markers:
- Full name: "First Last"
- Companies: CurrentCo, PreviousCo, University
- Location: City/Region
- Products/Technologies: Key products or tech they mention

Use these in ALL subsequent searches:
```
site:linkedin.com/posts/{username} "{full_name}" OR {company1} OR {company2}
```

### Search Strategy Workflow

1. **Verify profile first** (get identity markers)
2. **Build disambiguating query** using markers
3. **Search with filters** to ensure correct person
4. **Validate results** before batch processing

**Example workflow:**
```bash
# After verifying profile and extracting markers:
site:linkedin.com/posts/username "Full Name"
site:linkedin.com/posts/username Company1 OR Company2 OR University
site:linkedin.com/posts/username "Product Name" OR "Tech Stack"
```

This prevents fetching posts from other people with the same username or similar names.

---

**Output:**
- `linkedin_persona.json` - Single unified professional voice
- `linkedin_data/` - Scraped posts

**Note:** LinkedIn creates ONE persona (not multiple) for brand consistency.

**Next:** Continue to Session 3b (optional) or Session 4 (Generation).

---

### Session 3b: LLM-Assisted Refinement (Optional)

**Purpose:** Complete semantic analysis fields that require LLM understanding. This enhances the v2 persona with guardrails, negative examples, and detailed annotations.

**Prerequisites:** Session 3 complete (`linkedin_persona.json` exists with v2 schema)

**When to use:**
- You want richer guardrails (behavioral "never do" rules)
- You want negative examples (anti-patterns for the voice)
- You want annotations explaining why each example works

#### Step 1: Export Posts for Analysis

```bash
cd ~/Documents/my-writing-style

# Export all posts + current persona to a single markdown file
python3 prepare_llm_analysis.py

# Output: llm_analysis_input.md
```

The generated file contains:
- Analysis instructions (what fields to complete)
- Current persona JSON (already extracted patterns)
- All filtered posts with engagement data and comments

#### Step 2: LLM Analysis

1. Open `llm_analysis_input.md` in your preferred LLM (Claude, GPT-4, etc.)
2. The file includes complete instructions - just copy/paste the whole thing
3. LLM returns a JSON object with completed fields

**Fields the LLM completes:**
- `guardrails.never_do` - Behavioral rules ("never start with...")
- `guardrails.off_limits_topics` - Topics to avoid
- `voice.signature_phrases` - Unique recurring phrases
- `example_bank.positive` - Category, goal, audience, what_makes_it_work
- `example_bank.negative` - Anti-pattern examples with explanations

#### Step 3: Merge Results

```bash
# Save LLM output to a file
# (copy the JSON block from LLM response into llm_output.json)

# Merge into persona
python3 merge_llm_analysis.py llm_output.json

# Verify merged result
cat linkedin_persona.json | python3 -m json.tool | head -50
```

**Merge behavior:**
- Only fills empty/placeholder fields (won't overwrite existing values)
- Uses index matching for positive example annotations
- Validates structure before saving
- Prints summary of what changed

#### Dry Run Mode

Preview changes without modifying the file:

```bash
python3 merge_llm_analysis.py --dry-run llm_output.json
```

**Output:**
- Enhanced `linkedin_persona.json` with complete v2 schema

**See also:** `references/llm_analysis_guide.md` for detailed LLM instructions

**Next:** Proceed to Session 4 (Generation).

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
```

**Output:**
- `prompts/writing_assistant.md` - **FINAL ARTIFACT**

### Inline Validation (Recommended)

After generating the prompt, validate it interactively:

1. **Generate test samples** - Create 2-3 sample emails using the prompt:
   - Formal email to an executive
   - Casual reply to a teammate
   - Group announcement or update

2. **Present to user** - Show the generated samples and ask:
   > "Here's how the prompt would write in these scenarios. Does this sound like you?"

3. **Collect feedback** - User identifies what feels off:
   > "The casual one is too stiff - I use more exclamation points"
   > "The formal one is good but I never say 'Dear'"

4. **Refine the prompt** - Update `writing_assistant.md` based on feedback

5. **Iterate** - Generate new samples until user approves

**Why this works:** You are the ground truth for "does this sound like me" - no embedding score can match your judgment.

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
│   │   │   ├── fetch_linkedin_mcp.py     # LinkedIn automated fetch
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

### LinkedIn Persona Schema v2.0 (linkedin_persona.json)

**V2 Schema Features:**
- **Separated Voice vs Content:** Voice patterns (HOW you write) distinct from topics
- **Guardrails:** Explicit "never do" rules to prevent LinkedIn cringe drift
- **Variation Controls:** Ranges prevent robotic sameness
- **Example Bank:** Positive examples with usage guidance + placeholder for negative examples

```json
{
  "schema_version": "2.0",
  "generated_at": "2026-01-08T21:26:21Z",
  "sample_size": 5,
  "confidence": 0.6,

  "voice": {
    "tone_vectors": {
      "formality": 7,
      "warmth": 5,
      "authority": 6,
      "directness": 7
    },
    "linguistic_patterns": {
      "sentence_length_avg_words": 16.3,
      "short_punchy_ratio": 0.30,
      "uses_contractions": true,
      "uses_em_dash": false,
      "uses_parentheticals": true,
      "exclamations_per_post": 0.6,
      "questions_per_post": 0.2
    },
    "emoji_profile": {
      "signature_emojis": ["⚽", "🤣", "🍌", "🤯"],
      "placement": "beginning",
      "per_post_range": [0, 4]
    },
    "enthusiasm_level": 6
  },

  "guardrails": {
    "never_do": [],
    "forbidden_phrases": ["synergy", "leverage", "deep dive", "game-changer"],
    "off_limits_topics": [],
    "compliance": {
      "no_confidential_info": true,
      "no_unverified_claims": true
    }
  },

  "platform_rules": {
    "formatting": {
      "line_break_frequency": "low",
      "single_sentence_paragraphs": false,
      "uses_bullets": false,
      "uses_hashtags": true,
      "hashtags_count_range": [2, 2],
      "hashtag_placement": "inline"
    },
    "hooks": {
      "primary_style": "observation",
      "allowed_styles": ["call_to_action", "observation"]
    },
    "closings": {
      "primary_style": "invitation",
      "engagement_ask_frequency": 0.6,
      "link_placement": "end"
    },
    "length": {
      "target_chars": 492,
      "min_chars": 374,
      "max_chars": 780
    }
  },

  "variation_controls": {
    "emoji_per_post_range": [0, 3],
    "question_sentence_ratio_range": [0.0, 0.2],
    "hook_style_distribution": {"observation": 1.0}
  },

  "example_bank": {
    "usage_guidance": {
      "instruction": "Match rhythm, tone, and structural patterns. Adapt to new topics.",
      "what_to_match": ["Sentence length", "Hook style", "CTA pattern", "Emoji placement"],
      "what_to_adapt": ["Topic", "Names/products", "CTA details", "Links"],
      "warning": "Do NOT copy examples verbatim."
    },
    "positive": [
      {
        "engagement": {"likes": 129, "comments": 3},
        "text": "I know there's a lot of super talented folks...",
        "category": "",
        "goal": "",
        "audience": "",
        "what_makes_it_work": []
      }
    ],
    "negative": []
  }
}
```

**Confidence Scoring:**
- `< 0.5` - Insufficient data, use defaults
- `0.5-0.7` - Reasonable patterns, some inference
- `0.7-0.9` - Strong patterns, high reliability
- `> 0.9` - Very high confidence (20+ quality posts)

**See full schema specification:** `references/linkedin_persona_schema_v2.md`

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

### LinkedIn Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `fetch_linkedin_mcp.py` | Automated fetch with verification | Full profile URL | linkedin_data/*.json |
| `filter_linkedin.py` | Quality gate | linkedin_data/ | filtered/ |
| `cluster_linkedin.py` | Unify voice (v2 schema) | filtered/ | linkedin_persona.json |
| `prepare_llm_analysis.py` | Export for LLM analysis | filtered/ + persona | llm_analysis_input.md |
| `merge_llm_analysis.py` | Merge LLM output | llm_output.json | linkedin_persona.json |

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
| `linkedin_persona_schema_v2.md` | Advanced LinkedIn persona schema with guardrails, variation controls, and negative examples |

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
6. **Validates** interactively with user feedback
7. **Generates** final prompt (copy-paste ready)

### What Makes It Different

- ✅ **Mathematical:** Not vibes - actual clustering algorithms
- ✅ **Validated:** Interactive user feedback loop
- ✅ **Context-Aware:** Email personas adapt to recipient
- ✅ **Brand-Consistent:** LinkedIn maintains unified voice
- ✅ **State-Managed:** Resume anytime without data loss
- ✅ **Production-Grade:** 55 tests, comprehensive error handling

### Result

A system prompt that makes any AI write **exactly like you**, with:
- Context-sensitive tone adaptation (emails)
- Consistent professional voice (LinkedIn)
- Your actual patterns, not generic templates
- User-validated accuracy via feedback loop
