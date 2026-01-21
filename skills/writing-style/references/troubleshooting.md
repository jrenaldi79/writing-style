# Troubleshooting Guide

Common issues and solutions for the writing-style pipeline.

---

## Setup and Installation Issues

### "No such file or directory" for scripts

**Cause:** Scripts location varies based on how repo was downloaded/extracted.

**Fix:** Use dynamic path finding

```bash
# Find where scripts actually are
find ~/Documents/writing-style -name "fetch_emails.py" -exec dirname {} \;

# Then copy from discovered location
cp /path/from/above/*.py ~/Documents/my-writing-style/
```

**Common locations:**
- `~/Documents/writing-style/writing-style-main/skills/writing-style/scripts/`
- `~/Documents/writing-style/skills/writing-style/scripts/`

**Prevention:** Use the dynamic setup command in Session 1 which auto-locates scripts.

### "Missing dependencies"

**Cause:** Python packages not installed in virtual environment.

**Fix:**

```bash
cd ~/Documents/writing-style
venv/bin/python3 -m pip install -r requirements.txt
```

**Note:** The `requirements.txt` is in the skill directory (`~/skills/writing-style/requirements.txt`)

**Required packages:**
- sentence-transformers
- scikit-learn
- numpy
- hdbscan
- pandas
- openai (for OpenRouter API)

---

## Windows Setup Issues

### Pre-flight Check

Before running the pipeline on Windows, use the preflight check:

```powershell
python preflight_check.py
```

This validates Python version, npx availability, and data directory access.

### "ModuleNotFoundError: No module named 'config'"

**Cause:** Windows handles Python module paths differently. Local imports fail without sys.path fix.

**Fix:** All scripts now include automatic path configuration. If you have an older version:

```python
# Add at top of script (after imports like sys, pathlib)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### "'npx' is not recognized as an internal or external command"

**Cause:** Node.js not installed or not in PATH.

**Fix:**

1. Install Node.js from https://nodejs.org (LTS version recommended)
2. Restart your terminal/PowerShell after installation
3. Verify with: `npx --version`

**Note:** On Windows, `npx.cmd` is used automatically by the scripts.

### "UnicodeEncodeError" or garbled console output

**Cause:** Windows console doesn't support UTF-8 emojis by default.

**Fix:** Scripts now use ASCII-only output. If you see this error with an older version:

1. Update to latest version (emojis replaced with ASCII like `[OK]`, `[ERROR]`)
2. Or set UTF-8 in PowerShell: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

### Python not found or wrong version

**Cause:** Python not installed or using system Python.

**Fix:**

1. Install Python 3.10+ from https://www.python.org/downloads/
2. Check "Add Python to PATH" during installation
3. Create virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Permission errors with data directory

**Cause:** Cannot create/write to default data directory.

**Fix:** Set custom data location via environment variable:

```powershell
$env:WRITING_STYLE_DATA = "C:\Users\YourName\writing-style-data"
```

Or add to your PowerShell profile for persistence.

---

## State Management Issues

### "State not found"

**Cause:** `state.json` was not initialized.

**Fix:**

```bash
cd ~/Documents/my-writing-style
python3 -c 'from state_manager import init_state; init_state(".")'
```

**Alternative:** Run any pipeline script - state will auto-initialize.

### "State shows wrong phase"

**Cause:** Previous session didn't complete properly.

**Fix:** Check what actually exists:

```bash
# Check what files exist
ls ~/Documents/my-writing-style/

