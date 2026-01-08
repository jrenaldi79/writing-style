"""
Analysis Utilities - Similarity scoring and clustering for Writing Style Clone
"""

from typing import List, Dict, Optional


def compute_similarity_score(sample_analysis: dict, persona: dict) -> float:
    """
    Compute similarity between a sample and a persona.
    Returns score 0.0-1.0.
    """
    score = 0.0
    weights_used = 0.0
    
    sample = sample_analysis
    chars = persona.get("characteristics", {})
    
    # Tone match (weight: 0.25)
    sample_tone = set(sample.get("tone", []))
    persona_tone = set(chars.get("tone", []))
    if sample_tone and persona_tone:
        tone_overlap = len(sample_tone & persona_tone) / max(len(sample_tone | persona_tone), 1)
        score += tone_overlap * 0.25
        weights_used += 0.25
    
    # Formality match (weight: 0.20)
    if sample.get("formality") and chars.get("formality"):
        formality_levels = ["casual", "casual-professional", "semi-formal", "formal"]
        try:
            s_idx = formality_levels.index(sample["formality"])
            p_idx = formality_levels.index(chars["formality"])
            formality_score = 1.0 - (abs(s_idx - p_idx) / 3)
            score += formality_score * 0.20
            weights_used += 0.20
        except ValueError:
            pass
    
    # Sentence length match (weight: 0.10)
    if sample.get("avg_sentence_length") == chars.get("avg_sentence_length"):
        score += 0.10
        weights_used += 0.10
    elif sample.get("avg_sentence_length") and chars.get("avg_sentence_length"):
        weights_used += 0.10
    
    # Greeting pattern match (weight: 0.15) - email specific
    if sample.get("greeting_pattern") and chars.get("greeting_pattern"):
        if _patterns_similar(sample["greeting_pattern"], chars["greeting_pattern"]):
            score += 0.15
        weights_used += 0.15
    
    # Closing pattern match (weight: 0.15) - email specific
    if sample.get("closing_pattern") and chars.get("closing_pattern"):
        if _patterns_similar(sample["closing_pattern"], chars["closing_pattern"]):
            score += 0.15
        weights_used += 0.15
    
    # Hook style match (weight: 0.15) - LinkedIn specific
    if sample.get("hook_style") and chars.get("hook_style"):
        if sample["hook_style"] == chars["hook_style"]:
            score += 0.15
        weights_used += 0.15
    
    # Contractions match (weight: 0.10)
    if sample.get("contractions") == chars.get("contractions"):
        score += 0.10
        weights_used += 0.10
    elif sample.get("contractions") and chars.get("contractions"):
        weights_used += 0.10
    
    # Normalize by weights actually used
    if weights_used > 0:
        return score / weights_used
    return 0.0


def _patterns_similar(pattern1: str, pattern2: str) -> bool:
    """Check if two greeting/closing patterns are similar."""
    p1 = pattern1.lower().strip()
    p2 = pattern2.lower().strip()
    
    # Exact match
    if p1 == p2:
        return True
    
    # Same opener type (e.g., both "Hey [Name]" style)
    openers = {
        "hey": ["hey", "hi"],
        "team": ["team", "everyone", "all"],
        "dear": ["dear"],
        "name": ["[name]", "firstname"]
    }
    
    for group, patterns in openers.items():
        if any(pat in p1 for pat in patterns) and any(pat in p2 for pat in patterns):
            return True
    
    return False


