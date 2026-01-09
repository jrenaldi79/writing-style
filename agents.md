# Project: Writing Style Clone (v3.3)

> **⚠️ SYNC MANDATE**: `claude.md` and `agents.md` are duplicate manifests used by different AI coding agents. Any change to project logic, directory structure, or skill architecture **MUST** result in an update to **BOTH** files simultaneously.

## Project Compliance
- This project follows the **Anthropic Agent Skills** format.
- Always maintain strict compliance with the specification at: **https://agentskills.io/specification**

## Architecture & Logic
- **Nature:** Dual-pipeline (Email + LinkedIn) writing voice cloning.
- **Workflow:** Multi-session (Preprocessing → Analysis → LinkedIn → Generation).
- **Environment:** Isolated `venv/` for all Python 3.8+ dependencies.
- **State:** Persistent tracking via `state_manager.py` into `state.json`.
- **MCP Pattern:** Scripts use internal `MCPClient` for token-efficient tool execution.

## Directory Structure
```text
.
├── agents.md                   # Agent manifest (Sync with claude.md)
├── claude.md                   # Agent manifest (Sync with agents.md)
├── CHANGELOG.md                # Version history
├── README.md                   # Technical overview
├── system_prompt.md            # Generic Skills System Prompt (copy to ChatWise)
├── BOOTSTRAP.md                # Quick start user prompt for skill setup
├── SYSTEM_PROMPT.md            # DEPRECATED - see system_prompt.md
├── requirements.txt            # Python dependencies
├── index.html                  # User guide & dashboard
├── skills/                     # Agent Skills Specification root
│   └── writing-style/
│       ├── SKILL.md            # Skill entry point & workflow
│       ├── references/         # Progressive disclosure docs
│       │   ├── analysis_schema.md
│       │   ├── batch_schema.md
│       │   ├── calibration.md
│       │   ├── linkedin_persona_schema_v2.md
│       │   └── output_template.md
│       └── scripts/            # Core Python logic
│           ├── analysis_utils.py
│           ├── cluster_emails.py
│           ├── config.py
│           ├── cluster_linkedin.py
│           ├── embed_emails.py
│           ├── enrich_emails.py
│           ├── fetch_emails.py
│           ├── fetch_linkedin_mcp.py
│           ├── filter_emails.py
│           ├── filter_linkedin.py
│           ├── generate_system_prompt.py
│           ├── ingest.py
│           ├── prepare_batch.py
│           ├── state_manager.py
│           └── style_manager.py
└── tests/                      # Validation suite
    ├── README.md
    ├── run_tests.py
    └── test_*.py               # Unit and integration tests
```

## Configuration

### Custom Data Directory
By default, data is stored in `~/Documents/my-writing-style`.

To use a custom location, set the environment variable:
```bash
export WRITING_STYLE_DATA="/path/to/custom/data"
```

All scripts will automatically use this path.

## Build & Run Commands
Use `venv/bin/python3` (or `venv\Scripts\python.exe` on Windows).

### 1. Setup & Preprocessing
```bash
# Setup env
python3 -m venv venv && venv/bin/python3 -m pip install -r requirements.txt
# Email pipeline
venv/bin/python3 fetch_emails.py --count 200 && venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py && venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
```

### 2. Analysis & LinkedIn
```bash
# Email analysis
venv/bin/python3 prepare_batch.py && venv/bin/python3 ingest.py batches/batch_NNN.json
# LinkedIn pipeline
venv/bin/python3 fetch_linkedin_mcp.py --profile "URL" && venv/bin/python3 filter_linkedin.py
venv/bin/python3 cluster_linkedin.py
```

### 3. Generation & Testing
```bash
# Final synthesis
venv/bin/python3 generate_system_prompt.py
# Testing
cd tests && ../venv/bin/python3 run_tests.py
```

## Style Guidelines
- **Paths:** Always use OS-agnostic `pathlib`.
- **Validation:** User-interactive verification required for profile data.
- **Privacy:** Intermediate data remains local; only patterns are saved to personas.
