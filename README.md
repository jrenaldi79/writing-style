# Writing Style Clone

**Clone your writing voice so AI can write like you.**

This tool analyzes your emails and LinkedIn posts to discover your distinct writing personas, then generates a custom system prompt you can use with any AI.

---

> 📖 **New here?** Start with [TEAM_GUIDE.md](TEAM_GUIDE.md) for a human-friendly overview.
>
> 🖼️ **Visual learner?** Open [workflow_diagram.html](workflow_diagram.html) in your browser.

---

## Quick Start

**Copy everything below the line and paste it into ChatWise (or any LLM with file system access).**

The AI will guide you through setup and the entire process.

---

# PASTE EVERYTHING BELOW INTO YOUR LLM

---

## Writing Style Clone — Setup & Workflow Guide

You are helping me set up and run the Writing Style Clone project. This will analyze my writing to create a personalized AI writing assistant.

### Project Repository
**GitHub:** `https://github.com/jrenaldi79/writing-style`

### What You'll Help Me Do
1. **Setup** — Clone the repo and create my local workspace
2. **Analysis** — Fetch and analyze my emails/LinkedIn posts in batches
3. **Generation** — Create my personalized writing assistant prompt

Let's start with setup. After each phase, wait for my confirmation before proceeding.

---

## PHASE 1: SETUP

### Step 1.1: Clone the Repository

Clone the Writing Style Clone repo to my local machine:

```bash
cd ~/Documents
git clone https://github.com/jrenaldi79/writing-style.git
```

Confirm the following files exist:
- `writing-style/scripts/style_manager.py`
- `writing-style/scripts/analysis_utils.py`
- `writing-style/prompts/style_analyzer_prompt.md`
- `writing-style/prompts/style_generator_prompt.md`

### Step 1.2: Create My Data Directory

Create a personal data directory (separate from the repo) where my analysis will be stored:

```bash
mkdir -p ~/Documents/my-writing-style/{samples,prompts,scripts}
```

### Step 1.3: Copy Scripts to Data Directory

```bash
cp ~/Documents/writing-style/scripts/*.py ~/Documents/my-writing-style/scripts/
```

### Step 1.4: Initialize Configuration

Create `~/Documents/my-writing-style/config.json`:

```json
{
  "project_name": "My Writing Style Clone",
  "created_at": "[TODAY'S DATE]",
  "owner": "[MY NAME]",
  "repo_path": "~/Documents/writing-style",
  "sources": {
    "email": {"batch_size": 20},
    "linkedin": {"batch_size": 5}
  },
  "clustering": {
    "min_samples_for_persona": 3,
    "high_confidence_threshold": 0.80,
    "match_threshold_assign": 0.70,
    "match_threshold_review": 0.40
  }
}
```

### Step 1.5: Initialize Empty Registry

Create `~/Documents/my-writing-style/persona_registry.json`:

```json
{
  "version": 1,
  "last_updated": null,
  "total_samples": 0,
  "samples_by_source": {"email": 0, "linkedin": 0},
  "personas": [],
  "unassigned_samples": [],
  "merge_history": []
}
```

### Step 1.6: Verify Setup

Run this to confirm everything is working:

```python
import sys
sys.path.insert(0, "/Users/[USERNAME]/Documents/my-writing-style/scripts")
from style_manager import get_persona_summary
print(get_persona_summary())
```

Expected output: `"No personas discovered yet. Registry is empty."`

### Step 1.7: Setup Complete ✓

Tell me:
- ✅ Repo cloned successfully
- ✅ Data directory created at: `[PATH]`
- ✅ Config and registry initialized
- ✅ Python scripts verified

**Ask me:** "Setup complete! Ready to start Phase 2: Analysis? You'll need access to your Gmail and/or LinkedIn. Which would you like to start with?"

---

## PHASE 2: ANALYSIS

**Important:** For this phase, I need to create a new ChatWise assistant using the Style Analyzer system prompt.

### Step 2.1: Create the Style Analyzer Assistant

Guide me to:

1. Open ChatWise
2. Create a new Assistant called **"Style Analyzer"**
3. For the system prompt, use the contents of:
   ```
   ~/Documents/writing-style/prompts/style_analyzer_prompt.md
   ```
4. Read that file and show me the contents so I can copy them into ChatWise

### Step 2.2: Configure the Assistant

After I've created the assistant, tell me:

> "Great! Now open a new chat with your **Style Analyzer** assistant. In that chat, you'll run analysis batches. Here are the commands:"

**For Email Analysis (batches of 20):**
```
Initialize with data directory ~/Documents/my-writing-style, then fetch my last 20 sent emails and analyze them for writing style patterns.
```

