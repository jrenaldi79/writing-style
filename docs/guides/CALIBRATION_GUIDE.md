# Calibration Reference

**IMPORTANT:** Read these examples BEFORE analyzing any emails. Use them as anchors to ensure consistent scoring across all batches.

When assigning tone_vectors scores, reference these examples to calibrate your scale.

---

## Formality Scale (1-10)

### 1 - Very Casual (texting style)
> "yo u free tmrw? lmk asap"

### 2 - Casual
> "hey! quick q - are you around tomorrow afternoon? no rush"

### 3 - Casual Professional
> "Hey John - Quick question for you. Any chance you're free tomorrow afternoon?"

### 5 - Balanced Professional
> "Hi John, I wanted to follow up on our conversation from last week. Do you have availability tomorrow afternoon to discuss next steps?"

### 7 - Professional
> "Good afternoon, John. I'm writing to follow up on our recent discussion regarding the Q4 timeline. Would you have availability tomorrow afternoon to continue our conversation?"

### 9 - Formal
> "Dear Mr. Smith, I hope this message finds you well. I am writing to formally request a meeting at your earliest convenience to discuss the matters outlined in our previous correspondence."

### 10 - Highly Formal (legal/executive)
> "Dear Mr. Smith, Please be advised that the Board of Directors has reviewed the proposal submitted on January 15th. We formally request your attendance at the scheduled meeting to address the outstanding items enumerated in Appendix A."

---

## Warmth Scale (1-10)

### 1 - Cold/Distant
> "Per your request, attached is the document. Review and confirm receipt."

### 3 - Neutral
> "Here's the document you requested. Let me know if you have questions."

### 5 - Friendly
> "Here's that document you asked about! Happy to walk through it if anything's unclear."

### 7 - Warm
> "Great chatting with you earlier! Here's the doc we discussed - really excited to see where this goes. Let me know if you want to hop on a call to dig in together!"

### 9 - Very Warm
> "So great to hear from you! I've been thinking about our conversation and I'm genuinely excited about this. Here's everything you need - and seriously, reach out anytime. Looking forward to working together!"

### 10 - Effusive
> "What an absolute pleasure to connect with you! I can't tell you how thrilled I am about this opportunity. You've completely made my day. Here's everything, and I truly mean it - call me anytime, day or night!"

---

## Authority Scale (1-10)

### 1 - Deferential/Uncertain
> "I'm not sure if this is right, but I was thinking maybe we could possibly consider... what do you think? Sorry if this is off base."

### 3 - Tentative
> "I think this approach might work, but I'd love to get your input before moving forward. Does this seem reasonable to you?"

### 5 - Balanced
> "Based on my analysis, I recommend Option A. Here's my reasoning - let me know if you see it differently."

### 7 - Confident Expert
> "I've seen this pattern many times. Here's what works: Option A addresses the core issue. Option B is a common mistake - avoid it. Let me know if you want me to walk through the implementation."

### 9 - Authoritative
> "This is the approach. I've implemented this successfully across multiple engagements and the data is clear. The three things you need to do: 1) X, 2) Y, 3) Z. Any questions, I'm here."

### 10 - Directive/Executive
> "Effective immediately, we are implementing the following changes. This decision is final. All teams will comply with the new protocol by EOD Friday. Exceptions require my written approval."

---

## Directness Scale (1-10)

### 1 - Very Indirect
> "I was wondering if perhaps, when you have a moment, you might consider looking into the possibility of maybe adjusting the timeline somewhat, if that's not too much trouble and if it makes sense from your perspective..."

### 3 - Hedged
> "I think we might need to revisit the timeline. It seems like there could be some challenges with the current schedule. Maybe we could discuss some options?"

### 5 - Balanced
> "We should revisit the timeline. The current schedule has some risks I want to flag. Can we find time this week to discuss alternatives?"

### 7 - Direct
> "The timeline won't work. Here's why: [reasons]. I need a decision by Thursday on which alternative we're going with."

### 9 - Very Direct
> "Timeline's broken. Two options: push launch two weeks or cut Feature X. Pick one by Thursday."

### 10 - Blunt
> "No. This doesn't work. Fix it."

---

## Using These Anchors

When analyzing an email:

1. **Read the email** completely
2. **Compare to anchors** - Which examples feel most similar?
3. **Assign scores** - Use the anchor numbers as your guide
4. **Be consistent** - The same style should get the same score in every batch

### Example Analysis

Email: "Hey team - quick update on the RAG implementation. Three things: 1) embeddings are working, 2) retrieval needs tuning, 3) demo ready Thursday. Let me know if questions. -JR"

**Calibrated scores:**
- Formality: 3 (casual professional - "Hey team", uses abbreviations)
- Warmth: 5 (friendly but focused - offers help, not effusive)
- Authority: 7 (confident expert - clear direction, numbered items)
- Directness: 8 (very direct - short sentences, clear structure, deadline)

---

## Confirmation

When outputting batch analysis, include this field to confirm calibration:

```json
{
  "calibration_referenced": true,
  "calibration_notes": "Anchored formality against examples 3/5, authority against 7/9"
}
```

This ensures consistency across all analysis batches.
