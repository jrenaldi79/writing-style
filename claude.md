# Project: Writing Style Clone (v3.3)

> **⚠️ SYNC MANDATE**: `claude.md` and `agents.md` are duplicate manifests used by different AI coding agents. Any change to project logic, directory structure, or skill architecture **MUST** result in an update to **BOTH** files simultaneously.

## Project Compliance
- This project follows the **Anthropic Agent Skills** format.
- Always maintain strict compliance with the specification at: **https://agentskills.io/specification**

## Architecture & Logic
- **Nature:** Dual-pipeline (Email + LinkedIn) writing voice cloning.
- **Workflow:** Multi-session (Preprocessing → Analysis → Validation → LinkedIn → Generation).
- **Environment:** Isolated `venv/` for all Python 3.8+ dependencies.
- **State:** Persistent tracking via `state_manager.py` into `state.json`.
- **MCP Pattern:** Scripts use internal `MCPClient` for token-efficient tool execution.
- **Validation:** Blind testing against 15% held-out emails for persona accuracy.

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
│           ├── generate_skill.py
│           ├── ingest.py
│           ├── prepare_batch.py
│           ├── prepare_validation.py
│           ├── validate_personas.py
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

### 1. Setup & Preprocessing (Session 1: Architect)
```bash
# Setup env
python3 -m venv venv && venv/bin/python3 -m pip install -r requirements.txt
# Email pipeline with holdout for validation
venv/bin/python3 fetch_emails.py --count 200 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py && venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
```

### 2. Analysis (Session 2: Analyst)
```bash
# Email analysis (repeat for each cluster)
venv/bin/python3 prepare_batch.py && venv/bin/python3 ingest.py batches/batch_NNN.json
```

### 3. Validation (Session 2b: Judge) - Recommended
```bash
# Blind test against held-out emails
venv/bin/python3 prepare_validation.py
venv/bin/python3 validate_personas.py --auto
```

### 4. LinkedIn (Session 3) - Optional
```bash
venv/bin/python3 fetch_linkedin_mcp.py --profile "URL" && venv/bin/python3 filter_linkedin.py
venv/bin/python3 cluster_linkedin.py
```

### 5. Generation & Testing (Session 4)
```bash
# Generate installable skill package
venv/bin/python3 generate_skill.py --name <your-name>
# Testing
cd tests && ../venv/bin/python3 run_tests.py
```

## Style Guidelines
- **Paths:** Always use OS-agnostic `pathlib`.
- **Validation:** User-interactive verification required for profile data.
- **Privacy:** Intermediate data remains local; only patterns are saved to personas.

---

## 🚨 Mandatory TDD Process

**Every significant feature or script change MUST follow Test-Driven Development.**

### TDD Cycle

1. **Red Phase** (REQUIRED FIRST STEP):
   - Write failing tests in `tests/` defining expected behavior
   - Run tests to confirm failure: `venv/bin/python3 tests/run_tests.py`
   - This validates that your test actually tests something

2. **Green Phase**:
   - Implement simplest code to make tests pass
   - Focus on making it work, not making it optimal

3. **Refactor Phase**:
   - Clean up implementation
   - Ensure tests still pass
   - Improve both implementation AND test code

### TDD Enforcement

**Do NOT start implementing `scripts/` changes before tests exist and fail.**

Before writing ANY implementation code:
1. ✅ Explicitly state: "Following TDD - writing tests first"
2. ✅ Create test file in `tests/` directory (e.g., `test_new_feature.py`)
3. ✅ Write failing tests that define expected behavior
4. ✅ Run tests and show RED output proving tests fail
5. ✅ Only then write implementation
6. ✅ Run tests again and show GREEN output proving tests pass

### Test Commands

```bash
# Run all tests
cd tests && ../venv/bin/python3 run_tests.py

# Run specific test file
../venv/bin/python3 -m pytest test_filter_emails.py -v

# Run tests matching pattern
../venv/bin/python3 -m pytest -k "cluster" -v
```

### When TDD Applies

| Change Type | TDD Required? |
|------------|---------------|
| New script | ✅ Yes |
| New function in existing script | ✅ Yes |
| Bug fix | ✅ Yes (write test that reproduces bug first) |
| Refactoring | ✅ Yes (ensure existing tests pass) |
| Documentation only | ❌ No |
| Config changes | ❌ No |

---

## 📊 Code Quality Standards

### File Size Limits

| Entity | Max Lines | Action If Exceeded |
|--------|-----------|-------------------|
| Any script | 500 lines | Consider splitting |
| Any function | 50 lines | Break into smaller functions |

### Before Committing

1. ✅ Run all tests: `cd tests && ../venv/bin/python3 run_tests.py`
2. ✅ Check no regressions in existing functionality
3. ✅ Update CLAUDE.md and agents.md if architecture changed
4. ✅ Update SKILL.md if workflow changed
