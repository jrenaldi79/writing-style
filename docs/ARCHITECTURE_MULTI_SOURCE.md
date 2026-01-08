# Multi-Source Architecture - Separate Pipelines

## Core Principle

**EMAIL ≠ LINKEDIN**

These are fundamentally different communication channels that require
**completely separate processing pipelines.**

---

## Why Separate?

### LinkedIn (Public Professional Brand)
- **Audience:** 5K followers, public internet
- **Purpose:** Build professional reputation, thought leadership
- **Consistency requirement:** HIGH - one unified voice
- **Persona count:** EXACTLY ONE
- **Why:** Brand consistency, professional credibility

### Email (Private Communication)
- **Audience:** Specific individuals/groups (boss, colleagues, customers)
- **Purpose:** Get work done, maintain relationships
- **Consistency requirement:** LOW - adapt to context
- **Persona count:** MULTIPLE (3-7 typically)
- **Why:** Different relationships demand different tones

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     DATA SOURCES                        │
├──────────────────────┬──────────────────────────────────┤
│   Gmail API          │   Social Media Scraper          │
│   ├─ fetch_emails.py │   ├─ fetch_linkedin_mcp.py │
│   └─ raw_samples/    │   └─ raw_samples/               │
│      email_*.json    │      linkedin_*.json            │
└──────────────────────┴──────────────────────────────────┘
           ↓                           ↓
┌──────────────────────┬──────────────────────────────────┐
│   EMAIL PIPELINE     │   LINKEDIN PIPELINE              │
├──────────────────────┼──────────────────────────────────┤
│ 1. filter_emails.py  │ 1. filter_linkedin.py            │
│    └─ Quality check  │    └─ Engagement threshold       │
│                      │                                  │
│ 2. enrich_emails.py  │ 2. enrich_linkedin.py            │
│    └─ 9 signals      │    └─ Platform-specific signals  │
│       (recipient,    │       (hashtags, engagement,     │
│        thread, etc)  │        content type)             │
│                      │                                  │
│ 3. embed_emails.py   │ 3. (integrated in cluster)       │
│    └─ Create vectors │                                  │
│                      │                                  │
│ 4. cluster_emails.py │ 4. cluster_linkedin.py           │
│    └─ HDBSCAN/KMeans │    └─ NO CLUSTERING              │
│       3-7 clusters   │       Single centroid            │
│       Multiple       │       ONE persona                │
│       personas       │                                  │
└──────────────────────┴──────────────────────────────────┘
           ↓                           ↓
┌──────────────────────┬──────────────────────────────────┐
│   EMAIL OUTPUTS      │   LINKEDIN OUTPUT                │
├──────────────────────┼──────────────────────────────────┤
│ clusters.json        │ linkedin_persona.json            │
│ ├─ persona_1         │ └─ Single professional voice     │
│ ├─ persona_2         │                                  │
│ └─ persona_N         │                                  │
│                      │                                  │
│ email_batches/       │ linkedin_batch/                  │
│ ├─ batch_001.jsonl   │ └─ batch_001.jsonl               │
│ ├─ batch_002.jsonl   │    (ONE persona always)          │
│ └─ ...               │                                  │
└──────────────────────┴──────────────────────────────────┘
           ↓                           ↓
┌──────────────────────┬──────────────────────────────────┐
│   EMAIL PROMPTS      │   LINKEDIN PROMPT                │
├──────────────────────┼──────────────────────────────────┤
│ Multiple personas:   │ Single persona:                  │
│                      │                                  │
│ "When writing to     │ "When writing LinkedIn posts,    │
│  your boss, you are  │  maintain this professional      │
│  formal (8/10) and   │  voice consistently:             │
│  direct (7/10)..."   │                                  │
│                      │  - Technical but accessible      │
│ "When writing to     │  - Humor with emojis (🍌 🎯)   │
│  colleagues, you are │  - Thought leadership            │
│  casual (4/10) with  │  - 200-400 word posts            │
│  humor..."           │  - Hashtag usage (#ai #agents)   │
│                      │  - High engagement focus         │
│ "When writing to     │                                  │
│  customers, you are  │  Consistency: 0.87/1.0           │
│  warm (9/10) and     │  (ONE voice always)"             │
│  empathetic..."      │                                  │
└──────────────────────┴──────────────────────────────────┘
```

---

## Key Differences

| Aspect | Email | LinkedIn |
|--------|-------|----------|
| **Source** | Gmail API | Social Media Scraper |
| **Volume** | 100-500 emails | 20-50 posts |
| **Clustering** | HDBSCAN/KMeans | None (single centroid) |
| **Personas** | 3-7 personas | Exactly 1 persona |
| **Rationale** | Context-dependent | Brand consistency |
| **Batch files** | Multiple | One |
| **Prompt style** | Conditional (if boss... if colleague...) | Unified (always...) |

---

## File Organization

```
writing-style/
├── raw_samples/
│   ├── email_*.json           # Email raw data
│   └── linkedin_*.json        # LinkedIn raw data
│
├── filtered_samples/
│   ├── email_*.json           # Passed quality filter
│   └── linkedin_*.json        # Passed engagement threshold
│
├── enriched_samples/
│   ├── email_*.json           # +9 email signals
│   └── linkedin_*.json        # +LinkedIn signals
│
├── embeddings/
│   ├── email_embeddings.npy   # Email vectors
│   ├── email_index.json       # Email metadata
│   ├── linkedin_embeddings.npy # LinkedIn vectors
│   └── linkedin_index.json    # LinkedIn metadata
│
├── clusters/
│   ├── email_clusters.json    # Multiple personas
│   └── linkedin_persona.json  # Single persona
│
└── batches/
    ├── email_batch_001.jsonl  # For Claude with multiple personas
    └── linkedin_batch_001.jsonl # For Claude with one persona
