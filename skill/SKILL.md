---
name: writing-style-clone
description: Analyze a user's emails and LinkedIn posts to discover their distinct writing personas, then generate a personalized system prompt that enables any LLM to replicate their authentic voice. Use when the user wants to clone their writing style, create a writing assistant that sounds like them, analyze their communication patterns, or generate a personalized writing prompt. Triggers on phrases like "clone my writing style", "analyze my writing", "create a writing assistant", or "how do I write".
---

# Writing Style Clone

Analyze writing samples to discover personas and generate a personalized writing assistant prompt.

## Workflow Overview

This skill operates in three phases across multiple conversations (to manage context window):

1. **Setup** → Create data directory, download emails in bulk
2. **Analysis** → Analyze downloaded samples, cluster into personas
3. **Generation** → Synthesize patterns into final writing assistant prompt

Each phase should run in a **fresh conversation** to avoid context overflow.

## First Message Protocol

On every conversation start:

```python
from pathlib import Path

DATA_DIR = Path.home() / "Documents" / "my-writing-style"
state_file = DATA_DIR / "state.json"

if not state_file.exists():
    print("No existing project found. Starting Phase 1: Setup")
else:
    import json
    with open(state_file) as f:
        state = json.load(f)
    phase = state.get("current_phase", "setup")
    print(f"Resuming project. Current phase: {phase}")
```

Ask user to confirm, then route to correct phase.

## Phase 1: Setup

**Goal:** Create workspace, download emails in bulk.

### Steps

1. Create data directory structure:
```bash
mkdir -p ~/Documents/my-writing-style/{samples,prompts,raw_samples}
```

2. Copy scripts from skill to data directory:
```bash
cp ~/Documents/writing-style/skill/scripts/*.py ~/Documents/my-writing-style/
```

3. **Run the email fetcher** (this is the key efficiency gain):
```bash
cd ~/Documents/my-writing-style
python fetch_emails.py --count 50
```

This downloads 50 emails directly via MCP protocol WITHOUT using Claude's tokens.

4. Initialize state:
```python
import sys
sys.path.insert(0, str(Path.home() / "Documents" / "my-writing-style"))
from state_manager import init_state
init_state(str(DATA_DIR))
```

5. Confirm setup complete:
> "Setup complete! Downloaded [N] emails to `raw_samples/`.
>
> **Next step:** Start a NEW conversation and say 'Continue cloning my writing style' to analyze your emails."

## Phase 2: Analysis

**Goal:** Analyze downloaded samples, cluster into personas.

### Reading Raw Samples

Emails are pre-downloaded in `~/Documents/my-writing-style/raw_samples/`. Read them directly:

```python
from pathlib import Path
import json

raw_dir = Path.home() / "Documents" / "my-writing-style" / "raw_samples"
emails = list(raw_dir.glob("email_*.json"))
print(f"Found {len(emails)} emails to analyze")
```

### Batch Analysis

Process 10-15 emails per batch to stay within context limits:

```python
batch_size = 10
for i, email_file in enumerate(emails[:batch_size]):
    with open(email_file) as f:
        email = json.load(f)
    
    # Extract key fields
    subject = email.get("subject", "")
    body = email.get("body", email.get("snippet", ""))
    to = email.get("to", "")
    
    # Analyze using schema in references/analysis_schema.md
    # ... analysis logic ...
```

### For Each Sample

Extract analysis using schema in `references/analysis_schema.md`:
- Tone, formality, sentence length, paragraph style
- Punctuation patterns, contractions usage
- Greeting/closing patterns (email)
- Hook style, CTA patterns (LinkedIn)

### Clustering Logic

**Bootstrap mode (no personas yet):**
1. Analyze all samples in batch
2. Group by similarity (tone + formality + structure)
3. Create persona for each cluster of 3+ similar samples
4. Use specific names: "All-Hands Strategist" not "Formal Email"

**Update mode (personas exist):**
1. Score new samples against existing personas using `compute_similarity_score()`
2. Score ≥ 0.70 → Assign to persona
3. Score 0.40-0.70 → Flag for review, tentatively assign
4. Score < 0.40 all → Hold as unassigned
5. If 3+ unassigned cluster together → Create new persona

### After Each Batch

```python
from state_manager import update_analysis_progress
update_analysis_progress(batches_completed=N, total_samples=N)
```

Report:
```
════════════════════════════════════════
BATCH COMPLETE
════════════════════════════════════════
Samples analyzed: [N]
Personas: [list with sample counts and confidence]
Ready for generation: [Yes/No - need 50+ samples, 3+ per persona]
════════════════════════════════════════
```

### Completing Analysis

When user has sufficient data (50+ samples recommended):

```python
from state_manager import mark_ready_for_generation
mark_ready_for_generation()
```

> "Analysis complete! You have [N] samples across [N] personas.
>
> **Next step:** Start a NEW conversation and say 'Generate my writing assistant' to create your personalized prompt."

### Available Commands

| Command | Action |
|---------|--------|
| `Analyze next batch` | Process next 10 raw emails |
| `Show persona summary` | Print current persona state |
| `Show flagged samples` | List ambiguous assignments |
| `Merge [persona_A] into [persona_B]` | Combine personas |
| `I'm ready to generate` | Mark ready, prompt for new conversation |

## Phase 3: Generation

**Goal:** Synthesize all persona data into a production-ready writing assistant prompt.

### Steps

1. Load all data:
```python
from style_manager import init, export_for_prompt_generation
init(str(DATA_DIR))
data = export_for_prompt_generation()
```

2. Identify universal patterns across all personas (base voice)

3. For each persona, extract:
   - Trigger conditions (when to use)
   - Rules (patterns in >80% of samples)
   - Tendencies (patterns in 50-80%)
   - Best examples (2-3 excerpts)
   - Anti-patterns (what to avoid)

4. Generate markdown prompt following template in `references/output_template.md`

5. Save output:
```python
output_path = DATA_DIR / "prompts" / "writing_assistant.md"
with open(output_path, "w") as f:
    f.write(generated_prompt)
```

6. Update state:
```python
from state_manager import complete_generation
complete_generation(str(output_path))
```

7. Deliver to user:
> "Your personalized writing assistant is ready!
>
> **File:** `~/Documents/my-writing-style/prompts/writing_assistant.md`
>
> **To use it:** Create a new assistant in your preferred AI tool and paste the contents as the system prompt."

## State Management

All state operations use `state_manager.py`. Key functions:

- `init_state(data_dir)` — Create initial state.json
- `get_current_phase()` — Returns: setup | analysis | generation | complete
- `update_analysis_progress(batches, samples)` — Track analysis progress
- `mark_ready_for_generation()` — Transition from analysis to generation
- `complete_generation(output_path)` — Mark workflow complete

## Scripts

| Script | Purpose |
|--------|---------|
| `fetch_emails.py` | Bulk download emails via MCP (runs outside Claude) |
| `style_manager.py` | Persona and sample management |
| `state_manager.py` | Phase tracking across conversations |
| `analysis_utils.py` | Similarity scoring and clustering |

## Maintenance

After initial setup, users can:

- **Monthly:** Run `python fetch_emails.py --count 20` then analyze new batches
- **As needed:** Merge duplicate personas
- **Quarterly:** Regenerate writing_assistant.md with new patterns

To re-run generation: 
```python
from state_manager import reset_to_phase
reset_to_phase("generation")
```
