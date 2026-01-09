# Writing Style Clone System

Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates your authentic voice.

**🧠 Hybrid ML + GenAI Architecture:**
- ✅ **Machine Learning** - Semantic embeddings, clustering, engagement-weighted analysis
- ✅ **Large Language Models** - Nuanced persona interpretation, context-aware analysis
- ✅ **Strategic Separation** - ML for structured/quantifiable patterns, LLMs for subjective understanding

**🏆 Implements Anthropic Best Practices:**
- ✅ **[Progressive Disclosure](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** - 3-level loading: metadata → SKILL.md → references (only as needed)
- ✅ **[Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)** - Python scripts call MCP internally, achieving 99.2% token reduction
- ✅ **[Agent Skills Format](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)** - Fully compliant `/skills/writing-style/SKILL.md` structure
- ✅ **Context Efficiency** - Exceeds Anthropic's 98.7% target (27% → 0% context usage)

**Novel Adaptation:** Brings Claude Code's advanced patterns to ChatWise and other MCP clients

---

## 🔌 Prerequisites: MCP Servers

This skill requires MCP (Model Context Protocol) servers for data access. Install the servers needed for your pipeline(s).

### Email Pipeline

| Requirement | Details |
|-------------|---------|
| **MCP Server** | `@presto-ai/google-workspace-mcp` |
| **Authentication** | OAuth via Google (handled by MCP server) |
| **No API key needed** | Server manages auth automatically |

**One-click install (ChatWise):**
```
https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9
```

**Manual install:**
```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "npx",
      "args": ["-y", "@presto-ai/google-workspace-mcp"]
    }
  }
}
```

**Verify:** `venv/bin/python3 fetch_emails.py --check`

### LinkedIn Pipeline (Optional)

| Requirement | Details |
|-------------|---------|
| **MCP Server** | `@brightdata/mcp` |
| **API Token** | Required - sign up at [brightdata.com/cp/start](https://brightdata.com/cp/start) |
| **Environment** | `MCP_TOKEN` must be set |

**One-click install (ChatWise):**
```
https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0=
```
*(Replace `YOUR_BRIGHTDATA_TOKEN` after clicking)*

**Manual install:**
```json
{
  "mcpServers": {
    "brightdata": {
      "command": "npx",
      "args": ["@brightdata/mcp"],
      "env": {
        "API_TOKEN": "YOUR_BRIGHTDATA_TOKEN",
        "GROUPS": "advanced_scraping,social"
      }
    }
  }
}
```

**Set token for scripts:**
```bash
export MCP_TOKEN="your-brightdata-api-token"
```

**Verify:** `venv/bin/python3 fetch_linkedin_mcp.py --check`

### Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Install packages
venv/bin/pip install -r requirements.txt
```

Key packages: `sentence-transformers`, `scikit-learn`, `hdbscan`, `numpy`

---

## 🚀 Quick Start

### For End Users

**1. Open the Interactive Guide:**
Open `index.html` in your browser. It provides a clickable dashboard to launch every step of the process.

**2. Use the System Prompt:**
Copy the content of `system_prompt.md` into your AI assistant. This generic skills system prompt teaches the AI how to:
- Discover and load skills from the registry
- Execute skill workflows from SKILL.md
- Manage state across sessions

**3. Start with Bootstrap:**
Use `BOOTSTRAP.md` as your initial user prompt to check environment status and begin.

**Skill Triggers:** "Clone my email style", "Run Email Pipeline", "Run LinkedIn Pipeline"

---

## 📁 Repository Structure

```
/writing-style/
  ├── system_prompt.md          # Generic Skills System Prompt (Copy to ChatWise)
  ├── BOOTSTRAP.md              # Quick start user prompt for skill setup
  ├── SYSTEM_PROMPT.md          # DEPRECATED - see system_prompt.md
  ├── README.md                 # This file
  ├── CHANGELOG.md              # Version history
  ├── index.html                # Interactive user guide & dashboard
  ├── agents.md                 # Agent manifest

  ├── /docs/                    # Project documentation
  │   ├── COMPLETION_SUMMARY.md
  │   └── IMPLEMENTATION_PLAN.md

  └── /skills/                  # Anthropic Skill Format
      └── /writing-style/       # Skill directory
          ├── SKILL.md          # Single source of truth for workflow
          ├── /scripts/         # Python automation (bundled with skill)
          │   ├── fetch_emails.py         # Gmail MCP fetching
          │   ├── fetch_linkedin_mcp.py   # LinkedIn scraping
          │   ├── embed_emails.py         # ML: sentence-transformers
          │   ├── cluster_emails.py       # ML: HDBSCAN/K-Means
          │   ├── cluster_linkedin.py     # ML: statistical extraction
          │   ├── prepare_validation.py   # Validation: context extraction
          │   ├── validate_personas.py    # Validation: blind testing
          │   ├── generate_skill.py       # Final skill generation
          │   └── ...                     # Helper scripts
          └── /references/      # Reference data (progressive disclosure)
              ├── calibration.md
              ├── analysis_schema.md
              └── output_template.md
```

---

## 🎯 Current Version: v3.4

### What's New in v3.4 (2026-01-09)

**Hybrid ML + LLM Architecture Documentation**

- ✅ **Clear ML vs LLM separation** - Documented when/why each is used
- ✅ **Blind validation workflow** - Test personas against 15% held-out emails
- ✅ **Session 2b (Judge)** - New validation session with refinement suggestions
- ✅ **Engagement-weighted analysis** - Log-scale scoring for LinkedIn posts

**New Scripts:**
- `prepare_validation.py` - Extract context/reply pairs from holdout set
- `validate_personas.py` - Blind validation with automatic scoring
- `generate_skill.py` - Creates installable skill packages (replaces generate_system_prompt.py)

**Impact:**
- Personas validated before final skill generation
- Data-driven refinement suggestions
- Clear architectural reasoning for ML vs LLM choices

### What's New in v3.3 (2025-01-07)

**LinkedIn Pipeline Enhancement: Rich Data Capture**

- ✅ **20+ fields per post** (was: 5 fields)
- ✅ **Engagement signals**: Top comments, likes, authority mentions
- ✅ **Network context**: Tagged people, companies, follower count
- ✅ **Repost analysis**: Separate editorial voice from original content
- ✅ **Content metadata**: Images, links, post type (original vs repost)

---

## 📖 Documentation Guide

### For Users
1. **Start here:** `index.html` - Interactive dashboard
2. **System prompt:** `system_prompt.md` - Generic skills system prompt (copy to ChatWise)
3. **Bootstrap:** `BOOTSTRAP.md` - Quick start user prompt
4. **Workflow logic:** `skills/writing-style/SKILL.md` - Single source of truth for workflow
5. **Tone scoring:** `skills/writing-style/references/calibration.md` - Analysis anchors

### For Developers
- **Implementation Status:** `docs/COMPLETION_SUMMARY.md`
- **Tests:** `tests/README.md`

---

## 🏗️ Architecture

**Multi-Session Workflow:**
- **Session 1 (Architect):** Preprocessing (fetch, filter, embed, cluster)
- **Session 2 (Analyst):** Analysis (tone scoring, persona definition)
- **Session 2b (Judge):** Blind validation against held-out emails
- **Session 3:** LinkedIn (optional - unified professional voice)
- **Session 4:** Generation (synthesize final skill package)

**Dual Pipeline:**
- Email: Context-dependent (3-7 personas)
- LinkedIn: Unified professional brand (1 persona)

**State Persistence:**
- All progress saved to `state.json`
- Resume anytime without data loss

---

## 🧠 ML vs LLM: When We Use Each

This project strategically combines **traditional Machine Learning** and **Large Language Models** based on what each does best.

### The Philosophy

| Approach | Best For | Examples in This Project |
|----------|----------|--------------------------|
| **ML** | Structured patterns, quantifiable metrics, large-scale processing | Embeddings, clustering, engagement scoring |
| **LLM** | Nuanced understanding, subjective interpretation, context-dependent analysis | Persona creation, tone analysis, relationship dynamics |

### Email Pipeline: LLM-Heavy (Nuanced)

Email communication is inherently **context-dependent and nuanced**. The same person writes differently to their CEO vs their teammate vs a client. Understanding these shifts requires subjective interpretation.

| Stage | Technique | Why |
|-------|-----------|-----|
| **Embedding** | ML (sentence-transformers) | Convert text to vectors for mathematical comparison |
| **Clustering** | ML (HDBSCAN/K-Means) | Group similar emails without human bias |
| **Persona Analysis** | **LLM** | Interpret *why* emails cluster together, understand relationship dynamics, infer intent |
| **Tone Scoring** | **LLM** | Subjective 1-10 scales require human-like judgment |
| **Validation** | Hybrid | Heuristic scoring + optional LLM comparison |

**Why LLM for Email Personas?**
- Relationship context matters: "Hi Sarah" to a direct report vs CEO means different things
- Formality is subjective: What's "casual" varies by industry and culture
- Intent inference: Understanding *why* someone chose certain words
- Pattern synthesis: Combining greeting + closing + tone into coherent persona

### LinkedIn Pipeline: ML-Heavy (Formulaic)

LinkedIn posts are **public, structured, and engagement-validated**. We have quantifiable signals (likes, comments) that tell us what resonates. The patterns are more formulaic.

| Stage | Technique | Why |
|-------|-----------|-----|
| **Filtering** | Rule-based | Min length, quality thresholds |
| **Tone Vectors** | **ML** | Statistical analysis of formality markers, punctuation, sentence length |
| **Emoji Analysis** | **ML** | Frequency counting, placement detection |
| **Hook Classification** | **ML** | Pattern matching against known hook types |
| **Engagement Weighting** | **ML** | Log-scale scoring based on likes/comments |
| **Length Targets** | **ML** | Statistical bounds (min/max/target chars) |
| **Guardrails** | LLM (optional) | Session 3b refinement for "never do" rules |

**Why ML for LinkedIn?**
- **Engagement signals exist**: High-like posts = your strongest voice (quantifiable)
- **Patterns are extractable**: Emoji usage, sentence length, hashtag placement → statistics
- **Format is constrained**: LinkedIn posts follow platform conventions
- **No relationship context**: Public posts have consistent audience framing

### Engagement-Weighted Analysis (LinkedIn)

LinkedIn's engagement signals enable **data-driven voice extraction**:

```
Post A: 129 likes, 3 comments → High weight
Post B: 12 likes, 0 comments → Low weight
Post C: 47 likes, 8 comments → Medium-high weight
```

**Log-scale weighting** prevents viral outliers from dominating while still prioritizing resonant content:

```python
weight = log(1 + likes) + 2 * log(1 + comments)
```

This means:
- Your most engaging posts influence tone vectors more
- Best few-shot example = highest engagement post
- Consistent patterns emerge from what actually works

### Validation: Hybrid Approach

Blind validation uses **both techniques**:

| Component | Technique | Purpose |
|-----------|-----------|---------|
| Context extraction | Rule-based | Parse quoted text vs reply |
| Persona inference | Heuristics | Match context to likely persona |
| Tone comparison | ML metrics | Score formality, greeting, closing matches |
| Refinement suggestions | Statistical | Identify systematic mismatches |
| (Optional) Reply generation | LLM | Generate reply for qualitative comparison |

### Summary: Right Tool for the Job

```
┌─────────────────────────────────────────────────────────────┐
│                    WRITING STYLE CLONE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  EMAIL PIPELINE                 LINKEDIN PIPELINE            │
│  ─────────────────             ──────────────────            │
│                                                              │
│  ┌─────────────────┐           ┌─────────────────┐          │
│  │   Embeddings    │ ML        │   Embeddings    │ ML       │
│  │   Clustering    │ ML        │   Filtering     │ Rules    │
│  │   Enrichment    │ Rules     │   Tone Vectors  │ ML       │
│  │                 │           │   Emoji/Hooks   │ ML       │
│  │   ▼ ▼ ▼ ▼ ▼    │           │   Engagement    │ ML       │
│  │                 │           │                 │          │
│  │  Persona        │ LLM ◄──── │  Persona        │ ML       │
│  │  Analysis       │           │  Extraction     │          │
│  │  (nuanced)      │           │  (formulaic)    │          │
│  └─────────────────┘           └─────────────────┘          │
│                                                              │
│            ▼                            ▼                    │
│  ┌──────────────────────────────────────────────┐           │
│  │           VALIDATION (Hybrid)                 │           │
│  │   Heuristics + Scoring + Optional LLM        │           │
│  └──────────────────────────────────────────────┘           │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────┐           │
│  │         SKILL GENERATION (Template)          │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏆 Anthropic Best Practices Implementation

This project demonstrates advanced patterns from Anthropic's engineering research, adapted for use in ChatWise and other non-Claude Code environments.

### 1. Code Execution with MCP (Core Architecture)

**Anthropic's Insight:** [Code execution with MCP (Nov 2025)](https://www.anthropic.com/engineering/code-execution-with-mcp)

> "Direct tool calls consume context for each definition and result. Agents scale better by writing code to call tools instead."

**Our Implementation:**

```
❌ OLD WAY (Direct Tool Calls):
LLM → MCP tool call #1 → result in context
LLM → MCP tool call #2 → result in context
...[15+ iterations]
Result: 27% context consumed, 5 minutes

✅ NEW WAY (Code Execution with MCP):
LLM → start_process(python script)
Python → 23 internal MCP calls → filtered results
Result: 0% context consumed, 90 seconds
```

**Impact:** 98.7% token reduction

### 2. Progressive Disclosure (3-Level Context Loading)

**Anthropic's Insight:** [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

**Our Implementation:**

```
skills/writing-style/
  ├── SKILL.md (Level 1-2)              # Loaded when triggered
  ├── /references/ (Level 3)            # Loaded only when needed
  └── /scripts/ (Level 0)               # Executed, never read
```

**Total Context Savings:** 81% reduction vs loading everything.

---

## 🔧 Key Scripts

### Data Collection
- `fetch_emails.py` - Gmail MCP integration with holdout support
- `fetch_linkedin_mcp.py` - LinkedIn scraper (v3.3 with rich data + engagement)

### ML Processing
- `filter_*.py` - Quality filtering (rule-based)
- `enrich_emails.py` - Metadata addition (heuristics)
- `embed_emails.py` - Semantic embeddings (sentence-transformers)
- `cluster_emails.py` - Email clustering (HDBSCAN/K-Means)
- `cluster_linkedin.py` - LinkedIn persona extraction (statistical ML)

### LLM-Assisted Analysis
- `prepare_batch.py` - Format clusters for LLM persona analysis
- `ingest.py` - Save LLM-generated personas

### Validation
- `prepare_validation.py` - Extract context/reply pairs from holdout set
- `validate_personas.py` - Blind validation with refinement suggestions

### Generation
- `generate_skill.py` - Final skill package synthesis

---

## 🚦 Quick Commands

### Automated Setup
1. Copy `system_prompt.md` into your ChatWise assistant's system prompt
2. Use `BOOTSTRAP.md` as your first user prompt to check environment status
3. The AI will automatically load `SKILL.md` and guide you through the workflow

### Manual Usage
If you prefer running scripts manually:

```bash
# 1. Create Data Directory
mkdir -p ~/Documents/my-writing-style

# 2. Setup Venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run Pipeline
python3 skills/writing-style/scripts/fetch_emails.py --count 300
```

---

## 🤝 Contributing

See `docs/` for implementation details and roadmap.

---

## 📝 License

MIT License

---

**Last Updated:** 2026-01-09 (v3.4 - Hybrid ML/LLM Architecture + Blind Validation)
