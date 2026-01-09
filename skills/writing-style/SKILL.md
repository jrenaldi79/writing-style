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

~/Documents/my-writing-style/    # User data (intermediate outputs)
├── state.json                   # Workflow state
├── venv/                        # Python virtual environment
├── clusters.json                # Cluster assignments
├── persona_registry.json        # Email personas
└── linkedin_persona.json        # LinkedIn persona

~/Documents/[name]-writing-clone/  # FINAL OUTPUT: Installable skill
├── SKILL.md                     # Main skill file
└── references/
    ├── email_personas.md        # Detailed personas
    └── linkedin_voice.md        # LinkedIn profile
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

### Session Structure (Context Management)

**Session 1: Preprocessing (Architect)**
- Fetch emails → Filter → Enrich → Embed → Cluster
- **ENDS WITH:** Cluster summary + feedback checkpoint + validation set stats
- **CONTEXT:** Heavy with fetch/filter logs
- **ACTION:** Review clusters, adjust parameters if needed, then START NEW CHAT

**Session 2: Email Persona Analysis (Analyst)**
- LLM reads clusters, analyzes emails, creates persona JSONs
- Runs ingest.py after each batch
- **IMPORTANT:** Analyst never sees validation_set/ emails
- **CONTEXT:** Can stay in this session - each cluster analysis is self-contained

**Session 2b: Blind Validation (Judge) - Recommended**
- Tests personas against held-out emails (15% reserved in Session 1)
- Shows context only, compares generated patterns to actual replies
- Suggests refinements based on mismatches
- **CONTEXT:** Fresh chat for unbiased evaluation

**Session 3: LinkedIn (Optional)**
- Fetch posts → Filter → Generate LinkedIn persona
- **CONTEXT:** Separate from email pipeline

**Session 4: Generation**
- Generate final writing clone skill from all personas
- **CONTEXT:** Clean context for final assembly

