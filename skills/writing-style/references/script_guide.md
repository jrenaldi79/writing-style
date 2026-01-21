# Script Reference Guide

Complete reference for all scripts in the writing-style pipeline.

---

## Core Processing Scripts

Pipeline scripts for email analysis workflow.

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `state_manager.py` | Track workflow progress | - | state.json |
| `fetch_emails.py` | Pull from Gmail | MCP Server* | raw_samples/*.json |
| `filter_emails.py` | Quality gate | raw_samples/ | filtered_samples/ |
| `enrich_emails.py` | Add metadata + seniority | filtered_samples/ | enriched_samples/ |
| `embed_emails.py` | Generate vectors | enriched_samples/ | embeddings.npy |
| `cluster_emails.py` | Math clustering | embeddings.npy | clusters.json |
| `email_analysis_v2.py` | Deterministic metrics (v2) | enriched_samples/ | Used by analyze_clusters.py |
| `analyze_clusters.py` | Parallel analysis (v3.5+) | clusters.json | analysis_draft.json |
| `prepare_batch.py` | Format for manual analysis | clusters.json | stdout (console)** |
| `prepare_batch.py --coverage` | Show batch size requirements | clusters.json | Console output |
| `ingest.py` | Save persona | batches/*.json | persona_registry.json |
| `ingest.py --force` | Bypass coverage validation | batches/*.json | persona_registry.json |

**\*\*`prepare_batch.py` prints emails + instructions to console. LLM must analyze and create `batches/*.json` manually.**

**\*MCP Server = Google Workspace MCP (`@presto-ai/google-workspace-mcp`). Must be installed in your chat client. Authentication is handled by the MCP server - no credentials.json required.**

---

## Validation Scripts

Scripts for persona accuracy testing and refinement.

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

**Validation workflow:**
1. `prepare_validation.py` - Extract held-out email pairs
2. `validate_personas.py --auto` - Generate replies using personas
3. `validate_personas.py --review` - Compare generated vs actual replies
4. `validate_personas.py --feedback <pair_id> <response>` - Record corrections
5. `validate_personas.py --suggestions` - Get refinement recommendations

---

## LinkedIn Scripts

Scripts for LinkedIn content analysis pipeline.

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `fetch_linkedin_direct.py` | Direct API fetch with auto-search | Profile URL | linkedin_data/*.json |
| `filter_linkedin.py` | Quality gate (>200 chars) | linkedin_data/ | filtered/ |
| `cluster_linkedin.py` | Unify voice (v2 schema) | filtered/ | linkedin_persona.json |

### fetch_linkedin_direct.py Options

| Option | Description |
|--------|-------------|
| `--check` | Verify BrightData MCP is configured |
| `--profile <url>` | LinkedIn profile URL or username |
| `--limit <n>` | Max posts to fetch (default: 20) |
| `--min-posts <n>` | Auto-search if below threshold (recommended: 15) |
| `--search-queries` | Comma-separated search terms |
| `--search-engines` | google, bing, or both (default: google) |
| `--search-only` | Skip activity feed, use only search |
| `--status` | Show current fetch status |

**LinkedIn workflow:**
1. `fetch_linkedin_direct.py --profile <URL> --min-posts 15` - Fetch with auto-search
2. `filter_linkedin.py` - Remove low-quality posts
3. `cluster_linkedin.py` - Generate unified persona (with quality warnings)

**See complete LinkedIn workflow:** [linkedin_workflow.md](linkedin_workflow.md)

---

## Utility Scripts

Helper scripts for API management and final output generation.

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

---

## Script Usage Patterns

### Email Pipeline (Standard)

```bash
# Session 1: Preprocessing
cd ~/Documents/my-writing-style
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py

# Session 2: Analysis (repeat for each cluster)
venv/bin/python3 prepare_batch.py
# [LLM analyzes and creates batches/batch_NNN.json]
venv/bin/python3 ingest.py batches/batch_NNN.json

# Session 2b: Validation (optional but recommended)
venv/bin/python3 prepare_validation.py
venv/bin/python3 validate_personas.py --auto

# Session 4: Generation
venv/bin/python3 generate_skill.py --name <your-name>
```

### Email Pipeline (Parallel Analysis - v3.5+)

```bash
# Session 1: Preprocessing (same as standard)
cd ~/Documents/my-writing-style
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py
venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py

# Session 2: Parallel Analysis (all clusters at once)
export OPENROUTER_API_KEY="your-key-here"
venv/bin/python3 analyze_clusters.py --dry-run  # Preview cost
venv/bin/python3 analyze_clusters.py            # Generate personas

# Session 2b: Validation (same as standard)
venv/bin/python3 prepare_validation.py
venv/bin/python3 validate_personas.py --auto

# Session 4: Generation (same as standard)
venv/bin/python3 generate_skill.py --name <your-name>
```

**See complete email workflow:** [email_workflow.md](email_workflow.md)

### LinkedIn Pipeline

```bash
# Session 3: LinkedIn Processing
cd ~/Documents/my-writing-style
venv/bin/python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 20
venv/bin/python3 filter_linkedin.py
venv/bin/python3 cluster_linkedin.py

# Session 3b: LLM Enrichment (optional)
venv/bin/python3 prepare_llm_analysis.py
# [Copy llm_analysis_input.md to LLM, save output to llm_output.json]
venv/bin/python3 merge_llm_analysis.py llm_output.json
```

---

## Common Script Options

### State Management

All scripts automatically update `state.json`. Check state before resuming:

```bash
cat ~/Documents/my-writing-style/state.json
```

### Custom Data Directory

Set custom data location (applies to all scripts):

```bash
export WRITING_STYLE_DATA="/path/to/custom/data"
```

### Dry Run Mode

Many scripts support `--dry-run` to preview actions:

```bash
venv/bin/python3 analyze_clusters.py --dry-run
venv/bin/python3 merge_llm_analysis.py --dry-run llm_output.json
```

### Validation and Health Checks

Check system health before running pipelines:

```bash
# Check email MCP server
venv/bin/python3 fetch_emails.py --check

# Check LinkedIn MCP server
venv/bin/python3 fetch_linkedin_mcp.py --check

# Check OpenRouter API key
venv/bin/python3 api_keys.py --check

# Check persona file health
venv/bin/python3 validate_personas.py --health
```

---

## Reference Files

Documentation files used by scripts.

| File | Purpose |
|------|----------|
| `calibration.md` | Tone scoring anchor examples (1-10 scales) |
| `batch_schema.md` | Analysis format specification |
| `analysis_schema.md` | Persona output schema |
| `output_template.md` | Final prompt template |
| `email_persona_schema_v2.md` | Email persona v2 schema with voice fingerprint, relationship calibration, guardrails |
| `linkedin_persona_schema_v2.md` | LinkedIn persona v2 schema with guardrails, variation controls, negative examples |

---

## Best Practices

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
