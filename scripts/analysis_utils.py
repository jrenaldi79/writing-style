"""
Analysis Utilities - Helper functions for style analysis
"""

from typing import Optional
from collections import Counter


def compute_similarity_score(sample_analysis: dict, persona_characteristics: dict) -> float:
    """
    Compute how well a sample matches a persona's characteristics.
    Returns a score between 0.0 and 1.0.
    """
    score = 0.0
    weights_used = 0.0
    
    # Tone match (weight: 0.25)
    sample_tone = set(sample_analysis.get("tone", []))
    persona_tone = set(persona_characteristics.get("tone", []))
    if sample_tone and persona_tone:
        tone_overlap = len(sample_tone & persona_tone) / max(len(sample_tone | persona_tone), 1)
        score += tone_overlap * 0.25
        weights_used += 0.25
    
    # Formality match (weight: 0.20)
    if sample_analysis.get("formality") and persona_characteristics.get("formality"):
        if sample_analysis["formality"] == persona_characteristics["formality"]:
            score += 0.20
        elif abs(_formality_level(sample_analysis["formality"]) - 
                 _formality_level(persona_characteristics["formality"])) == 1:
            score += 0.10  # Adjacent formality levels get partial credit
        weights_used += 0.20
    
    # Sentence length match (weight: 0.10)
    if sample_analysis.get("avg_sentence_length") and persona_characteristics.get("avg_sentence_length"):
        if sample_analysis["avg_sentence_length"] == persona_characteristics["avg_sentence_length"]:
            score += 0.10
        weights_used += 0.10
    
    # Greeting pattern (weight: 0.15) - for email
    sample_greeting = sample_analysis.get("greeting_pattern", "").lower()
    persona_greeting = persona_characteristics.get("greeting_pattern", "").lower()
    if sample_greeting and persona_greeting:
        if _greeting_similarity(sample_greeting, persona_greeting):
            score += 0.15
        weights_used += 0.15
    
    # Closing pattern (weight: 0.10) - for email
    sample_closing = sample_analysis.get("closing_pattern", "").lower()
    persona_closing = persona_characteristics.get("closing_pattern", "").lower()
    if sample_closing and persona_closing:
        if _closing_similarity(sample_closing, persona_closing):
            score += 0.10
        weights_used += 0.10
    
    # Contractions usage (weight: 0.10)
    if sample_analysis.get("contractions") and persona_characteristics.get("contractions"):
        if sample_analysis["contractions"] == persona_characteristics["contractions"]:
            score += 0.10
        weights_used += 0.10
    
    # Hook style (weight: 0.15) - for LinkedIn
    if sample_analysis.get("hook_style") and persona_characteristics.get("hook_style"):
        if sample_analysis["hook_style"] == persona_characteristics["hook_style"]:
            score += 0.15
        weights_used += 0.15
    
    # Normalize by weights actually used
    if weights_used > 0:
        return score / weights_used
    return 0.0


def _formality_level(formality: str) -> int:
    """Convert formality string to numeric level for comparison."""
    levels = {
        "casual": 1,
        "casual-professional": 2,
        "semi-formal": 3,
        "professional": 4,
        "formal": 5
    }
    return levels.get(formality.lower(), 3)


def _greeting_similarity(g1: str, g2: str) -> bool:
    """Check if two greetings are similar in style."""
    casual_markers = ["hey", "hi ", "yo", "what's up"]
    formal_markers = ["dear", "hello", "good morning", "good afternoon"]
    team_markers = ["team", "everyone", "all"]
    
    g1_casual = any(m in g1 for m in casual_markers)
    g2_casual = any(m in g2 for m in casual_markers)
    
    g1_formal = any(m in g1 for m in formal_markers)
    g2_formal = any(m in g2 for m in formal_markers)
    
    g1_team = any(m in g1 for m in team_markers)
    g2_team = any(m in g2 for m in team_markers)
    
    # Same category = similar
    if g1_casual == g2_casual and g1_formal == g2_formal and g1_team == g2_team:
        return True
    return False


def _closing_similarity(c1: str, c2: str) -> bool:
    """Check if two closings are similar in style."""
    casual_markers = ["thanks!", "cheers", "lmk", "-j", "talk soon"]
    formal_markers = ["best regards", "sincerely", "respectfully", "regards"]
    warm_markers = ["best,", "thanks,", "warm regards", "take care"]
    
    c1_casual = any(m in c1 for m in casual_markers)
    c2_casual = any(m in c2 for m in casual_markers)
    
    c1_formal = any(m in c1 for m in formal_markers)
    c2_formal = any(m in c2 for m in formal_markers)
    
    if c1_casual == c2_casual and c1_formal == c2_formal:
        return True
    return False