def aggregate_characteristics(samples: List[dict]) -> dict:
    """
    Aggregate characteristics from multiple samples into persona characteristics.
    Returns characteristics that appear in >50% of samples.
    """
    if not samples:
        return {}
    
    # Collect all values
    tone_counts = {}
    formality_counts = {}
    sentence_counts = {}
    greeting_counts = {}
    closing_counts = {}
    contractions_counts = {}
    phrases = []
    
    for sample in samples:
        analysis = sample.get("analysis", sample)  # Handle both formats
        
        for tone in analysis.get("tone", []):
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        
        if analysis.get("formality"):
            formality_counts[analysis["formality"]] = formality_counts.get(analysis["formality"], 0) + 1
        
        if analysis.get("avg_sentence_length"):
            sentence_counts[analysis["avg_sentence_length"]] = sentence_counts.get(analysis["avg_sentence_length"], 0) + 1
        
        if analysis.get("greeting_pattern"):
            greeting_counts[analysis["greeting_pattern"]] = greeting_counts.get(analysis["greeting_pattern"], 0) + 1
        
        if analysis.get("closing_pattern"):
            closing_counts[analysis["closing_pattern"]] = closing_counts.get(analysis["closing_pattern"], 0) + 1
        
        if analysis.get("contractions"):
            contractions_counts[analysis["contractions"]] = contractions_counts.get(analysis["contractions"], 0) + 1
        
        phrases.extend(analysis.get("distinctive_phrases", []))
    
    n = len(samples)
    threshold = n * 0.5  # >50% occurrence
    
    characteristics = {
        "tone": [t for t, c in tone_counts.items() if c >= threshold],
        "formality": max(formality_counts, key=formality_counts.get) if formality_counts else None,
        "avg_sentence_length": max(sentence_counts, key=sentence_counts.get) if sentence_counts else None,
        "contractions": max(contractions_counts, key=contractions_counts.get) if contractions_counts else None,
    }
    
    # Add most common greeting/closing if >30% occurrence
    low_threshold = n * 0.3
    if greeting_counts:
        top_greeting = max(greeting_counts, key=greeting_counts.get)
        if greeting_counts[top_greeting] >= low_threshold:
            characteristics["greeting_pattern"] = top_greeting
    
    if closing_counts:
        top_closing = max(closing_counts, key=closing_counts.get)
        if closing_counts[top_closing] >= low_threshold:
            characteristics["closing_pattern"] = top_closing
    
    # Add phrases that appear 3+ times
    phrase_counts = {}
    for p in phrases:
        phrase_counts[p] = phrase_counts.get(p, 0) + 1
    characteristics["distinctive_phrases"] = [p for p, c in phrase_counts.items() if c >= 3]
    
    return characteristics


def derive_rules(samples: List[dict], characteristics: dict) -> List[str]:
    """
    Derive actionable rules from characteristics.
    Rules are patterns in >80% of samples.
    """
    if not samples:
        return []
    
    rules = []
    n = len(samples)
    high_threshold = n * 0.8
    
    # Greeting rule
    greeting_counts = {}
    for s in samples:
        analysis = s.get("analysis", s)
        if analysis.get("greeting_pattern"):
            greeting_counts[analysis["greeting_pattern"]] = greeting_counts.get(analysis["greeting_pattern"], 0) + 1
    
    for greeting, count in greeting_counts.items():
        if count >= high_threshold:
            rules.append(f"Open with: {greeting}")
            break
    
    # Closing rule
    closing_counts = {}
    for s in samples:
        analysis = s.get("analysis", s)
        if analysis.get("closing_pattern"):
            closing_counts[analysis["closing_pattern"]] = closing_counts.get(analysis["closing_pattern"], 0) + 1
    
    for closing, count in closing_counts.items():
        if count >= high_threshold:
            rules.append(f"Sign off with: {closing}")
            break
    
    # Tone rule
    if characteristics.get("tone"):
        rules.append(f"Maintain {', '.join(characteristics['tone'])} tone")
    
    # Formality rule
    if characteristics.get("formality"):
        rules.append(f"Keep {characteristics['formality']} register")
    
    # Contractions rule
    contractions = characteristics.get("contractions")
    if contractions == "frequent":
        rules.append("Use contractions freely")
    elif contractions == "rare":
        rules.append("Avoid contractions")
    
    return rules


