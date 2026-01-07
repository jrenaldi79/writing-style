---
name: writing-style-clone
description: Analyze written content (Emails & LinkedIn) to generate a personalized system prompt that replicates the user's authentic voice.
---

# Writing Style Clone

Analyze writing samples to discover personas and generate personalized writing assistant prompts.

## 🏗️ Architecture: Dual Persona Pipeline

**CRITICAL RULE:** Never mix Email content with LinkedIn content.

### 1. Email Pipeline (Adaptive)
- **Source:** Gmail API
- **Nature:** Context-dependent (Boss vs Team vs Client)
- **Output:** Multiple Personas (3-7 clusters)

### 2. LinkedIn Pipeline (Unified)
- **Source:** LinkedIn Scraper
- **Nature:** Public Professional Brand
- **Output:** EXACTLY ONE Persona (Single centroid)

---

## 🔄 Workflow 1: Email Processing

### Phase 1: Setup
```bash
mkdir -p ~/Documents/my-writing-style/{samples,prompts,raw_samples,batches} && \
cp ~/Documents/writing-style/skill/scripts/*.py ~/Documents/my-writing-style/ && \
cd ~/Documents/my-writing-style
python3 fetch_emails.py --count 200 --holdout 0.15
```

### Phase 2: Analysis (Batch Processing)
```bash
# 1. Filter (Quality gate)
python3 filter_emails.py

# 2. Enrich (Context signals)
python3 enrich_emails.py

# 3. Embed & Cluster (Discovery)
python3 embed_emails.py
python3 cluster_emails.py

# 4. Validation
python3 validate.py
```

---

## 🔄 Workflow 2: LinkedIn Processing (NEW)

**Token-Efficient Batch Pattern (Cost: 5 tool calls for ANY size)**

### Step 1: Fetch & Scrape
```bash
# Automatically runs: Search -> Scrape Batch -> Process Batch -> Status
python3 fetch_linkedin_complete.py --profile <username> --limit 20
```

### Step 2: Filter (Quality Gate)
```bash
# Enforces length > 200 chars to avoid snippets
python3 filter_linkedin.py
```

### Step 3: Architecture & Persona Generation
```bash
# 1. Enrich (Hashtags, content type)
python3 enrich_linkedin.py  # (Coming in v2.1)

# 2. Generate Single Persona
# Calculates centroid of all professional posts
python3 cluster_linkedin.py
```

### Step 4: Validation
```bash
python3 validate_linkedin.py  # (Coming in v2.1)
```

---

## 📦 Data Schema

### Email Cluster Schema
```json
{
  "clusters": [
    {
      "id": 1,
      "name": "Formal - Boss Communication",
      "tone_vectors": {"formality": 8, ...},
      "context": {"recipients": ["boss"]}
    }
  ]
}
```

### LinkedIn Persona Schema
```json
{
  "source": "linkedin",
  "persona": {
    "name": "Professional LinkedIn Voice",
    "consistency_score": 0.87,
    "characteristics": {
      "avg_post_length": 285,
      "uses_emojis": true,
      "top_hashtags": ["#ai", "#product"]
    }
  }
}
```

---

## 🛠️ Efficient Scripting (Best Practices)

**Do not use REPL loops for batch operations.** Use the provided batch scripts.

| Operation | OLD (Inefficient) | NEW (Efficient) |
|-----------|-------------------|-----------------|
| **Scraping** | `for url in urls: scrape(url)` (N calls) | `scrape_batch(urls)` (1 call) |
| **Processing** | `for item in items: parse(item)` (N calls) | `process_batch.py file.json` (1 call) |
| **Cost** | 50-150 tool calls | **5 tool calls total** |

**Reference:** `skill/scripts/LINKEDIN_INTEGRATION.md`
