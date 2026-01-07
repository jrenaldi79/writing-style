# Writing Style Clone — Team Guide

## What Is This?

**Writing Style Clone** is a skill that teaches AI to write like *you*.

Instead of getting generic AI-generated text, you'll have a personalized writing assistant that matches your actual voice across different contexts—whether you're sending an all-hands email, coaching a direct report, or posting on LinkedIn.

> 🖼️ **Visual guide:** Open [workflow_diagram.html](workflow_diagram.html) in your browser

---

## Why Use It?

| The Problem | The Solution |
|-------------|--------------|
| AI writing sounds generic and robotic | AI learns *your* specific patterns and phrases |
| You write differently for different audiences | AI recognizes your distinct "personas" and switches between them |
| Editing AI output to sound like you takes forever | AI gets it right the first time |

---

## What You'll Get

After ~30 minutes, you'll have a **personalized writing assistant prompt** that:

- Knows your greeting and sign-off patterns
- Matches your tone (formal vs. casual)
- Uses your actual phrases and vocabulary
- Understands when to be brief vs. detailed
- Switches voice based on context (team email vs. 1:1 vs. LinkedIn)

---

## Quick Start (5 minutes to install)

### 1. Clone the Repository

Open Terminal and run:
```bash
cd ~/Documents
git clone https://github.com/jrenaldi79/writing-style.git
```

### 2. Create the ChatWise Assistant

1. Open **ChatWise**
2. Go to **Assistants** → **Create New Assistant**
3. Name it: **"Writing Style Clone"**
4. Open this file and copy its contents as the system prompt:
   ```
   ~/Documents/writing-style/CHATWISE_PROMPT.md
   ```
5. Save the assistant

### 3. Start Cloning Your Style

Open a chat with your new assistant and say:
```
Clone my writing style
```

That's it! Follow the prompts from there.

---

## The Three Phases

The skill runs in three phases. **Start a new conversation for each phase** to keep things fast.

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   SETUP     │  →   │   ANALYZE   │  →   │  GENERATE   │
│  (5 min)    │      │  (15 min)   │      │  (5 min)    │
│             │      │             │      │             │
│ "Clone my   │      │ "Continue   │      │ "Generate   │
│  writing    │      │  cloning    │      │  my writing │
│  style"     │      │  my style"  │      │  assistant" │
└─────────────┘      └─────────────┘      └─────────────┘
       ↓                    ↓                    ↓
   New chat             New chat             New chat
```

### Phase 1: Setup
**Trigger:** "Clone my writing style"

Creates your personal workspace at `~/Documents/my-writing-style/`

### Phase 2: Analysis  
**Trigger:** "Continue cloning my writing style"

Fetches your emails and LinkedIn posts in batches, discovers your writing patterns, and clusters them into personas. Run multiple batches until you have 50+ samples.

**Useful commands:**
- "Fetch my last 20 emails and analyze"
- "Fetch my last 5 LinkedIn posts and analyze"
- "Show persona summary"
- "I'm ready to generate"

### Phase 3: Generation
**Trigger:** "Generate my writing assistant"

Creates your personalized system prompt with all discovered personas.

---

## Your Output

After Phase 3, you'll have:

```
~/Documents/my-writing-style/prompts/writing_assistant.md
```

This is your personalized writing assistant prompt. Use it:
- Create a new ChatWise assistant with it as the system prompt
- Paste it into ChatGPT, Claude, or any AI
- Save it for whenever you need help writing

---

## Example: Before vs. After

### Before (Generic AI)
> Dear Team,
>
> I hope this email finds you well. I wanted to reach out regarding our upcoming project timeline. Please let me know if you have any questions.
>
> Best regards

### After (Your Voice)
> Team,
>
> Quick update on Q2 priorities. We're shifting focus to the customer dashboard—I'll share the full roadmap in Thursday's all-hands.
>
> Three things I need by EOD Wednesday: [...]
>
> Appreciate you all pushing hard on this. Let's sync Thursday.
>
> -John

---

## Time Investment

| Phase | Time | Frequency |
|-------|------|-----------|
| Installation | 5 min | Once |
| Setup | 2 min | Once |
| Analysis | 15-20 min | Once (repeat monthly) |
| Generation | 5 min | Quarterly |

**Total: ~30 minutes** for initial setup

---

## Prerequisites

- [ ] **ChatWise** installed
- [ ] **Git** installed (for cloning the repo)
- [ ] **Gmail MCP** configured in ChatWise
- [ ] **LinkedIn MCP** configured (optional)

---

## Privacy & Security

- ✅ Everything runs **locally** on your machine
- ✅ Only style patterns are saved, not full email contents
- ✅ Your data folder is **never uploaded** anywhere
- ✅ The repo contains only the skill code, not your data

---

## Maintenance

| When | What to Do |
|------|------------|
| Monthly | Run 1-2 analysis batches to capture style evolution |
| Quarterly | Regenerate your writing assistant prompt |
| As needed | `cd ~/Documents/writing-style && git pull` for updates |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Skill not found" | Make sure repo is at `~/Documents/writing-style/` |
| "No project found" | Start with "Clone my writing style" first |
| Wrong phase | Say "Check my writing style status" |
| Start over | Delete `~/Documents/my-writing-style/` and restart |

---

## File Structure

```
~/Documents/
├── writing-style/              # The skill (from GitHub)
│   ├── skill/
│   │   ├── SKILL.md           # Main instructions
│   │   ├── scripts/           # Python utilities
│   │   └── references/        # Analysis schemas
│   ├── CHATWISE_PROMPT.md     # System prompt to copy
│   ├── TEAM_GUIDE.md          # This file
│   └── INSTALL.md             # Installation details
│
└── my-writing-style/           # Your personal data (created by skill)
    ├── state.json             # Tracks your progress
    ├── persona_registry.json  # Your discovered personas
    ├── samples/               # Analyzed writing samples
    └── prompts/
        └── writing_assistant.md  # YOUR OUTPUT
```

---

## Questions?

- **Slack:** Reach out to John Renaldi
- **GitHub:** [github.com/jrenaldi79/writing-style](https://github.com/jrenaldi79/writing-style)
- **Issues:** File on GitHub

---

*Built by John Renaldi • January 2025*