# Reset to correct phase if needed
# Edit state.json manually or re-run the last successful script
```

---

## Email Pipeline Issues

### "MCP server not found" or "Authentication required"

**Cause:** Google Workspace MCP server not installed or authenticated.

**Verify:**

```bash
python3 fetch_emails.py --check
```

**Fix (ChatWise one-click install):**

```
https://chatwise.app/mcp-add?json=ew0KICAibWNwU2VydmVycyI6IHsNCiAgICAiZ29vZ2xlLXdvcmtzcGFjZSI6IHsNCiAgICAgICJjb21tYW5kIjogIm5weCIsDQogICAgICAiYXJncyI6IFsNCiAgICAgICAgIi15IiwNCiAgICAgICAgIkBwcmVzdG8tYWkvZ29vZ2xlLXdvcmtzcGFjZS1tY3AiDQogICAgICBdDQogICAgfQ0KICB9DQp9
```

**Fix (Manual):** Add `@presto-ai/google-workspace-mcp` to your chat client's MCP config.

**After installing:** Authenticate with Google when prompted.

### "No clusters found"

**Cause 1:** `filter_emails.py` rejected too many emails.

**Fix:** Lower quality thresholds or fetch more emails:

```bash
# Check how many emails survived filtering
ls filtered_samples/*.json | wc -l

# If too few, adjust filter thresholds or fetch more
venv/bin/python3 fetch_emails.py --count 500
```

**Cause 2:** Not enough quality emails for clustering (need 50+ minimum).

**Fix:** Fetch more emails:

```bash
venv/bin/python3 fetch_emails.py --count 500
```

### "Persona scores inconsistent"

**Cause:** Not using calibrated scoring reference.

**Fix:** Always reference `calibration.md` anchor examples:

```bash
# Read calibration before each analysis session
cat references/calibration.md
```

**Best practice:** Use same calibration across all batches for consistency.

### "prepare_batch.py doesn't create JSON file"

**This is expected behavior!**

`prepare_batch.py` outputs to **console/stdout**, not to a file. The LLM/agent must:

1. Read the console output
2. Analyze the emails
3. Create `batches/batch_NNN.json` manually

**See:** Session 2 documentation for the required JSON schema ([email_workflow.md](email_workflow.md))

---

## LinkedIn Pipeline Issues

### "MCP_TOKEN not set" or "BrightData API failed"

**Cause:** BrightData MCP server or API token not configured.

**Verify:**

```bash
python3 fetch_linkedin_mcp.py --check
```

**Fix:**

1. **Get token:** Sign up at https://brightdata.com/cp/start
2. **Install BrightData MCP (ChatWise):**
   ```
   https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0=
   ```
   Replace `YOUR_BRIGHTDATA_TOKEN` with your actual token!

3. **Set MCP_TOKEN in terminal tool:**

   If using desktop-commander (ChatWise):
   ```
   https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImRlc2t0b3AtY29tbWFuZGVyIjogewogICAgICAiY29tbWFuZCI6ICJucHgiLAogICAgICAiYXJncyI6IFsiLXkiLCAiQHdvbmRlcndoeS1lci9kZXNrdG9wLWNvbW1hbmRlciJdLAogICAgICAiZW52IjogewogICAgICAgICJNQ1BfVE9LRU4iOiAiWU9VUl9CUklHSFREQVRBX1RPS0VOIgogICAgICB9CiAgICB9CiAgfQp9
   ```

   **Alternative:** Add to `~/.bashrc` or `~/.zshrc`:
   ```bash
   export MCP_TOKEN="your-brightdata-api-token"
   ```

**Note:** Both the BrightData MCP AND the terminal tool need the token configured.

### "LinkedIn returns empty"

**Cause 1:** Profile not public.

**Fix:** Ensure LinkedIn profile is set to public visibility.

**Cause 2:** Not enough quality posts (need 10+ posts with 200+ chars each).

**Fix:**
- Publish more substantial content on LinkedIn
- Lower the character threshold in `filter_linkedin.py`

**Cause 3:** Fetching wrong person (common names).

**Fix:** Always provide full profile URL:

```bash
# GOOD - Full URL ensures correct person
venv/bin/python3 fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username"

# BAD - Ambiguous, may fetch wrong profile
venv/bin/python3 fetch_linkedin_mcp.py --profile "username"
```

**See:** [linkedin_workflow.md](linkedin_workflow.md#linkedin-search-strategies-critical) for search best practices.

---

## Validation Issues

### "Validation pairs empty"

**Cause:** No held-out emails exist (didn't use `--holdout` flag).

**Fix:** Re-fetch emails with holdout:

```bash
venv/bin/python3 fetch_emails.py --count 300 --holdout 0.15
```

**Note:** This will create a separate `validation_set/` directory with 15% of emails.

### "OpenRouter API key not found"

**Cause:** OPENROUTER_API_KEY environment variable not set.

**Check:**

```bash
venv/bin/python3 api_keys.py --check
venv/bin/python3 api_keys.py --source
```

**Fix:** Set API key in environment or ChatWise:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

**ChatWise users:** Use ChatWise environment variables feature.

---

## Generation Issues

### "generate_skill.py can't find data"

**Cause:** Required persona files don't exist.

**Check what data is available:**

```bash
python3 generate_skill.py --status
```

**Required files:**
- `persona_registry.json` (from email pipeline via `ingest.py`)
- OR `linkedin_persona.json` (from LinkedIn pipeline via `cluster_linkedin.py`)

**Fix:** Complete at least one pipeline:

```bash
# For email personas
venv/bin/python3 ingest.py batches/batch_NNN.json

# For LinkedIn persona
venv/bin/python3 cluster_linkedin.py
```

**Note:** At least one of email personas or LinkedIn voice is required.

---

## Performance Issues

### "Clustering takes too long"

**Cause:** Too many emails for HDBSCAN algorithm.

**Solutions:**

1. **Use sampling:** Process subset of emails
   ```bash
   # Sample 200 random emails
   ls enriched_samples/*.json | sort -R | head -200 | xargs -I {} cp {} sampled/
   ```

2. **Switch algorithm:** Use faster k-means (less accurate)
   ```bash
   # Edit cluster_emails.py to use kmeans instead of hdbscan
   ```

### "OpenRouter API calls too expensive"

**Cause:** Using expensive model or analyzing too many clusters.

**Solutions:**

1. **Preview cost first:**
   ```bash
   venv/bin/python3 analyze_clusters.py --dry-run
   ```

2. **Use cheaper model:**
   ```bash
   venv/bin/python3 validate_personas.py --list-models
   venv/bin/python3 validate_personas.py --set-model "anthropic/claude-3-haiku"
   ```

3. **Reduce sample size:** Use fewer representative emails per cluster.

---

## Data Quality Issues

### "Too many personas discovered"

**Expected:** 3-7 email personas, 1 LinkedIn persona.

**If too many (>10):**
- Increase minimum cluster size in `cluster_emails.py`
- Filter more aggressively in `filter_emails.py`
- Check for noise emails (automated messages, spam)

**If too few (<3):**
- Decrease minimum cluster size
- Ensure diverse email corpus (different recipients, contexts)
- Check that filtering isn't too aggressive

### "Personas don't match actual writing"

**Cause:** Poor calibration or validation skipped.

**Fix:**

1. **Run validation workflow:**
   ```bash
   venv/bin/python3 prepare_validation.py
   venv/bin/python3 validate_personas.py --auto
   venv/bin/python3 validate_personas.py --review
   ```

2. **Use calibration anchors:** Always reference `calibration.md` during analysis

3. **Provide feedback:** Use `--feedback` to record corrections:
   ```bash
   venv/bin/python3 validate_personas.py --feedback <pair_id> "accept"
   venv/bin/python3 validate_personas.py --feedback <pair_id> "reject"
   ```

4. **Get suggestions:** View recommended refinements:
   ```bash
   venv/bin/python3 validate_personas.py --suggestions
   ```

---

## Getting Help

### Diagnostic Commands

Run these to gather information before asking for help:

```bash
# Check system status
venv/bin/python3 fetch_emails.py --check
venv/bin/python3 fetch_linkedin_mcp.py --check
venv/bin/python3 api_keys.py --check
venv/bin/python3 api_keys.py --source

# Check data state
cat ~/Documents/my-writing-style/state.json
ls -la ~/Documents/my-writing-style/

# Check persona health
venv/bin/python3 validate_personas.py --health

# Check generation readiness
python3 generate_skill.py --status
```

### Log Files

Check logs for detailed error messages:

```bash
# Most scripts write to stdout/stderr
# Redirect to file if needed
venv/bin/python3 cluster_emails.py 2>&1 | tee cluster.log
```

### Additional Resources

- **README.md** - Complete project overview
- **CHANGELOG.md** - Version history and breaking changes
- **index.html** - User guide with clickable workflows
- **tests/** - Unit and integration tests for validation
