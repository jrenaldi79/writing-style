# Writing Style Clone - Bootstrap

Use this prompt to start a new session with your AI assistant. Copy and paste it to begin.

---

## Quick Start Prompt

```
I want to work with the writing-style skill. Please run the bootstrap check:

# Check skill location (primary, then fallbacks)
SKILL_DIR=""
for dir in ~/skills/writing-style ~/.local/share/skills/writing-style ~/Documents/skills/writing-style; do
  [ -f "$dir/SKILL.md" ] && SKILL_DIR="$dir" && break
done

# Data directory (where outputs go)
DATA_DIR=~/Documents/my-writing-style

# Report status
echo "PLATFORM: $(uname -s || echo WINDOWS)"
echo "SKILL_DIR: ${SKILL_DIR:-NOT_FOUND}"
echo "DATA_DIR: $DATA_DIR"
[ -d "$DATA_DIR/venv" ] && echo "VENV: OK" || echo "VENV: MISSING"
[ -f "$DATA_DIR/state.json" ] && cat "$DATA_DIR/state.json" || echo "STATUS: NEW_PROJECT"

Then read the SKILL.md file and continue from my current state.
```

---

## Directory Structure

| Location | Purpose |
|----------|---------|
| `~/skills/writing-style/` | Skill code (SKILL.md, scripts, references) |
| `~/Documents/my-writing-style/` | Your data (outputs, state, venv) |

**Why separate?** Skills are read-only code; data is user-generated. This allows clean updates and uninstalls.

---

## Interpreting Results

| Output | Meaning | Action |
|--------|---------|--------|
| `STATUS: NEW_PROJECT` | First time user | Start with "Clone my email style" |
| `VENV: MISSING` | No Python environment | Setup will create it automatically |
| `current_phase: "preprocessing"` | Preprocessing done | Continue with "Continue email analysis" |
| `current_phase: "analysis"` | Analysis done | Run LinkedIn or "Generate my writing assistant" |
| `SKILL_DIR: NOT_FOUND` | Skill not installed | Install skill to `~/skills/writing-style/` |

---

## Skill Triggers

Once the skill is loaded, use these phrases:

- **"Clone my email style"** - Start email pipeline (Session 1)
- **"Continue email analysis"** - Resume after preprocessing (Session 2)
- **"Run LinkedIn Pipeline"** - Add LinkedIn voice (Session 3)
- **"Generate my writing assistant"** - Create final prompt (Session 4)
- **"Show project status"** - Check current state

---

## First-Time Setup

If this is your first time, the skill will automatically:

1. Create data directory at `~/Documents/my-writing-style/`
2. Copy scripts from the skill repository
3. Create Python virtual environment
4. Initialize state tracking

Just say **"Clone my email style"** and the skill handles the rest.

---

## Workflow Reference

Full workflow documentation: `~/skills/writing-style/SKILL.md`

The SKILL.md file contains:
- Complete session-by-session workflow
- Script documentation
- Troubleshooting guide
- Data schemas
