# Project: Writing Style Clone (v3.6)

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
- **v3.6 Analysis:** Hybrid approach - deterministic metrics (Python) + semantic fields (LLM via OpenRouter).
- **v3.6 Schema:** Email persona v2.0 with voice fingerprint, relationship calibration, instruction siblings.

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
├── package_skill.sh            # NEW v3.6: Skill packaging automation script
├── PACKAGING_GUIDE.md          # NEW v3.6: Distribution & installation guide
├── skills/                     # Agent Skills Specification root
│   └── writing-style/
│       ├── SKILL.md            # Skill entry point & workflow
│       ├── references/         # Progressive disclosure docs
│       │   ├── analysis_schema.md
│       │   ├── architecture.md             # NEW v3.6: System design & best practices
│       │   ├── batch_schema.md
│       │   ├── calibration.md
│       │   ├── data_schemas.md             # NEW v3.6: All schema specifications
│       │   ├── email_persona_schema_v2.md
│       │   ├── email_workflow.md           # NEW v3.6: Email pipeline detailed workflow
│       │   ├── linkedin_persona_schema_v2.md
│       │   ├── linkedin_workflow.md        # NEW v3.6: LinkedIn pipeline workflow
│       │   ├── output_template.md
│       │   ├── script_guide.md             # NEW v3.6: Complete script reference
│       │   └── troubleshooting.md          # NEW v3.6: Common issues & solutions
│       └── scripts/            # Core Python logic
│           ├── analysis_utils.py
│           ├── api_keys.py
│           ├── cluster_emails.py
│           ├── config.py
│           ├── cluster_linkedin.py
│           ├── embed_emails.py
│           ├── email_analysis_v2.py
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
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
venv/bin/python3 filter_emails.py
venv/bin/python3 enrich_emails.py && venv/bin/python3 embed_emails.py
venv/bin/python3 cluster_emails.py
```

### 2. Analysis (Session 2: Analyst)
```bash
# Estimate cost first (recommended)
venv/bin/python3 analyze_clusters.py --estimate

# Run parallel analysis (uses OpenRouter API)
venv/bin/python3 analyze_clusters.py

# Review draft results
venv/bin/python3 analyze_clusters.py --review

# Approve and ingest all clusters
venv/bin/python3 analyze_clusters.py --approve
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

## 🤖 LLM-Callable Script Design

**Scripts in this project are executed by LLMs via shell commands, NOT by humans interactively.**

This is a critical design constraint. All scripts must be fully automatable without human intervention during execution.

### ❌ Never Do This

```python
# BAD: Requires human at keyboard
response = input("Do you want to continue? (y/n): ")
choice = input("Select option (1-3): ")

# BAD: Interactive loops
while True:
    action = input("Next action: ")
    if action == "quit":
        break
```

### ✅ Always Do This

```python
# GOOD: CLI arguments for all inputs
parser.add_argument("--confirm", action="store_true")
parser.add_argument("--option", choices=["1", "2", "3"])

# GOOD: Separate commands for multi-step workflows
parser.add_argument("--review", action="store_true", help="Output data for review")
parser.add_argument("--feedback", metavar="ID", help="Record feedback for item")
parser.add_argument("--apply", action="store_true", help="Apply changes")
```

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **No stdin** | All inputs via CLI args or config files |
| **Structured output** | JSON for LLM consumption, human-readable summaries |
| **Idempotent operations** | Safe to re-run without side effects |
| **Atomic commands** | One action per invocation, chain via separate calls |
| **Clear exit codes** | 0 = success, non-zero = specific error types |

### Multi-Step Workflow Pattern

When a workflow requires user decisions (like reviewing and approving changes):

```bash
# Step 1: Generate review data (LLM reads output)
python script.py --review > review.json

# Step 2: LLM analyzes and decides, then records decisions
python script.py --approve item_001
python script.py --reject item_002 --reason "Not applicable"

# Step 3: Apply approved changes
python script.py --apply
```

### External LLM Calls for Blind Validation

When validation requires an LLM that hasn't seen the source data (to avoid context pollution):

```python
# GOOD: Use external API (OpenRouter) for blind validation
def generate_blind_reply(persona, context):
    # Call external LLM that never saw the training emails
    response = requests.post(OPENROUTER_API_URL, ...)
    return response.json()["choices"][0]["message"]["content"]
```

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

### Documentation Quality Standards

| Entity | Max Lines | Action If Exceeded |
|--------|-----------|-------------------|
| SKILL.md | 500 lines | **MANDATORY**: Split into reference files |
| Reference files | 1000 lines | Consider splitting further |
| No duplication | - | Information in ONE place only |

**SKILL.md Compliance Rules:**

1. **Progressive Disclosure Required:**
   - SKILL.md: Overview + navigation (max 500 lines)
   - `references/`: Detailed workflows and schemas

2. **No Schema Duplication:**
   - Schemas documented ONLY in `references/*_schema*.md`
   - SKILL.md: Brief summary + link

3. **Valid Frontmatter Only:**
   - Allowed fields: `name`, `description`, `compatibility`, `license`, `metadata`
   - No custom fields (e.g., `triggers`)

### Before Committing

1. ✅ Run all tests: `cd tests && ../venv/bin/python3 run_tests.py`
2. ✅ Check no regressions in existing functionality
3. ✅ Validate documentation compliance:
   ```bash
   # Check SKILL.md size
   [ $(wc -l < skills/writing-style/SKILL.md) -le 500 ] || echo "FAIL: SKILL.md exceeds 500 lines"

   # Check for invalid frontmatter
   ! grep -A 20 "^---$" skills/writing-style/SKILL.md | grep -q "^triggers:" || echo "FAIL: Invalid triggers field"

   # Check for schema duplication
   ! (grep -q "voice_fingerprint" skills/writing-style/SKILL.md && \
      grep -q "voice_fingerprint" skills/writing-style/references/email_persona_schema_v2.md) || \
   echo "FAIL: Schema duplication detected"
   ```
4. ✅ Update claude.md and agents.md if architecture changed (SYNC MANDATE)
5. ✅ Update SKILL.md if workflow changed (keep under 500 lines)
