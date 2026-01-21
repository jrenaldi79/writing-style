# LinkedIn Pipeline Workflow

Complete workflow documentation for the LinkedIn analysis pipeline.

---

## Session 3: LinkedIn Processing (Optional)

**Purpose:** Build unified professional voice from LinkedIn posts.

---

## Data Captured from LinkedIn Posts (v3.3 Enhancement)

The LinkedIn pipeline captures **20+ fields per post** for rich persona development.

### Content Types Supported (v3.3)
- **Short-form posts** (`/posts/`): Regular LinkedIn updates
- **Long-form articles** (`/pulse/`): Blog-style articles you've published

### Core Content
- **Text**: Full post content (your actual words)
- **Headline**: Opening hook/summary
- **Post Type**: Original vs Repost/Share
- **Date**: When published
- **HTML Version**: Formatted text with links

### Engagement Signals (v3.3)
**Why this matters:** High-engagement posts = strongest voice examples

- **Likes/Comments Count**: Quantitative engagement (47 likes, 3 comments)
- **Top Comments**: Actual audience responses
  - **Reveals:** What resonates with your audience
  - **Shows:** How others perceive you (authority signals)
  - **Identifies:** Content gaps (questions people ask)

**Engagement-Weighted Analysis:** Posts with higher engagement influence tone vectors more heavily using log-scale weighting.

**Best Example Selection:** The few-shot example in the persona is automatically selected by highest engagement (likes), with length as tiebreaker.

### Network Context (v3.3)
**Why this matters:** Shows collaboration patterns and relationship style

- **Tagged People**: Who you mention/collaborate with
- **Tagged Companies**: Organizations you reference
- **Your Metrics**: Follower count, total posts, articles

### Repost Analysis (v3.3)
**Why this matters:** Separates your editorial voice from creation voice

When you share others' content:
- **Your Commentary**: What you add/emphasize
- **Original Content**: What you're amplifying
- **Attribution**: Who you credit
- **Network**: Tagged users/companies in original post

### Content Structure
- **Embedded Links**: External references you include
- **Images**: Visual content used
- **External Link Data**: Previews of shared URLs

### Authority Signals
- **Follower Count**: Your platform reach
- **Total Posts**: Publishing frequency
- **Articles**: Long-form vs short-form ratio

---

## How This Improves Persona Quality

**Before v3.3 (5 fields):**
- Could only analyze text content
- No idea what resonated
- Couldn't distinguish original vs curated
- Missing authority context

**After v3.3 (20+ fields):**
- ✅ Voice Validation: High-engagement posts weighted higher
- ✅ Content Balance: Know original vs curated ratio
- ✅ Editorial Voice: How you frame others' work
- ✅ Network Patterns: Collaboration style
- ✅ Authority Context: Platform engagement level
- ✅ Article Support: Long-form articles included
- ✅ Engagement Weighting: Log-scale prevents viral post domination

---

## LinkedIn Fetching (Automated)

**CRITICAL: Always provide full profile URL to avoid wrong-person errors!**

### Prerequisites

The LinkedIn pipeline requires the BrightData MCP server and an API token.

**Step 1: Get a BrightData API Token**
1. Sign up at: https://brightdata.com/cp/start
2. Navigate to API settings to get your token
3. Copy the token for the next steps

**Step 2: Install BrightData MCP Server (ChatWise one-click):**
```
https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImJyaWdodGRhdGEiOiB7CiAgICAgICJjb21tYW5kIjogIm5weCIsCiAgICAgICJhcmdzIjogWyJAYnJpZ2h0ZGF0YS9tY3AiXSwKICAgICAgImVudiI6IHsKICAgICAgICAiQVBJX1RPS0VOIjogIllPVVJfQlJJR0hUREFUQV9UT0tFTiIsCiAgICAgICAgIkdST1VQUyI6ICJhZHZhbmNlZF9zY3JhcGluZyxzb2NpYWwiCiAgICAgIH0KICAgIH0KICB9Cn0=
```

After clicking, replace `YOUR_BRIGHTDATA_TOKEN` with your actual token!

**Step 3: Set MCP_TOKEN in Terminal Tool**

If using desktop-commander (ChatWise):
```
https://chatwise.app/mcp-add?json=ewogICJtY3BTZXJ2ZXJzIjogewogICAgImRlc2t0b3AtY29tbWFuZGVyIjogewogICAgICAiY29tbWFuZCI6ICJucHgiLAogICAgICAiYXJncyI6IFsiLXkiLCAiQHdvbmRlcndoeS1lci9kZXNrdG9wLWNvbW1hbmRlciJdLAogICAgICAiZW52IjogewogICAgICAgICJNQ1BfVE9LRU4iOiAiWU9VUl9CUklHSFREQVRBX1RPS0VOIgogICAgICB9CiAgICB9CiAgfQp9
```

**Alternative:** Add to `~/.bashrc` or `~/.zshrc`:
```bash
export MCP_TOKEN="your-brightdata-api-token"
```

### Verify Setup & Fetch Posts

```bash
cd ~/Documents/my-writing-style

# Verify BrightData MCP is configured
venv/bin/python3 fetch_linkedin_direct.py --check

# Basic fetch (uses activity feed only)
venv/bin/python3 fetch_linkedin_direct.py --profile "https://linkedin.com/in/username" --limit 20

# Recommended: Auto-search for more posts if below threshold
venv/bin/python3 fetch_linkedin_direct.py --profile "username" --min-posts 15

# Manual search with custom queries
venv/bin/python3 fetch_linkedin_direct.py --profile "username" --search-queries "company,topic1,topic2"

# Filter quality posts (min 200 chars)
venv/bin/python3 filter_linkedin.py

# Generate unified persona (with quality warnings)
venv/bin/python3 cluster_linkedin.py
```