```

---

## Processing Scripts

### Email Pipeline (Multi-Persona)
```bash
# 1. Fetch
python fetch_emails.py --limit 200 --holdout 0.15

# 2. Filter (quality-based)
python filter_emails.py

# 3. Enrich (recipient, thread, time, structure)
python enrich_emails.py

# 4. Embed
python embed_emails.py

# 5. Cluster (HDBSCAN → 3-7 personas)
python cluster_emails.py

# 6. Prepare batches (one per persona)
python prepare_batch.py

# 7. Validate
python validate.py
```

### LinkedIn Pipeline (Single-Persona)
```bash
# 1. Fetch (efficient batch pattern)
python fetch_linkedin_mcp.py --profile "https://linkedin.com/in/username" --limit 50
# Agent executes: search → scrape_batch → process_batch (5 calls)

# 2. Filter (engagement-based)
python filter_linkedin.py

# 3. Enrich (hashtags, engagement, content type)
python enrich_linkedin.py

# 4. Create persona (NO clustering, single centroid)
python cluster_linkedin.py

# 5. Prepare batch (one file, one persona)
python prepare_linkedin_batch.py

# 6. Validate (consistency check)
python validate_linkedin.py
```

---

## Batch Formats

### Email Batch (Multiple Personas)
```jsonl
{"custom_id": "email-1", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
{"custom_id": "email-2", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
...
```

**System prompt includes:**
```
You have 5 distinct personas based on context:

1. BOSS persona (Formal 8/10, Direct 7/10):
   - Used when: Writing to executives, board members
   - Characteristics: ...

2. COLLEAGUE persona (Casual 4/10, Warm 8/10):
   - Used when: Internal team communication
   - Characteristics: ...

[... 3 more personas ...]

Select appropriate persona based on recipient and context.
```

### LinkedIn Batch (Single Persona)
```jsonl
{"custom_id": "linkedin-1", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
{"custom_id": "linkedin-2", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
...
```

**System prompt is unified:**
```
Your LinkedIn voice is consistent across all posts:

PROFESSIONAL VOICE (always):
- Technical but accessible (6/10 formality)
- Thought leadership with personality
- Uses emojis strategically (🍌 🎯 🤯)
- 200-400 word posts typically
- Hashtags: #ai #agents #product
- High engagement focus (avg 140 likes/post)
- Shares insights, not just updates

Consistency score: 0.87/1.0

Maintain this EXACT voice for all LinkedIn content.
NEVER vary based on topic - consistency is key.
```

---

## Validation Differences

### Email Validation
**Tests:** Does persona selection work correctly?
```python
# Test: Boss email → Should use Formal persona
# Test: Colleague email → Should use Casual persona
# Metric: Cosine similarity to cluster centroid
# Target: ≥0.70 per persona
```

### LinkedIn Validation  
**Tests:** Is voice consistent?
```python
# Test: All posts → Should match single centroid
# Metric: Mean cosine similarity across all posts
# Target: ≥0.75 (consistency, not diversity)
```

---

## Why This Matters

### Brand Consistency (LinkedIn)
❌ **Bad:** "Sometimes technical, sometimes casual, sometimes formal"
✅ **Good:** "Consistently technical-yet-accessible thought leader"

**Result:** Audience knows what to expect, builds trust

### Contextual Adaptation (Email)
❌ **Bad:** "Same tone for boss and intern"
✅ **Good:** "Formal with executives, casual with peers"

**Result:** Appropriate for each relationship

---

## Implementation Status

### ✅ Email Pipeline (v2.0.0)
- [x] Fetch, filter, enrich, embed, cluster
- [x] Multiple personas via HDBSCAN
- [x] Validation with holdout set
- [x] 55/55 tests passing
- [x] Pushed to GitHub (tag v2.0.0)

### 🚧 LinkedIn Pipeline (in progress)
- [x] Token-efficient fetching (5 calls for any N)
- [x] Batch processing infrastructure
- [x] Single-persona clustering
- [ ] Filter/enrich generalization
- [ ] Batch preparation
- [ ] Validation script
- [ ] Integration tests

### 📋 Remaining Work (v2.1)

1. **Create filter_linkedin.py**
   - Engagement threshold (min 10 likes?)
   - No auto-replies/spam (less common on LinkedIn)
   - Content quality scoring

2. **Create enrich_linkedin.py**
   - Extract hashtags
   - Classify content type (announcement, insight, share)
   - Engagement metrics as quality signals
   - Emoji usage detection

3. **Create prepare_linkedin_batch.py**
   - Single persona batch file
   - Unified professional voice
   - Consistency instructions

4. **Create validate_linkedin.py**
   - Consistency validation (not diversity)
   - Target score: ≥0.75 similarity to centroid
   - Check for unwanted variation

5. **Update documentation**
   - batch_schema.md (LinkedIn fields)
   - README.md (two-pipeline architecture)
   - SKILL.md (LinkedIn usage)

---

## Usage Examples

### Generate Email (Context-Aware)
```python
# System detects: Writing to boss → Selects Formal persona
prompt = "Draft email to CEO about Q4 roadmap"

# LLM uses: persona_3 (Formal, Direct, Authority 7/10)
result = "Dear [CEO name], I wanted to share..."
```

### Generate LinkedIn Post (Always Consistent)
```python
# System: Always uses single LinkedIn persona
prompt = "Write LinkedIn post about new AI framework"

# LLM always uses: PROFESSIONAL VOICE
# - Technical but accessible
# - Thought leadership
# - Strategic emoji usage
# - 200-400 words
result = "Just discovered an incredible framework... 🎯"
```

---

## Data Flow Diagram

```
USER CONTENT
    ↓
    ├─→ Emails (Private)
    │   ├─ Quality filter
    │   ├─ Enrich (recipient, thread)
    │   ├─ Embed (vectors)
    │   ├─ Cluster (HDBSCAN)
    │   └─ OUTPUT: 3-7 personas
    │
    └─→ LinkedIn (Public)
        ├─ Engagement filter
        ├─ Enrich (hashtags, engagement)
        ├─ Embed (vectors)
        ├─ Compute centroid (NO cluster)
        └─ OUTPUT: 1 persona

NEVER MIXED
```

---

## Schema Differences

### Email Cluster Schema
```json
{
  "clusters": [
    {
      "id": 1,
      "name": "Formal - Boss Communication",
      "sample_count": 23,
      "tone_vectors": {"formality": 8, "warmth": 5, ...},
      "context": {
        "typical_recipients": ["boss", "executive"],
        "typical_threads": ["initiating", "reply"]
      }
    },
    // ... more personas
  ]
}
```

### LinkedIn Persona Schema
```json
{
  "source": "linkedin",
  "persona_count": 1,
  "persona": {
    "name": "Professional LinkedIn Voice",
    "post_count": 47,
    "consistency_score": 0.87,
    "characteristics": {
      "avg_post_length": 285,
      "uses_emojis": true,
      "technical_content_ratio": 0.65,
      "top_hashtags": ["#ai", "#agents", "#product"]
    },
    "tone_profile": {
      "formality": 6,
      "warmth": 7,
      "technical_depth": 8,
      "humor": 6
    }
  }
}
```

---

## Validation Differences

### Email Validation (Diversity)
**Question:** Can the LLM select the right persona?

```python
# Generate test emails for each persona
for persona in personas:
    test_email = llm.generate(persona_prompt)
    similarity = cosine(test_email, persona.centroid)
    
    # Should be CLOSE to its own centroid
    assert similarity >= 0.70
    
    # Should be FAR from other centroids
    for other_persona in personas:
        if other_persona != persona:
            other_sim = cosine(test_email, other_persona.centroid)
            assert other_sim < 0.60  # Distinctiveness
```

### LinkedIn Validation (Consistency)
**Question:** Is the voice consistently professional?

```python
# Generate test posts
for i in range(10):
    test_post = llm.generate(linkedin_prompt)
    similarity = cosine(test_post, linkedin_persona.centroid)
    
    # Should ALL be close to the SAME centroid
    assert similarity >= 0.75

# Check variance (should be LOW)
variance = np.var(all_similarities)
assert variance < 0.05  # High consistency
```

---

## Summary

### ✅ Email Pipeline
**Goal:** Context-aware multi-persona system
- Multiple writing styles for different recipients
- Agent selects appropriate persona
- Validated for diversity AND accuracy

### ✅ LinkedIn Pipeline  
**Goal:** Consistent single-voice professional brand
- One unified writing style
- No persona selection needed
- Validated for consistency (not diversity)

### 🎯 Critical Rule
**NEVER MIX THESE SOURCES**
- Different purposes
- Different audiences  
- Different requirements
- Separate pipelines always

---

## Next Steps

Choose your path:

**A. Finish LinkedIn Pipeline** (2-3 hours)
- Complete filter/enrich/batch/validate
- Ship v2.1 with full multi-source support

**B. Validate Email Pipeline First** (1 hour)
- Test v2.0.0 with real data
- Refine before adding LinkedIn
- Ship v2.0.0, then v2.1

**C. Expand LinkedIn Data Collection** (30 min)
- Fetch 20-50 posts using efficient pattern
- More data = better persona
- Then complete pipeline

All are valid. What's your priority?