def cluster_samples(samples: List[dict], existing_personas: List[dict] = None) -> Dict:
    """
    Cluster samples into groups for persona creation.
    
    Returns:
        {
            "assigned": {persona_id: [sample_ids]},
            "flagged": [(sample_id, reason, scores)],
            "unassigned": [sample_ids],
            "new_clusters": [[sample_ids]]  # Potential new personas
        }
    """
    result = {
        "assigned": {},
        "flagged": [],
        "unassigned": [],
        "new_clusters": []
    }
    
    if not samples:
        return result
    
    # If no existing personas, cluster all samples
    if not existing_personas:
        clusters = _cluster_by_similarity(samples)
        result["new_clusters"] = [[s["id"] for s in cluster] for cluster in clusters if len(cluster) >= 3]
        result["unassigned"] = [s["id"] for cluster in clusters if len(cluster) < 3 for s in cluster]
        return result
    
    # Score each sample against existing personas
    for sample in samples:
        analysis = sample.get("analysis", sample)
        best_score = 0.0
        best_persona = None
        scores = {}
        
        for persona in existing_personas:
            score = compute_similarity_score(analysis, persona)
            scores[persona["id"]] = score
            if score > best_score:
                best_score = score
                best_persona = persona["id"]
        
        if best_score >= 0.70:
            if best_persona not in result["assigned"]:
                result["assigned"][best_persona] = []
            result["assigned"][best_persona].append(sample["id"])
        elif best_score >= 0.40:
            result["flagged"].append((sample["id"], f"Ambiguous: best={best_score:.0%}", scores))
            # Tentatively assign
            if best_persona not in result["assigned"]:
                result["assigned"][best_persona] = []
            result["assigned"][best_persona].append(sample["id"])
        else:
            result["unassigned"].append(sample["id"])
    
    # Check if unassigned samples form new clusters
    if len(result["unassigned"]) >= 3:
        unassigned_samples = [s for s in samples if s["id"] in result["unassigned"]]
        clusters = _cluster_by_similarity(unassigned_samples)
        result["new_clusters"] = [[s["id"] for s in cluster] for cluster in clusters if len(cluster) >= 3]
        result["unassigned"] = [s["id"] for cluster in clusters if len(cluster) < 3 for s in cluster]
    
    return result


def _cluster_by_similarity(samples: List[dict], threshold: float = 0.50) -> List[List[dict]]:
    """Simple clustering by pairwise similarity."""
    if not samples:
        return []
    
    clusters = []
    used = set()
    
    for i, sample in enumerate(samples):
        if sample["id"] in used:
            continue
        
        cluster = [sample]
        used.add(sample["id"])
        
        for j, other in enumerate(samples[i+1:], i+1):
            if other["id"] in used:
                continue
            
            analysis_i = sample.get("analysis", sample)
            analysis_j = other.get("analysis", other)
            
            # Simple similarity check
            sim = _simple_similarity(analysis_i, analysis_j)
            if sim >= threshold:
                cluster.append(other)
                used.add(other["id"])
        
        clusters.append(cluster)
    
    return clusters


def _simple_similarity(a1: dict, a2: dict) -> float:
    """Quick similarity check between two analyses."""
    score = 0.0
    checks = 0
    
    # Tone overlap
    t1, t2 = set(a1.get("tone", [])), set(a2.get("tone", []))
    if t1 and t2:
        score += len(t1 & t2) / max(len(t1 | t2), 1)
        checks += 1
    
    # Formality match
    if a1.get("formality") and a2.get("formality"):
        score += 1.0 if a1["formality"] == a2["formality"] else 0.0
        checks += 1
    
    # Greeting similarity
    if a1.get("greeting_pattern") and a2.get("greeting_pattern"):
        score += 1.0 if _patterns_similar(a1["greeting_pattern"], a2["greeting_pattern"]) else 0.0
        checks += 1
    
    return score / max(checks, 1)
