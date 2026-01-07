# Writing Style Clone — Team Guide

## What Is This?

**Writing Style Clone** is a skill that teaches AI to write like *you*.

Instead of getting generic AI-generated text, you'll have a personalized writing assistant that matches your actual voice across different contexts—whether you're sending an all-hands email, coaching a direct report, or posting on LinkedIn.

> 🖼️ **See the full workflow:** Open [workflow_diagram.html](workflow_diagram.html) in your browser.

---

## Why Use It?

| The Problem | The Solution |
|-------------|--------------|
| AI writing sounds generic and robotic | AI learns *your* specific patterns and phrases |
| You write differently for different audiences | AI recognizes your distinct "personas" and switches between them |
| Editing AI output to sound like you takes forever | AI gets it right the first time |

---

## What You'll Get

After ~30 minutes of setup, you'll have a **personalized writing assistant prompt** that:

- Knows your greeting and sign-off patterns
- Matches your tone (formal vs. casual)
- Uses your actual phrases and vocabulary
- Understands when to be brief vs. detailed
- Switches voice based on context (team email vs. 1:1 vs. LinkedIn)

---

## How It Works

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   SETUP     │  →   │   ANALYZE   │  →   │  GENERATE   │
│  (5 min)    │      │  (15 min)   │      │  (5 min)    │
│             │      │             │      │             │
│ Install the │      │ AI reads    │      │ AI creates  │
│ skill       │      │ your emails │      │ your custom │
│             │      │ & LinkedIn  │      │ prompt      │
└─────────────┘      └─────────────┘      └─────────────┘
       ↓                    ↓                    ↓
   New chat             New chat             New chat
```

**Key point:** Start a **new conversation** for each phase. This keeps things fast.

---

## Time Investment

| Phase | Time | What Happens |
|-------|------|--------------|
| Setup | 5 min | Install skill, create workspace |
| Analysis | 15-20 min | Analyze 3-5 batches of your writing |
| Generation | 5 min | Create your personalized prompt |

**Total: ~30 minutes**

---

## What You'll Need

- [ ] **Claude** (claude.ai or Claude Desktop)
- [ ] **The skill installed** (ask John for the .skill file)
- [ ] **Gmail access** via MCP (for email analysis)
- [ ] **LinkedIn access** via MCP (optional)
- [ ] **30 minutes** of focused time

---

## Getting Started

### Step 1: Install the Skill

1. Get the `writing-style-clone.skill` file from John
2. Install it in Claude (drag & drop or use settings)
3. The skill is now available in all your conversations

### Step 2: Run Each Phase

**Phase 1 — Setup** (new conversation)
```
Clone my writing style
```
Claude creates your workspace and saves state. When done:
> "Setup complete! Start a NEW conversation to begin analysis."

**Phase 2 — Analysis** (new conversation)
```
Continue cloning my writing style
```
Claude fetches and analyzes your emails in batches. Run multiple batches until you have 50+ samples. When done:
> "Analysis complete! Start a NEW conversation to generate your assistant."

**Phase 3 — Generation** (new conversation)
```
Generate my writing assistant
```
Claude creates your personalized prompt and saves it.

### Step 3: Use Your Writing Assistant

Your prompt is saved at:
```
~/Documents/my-writing-style/prompts/writing_assistant.md
```

Create a new assistant in your preferred AI tool using this prompt, or just paste it when you need help writing.

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

## Privacy & Security

- ✅ Your emails are analyzed **locally** on your machine
- ✅ Only style patterns are saved, not full email contents
- ✅ Your personal data folder is **never uploaded** anywhere
- ✅ The analysis stays on your computer

---

## Maintenance

| When | What to Do |
|------|------------|
| Monthly | Run 1-2 analysis batches to capture style evolution |
| Quarterly | Regenerate your writing assistant prompt |
| As needed | Merge duplicate personas if discovered |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No project found" | Start with "Clone my writing style" first |
| Stuck in wrong phase | Say "reset to [phase]" |
| Want to start over | Delete `~/Documents/my-writing-style/` and restart |

---

## Questions?

- **Slack:** Reach out to John Renaldi
- **GitHub:** `github.com/jrenaldi79/writing-style`

---

*Built by John Renaldi • January 2025*
