# LinkedIn Integration - Token-Efficient Pattern

## Overview

This demonstrates the **token-efficient pattern** for batch data collection and processing.

## The Problem: Sequential Processing

**Old approach (wasteful):**
```python
# Search (1 call)
results = search_linkedin()

# Scrape batch (1 call)  
scraped = scrape_batch(urls)

# Process one-by-one (N calls via REPL)
for item in scraped:
    post = parse(item)      # REPL interaction
    save(post)              # REPL interaction
    print(status)           # REPL interaction
```

**Result:** 1 + 1 + (N × 3) = **3N + 2 tool calls** 😱

For 20 posts: **62 tool calls**

## The Solution: Batch Processing

**New approach (efficient):**
```python
# 1. Search (1 call)
results = search_linkedin()

# 2. Scrape batch (1 call)
scraped = scrape_batch(urls)

# 3. Write temp file (1 call)
write_file('/tmp/data.json', scraped)

# 4. Batch process (1 call)
execute('python process_batch.py /tmp/data.json')

# 5. Status check (1 call)
execute('python show_status.py')
```

**Result:** **5 tool calls total** 🎉

For 20 posts: **5 tool calls** (vs 62)

**Token savings: ~92%**

## Implementation

### Core Scripts

1. **fetch_linkedin_complete.py** - Shows the efficient workflow pattern
2. **process_linkedin_batch.py** - Batch processes scraped data
3. **extract_linkedin_engagement.py** - Utility for parsing engagement metrics

### Workflow

```bash
# Step 1: See instructions
python fetch_linkedin_complete.py --profile renaldi --limit 20

# Step 2: Agent executes (via MCP tools):
# - search_engine (1 call)
# - scrape_batch (1 call)  
# - write temp file (1 call)
# - process_batch (1 call)
# - show status (1 call)

# Total: 5 tool calls for 20 posts
```

### Example: Processing 20 Posts

```python
import json
from extract_linkedin_engagement import extract_engagement, extract_main_text
import process_linkedin_batch

# After scraping (via MCP tool)
scraped = [
    {"url": "https://...", "content": "John's post..."},
    # ... 19 more
]

# Extract engagement in memory (no additional calls)
data = []
for item in scraped:
    engagement = extract_engagement(item['content'])
    text = extract_main_text(item['content'])
    data.append({
        'url': item['url'],
        'content': text,
        'likes': engagement['likes'],
        'comments': engagement['comments']
    })

# Write once
with open('/tmp/linkedin.json', 'w') as f:
    json.dump(data, f)

# Process once
stats = process_linkedin_batch.process_batch(data, holdout_fraction=0.15)

print(f"✅ Processed {stats['successful']} posts")
print(f"💾 Total engagement: {stats['engagement']['total_likes']} likes")
```

## Key Principles

### 1. Batch MCP Operations
✅ Use `scrape_batch` (not individual `scrape_as_markdown`)
✅ Use `search_engine` once (not multiple searches)

### 2. Minimize Context Switches
❌ Don't use REPL for loops
✅ Write script, execute once

### 3. File-Based Handoffs
✅ MCP scrape → temp file → Python batch process
✅ One write, one read, one execution

### 4. Aggregated Results
✅ Return summary stats (not individual confirmations)
✅ One status check at end

## Token Savings Breakdown

| Operation | Old (Sequential) | New (Batch) | Savings |
|-----------|-----------------|-------------|----------|
| Search | 1 | 1 | 0 |
| Scrape | 1 | 1 | 0 |
| Parse | N × 1 | 0 | N |
| Save | N × 1 | 0 | N |
| Status | N × 1 | 1 | N-1 |
| Process | 0 | 1 | -1 |
| **TOTAL** | **3N + 2** | **5** | **3N - 3** |

For N=20: **62 → 5** (92% reduction)
For N=50: **152 → 5** (97% reduction)

## Applying This Pattern

This pattern works for ANY batch operation:

### Email Fetching
```python
# Old: fetch_emails.py with sequential saves
# New: fetch_emails_batch.py with one-pass processing
```

### File Processing
```python
# Old: for file in files: process(file)
# New: process_files_batch(all_files)
```

### Data Transformation
```python
# Old: filter → enrich → cluster (sequential)
# New: pipeline script (batch)
```

## Future Enhancements

### v2.1: Full LinkedIn Integration
- [ ] Generalize filter_emails.py → filter_content.py
- [ ] Generalize enrich_emails.py → enrich_content.py  
- [ ] Update batch_schema.md for multi-source
- [ ] Unified pipeline for emails + LinkedIn

### v2.2: Multi-Platform
- [ ] Twitter/X posts
- [ ] Blog articles
- [ ] Slack messages
- [ ] All using same efficient pattern

## Summary

✅ **Old approach:** ~60+ tool calls for 20 items
✅ **New approach:** 5 tool calls for ANY number of items
✅ **Token savings:** 90-97% depending on batch size
✅ **Pattern applies:** Emails, files, APIs, any batch work

🎯 **Key insight:** Think in pipelines, not loops. Batch everything.