### Fetch Options

| Option | Description |
|--------|-------------|
| `--profile <url>` | LinkedIn profile URL or username (required) |
| `--limit <n>` | Max posts to fetch (default: 20) |
| `--min-posts <n>` | Auto-search if activity returns fewer than n posts |
| `--search-queries` | Comma-separated search terms (e.g., "jiobit,google") |
| `--search-engines` | google, bing, or both (default: google) |
| `--search-only` | Skip activity feed, use only search discovery |

### How It Works

1. **Direct API:** Uses BrightData's `web_data_linkedin_person_profile` API
2. **Activity Feed:** Extracts post URLs from profile activity (limited to ~10-20 recent items)
3. **Ownership Filter:** Only includes posts authored by the user (filters out likes/shares)
4. **Auto-Search Fallback:** If `--min-posts` set and activity < threshold, auto-generates search queries
5. **Smart Queries:** Extracts company names and keywords from profile for search
6. **Parallel Scraping:** Fetches posts in parallel (5 concurrent workers)
7. **Quality Warnings:** Alerts when post count is below recommended (15-20)

### Quality Thresholds

| Post Count | Quality | Impact |
|------------|---------|--------|
| < 5 | VERY LOW | Persona unreliable |
| 5-9 | LOW | Important patterns missed |
| 10-14 | BELOW RECOMMENDED | Confidence reduced |
| 15-20+ | GOOD | Full voice capture |

**Why full URL matters:**
- Common names return multiple profiles
- URL ensures correct person from the start
- Saves tokens by avoiding wrong-person errors

---

## LinkedIn Search Strategies (CRITICAL)

### The Wrong-Person Problem

Common names return many profiles from Google searches.

**BAD searches (will return wrong people):**
```
site:linkedin.com/posts/username 2024
site:linkedin.com/posts/username CompanyName
```

**GOOD searches (filtered by identity):**
```
site:linkedin.com/posts/username "Full Name" Company
site:linkedin.com/posts/username Product OR TechStack OR Location
```

### After Profile Verification

Once you've verified the profile, extract identity markers:
- Full name: "First Last"
- Companies: CurrentCo, PreviousCo, University
- Location: City/Region
- Products/Technologies: Key products or tech they mention

Use these in ALL subsequent searches:
```
site:linkedin.com/posts/{username} "{full_name}" OR {company1} OR {company2}
```

### Search Strategy Workflow

1. **Verify profile first** (get identity markers)
2. **Build disambiguating query** using markers
3. **Search with filters** to ensure correct person
4. **Validate results** before batch processing

**Example workflow:**
```bash
# After verifying profile and extracting markers:
site:linkedin.com/posts/username "Full Name"
site:linkedin.com/posts/username Company1 OR Company2 OR University
site:linkedin.com/posts/username "Product Name" OR "Tech Stack"
```

---

## Output

- `linkedin_persona.json` - Single unified professional voice
- `linkedin_data/` - Scraped posts

**Note:** LinkedIn creates ONE persona (not multiple) for brand consistency.

---

## Session 3b: LLM-Assisted Refinement (MANDATORY)

**Purpose:** Complete semantic analysis fields that require LLM understanding. Enhances v2 persona with guardrails, negative examples, and annotations.

**Prerequisites:** Session 3 complete (`linkedin_persona.json` exists with v2 schema)

**Why mandatory:**
- Guardrails prevent "LinkedIn cringe" drift
- Negative examples provide clear anti-patterns
- Annotations explain what makes high-performing posts effective
- Semantic fields cannot be reliably extracted via deterministic methods

### Step 1: Export Posts for Analysis

```bash
cd ~/Documents/my-writing-style

# Export all posts + current persona to a single markdown file
python3 prepare_llm_analysis.py

# Output: llm_analysis_input.md
```

The generated file contains:
- Analysis instructions (what fields to complete)
- Current persona JSON (already extracted patterns)
- All filtered posts with engagement data and comments

### Step 2: LLM Analysis

1. Open `llm_analysis_input.md` in your preferred LLM (Claude, GPT-4, etc.)
2. The file includes complete instructions - just copy/paste the whole thing
3. LLM returns a JSON object with completed fields

**Fields the LLM completes:**
- `guardrails.never_do` - Behavioral rules
- `guardrails.off_limits_topics` - Topics to avoid
- `voice.signature_phrases` - Unique recurring phrases
- `example_bank.positive` - Category, goal, audience, what_makes_it_work
- `example_bank.negative` - Anti-pattern examples with explanations

### Step 3: Merge Results

```bash
# Save LLM output to a file
# (copy the JSON block from LLM response into llm_output.json)

# Merge into persona
python3 merge_llm_analysis.py llm_output.json

# Verify merged result
cat linkedin_persona.json | python3 -m json.tool | head -50
```

**Merge behavior:**
- Only fills empty/placeholder fields (won't overwrite existing values)
- Uses index matching for positive example annotations
- Validates structure before saving
- Prints summary of what changed

### Dry Run Mode

Preview changes without modifying the file:

```bash
python3 merge_llm_analysis.py --dry-run llm_output.json
```

**Output:**
- Enhanced `linkedin_persona.json` with complete v2 schema

**See also:** `references/llm_analysis_guide.md` for detailed LLM instructions