**For LinkedIn Analysis (batches of 5):**
```
Initialize with data directory ~/Documents/my-writing-style, then fetch my last 5 LinkedIn posts and analyze them for writing style patterns.
```

### Step 2.3: What to Expect

After each batch, the Style Analyzer will:
- Show me discovered personas (e.g., "All-Hands Leader", "Direct Report Coach")
- Report sample counts and confidence levels
- Flag any ambiguous samples for review
- Save everything to my local `~/Documents/my-writing-style/` directory

### Step 2.4: Repeat Until Sufficient Data

Tell me:

> "Run multiple batches until you have:"
> - At least 50 total samples (ideally 100)
> - 3+ samples per persona
> - Coverage of your different writing contexts
>
> **Useful commands in the Style Analyzer:**
> - `Show persona summary` — See all discovered personas
> - `Show flagged samples` — Review ambiguous assignments  
> - `Merge persona_001 into persona_002` — Combine similar personas
>
> "Let me know when you've completed your analysis batches and are ready for Phase 3!"

---

## PHASE 3: GENERATION

**Important:** For this phase, I need to create another ChatWise assistant using the Style Generator system prompt.

### Step 3.1: Create the Style Generator Assistant

Guide me to:

1. Open ChatWise
2. Create a new Assistant called **"Style Generator"**
3. For the system prompt, use the contents of:
   ```
   ~/Documents/writing-style/prompts/style_generator_prompt.md
   ```
4. Read that file and show me the contents so I can copy them into ChatWise

### Step 3.2: Generate My Writing Assistant Prompt

After I've created the assistant, tell me:

> "Great! Now open a new chat with your **Style Generator** assistant. Run this command:"
>
> ```
> Using data from ~/Documents/my-writing-style, generate my personalized writing assistant system prompt.
> ```

### Step 3.3: What to Expect

The Style Generator will:
- Read all my persona data
- Identify patterns across my writing
- Create a comprehensive system prompt with:
  - My universal voice characteristics
  - Each persona with triggers, rules, and examples
  - Guidelines for when to use which voice
- Save the output to `~/Documents/my-writing-style/prompts/writing_assistant.md`

### Step 3.4: Create My Final Writing Assistant

Guide me to:

1. Open ChatWise
2. Create a new Assistant called **"[My Name]'s Writing Voice"** (or similar)
3. Use the contents of `~/Documents/my-writing-style/prompts/writing_assistant.md` as the system prompt
4. This is now my personalized writing assistant!

### Step 3.5: How to Use It

Tell me:

> "Your Writing Voice assistant is ready! Use it for:"
> - Drafting emails in your authentic voice
> - Writing LinkedIn posts that sound like you
> - Any writing where you want AI to match your style
>
> **Tips:**
> - Tell it which persona to use: "Write this as my Team Leader voice"
> - Or let it choose: "Draft an email to my direct report about the project delay"
> - It will ask for clarification if the context is ambiguous

---

## MAINTENANCE

Tell me about ongoing maintenance:

> **Monthly:** Run 1-2 batches of recent emails with the Style Analyzer to capture any evolution in your writing style.
>
> **As Needed:** Use `Merge persona_X into persona_Y` if you discover duplicate personas.
>
> **Quarterly:** Regenerate your `writing_assistant.md` with the Style Generator to incorporate new patterns, then update your Writing Voice assistant.

---

## TROUBLESHOOTING

If I encounter issues, help me with:

| Issue | Solution |
|-------|----------|
| "Module not found" | Verify scripts path in sys.path.insert() matches actual location |
| Personas seem wrong | Use `Show persona summary` and consider merging similar ones |
| Not enough samples | Run more analysis batches |
| Want to start over | Delete `persona_registry.json` and `samples/` folder contents |

---

## FILE STRUCTURE REFERENCE

```
~/Documents/
├── writing-style/              # Cloned repo (shared tools)
│   ├── scripts/
│   │   ├── style_manager.py
│   │   └── analysis_utils.py
│   ├── prompts/
│   │   ├── style_analyzer_prompt.md
│   │   └── style_generator_prompt.md
│   ├── README.md
│   └── workflow_diagram.svg
│
└── my-writing-style/           # Your personal data (private)
    ├── config.json
    ├── persona_registry.json
    ├── samples/
    │   ├── email_001.json
    │   ├── email_002.json
    │   └── ...
    ├── prompts/
    │   └── writing_assistant.md  # YOUR OUTPUT
    └── scripts/
        ├── style_manager.py
        └── analysis_utils.py
```

---

## BEGIN

Start by asking me: **"Ready to set up Writing Style Clone? I'll guide you through cloning the repo and creating your workspace. This takes about 5 minutes. Let's begin?"**

Then proceed with Phase 1, Step 1.1.
