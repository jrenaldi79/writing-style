---
name: writing-style-clone
description: Analyze a user's emails and LinkedIn posts to discover their distinct writing personas, then generate a personalized system prompt that enables any LLM to replicate their authentic voice. Use when the user wants to clone their writing style, create a writing assistant that sounds like them, analyze their communication patterns, or generate a personalized writing prompt. Triggers on phrases like "clone my writing style", "analyze my writing", "create a writing assistant", or "how do I write".
---

# Writing Style Clone

Analyze writing samples to discover personas and generate a personalized writing assistant prompt.

## Workflow Overview

This skill operates in three phases across multiple conversations (to manage context window):

1. **Setup** → Create data directory, initialize config and state
2. **Analysis** → Fetch emails/LinkedIn in batches, cluster into personas
3. **Generation** → Synthesize patterns into final writing assistant prompt

Each phase should run in a **fresh conversation** to avoid context overflow.

## First Message Protocol

On every conversation start:

```python
import sys
from pathlib import Path

# Default location
DATA_DIR = Path.home() / "Documents" / "my-writing-style"

# Check if state exists to determine phase
state_file = DATA_DIR / "state.json"

if not state_file.exists():
    print("No existing project found. Starting Phase 1: Setup")
    # Proceed to Phase 1
else:
    import json
    with open(state_file) as f:
        state = json.load(f)
    
    phase = state.get("current_phase", "setup")
    print(f"Resuming project. Current phase: {phase}")
    # Route to appropriate phase
```

Ask user to confirm data directory path (offer default), then route to correct phase.

## Phase 1: Setup

**Goal:** Create workspace and initialize all required files.

### Steps

1. Create data directory structure:
```bash
mkdir -p ~/Documents/my-writing-style/{samples,prompts}
```

2. Copy scripts from skill to data directory:
```bash
cp [SKILL_PATH]/scripts/*.py ~/Documents/my-writing-style/
```

3. Initialize using style_manager:
```python
sys.path.insert(0, str(DATA_DIR))
from style_manager import init
init(str(DATA_DIR))
```

4. Create state.json:
```python
from state_manager import init_state
init_state(str(DATA_DIR))
```

5. Confirm setup complete, instruct user:
> "Setup complete! Your data directory is ready at `~/Documents/my-writing-style/`.
>
> **Next step:** Start a NEW conversation and say 'continue cloning my writing style' to begin analyzing your emails."

## Phase 2: Analysis

**Goal:** Fetch writing samples in batches, analyze patterns, cluster into personas.

### Batch Processing

- **Emails:** 20 per batch via Gmail MCP
- **LinkedIn:** 5 per batch via LinkedIn MCP

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
Samples processed: [N]
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
> **Next step:** Start a NEW conversation and say 'generate my writing assistant' to create your personalized prompt."

### Available Commands

| Command | Action |
|---------|--------|
| `Fetch my last 20 emails and analyze` | Fetch via Gmail MCP, run analysis |
| `Fetch my last 5 LinkedIn posts and analyze` | Fetch via LinkedIn MCP, run analysis |
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
> **To use it:** Create a new assistant in your preferred AI tool and paste the contents as the system prompt.
>
> **Tips:**
> - Specify persona: 'Write this in my Team Leader voice'
> - Or describe context: 'Draft an email to my direct report'
> - The assistant will ask if context is ambiguous"

## State Management

All state operations use `state_manager.py`. Key functions:

- `init_state(data_dir)` — Create initial state.json
- `get_current_phase()` — Returns: setup | analysis | generation | complete
- `update_analysis_progress(batches, samples)` — Track analysis progress
- `mark_ready_for_generation()` — Transition from analysis to generation
- `complete_generation(output_path)` — Mark workflow complete

## Maintenance

After initial setup, users can:

- **Monthly:** Run 1-2 analysis batches to capture style evolution
- **As needed:** Merge duplicate personas
- **Quarterly:** Regenerate writing_assistant.md with new patterns

To re-run generation: 
```python
from state_manager import reset_to_phase
reset_to_phase("generation")
```
