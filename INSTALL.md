# Installing Writing Style Clone

## Prerequisites

- **ChatWise** installed on your computer
- **Git** installed (to clone the repo)
- **Gmail MCP** configured in ChatWise (for email analysis)
- **LinkedIn MCP** configured in ChatWise (optional, for post analysis)

---

## Step 1: Clone the Repository

Open Terminal and run:

```bash
cd ~/Documents
git clone https://github.com/jrenaldi79/writing-style.git
```

This creates `~/Documents/writing-style/` with the skill files.

---

## Step 2: Create the ChatWise Assistant

1. Open **ChatWise**
2. Go to **Assistants** → **Create New Assistant**
3. Name it: **"Writing Style Clone"**
4. For the **System Prompt**, copy the entire contents of:
   ```
   ~/Documents/writing-style/CHATWISE_PROMPT.md
   ```
   Or copy from the repo: [CHATWISE_PROMPT.md](CHATWISE_PROMPT.md)

5. Save the assistant

---

## Step 3: Start Using It

1. Open a new chat with your **"Writing Style Clone"** assistant
2. Say: **"Clone my writing style"**
3. Follow Claude's instructions

**Important:** Start a **new conversation** for each phase:
- Phase 1: Setup → "Clone my writing style"
- Phase 2: Analysis → "Continue cloning my writing style"  
- Phase 3: Generation → "Generate my writing assistant"

---

## File Locations

After installation, you'll have:

| Location | Purpose |
|----------|---------|
| `~/Documents/writing-style/` | The skill (shared repo) |
| `~/Documents/my-writing-style/` | Your personal data (created during setup) |

---

## Updating the Skill

To get the latest version:

```bash
cd ~/Documents/writing-style
git pull origin main
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Skill not found" | Make sure you cloned to `~/Documents/writing-style/` |
| "Gmail MCP not available" | Configure Gmail in ChatWise settings |
| "Permission denied" | Check file permissions on the scripts |

---

## Next Steps

After installation, see [TEAM_GUIDE.md](TEAM_GUIDE.md) for detailed usage instructions.
