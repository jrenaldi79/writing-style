# Analysis Schema

Extract these fields for each writing sample.

## Universal Fields (All Sources)

```python
{
    "tone": ["adj1", "adj2", "adj3"],  # e.g., ["warm", "direct", "confident"]
    "formality": "formal | semi-formal | casual-professional | casual",
    "avg_sentence_length": "short | medium | long",
    "paragraph_style": "description of structure",
    "punctuation_signature": ["em-dashes", "semicolons", "ellipses", "exclamation points"],
    "contractions": "frequent | occasional | rare",
    "distinctive_phrases": ["recurring phrases", "verbal tics"]
}
```

## Email-Specific Fields

```python
{
    "greeting_pattern": "exact opener, e.g., 'Hey [Name],' or 'Team,'",
    "closing_pattern": "exact sign-off, e.g., 'Best, John' or '-J'",
    "recipient_awareness": "how tone shifts with audience size"
}
```

## LinkedIn-Specific Fields

```python
{
    "hook_style": "question | bold_statement | story | statistic | counterintuitive",
    "cta_pattern": "how posts typically end",
    "hashtag_strategy": "none | minimal | moderate | heavy",
    "line_break_usage": "dense | moderate | heavy"
}
```

## Metadata

```python
# Email
{
    "subject": "email subject line",
    "recipient_count": 1,
    "recipient_pattern": "individual | small_group | team_wide | external"
}

# LinkedIn
{
    "post_type": "thought_leadership | announcement | engagement | story",
    "media_attached": True/False,
    "estimated_length": "short | medium | long"
}
```

## Excerpt

Select 2-4 sentences that best capture the voice. The excerpt should:
- Stand alone without context
- Show distinctive patterns
- Feel authentic to the writer