def aggregate_characteristics(samples: list) -> dict:
    """
    Aggregate characteristics across multiple samples to define a persona.
    Uses frequency analysis to determine dominant patterns.
    """
    if not samples:
        return {}
    
    tone_counter = Counter()
    formality_counter = Counter()
    sentence_length_counter = Counter()
    greeting_counter = Counter()
    closing_counter = Counter()
    contractions_counter = Counter()
    punctuation_all = []
    phrases_all = []
    hook_counter = Counter()
    
    for s in samples:
        analysis = s.get("analysis", {})
        
        for tone in analysis.get("tone", []):
            tone_counter[tone] += 1
        
        if analysis.get("formality"):
            formality_counter[analysis["formality"]] += 1
        
        if analysis.get("avg_sentence_length"):
            sentence_length_counter[analysis["avg_sentence_length"]] += 1
        
        if analysis.get("greeting_pattern"):
            greeting_counter[analysis["greeting_pattern"]] += 1
        
        if analysis.get("closing_pattern"):
            closing_counter[analysis["closing_pattern"]] += 1
        
        if analysis.get("contractions"):
            contractions_counter[analysis["contractions"]] += 1
        
        punctuation_all.extend(analysis.get("punctuation_signature", []))
        phrases_all.extend(analysis.get("distinctive_phrases", []))
        
        if analysis.get("hook_style"):
            hook_counter[analysis["hook_style"]] += 1
    
    # Build aggregated characteristics
    n = len(samples)
    threshold = 0.3  # Pattern must appear in 30%+ of samples
    
    characteristics = {
        "tone": [t for t, c in tone_counter.most_common(3) if c / n >= threshold],
        "formality": formality_counter.most_common(1)[0][0] if formality_counter else None,
        "avg_sentence_length": sentence_length_counter.most_common(1)[0][0] if sentence_length_counter else None,
        "contractions": contractions_counter.most_common(1)[0][0] if contractions_counter else None,
    }
    
    # Add most common greeting/closing if present
    if greeting_counter:
        top_greetings = [g for g, c in greeting_counter.most_common(2) if c / n >= threshold]
        characteristics["greeting_pattern"] = " / ".join(top_greetings) if top_greetings else greeting_counter.most_common(1)[0][0]
    
    if closing_counter:
        top_closings = [c for c, cnt in closing_counter.most_common(2) if cnt / n >= threshold]
        characteristics["closing_pattern"] = " / ".join(top_closings) if top_closings else closing_counter.most_common(1)[0][0]
    
    # Punctuation: include if appears in 40%+ of samples
    punct_counter = Counter(punctuation_all)
    characteristics["punctuation_signature"] = [p for p, c in punct_counter.most_common(5) if c / n >= 0.4]
    
    # Phrases: include if appears in 2+ samples
    phrase_counter = Counter(phrases_all)
    characteristics["distinctive_phrases"] = [p for p, c in phrase_counter.most_common(5) if c >= 2]
    
    # LinkedIn-specific
    if hook_counter:
        characteristics["hook_style"] = hook_counter.most_common(1)[0][0]
    
    return characteristics


def derive_rules(characteristics: dict, sample_count: int) -> list:
    """
    Convert characteristics into actionable writing rules.
    """
    rules = []
    
    # Greeting rule
    if characteristics.get("greeting_pattern"):
        rules.append(f"Open with: {characteristics['greeting_pattern']}")
    
    # Closing rule
    if characteristics.get("closing_pattern"):
        rules.append(f"Close with: {characteristics['closing_pattern']}")
    
    # Formality
    formality = characteristics.get("formality")
    if formality == "formal":
        rules.append("Maintain formal tone throughout; avoid contractions")
    elif formality == "casual":
        rules.append("Keep it conversational; contractions encouraged")
    elif formality in ["casual-professional", "semi-formal"]:
        rules.append("Balance professionalism with warmth; contractions acceptable")
    
    # Sentence length
    length = characteristics.get("avg_sentence_length")
    if length == "short":
        rules.append("Keep sentences punchy (under 15 words average)")
    elif length == "long":
        rules.append("Use flowing, complex sentences when explaining")
    
    # Punctuation
    punct = characteristics.get("punctuation_signature", [])
    if "em-dashes" in punct or "em-dash" in punct:
        rules.append("Use em-dashes for asides and emphasis")
    if "ellipses" in punct:
        rules.append("Ellipses acceptable for trailing thoughts")
    if "exclamation points" in punct:
        rules.append("Occasional exclamation points for enthusiasm")
    
    # Hook style (LinkedIn)
    hook = characteristics.get("hook_style")
    if hook == "question":
        rules.append("Open with a provocative question")
    elif hook == "bold_statement":
        rules.append("Lead with a bold, counterintuitive claim")
    elif hook == "story":
        rules.append("Start with a brief anecdote or observation")
    
    return rules


def suggest_cluster_names(clusters: list) -> list:
    """
    Suggest persona names based on cluster characteristics.
    """
    suggestions = []
    
    for cluster in clusters:
        chars = cluster.get("characteristics", {})
        source = cluster.get("primary_source", "mixed")
        
        # Determine primary audience
        formality = chars.get("formality", "")
        greeting = chars.get("greeting_pattern", "").lower()
        
        if "team" in greeting or "everyone" in greeting:
            base = "Team Communicator"
        elif "hey" in greeting or formality == "casual":
            base = "Direct Collaborator"
        elif "dear" in greeting or formality == "formal":
            base = "Formal Correspondent"
        elif source == "linkedin":
            base = "Thought Leader"
        else:
            base = "Professional Voice"
        
        # Add modifier based on tone
        tone = chars.get("tone", [])
        if "authoritative" in tone:
            base = "The " + base.split()[-1] + " (Authoritative)"
        elif "encouraging" in tone or "warm" in tone:
            base = "The " + base.split()[-1] + " (Warm)"
        
        suggestions.append(base)
    
    return suggestions
