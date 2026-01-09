# LLM-Assisted LinkedIn Voice Analysis Guide

## Your Task

Analyze the provided LinkedIn posts and complete the missing fields in the persona JSON. You have access to:
1. The current auto-extracted persona (tone vectors, linguistic patterns, etc.)
2. All filtered LinkedIn posts with engagement data and comments

Your job is to provide the **semantic analysis** that requires understanding context, patterns, and intent.

---

## Fields to Complete

### 1. guardrails.never_do (array of strings)

Look for patterns the user **NEVER** does across ALL posts. These are behavioral rules.

**How to identify:**
- What opening patterns are consistently avoided?
- What engagement tactics are never used?
- What tone/style is never present?

**Format:** Short action phrases starting with a verb

**Examples:**
- "use clickbait hooks or sensationalized openers"
- "start with 'I'm excited to announce' or 'I'm thrilled to share'"
- "ask for engagement directly ('Like if you agree', 'Thoughts?')"
- "use corporate buzzwords excessively"
- "make unsubstantiated claims about results"

---

### 2. guardrails.off_limits_topics (array of strings)

Topics the user **avoids entirely** in their professional content.

**How to identify:**
- What topics appear in typical LinkedIn content but are absent here?
- What controversial areas are clearly avoided?

**Common categories:**
- "politics"
- "religion"
- "personal drama"
- "controversial hot takes"
- "competitor criticism"

---

### 3. voice.signature_phrases (array of strings)

Identify 3-5 phrases that appear across multiple posts and are unique to this voice.

**How to identify:**
- Look for repeated phrases that aren't common LinkedIn clichés
- Focus on distinctive word combinations
- Check closings, CTAs, and transitions

**Examples:**
- "give it a whirl"
- "come join me/us"
- "feel free to..."
- "looking for folks with..."

---

### 4. example_bank.positive annotations

For each positive example post, provide classification and analysis.

#### category (string)
Choose the best fit:
- `hiring_announcement` - Recruiting for open positions
- `product_insight` - Technical observations or product commentary
- `thought_leadership` - Industry perspectives, trends, opinions
- `personal_update` - Career milestones, personal reflections
- `industry_commentary` - Reactions to news, market analysis
- `company_news` - Announcements about employer/investments
- `tool_recommendation` - Sharing useful tools, resources

#### goal (string)
What the post aims to achieve:
- `recruit` - Attract talent to a role
- `educate` - Share knowledge or insights
- `promote` - Highlight product, company, or person
- `engage` - Start a discussion or get feedback
- `announce` - Share news or updates
- `recommend` - Endorse a tool, product, or approach

#### audience (string)
Primary target audience:
- `engineers` - Software developers, technical roles
- `product_managers` - PMs, product leaders
- `founders` - Startup founders, entrepreneurs
- `investors` - VCs, angels, LPs
- `hiring_managers` - People with open roles
- `general_professional` - Broad LinkedIn audience

#### what_makes_it_work (array of 3-5 strings)

Annotate the **voice patterns** that make this post effective. Focus on:
- Opening technique
- Credibility signals
- Emotional hooks
- Structural choices
- Closing effectiveness

**Example annotations:**
- "Opens with empathy, not self-promotion"
- "Names specific products/companies (credibility through specifics)"
- "Uses inclusive language ('me/us' not just 'me')"
- "Balances technical depth with accessibility"
- "Ends with clear, non-desperate call to action"

---

### 5. example_bank.negative (array of objects)

Generate 3-5 **ANTI-PATTERN** examples - posts that would NOT sound like this person.

**How to create:**
1. Take the opposite of the detected voice patterns
2. Include common LinkedIn cringe the user avoids
3. Make them realistic enough to be instructive

**Format:**
```json
{
  "text": "Full example post text (1-3 sentences is enough)",
  "why_not_me": ["reason 1", "reason 2", "reason 3"]
}
```

**Examples to include:**
- Clickbait/hype style opener
- Corporate buzzword overload
- Desperate engagement bait
- Self-aggrandizing announcement
- Generic motivational content

---

## Output Format

Return a **single JSON object** with ONLY the fields you're completing. The merge script will integrate these into the existing persona.

```json
{
  "guardrails": {
    "never_do": [
      "use clickbait hooks",
      "start with 'I'm excited to announce'",
      "ask for engagement directly"
    ],
    "off_limits_topics": [
      "politics",
      "religion"
    ]
  },
  "voice": {
    "signature_phrases": [
      "give it a whirl",
      "come join me/us"
    ]
  },
  "example_bank": {
    "positive": [
      {
        "index": 0,
        "category": "hiring_announcement",
        "goal": "recruit",
        "audience": "engineers",
        "what_makes_it_work": [
          "Opens with empathy for job seekers",
          "Lists specific technical requirements",
          "Names real products (Pixel Watch, Galaxy Watch)",
          "Ends with inclusive 'join me/us'"
        ]
      },
      {
        "index": 1,
        "category": "company_news",
        "goal": "promote",
        "audience": "founders",
        "what_makes_it_work": [
          "..."
        ]
      }
    ],
    "negative": [
      {
        "text": "HUGE NEWS! You won't BELIEVE what just happened...",
        "why_not_me": ["clickbait opener", "all-caps for emphasis", "creates artificial suspense"]
      },
      {
        "text": "I'm excited to announce that I'm thrilled to share...",
        "why_not_me": ["corporate boilerplate", "empty enthusiasm", "says nothing substantive"]
      },
      {
        "text": "Thoughts? Drop a comment below! Like and share if you agree!",
        "why_not_me": ["desperate engagement bait", "no value provided", "LinkedIn cringe energy"]
      }
    ]
  }
}
```

---

## Important Notes

1. **Use index for positive examples** - Reference posts by their index (0, 1, 2...) as shown in the input file
2. **Be specific** - Generic observations aren't useful. "Good opener" is weak; "Opens with empathy for job seekers, not self-promotion" is strong
3. **Match the voice** - Your analysis should reflect understanding of THIS person's specific patterns, not generic LinkedIn advice
4. **JSON must be valid** - Ensure proper escaping of quotes and special characters
5. **Don't invent** - Base all observations on the actual post content provided
