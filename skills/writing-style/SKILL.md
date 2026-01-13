---
name: writing-style
description: |
  Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates the user's authentic voice.

  Use this skill when:
  - Cloning email or writing style
  - Analyzing emails for voice patterns
  - Building writing personas
  - Running email or LinkedIn pipelines
  - Generating writing assistants
  - Continuing email analysis or analyzing clusters
  - Showing writing style project status

  v3.6 features: hybrid deterministic + LLM analysis, email persona schema v2.0 with voice fingerprint and relationship calibration.
---

# Writing Style Clone v3.6

Analyze writing samples to discover personas and generate personalized writing assistant prompts.

---

## 📂 Quick Reference

### Complete Documentation

This SKILL.md provides overview and navigation. For detailed instructions, see:

- **[Email Workflow](references/email_workflow.md)** - Complete email pipeline (Sessions 1, 2, 2b)
- **[LinkedIn Workflow](references/linkedin_workflow.md)** - Complete LinkedIn pipeline (Sessions 3, 3b)
- **[Data Schemas](references/data_schemas.md)** - All JSON schema specifications
- **[Script Guide](references/script_guide.md)** - Complete script reference and usage
- **[Troubleshooting](references/troubleshooting.md)** - Common issues and solutions
- **[Architecture](references/architecture.md)** - System design and best practices

### Directory Structure

```
~/skills/writing-style/          # Skill installation (read-only code)
├── SKILL.md                     # This file - workflow overview
├── scripts/                     # Python automation scripts
└── references/                  # Detailed documentation
    ├── email_workflow.md
    ├── linkedin_workflow.md
    ├── data_schemas.md
    ├── script_guide.md
    ├── troubleshooting.md
    ├── architecture.md
    ├── calibration.md
    ├── batch_schema.md
    ├── analysis_schema.md
    ├── output_template.md
    ├── email_persona_schema_v2.md
    └── linkedin_persona_schema_v2.md

~/Documents/my-writing-style/    # User data (outputs)
├── state.json                   # Workflow state
├── persona_registry.json        # Email personas
└── linkedin_persona.json        # LinkedIn persona

~/Documents/[name]-writing-clone/  # FINAL OUTPUT
```

**See:** [Architecture](references/architecture.md) for complete directory documentation.

---

## 🏗️ Architecture Overview

### Dual Pipeline Design

**Email Pipeline (Adaptive):**
- Context-dependent voice (Boss vs Team vs Client)
- Multiple personas (3-7 clusters)
- Relationship calibration

**LinkedIn Pipeline (Unified):**
- Consistent professional brand
- Single unified voice
- Engagement-weighted analysis

**CRITICAL RULE:** Never mix Email content with LinkedIn content.

**See:** [Architecture](references/architecture.md) for complete design documentation.

---

## 🆕 Multi-Session Workflow

**CRITICAL:** This workflow uses strategic session boundaries for clean context and higher quality outputs.

### Session Structure

**Session 1: Preprocessing (Architect)**
- Fetch emails → Filter → Enrich → Embed → Cluster
- **Output:** clusters.json + validation_set/ (15% held-out)
- **Action:** Review clusters, then START NEW CHAT

**Session 2: Email Persona Analysis (Analyst)**
- Analyze clusters → Generate personas → Ingest
- **Output:** persona_registry.json
- **Context:** Fresh session for analysis work

**Session 2b: Blind Validation (Judge) - Recommended**
- Test personas against held-out emails
- **Output:** validation_report.json
- **Context:** Fresh session for unbiased evaluation

**Session 3: LinkedIn Processing**
- Fetch posts → Filter → Generate persona
- **Output:** linkedin_persona.json
- **Context:** Separate from email pipeline

**Session 3b: LLM-Assisted Refinement - MANDATORY**
- Complete semantic fields (guardrails, negative examples)
- **Output:** Enhanced linkedin_persona.json
- **Reason:** Prevents "LinkedIn cringe" drift

**Session 4: Generation**
- Combine personas → Generate skill
- **Output:** ~/Documents/[name]-writing-clone/