**Why separate sessions?**
- Preprocessing generates 6,500+ tokens of logs
- Fresh context for creative persona analysis work
- Validation requires unbiased evaluator (didn't see training data)
- Scripts print session boundary reminders automatically

**State Persistence:** All progress saved to `state.json` - resume anytime without data loss.

---

## 🏗️ Architecture: Dual Pipeline

**CRITICAL RULE:** Never mix Email content with LinkedIn content.

### 1. Email Pipeline (Adaptive)
- **Source:** Google Workspace MCP Server (handles Gmail authentication automatically)
- **Nature:** Context-dependent (Boss vs Team vs Client)
- **Output:** Multiple Personas (3-7 clusters)
- **Sessions:** Preprocessing (Session 1) → Analysis (Session 2)

**Prerequisites:**
- Google Workspace MCP server installed in your chat client (`@presto-ai/google-workspace-mcp`)
- Already authenticated with Gmail (the MCP server handles auth - no credentials.json needed)
- The `fetch_emails.py` script communicates directly with the MCP server

### 2. LinkedIn Pipeline (Unified)
- **Source:** LinkedIn Scraper
- **Nature:** Public Professional Brand
- **Output:** EXACTLY ONE Persona (Single centroid)
- **Sessions:** Unified processing (Session 3)

---

## 🔄 Complete Workflow: Email Pipeline

### Session 1: Setup & Preprocessing

**Purpose:** Fetch emails, filter quality, enrich metadata, cluster mathematically.

**MCP Requirement:** The email scripts use the Google Workspace MCP server (`@presto-ai/google-workspace-mcp`) which should already be installed and authenticated in your chat client. No separate credentials.json or OAuth setup is needed - the MCP server handles all Gmail authentication.

**Not installed yet?** Use this one-click install link for ChatWise:
`https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9`

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

# 5. Verify MCP is installed and authenticated (auto-runs before fetch)
#    If this fails, the script will show install instructions with a one-click link
venv/bin/python3 fetch_emails.py --check

# 6. Run preprocessing pipeline (MCP check runs automatically)
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
```

---

### 🛑 Health Check: Cluster Quality (DECISION POINT)

After `cluster_emails.py` completes, **evaluate the output before proceeding**. The clustering algorithm's default settings may not be optimal for your writing patterns.

#### Quick Assessment

| Result | Status | Action |
|--------|--------|--------|
| **3-7 clusters** | ✅ Ideal | Proceed to Session 2 |
| **< 3 clusters** | ⚠️ Underwhelming | See options below |
| **> 10 clusters** | ⚠️ Fragmented | Consider merging or increasing min-cluster |
| **> 30% Noise** | ⚠️ Poor fit | Switch to K-Means |

#### Q: Did you get fewer than 3 clusters?

This is common with HDBSCAN if your recent emails are stylistically consistent. **You have options:**

**Option A (Recommended): Force variety with K-Means**
```bash
# Force 5 distinct personas
venv/bin/python3 cluster_emails.py --algorithm kmeans -k 5
```
*Why:* K-Means guarantees exactly k clusters. Good when you know you write differently to different audiences.

**Option B: Fetch more email history**
```bash
# Get 500 emails instead of 200
venv/bin/python3 fetch_emails.py --count 500 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
```
*Why:* More data = more variation. HDBSCAN may find natural clusters with larger samples.

**Option C: Adjust HDBSCAN sensitivity**
```bash
# Smaller minimum cluster size = more clusters
venv/bin/python3 cluster_emails.py --algorithm hdbscan --min-cluster 3
```
*Why:* Default min-cluster is 5. Lowering it allows smaller groups to form.

#### Q: Did you get too much "Noise"?

"Noise" = emails that didn't fit cleanly into any cluster. Some noise is fine (edge cases), but high noise is problematic.

| Noise Level | Meaning | Action |
|-------------|---------|--------|
| **< 10%** | ✅ Normal | Proceed |
| **10-30%** | ⚠️ Moderate | Consider K-Means |
| **> 30%** | ❌ Poor fit | **Use K-Means** to force assignment |

```bash
# Force all emails into clusters (no noise)
venv/bin/python3 cluster_emails.py --algorithm kmeans -k 5
```

#### Q: How many clusters should I target?

| Email Volume | Suggested k | Rationale |
|--------------|-------------|-----------|
| 100-200 | 3-4 | Limited data, broader personas |
| 200-500 | 4-6 | Good variety, distinct styles |
| 500+ | 5-8 | Rich data, fine-grained personas |

**Rule of thumb:** Start with `k = 5` if unsure. You can always re-cluster.

#### Making the Decision

**Ask yourself:** "Do I write differently to different audiences?"

- **Yes, definitely** → Target 4-6 clusters (CEO vs team vs clients vs vendors)
- **Somewhat** → Target 3-4 clusters
- **I'm pretty consistent** → 2-3 clusters may be accurate!

**Remember:** More clusters ≠ better. The goal is **meaningful** personas, not maximum fragmentation.

---

**Output:**
- `clusters.json` - Discovered email clusters
- `state.json` - Workflow state (enables resume)
- `filtered_samples/` - Quality-filtered emails
- `enriched_samples/` - Emails with metadata
- `validation_set/` - Held-out samples for testing

> **🛑 STOP HERE - START A NEW CHAT**
>
> Do NOT continue in this session. Context from preprocessing (6,500+ tokens of logs)
> will degrade persona analysis quality.
>
> **Session 1 is complete when:** Clusters look reasonable, validation set exists.

---

### Session 2: Cluster Analysis

**Purpose:** Analyze each cluster to build persona profiles with calibrated scoring.

**IMPORTANT:** `prepare_batch.py` outputs analysis content to **stdout** (console), not to a file. The LLM/agent must:
1. Read the output
2. Analyze the emails
3. Create the batch JSON file manually
4. Run ingest.py with that file

---

#### MANDATORY STEP 1: Calculate Batch Sizes

**Before analyzing ANY cluster, you MUST calculate required batch sizes.**

```bash
# Show batch size requirements for 80% coverage
venv/bin/python3 prepare_batch.py --coverage
```

This displays:
```
════════════════════════════════════════════════════════════
BATCH SIZE REQUIREMENTS (80% COVERAGE TARGET)
════════════════════════════════════════════════════════════

Formula: Required Emails = ceil(Cluster Size × 0.8)

────────────────────────────────────────────────────────────
  ⬚ Cluster 0: 45 emails → Need 36 (0 done, 0%)
  ⬚ Cluster 1: 32 emails → Need 26 (0 done, 0%)
  ⬚ Cluster 2: 28 emails → Need 23 (0 done, 0%)
────────────────────────────────────────────────────────────

  TOTAL: 105 emails → Need 85 for 80% coverage
  CURRENT: 0 analyzed (0% overall)

  📊 Still need: 85 more emails
════════════════════════════════════════════════════════════
```

**Coverage Rules:**
| Rule | Requirement |
|------|-------------|
| **Minimum threshold** | 80% of each cluster MUST be analyzed |
| **Enforcement** | `ingest.py` will REJECT batches that leave coverage below 80% |
| **Override** | Use `--force` flag only with documented justification |

**Why 80%?** Lower coverage creates unreliable personas. A persona built from 50% of a cluster may miss critical voice patterns.

---

#### Workflow Steps

```bash
# 1. Check state (should show preprocessing complete)
cat state.json

# 2. View cluster status
venv/bin/python3 prepare_batch.py --all

# 3. Prepare first cluster (outputs to CONSOLE, not file)
venv/bin/python3 prepare_batch.py
# This prints: calibration reference + emails + JSON schema instructions
# READ THIS OUTPUT CAREFULLY - it contains the emails to analyze
```

#### LLM Analysis Step (Manual)

After running `prepare_batch.py`, the LLM should:

1. **Read the console output** - Contains emails and instructions
2. **Analyze each email** for tone, formality, structure, patterns
3. **Create a persona** based on the cluster characteristics
4. **Write the batch JSON file** following the schema printed in the output

**Create file: `batches/batch_001.json`** with this structure:
```json
{
  "batch_id": "batch_001",
  "analyzed_at": "2026-01-09T12:00:00Z",
  "cluster_id": 0,
  "calibration_referenced": true,
  "new_personas": [
    {
      "name": "Formal Executive",
      "description": "Used for communication with executives and leadership",
      "characteristics": {
        "formality": 8, "warmth": 5, "authority": 7, "directness": 6,
        "typical_greeting": "Hi",
        "typical_closing": "Best, JR"
      }
    }
  ],
  "samples": [
    {
      "id": "email_abc123",
      "source": "email",
      "persona": "Formal Executive",
      "confidence": 0.85,
      "analysis": {"formality": 8, "warmth": 5},
      "context": {"recipient_type": "executive", "audience": "superior"}
    }
  ]
}
```

#### Continue Processing

```bash
# 4. Ingest the batch you created
venv/bin/python3 ingest.py batches/batch_001.json

# 5. Repeat for next cluster
venv/bin/python3 prepare_batch.py  # Gets next unanalyzed cluster
# ... LLM analyzes and creates batch_002.json ...
venv/bin/python3 ingest.py batches/batch_002.json

# 6. Continue until all clusters are done
venv/bin/python3 prepare_batch.py --all  # Check remaining
```

**Key Files:**
- `calibration.md` - Anchor examples for consistent scoring (in references/)
- `prepare_batch.py` - Outputs cluster emails to console for analysis
- `ingest.py` - Ingests your analysis JSON into persona_registry.json
- `persona_registry.json` - All discovered personas

#### Cluster Coverage Requirement

**You MUST analyze at least 80% of each cluster's emails** before moving to the next cluster. Incomplete coverage creates unreliable personas.

- Run `prepare_batch.py` repeatedly until "Unanalyzed: 0" or coverage reaches 80%+
- The script will warn you if coverage drops below 80%
- Use `--force` flag to bypass warnings if you have a documented reason

> **🛑 STOP HERE - START A NEW CHAT**
>
> After all clusters are analyzed, the `ingest.py` script will display a STOP banner.
> Do NOT continue to validation or generation in this session.
>
> **Session 2 is complete when:** All clusters show ✅ Complete or 80%+ coverage.

---

### Session 2b: Blind Validation (REQUIRED)

**Purpose:** Test persona accuracy against held-out emails before generating the final skill.

**⚠️ Validation has TWO phases - both are REQUIRED:**
- **Phase 1 (Automatic):** Quick heuristic scoring to catch obvious issues
- **Phase 2 (Interactive):** Manual judgment of generated replies - the fine-tuning phase

**Why validate?**
- Session 2 builds personas from training data only
- Validation uses emails the LLM **never saw during analysis**
- Catches persona mismatches before you commit to the final skill
- Provides concrete refinement suggestions

**Prerequisites:**
- All clusters analyzed (Session 2 complete)
- Validation set exists (`fetch_emails.py --holdout 0.15` was used in Session 1)
- (Recommended) OpenRouter API key for true blind validation

#### OpenRouter Setup (Recommended)

For **true blind validation**, an LLM generates replies using only the persona characteristics (never seeing the actual emails). This requires an OpenRouter API key.

The skill automatically detects your API key from:

1. **Chatwise settings** (Recommended) - If you've configured OpenRouter in Chatwise, the skill will use it automatically.

2. **Environment variable** - Set `OPENROUTER_API_KEY` in your terminal:
   ```bash
   export OPENROUTER_API_KEY='your-key-here'
   # Or add to ~/.bashrc or ~/.zshrc for persistence
   ```

Get your key at: https://openrouter.ai/keys

#### Model Selection (REQUIRED)

**You MUST select a model before running LLM validation.** Models can become unavailable or outdated, so explicit selection ensures you're using a working model.

```bash
# 1. List available models (fetches from OpenRouter, last 6 months)
venv/bin/python3 validate_personas.py --list-models

# 2. Select your preferred model (REQUIRED before --auto or --review)
venv/bin/python3 validate_personas.py --set-model 'anthropic/claude-sonnet-4-20250514'
```

The script shows models from major providers (Anthropic, OpenAI, Google, Meta, Mistral) with pricing and context length info. Your selection is saved to `openrouter_model.json`.

**Note:** Validation will not proceed until you've explicitly selected a model. This prevents failures from outdated default models.

Without OpenRouter, validation falls back to template-based generation (less accurate).

#### Phase 1: Automatic Validation

```bash
cd ~/Documents/my-writing-style

# 1. Check persona health (detects wrong filenames, schema issues)
venv/bin/python3 validate_personas.py --health

# 2. Check validation data exists
ls validation_set/*.json | wc -l
# Should show 15-30 emails (15% of total)

# 3. Extract context/reply pairs from validation emails
venv/bin/python3 prepare_validation.py

# 4. Run automatic validation (Phase 1)
venv/bin/python3 validate_personas.py --auto
```

**⚠️ DO NOT STOP HERE** - Phase 1 provides a baseline score using heuristics, but does NOT test real generated text. You MUST complete Phase 2 for accurate validation.

#### How Blind Validation Works

1. **Load personas** - Your draft personas from training data
2. **Load validation pairs** - Each email split into:
   - **Context**: What was received (quoted text, subject, sender)
   - **Ground truth**: Your actual reply (hidden from scoring)
3. **Inference**: For each validation email, determine which persona should respond
4. **Generate reply** - A separate LLM (via OpenRouter) generates a reply using ONLY the persona + context. This LLM has never seen the actual emails, ensuring true blind validation.
5. **Compare**: The generated reply vs your actual reply shows if the persona captures your voice
6. **Refinement**: Suggest persona adjustments based on mismatches

**Why a separate LLM call?** The LLM running this skill may have seen the actual emails during analysis (Session 2). A fresh LLM call with only persona + context ensures unbiased evaluation.

#### Validation Metrics

| Metric | What It Measures |
|--------|------------------|
| **Tone Match** | Formality, warmth, contractions match persona? |
| **Greeting Match** | Same greeting pattern (Hi vs Dear vs Hey)? |
| **Closing Match** | Same sign-off style (Best vs Thanks vs Cheers)? |
| **Overall Score** | Weighted composite (0-100) |

#### Understanding Results

```
VALIDATION COMPLETE
═══════════════════════════════════════════════════════════════

Overall Score: 78/100

Tone Match:
  formality       [+++++++-]  72%
  contractions    [+++++++++-] 90%
  warmth          [+++++++--] 78%

Structure Match:
  greeting        [++++++---] 65%
  closing         [++++++++] 82%

SUGGESTED REFINEMENTS
═══════════════════════════════════════════════════════════════

  1. [Formal Executive] greeting
     Current: Dear
     Suggestion: Update typical_greeting to match: 'Hi'
     Reason: Ground truth emails use different greeting pattern
```

#### Acting on Suggestions

If validation score is low (<70%), consider:

1. **Update persona_registry.json** with suggested changes
2. **Re-run validation** to verify improvements
3. **Iterate** until score is acceptable

```bash
# Edit personas based on suggestions
cat persona_registry.json | jq '.personas["Formal Executive"].characteristics.typical_greeting = "Hi"' > temp.json
mv temp.json persona_registry.json

# Re-validate
venv/bin/python3 validate_personas.py --auto
```

#### Phase 2: Interactive Validation (REQUIRED)

**This is the FINE-TUNING phase** - you must manually judge generated replies to properly calibrate your personas.

```bash
# 1. Review generated replies side-by-side with your actual emails
#    Shows: actual reply vs what persona would generate
venv/bin/python3 validate_personas.py --review

# 2. Judge each mismatch: "Does this sound like me?"
venv/bin/python3 validate_personas.py --feedback 'email_001' --sounds-like-me true
venv/bin/python3 validate_personas.py --feedback 'email_002' --sounds-like-me false --notes 'too formal for this context'

# 3. Get refinement suggestions based on YOUR feedback
venv/bin/python3 validate_personas.py --suggestions

# 4. Apply refinements to persona_registry.json and re-validate
```

**Why Phase 2 is REQUIRED:**
- Heuristics ≠ Reality - automatic validation uses templates, not real generated text
- You are the expert on your voice - only YOU can judge if text sounds authentic
- Manual judgment is the ground truth for persona calibration
- Skipping Phase 2 means your personas may not match your actual voice

**CLI Options:**
| Flag | Purpose |
|------|---------|
| `--health` | Check persona file naming and schema issues |
| `--auto` | Run automatic validation with heuristics |
| `--review` | Show mismatches with generated reply previews |
| `--feedback <id>` | Record feedback for a validation pair |
| `--sounds-like-me` | Whether generated reply sounds authentic (true/false) |
| `--notes` | Optional explanation for negative feedback |
| `--suggestions` | Show refinement suggestions from feedback |
| `--report` | Display validation report |
| `--status` | Show validation status |

**Health Check Detects:**
- Wrong filename (`personas.json` instead of `persona_registry.json`)
- Schema issues (characteristics as list instead of dict with tone vectors)
- Missing required fields (formality, warmth, directness)

#### When to Skip Phase 2 (Not Recommended)

Phase 2 should only be skipped in rare circumstances:

- **Never for initial skill generation** - you're learning your voice for the first time
- **Only if regenerating after minor edits** - and you're confident in existing personas
- **Time investment:** 30 minutes of manual judgment now saves hours of fixing bad outputs later

The skill generator (`generate_skill.py`) will **block generation** if Phase 2 is not complete. Use `--skip-validation-check` to override, but this is not recommended.

**Output:**
- `validation_pairs.json` - Extracted context/reply pairs
- `validation_results.json` - Detailed per-email results
- `validation_report.json` - Summary with refinement suggestions

> **🛑 SESSION 2b COMPLETION CHECKLIST**
>
> Before proceeding to generation, confirm:
>
> - [ ] **Phase 1 complete:** `validate_personas.py --auto` run, baseline score recorded
> - [ ] **Phase 2 complete:** `validate_personas.py --review` run, reviewed generated replies
> - [ ] **Feedback recorded:** `validate_personas.py --feedback` for mismatches
> - [ ] **Suggestions reviewed:** `validate_personas.py --suggestions` applied to personas
> - [ ] **Final check:** "Yes, these generated replies sound like me"
>
> **Session 2b is complete when:** Both phases are done and you're confident the personas capture your voice.

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

#### Prerequisites

The LinkedIn pipeline requires the BrightData MCP server and an API token.

**Step 1: Get a BrightData API Token**
1. Sign up at: https://brightdata.com/cp/start
2. Navigate to API settings to get your token
3. Copy the token for the next steps

**Step 2: Install BrightData MCP Server (ChatWise one-click):**
`https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0=`

After clicking, replace `YOUR_BRIGHTDATA_TOKEN` with your actual token!

**Step 3: Set MCP_TOKEN in Terminal Tool**

The scripts need MCP_TOKEN available when running via terminal. If using desktop-commander (ChatWise one-click):
`https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImRlc2t0b3AtY29tbWFuZGVyIjogewogICAgICAiY29tbWFuZCI6ICJucHgiLAogICAgICAiYXJncyI6IFsiLXkiLCAiQHdvbmRlcndoeS1lci9kZXNrdG9wLWNvbW1hbmRlciJdLAogICAgICAiZW52IjogewogICAgICAgICJNQ1BfVE9LRU4iOiAiWU9VUl9CUklHSFREQVRBX1RPS0VOIgogICAgICB9CiAgICB9CiAgfQp9`

After clicking, replace `YOUR_BRIGHTDATA_TOKEN` with your actual token!

**Alternative:** Add to `~/.bashrc` or `~/.zshrc`:
```bash
export MCP_TOKEN="your-brightdata-api-token"
```

#### Verify Setup & Fetch Posts

```bash
cd ~/Documents/my-writing-style

# Verify BrightData MCP is configured (run this first!)
venv/bin/python3 fetch_linkedin_mcp.py --check

# Fetch posts (fully automated with built-in verification)
venv/bin/python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 20

# Filter quality posts (min 200 chars)
venv/bin/python3 filter_linkedin.py

# Generate unified persona (NO clustering - single voice)
venv/bin/python3 cluster_linkedin.py
```

**How it works:**
1. **Profile Verification:** Scrapes profile to verify identity (name, headline, company)
2. **Smart Search:** Uses disambiguating terms to find correct person's posts AND articles
3. **Parallel Scraping:** Fetches posts in parallel (5 concurrent) for faster processing
4. **Content Types:** Captures both short-form posts (`/posts/`) and long-form articles (`/pulse/`)
5. **Validation:** Filters out posts from wrong people
6. **State Tracking:** Saves progress for resume/debugging

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

# 1. Check available data
venv/bin/python3 generate_skill.py --status

# 2. Generate the writing clone skill
# Prompts for your name, then creates skill package
venv/bin/python3 generate_skill.py --name john
```

**Output:**
- `~/Documents/john-writing-clone/` - **INSTALLABLE SKILL PACKAGE**
  - `SKILL.md` - Main skill file with frontmatter
  - `references/email_personas.md` - Detailed email personas
  - `references/linkedin_voice.md` - LinkedIn voice profile (if exists)

### Installing Your Writing Clone Skill

After generating the skill:

1. **Start a new chat** with clean context

2. **Ask the LLM to install it:**
   > "Install my writing clone skill from ~/Documents/john-writing-clone"

3. **Or manually copy:**
   ```bash
   cp -r ~/Documents/john-writing-clone ~/.claude/skills/
   ```

### Testing Your Writing Clone

Once installed, test the skill by asking:
- "Write a formal email to the CEO about Q4 results"
- "Write a casual Slack message to my team"
- "Write a LinkedIn post about product launches"

**Collect feedback** - Identify what feels off and refine the skill.

**Done!** You now have an installable writing clone skill.

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
│   │   │   ├── generate_skill.py # Final generation
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
├── my-writing-style/          # Your personal data (created by scripts)
│   ├── state.json             # Workflow state (enables resume)
│   ├── raw_samples/           # Fetched emails/posts (200+)
│   ├── filtered_samples/      # Quality-filtered (170+)
│   ├── enriched_samples/      # With metadata (170+)
│   ├── validation_set/        # Held-out for testing (30)
│   ├── batches/               # Prepared for analysis
│   │   ├── batch_001.json     # Cluster 1 emails
│   │   ├── batch_002.json     # Cluster 2 emails
│   │   └── ...
│   ├── clusters.json          # Email cluster definitions
│   ├── persona_registry.json  # All email personas
│   ├── linkedin_persona.json  # LinkedIn voice (if used)
│   ├── validation_pairs.json  # Context/reply pairs (for validation)
│   ├── validation_results.json # Per-email validation results
│   ├── validation_report.json # Summary with refinements
│   ├── validation_review.json # Mismatches with generated replies
│   └── validation_feedback.json # User feedback on mismatches
│
└── [name]-writing-clone/      # ← FINAL OUTPUT: Installable skill
    ├── SKILL.md               # Main skill file with frontmatter
    └── references/
        ├── email_personas.md  # Detailed persona profiles
        └── linkedin_voice.md  # LinkedIn voice profile
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
| `fetch_emails.py` | Pull from Gmail | MCP Server* | raw_samples/*.json |
| `filter_emails.py` | Quality gate | raw_samples/ | filtered_samples/ |
| `enrich_emails.py` | Add metadata | filtered_samples/ | enriched_samples/ |
| `embed_emails.py` | Generate vectors | enriched_samples/ | embeddings.npy |
| `cluster_emails.py` | Math clustering | embeddings.npy | clusters.json |
| `prepare_batch.py` | Format for analysis | clusters.json | stdout (console)** |
| `prepare_batch.py --coverage` | Show batch size requirements | clusters.json | Console output |
| `prepare_batch.py --target-coverage 0.9` | Custom coverage threshold | clusters.json | Console output |
| `ingest.py` | Save persona | batches/*.json | persona_registry.json |
| `ingest.py --force` | Bypass coverage validation | batches/*.json | persona_registry.json |

*\*\*`prepare_batch.py` prints emails + instructions to console. LLM must analyze and create `batches/*.json` manually.*

*\*MCP Server = Google Workspace MCP (`@presto-ai/google-workspace-mcp`). Must be installed in your chat client. Authentication is handled by the MCP server - no credentials.json required.*

### Validation Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `prepare_validation.py` | Extract context/reply pairs | validation_set/ | validation_pairs.json |
| `validate_personas.py --health` | Check persona file/schema issues | persona_registry.json | Console output |
| `validate_personas.py --auto` | Automatic blind validation | personas + pairs | validation_report.json |
| `validate_personas.py --review` | Review mismatches with generated replies | personas + pairs | validation_review.json |
| `validate_personas.py --feedback` | Record feedback on mismatch | pair_id + response | validation_feedback.json |
| `validate_personas.py --suggestions` | Show refinement suggestions | feedback | Console output |
| `validate_personas.py --list-models` | List available OpenRouter models | OPENROUTER_API_KEY | Console output |
| `validate_personas.py --set-model` | Set model for LLM validation | model_id | openrouter_model.json |

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
| `generate_skill.py` | Create final artifact |
| `api_keys.py` | API key management (Chatwise + env var) |
| `api_keys.py --check` | Verify OpenRouter API key is available |
| `api_keys.py --source` | Show where API key was found |
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
- The `requirements.txt` is in the skill directory (`~/skills/writing-style/requirements.txt`)

**"prepare_batch.py doesn't create JSON file"**
- This is expected behavior! `prepare_batch.py` outputs to **console/stdout**, not to a file
- The LLM/agent must read the output, analyze the emails, and create `batches/batch_NNN.json` manually
- See Session 2 documentation for the required JSON schema

**"generate_skill.py can't find data"**
- The script reads from `persona_registry.json` (created by ingest.py)
- Run `python3 generate_skill.py --status` to check what data is available
- Make sure you've run the full analysis pipeline including `ingest.py`
- At least one of email personas or LinkedIn voice is required

**"MCP server not found" or "Authentication required" (Email)**
- The email pipeline requires the Google Workspace MCP server
- Verify with: `python3 fetch_emails.py --check`
- One-click install (ChatWise): `https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9`
- Manual: Add `@presto-ai/google-workspace-mcp` to your chat client's MCP config
- After installing, authenticate with Google when prompted

**"MCP_TOKEN not set" or "BrightData API failed" (LinkedIn)**
- The LinkedIn pipeline requires BrightData MCP server + API token
- Verify with: `python3 fetch_linkedin_mcp.py --check`
- Get token: Sign up at https://brightdata.com/cp/start
- Install BrightData MCP (ChatWise): See LinkedIn Prerequisites section above
- Set MCP_TOKEN in desktop-commander or shell profile (`export MCP_TOKEN="..."`)
- Both the BrightData MCP AND the terminal tool need the token configured

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
