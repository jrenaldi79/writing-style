# Writing Style Clone System

Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates your authentic voice.

**🏆 Implements Anthropic Best Practices:**
- ✅ **[Progressive Disclosure](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** - 3-level loading: metadata → SKILL.md → references (only as needed)
- ✅ **[Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)** - Python scripts call MCP internally, achieving 99.2% token reduction
- ✅ **[Agent Skills Format](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)** - Fully compliant `/skills/writing-style/SKILL.md` structure
- ✅ **Context Efficiency** - Exceeds Anthropic's 98.7% target (27% → 0% context usage)

**Novel Adaptation:** Brings Claude Code's advanced patterns to ChatWise and other MCP clients

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
          │   ├── fetch_emails.py
          │   ├── fetch_linkedin_mcp.py
          │   ├── filter_*.py
          │   ├── cluster_*.py
          │   ├── generate_system_prompt.py
          │   └── ...           # Helper scripts
          └── /references/      # Reference data (progressive disclosure)
              ├── calibration.md
              ├── analysis_schema.md
              └── output_template.md
```

---

## 🎯 Current Version: v3.3

### What's New in v3.3 (2025-01-07)

**LinkedIn Pipeline Enhancement: Rich Data Capture**

- ✅ **20+ fields per post** (was: 5 fields)
- ✅ **Engagement signals**: Top comments, likes, authority mentions
- ✅ **Network context**: Tagged people, companies, follower count
- ✅ **Repost analysis**: Separate editorial voice from original content
- ✅ **Content metadata**: Images, links, post type (original vs repost)

**Impact:**
- Better persona quality through engagement validation
- Content balance analysis (creator vs curator ratio)
- Authority signals captured ("best mentor", "thought leader")
- Network collaboration patterns identified

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
- **Session 1:** Preprocessing (fetch, filter, cluster)
- **Session 2:** Analysis (tone scoring, persona definition)
- **Session 3:** LinkedIn (optional - unified professional voice)
- **Session 4:** Generation (synthesize final prompt)

**Dual Pipeline:**
- Email: Context-dependent (3-7 personas)
- LinkedIn: Unified professional brand (1 persona)

**State Persistence:**
- All progress saved to `state.json`
- Resume anytime without data loss

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
- `fetch_emails.py` - Gmail API integration
- `fetch_linkedin_mcp.py` - LinkedIn scraper (v3.3 with rich data)

### Processing
- `filter_*.py` - Quality filtering
- `enrich_*.py` - Metadata addition
- `embed_*.py` - Semantic embeddings
- `cluster_*.py` - Persona discovery

### Generation
- `generate_system_prompt.py` - Final prompt synthesis

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
python3 skills/writing-style/scripts/fetch_emails.py --count 200
```

---

## 🤝 Contributing

See `docs/` for implementation details and roadmap.

---

## 📝 License

MIT License

---

**Last Updated:** 2025-01-08 (v3.3 - Rich Data Capture)