**See:** [Architecture](references/architecture.md#session-architecture) for session design rationale.

---

## 📋 Prerequisites

### Email Pipeline

**Required:** Google Workspace MCP Server (`@presto-ai/google-workspace-mcp`)

**Install (ChatWise one-click):**
```
https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9
```

**Verify:** `python3 fetch_emails.py --check`

**See:** [Email Workflow](references/email_workflow.md) for complete setup.

### LinkedIn Pipeline

**Required:**
1. BrightData API token (https://brightdata.com/cp/start)
2. BrightData MCP Server
3. MCP_TOKEN environment variable

**Install (ChatWise one-click):**
```
https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0=
```

**Verify:** `python3 fetch_linkedin_mcp.py --check`

**See:** [LinkedIn Workflow](references/linkedin_workflow.md) for complete setup.

---

## 🚀 Quick Start

### Email Pipeline (Standard Workflow)

```bash
# Session 1: Preprocessing
cd ~/Documents/my-writing-style
python3 -m venv venv && venv/bin/python3 -m pip install -r requirements.txt
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py

# [Review clusters, then START NEW CHAT]

# Session 2: Analysis (repeat for each cluster)
venv/bin/python3 prepare_batch.py
# [LLM analyzes and creates batches/batch_NNN.json]
venv/bin/python3 ingest.py batches/batch_NNN.json

# Session 2b: Validation (recommended)
venv/bin/python3 prepare_validation.py
venv/bin/python3 validate_personas.py --auto

# Session 4: Generation
venv/bin/python3 generate_skill.py --name <your-name>
```

**See:** [Email Workflow](references/email_workflow.md) for detailed step-by-step instructions.

### Email Pipeline (Parallel Analysis - v3.5+)

```bash
# Session 1: Preprocessing (same as standard)
cd ~/Documents/my-writing-style
python3 -m venv venv && venv/bin/python3 -m pip install -r requirements.txt
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py

# Session 2: Parallel Analysis (all clusters at once - v3.6 hybrid)
export OPENROUTER_API_KEY="your-key-here"
venv/bin/python3 analyze_clusters.py --dry-run  # Preview cost
venv/bin/python3 analyze_clusters.py            # Generate personas

# Session 2b: Validation (same as standard)
venv/bin/python3 prepare_validation.py
venv/bin/python3 validate_personas.py --auto
```

**Benefits:**
- 60% token reduction (deterministic metrics computed locally)
- Automatic persona merging via embeddings
- Parallel processing of all clusters

**See:** [Email Workflow - Parallel Analysis](references/email_workflow.md#alternative-parallel-cluster-analysis-v35) for complete workflow.

### LinkedIn Pipeline

```bash
# Session 3: LinkedIn Processing
cd ~/Documents/my-writing-style
venv/bin/python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 20
venv/bin/python3 filter_linkedin.py
venv/bin/python3 cluster_linkedin.py

# Session 3b: LLM Enrichment (MANDATORY)
venv/bin/python3 prepare_llm_analysis.py
# [Copy llm_analysis_input.md to LLM, save output to llm_output.json]
venv/bin/python3 merge_llm_analysis.py llm_output.json
```

**CRITICAL:** Always provide full profile URL to avoid wrong-person errors!

**See:** [LinkedIn Workflow](references/linkedin_workflow.md) for detailed instructions and search strategies.

---

## 📊 What This Skill Does

1. **Fetches** your writing samples (emails, LinkedIn posts)
2. **Filters** for quality (removes garbage)
3. **Enriches** with metadata (recipient context, structure)
4. **Clusters** mathematically (discovers natural groupings)
5. **Analyzes** with calibrated scoring (1-10 tone vectors)
6. **Validates** against held-out samples
7. **Generates** final prompt (copy-paste ready skill)

### v3.6 Key Features

**Hybrid Analysis:**
- Deterministic metrics (Python): Sentence length, structure, punctuation
- Semantic fields (LLM): Tone interpretation, guardrails, annotations
- Result: 60% cost reduction, more consistent patterns

**Email Persona v2.0:**
- Voice Fingerprint: Core patterns consistent across contexts
- Relationship Calibration: Tone adjustments by recipient seniority
- Instruction Siblings: Every numeric score has text explanation
- Example Bank: Top 3-5 emails with ≥0.85 confidence

**LinkedIn Persona v2.0:**
- Separated Voice vs Content: HOW you write vs WHAT you write about
- Guardrails: Explicit "never do" rules (prevents LinkedIn cringe)
- Variation Controls: Ranges prevent robotic sameness
- Negative Examples: Anti-patterns to avoid

**See:** [Data Schemas](references/data_schemas.md) for complete schema specifications.

---

## 🎯 Best Practices

### Token Efficiency

1. **Use Batch Scripts:** Don't loop in REPL - use provided batch processors
2. **Offline Preprocessing:** Math operations (filter/enrich/embed/cluster) cost 0 tokens
3. **Session Boundaries:** Keep phases separate for clean context
4. **State Persistence:** Resume anytime without re-work

### Quality Control

1. **Always Use Calibration:** Reference `calibration.md` when scoring
2. **Holdout Validation:** Use `--holdout 0.15` to test accuracy
3. **Quality Filter:** Remove garbage before analysis (15-20% rejection rate is good)
4. **Multiple Clusters:** Email should discover 3-7 personas, LinkedIn exactly 1

### Workflow Management

1. **Check State First:** Always `cat state.json` before continuing
2. **Follow Session Structure:** Don't skip session boundaries
3. **Save Progress:** State is automatically saved after each phase
4. **Separate Pipelines:** Email and LinkedIn data stay separate

**See:** [Architecture - Best Practices](references/architecture.md#best-practices) for complete guidelines.

---

## 🔧 Common Issues

**Quick diagnostics:**

```bash
# Check MCP servers
python3 fetch_emails.py --check
python3 fetch_linkedin_mcp.py --check

# Check API keys
python3 api_keys.py --check
python3 api_keys.py --source

# Check data state
cat ~/Documents/my-writing-style/state.json

# Check persona health
python3 validate_personas.py --health
```

**Common fixes:**

| Issue | Quick Fix |
|-------|-----------|
| "No such file or directory" | Use dynamic path finding (see [Troubleshooting](references/troubleshooting.md#setup-and-installation-issues)) |
| "MCP server not found" | Install Google Workspace or BrightData MCP (see [Prerequisites](#-prerequisites)) |
| "No clusters found" | Fetch more emails or lower quality thresholds |
| "Persona scores inconsistent" | Always reference `calibration.md` |
| "LinkedIn returns empty" | Provide full profile URL, ensure profile is public |

**See:** [Troubleshooting](references/troubleshooting.md) for comprehensive solutions.

---

## 📚 Reference Documentation

### Workflows
- [Email Workflow](references/email_workflow.md) - Complete email pipeline (Sessions 1, 2, 2b)
- [LinkedIn Workflow](references/linkedin_workflow.md) - Complete LinkedIn pipeline (Sessions 3, 3b)

### Technical Reference
- [Data Schemas](references/data_schemas.md) - All JSON schema specifications
- [Script Guide](references/script_guide.md) - Complete script reference and usage patterns
- [Architecture](references/architecture.md) - System design and session management

### Guides
- [Troubleshooting](references/troubleshooting.md) - Common issues and solutions
- [Calibration](references/calibration.md) - Tone scoring anchor examples (1-10 scales)
- [Batch Schema](references/batch_schema.md) - Analysis format specification
- [Output Template](references/output_template.md) - Final prompt template

### Schemas
- [Email Persona v2.0](references/email_persona_schema_v2.md) - Complete email persona schema
- [LinkedIn Persona v2.0](references/linkedin_persona_schema_v2.md) - Complete LinkedIn persona schema
- [Analysis Schema](references/analysis_schema.md) - Persona output format

---

## 🎓 Summary

### What Makes It Different

- ✅ **Mathematical:** Not vibes - actual clustering algorithms
- ✅ **Validated:** Blind testing against held-out data
- ✅ **Context-Aware:** Email personas adapt to recipient
- ✅ **Brand-Consistent:** LinkedIn maintains unified voice
- ✅ **State-Managed:** Resume anytime without data loss
- ✅ **Production-Grade:** Comprehensive test suite

### Result

A system prompt that makes any AI write **exactly like you**, with:
- Context-sensitive tone adaptation (emails)
- Consistent professional voice (LinkedIn)
- Your actual patterns, not generic templates
- Validated accuracy via feedback loop

---

## 📖 Additional Resources

- **README.md** - Complete project overview
- **CHANGELOG.md** - Version history and breaking changes
- **index.html** - User guide with clickable workflows
- **tests/** - Unit and integration tests for validation

---

*For detailed step-by-step instructions, always consult the reference files linked throughout this document.*
