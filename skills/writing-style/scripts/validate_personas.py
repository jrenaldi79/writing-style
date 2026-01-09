#!/usr/bin/env python3
"""
Validate Personas - Blind validation against held-out emails

Runs blind validation tests:
1. Loads personas (the draft from training data)
2. Loads validation pairs (context + hidden ground truth)
3. For each pair: shows context, determines persona, compares to actual reply
4. Scores: persona match, tone match, structure match
5. Outputs: validation_report.json with scores and refinement suggestions

Usage:
    python validate_personas.py                  # Interactive mode
    python validate_personas.py --auto           # Auto-score using heuristics
    python validate_personas.py --report         # Generate report from existing results
    python validate_personas.py --status         # Show validation status
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from config import get_data_dir, get_path

PERSONA_REGISTRY_FILE = get_path("persona_registry.json")
VALIDATION_PAIRS_FILE = get_path("validation_pairs.json")
VALIDATION_RESULTS_FILE = get_path("validation_results.json")
VALIDATION_REPORT_FILE = get_path("validation_report.json")


def load_personas() -> Dict:
    """Load personas from registry."""
    if not PERSONA_REGISTRY_FILE.exists():
        return {}
    with open(PERSONA_REGISTRY_FILE) as f:
        data = json.load(f)
    return data.get('personas', {})


def load_validation_pairs() -> List[Dict]:
    """Load validation pairs."""
    if not VALIDATION_PAIRS_FILE.exists():
        return []
    with open(VALIDATION_PAIRS_FILE) as f:
        data = json.load(f)
    return data.get('pairs', [])


def infer_persona_from_context(context: Dict, personas: Dict) -> Tuple[str, float]:
    """
    Infer which persona should respond based on context.

    Uses heuristics based on subject, quoted text, and recipient.
    Returns (persona_name, confidence).
    """
    subject = context.get('subject', '').lower()
    quoted = context.get('quoted_text', '').lower()
    to = context.get('from_original', '').lower()  # Who they're replying to

    best_persona = None
    best_score = 0.0

    for name, persona_data in personas.items():
        score = 0.0
        desc = persona_data.get('description', '').lower()
        chars = persona_data.get('characteristics', {})

        # Match on description keywords
        desc_words = desc.split()
        for word in desc_words:
            if len(word) > 4:  # Skip short words
                if word in subject or word in quoted or word in to:
                    score += 0.2

        # Match on formality level
        formality = chars.get('formality', 5)
        if formality >= 7:  # Formal persona
            if any(w in subject for w in ['meeting', 'review', 'report', 'update', 'board']):
                score += 0.3
            if any(w in to for w in ['ceo', 'chief', 'director', 'vp', 'president']):
                score += 0.3
        elif formality <= 4:  # Casual persona
            if any(w in subject for w in ['hey', 'quick', 'fyi', 'lunch', 'drinks']):
                score += 0.3

        if score > best_score:
            best_score = score
            best_persona = name

    # Default to first persona if no match
    if not best_persona and personas:
        best_persona = list(personas.keys())[0]
        best_score = 0.3

    return best_persona or "Unknown", min(best_score, 1.0)


def score_tone_match(ground_truth: Dict, persona_chars: Dict) -> Dict[str, float]:
    """Score how well the ground truth matches persona characteristics."""
    scores = {}

    # Formality score
    tone_hints = ground_truth.get('tone_hints', [])
    formality = persona_chars.get('formality', 5)

    if 'formal' in tone_hints:
        scores['formality'] = 1.0 if formality >= 6 else 0.5 if formality >= 4 else 0.2
    elif 'casual' in tone_hints:
        scores['formality'] = 1.0 if formality <= 4 else 0.5 if formality <= 6 else 0.2
    else:
        scores['formality'] = 0.7  # Neutral

    # Contraction usage
    has_contractions = ground_truth.get('has_contractions', False)
    persona_contractions = persona_chars.get('uses_contractions', True)

    if has_contractions == persona_contractions:
        scores['contractions'] = 1.0
    elif has_contractions and not persona_contractions:
        scores['contractions'] = 0.3  # Ground truth uses, persona doesn't
    else:
        scores['contractions'] = 0.5  # Persona uses, ground truth doesn't

    # Warmth score
    warmth = persona_chars.get('warmth', 5)
    if 'warm' in tone_hints:
        scores['warmth'] = 1.0 if warmth >= 6 else 0.5 if warmth >= 4 else 0.2
    else:
        scores['warmth'] = 0.7

    return scores


def score_structure_match(ground_truth: Dict, persona_chars: Dict) -> Dict[str, float]:
    """Score structural pattern matches."""
    scores = {}

    # Greeting match
    greeting = ground_truth.get('greeting', '').lower()
    typical_greeting = persona_chars.get('typical_greeting', '').lower()

    if greeting and typical_greeting:
        # Check if same greeting type
        greeting_patterns = {
            'hi': ['hi', 'hey', 'hello'],
            'dear': ['dear'],
            'thanks': ['thanks', 'thank you'],
            'good': ['good morning', 'good afternoon', 'good evening']
        }
        for pattern_name, patterns in greeting_patterns.items():
            greeting_match = any(p in greeting for p in patterns)
            typical_match = any(p in typical_greeting for p in patterns)
            if greeting_match and typical_match:
                scores['greeting'] = 1.0
                break
        else:
            scores['greeting'] = 0.5
    else:
        scores['greeting'] = 0.7  # Can't compare

    # Closing match
    closing = ground_truth.get('closing', '').lower()
    typical_closing = persona_chars.get('typical_closing', '').lower()

    if closing and typical_closing:
        closing_patterns = {
            'best': ['best', 'best regards', 'kind regards'],
            'thanks': ['thanks', 'thank you'],
            'cheers': ['cheers'],
            'regards': ['regards', 'warm regards']
        }
        for pattern_name, patterns in closing_patterns.items():
            closing_match = any(p in closing for p in patterns)
            typical_match = any(p in typical_closing for p in patterns)
            if closing_match and typical_match:
                scores['closing'] = 1.0
                break
        else:
            scores['closing'] = 0.5
    else:
        scores['closing'] = 0.7

    return scores


def score_validation_pair(pair: Dict, personas: Dict) -> Dict:
    """Score a single validation pair."""
    context = pair.get('context', {})
    ground_truth = pair.get('ground_truth', {})

    # Infer which persona should have responded
    inferred_persona, confidence = infer_persona_from_context(context, personas)

    # Get persona characteristics
    persona_chars = personas.get(inferred_persona, {}).get('characteristics', {})

    # Score different aspects
    tone_scores = score_tone_match(ground_truth, persona_chars)
    structure_scores = score_structure_match(ground_truth, persona_chars)

    # Calculate composite score
    all_scores = {**tone_scores, **structure_scores}
    if all_scores:
        composite = sum(all_scores.values()) / len(all_scores)
    else:
        composite = 0.5

    return {
        "pair_id": pair.get('id'),
        "inferred_persona": inferred_persona,
        "inference_confidence": confidence,
        "tone_scores": tone_scores,
        "structure_scores": structure_scores,
        "composite_score": composite,
        "ground_truth_summary": {
            "word_count": ground_truth.get('word_count', 0),
            "greeting": ground_truth.get('greeting', ''),
            "closing": ground_truth.get('closing', ''),
            "tone_hints": ground_truth.get('tone_hints', [])
        }
    }


def generate_refinement_suggestions(results: List[Dict], personas: Dict) -> List[Dict]:
    """Generate suggestions for persona refinement based on mismatches."""
    suggestions = []

    # Group results by persona
    by_persona = defaultdict(list)
    for r in results:
        by_persona[r['inferred_persona']].append(r)

    for persona_name, persona_results in by_persona.items():
        if not persona_results:
            continue

        persona_data = personas.get(persona_name, {})
        chars = persona_data.get('characteristics', {})

        # Analyze tone mismatches
        formality_scores = [r['tone_scores'].get('formality', 0.5) for r in persona_results]
        avg_formality = sum(formality_scores) / len(formality_scores)

        if avg_formality < 0.6:
            # Check if we're consistently over or under
            tone_hints = []
            for r in persona_results:
                tone_hints.extend(r['ground_truth_summary'].get('tone_hints', []))

            if tone_hints.count('formal') > tone_hints.count('casual'):
                suggestions.append({
                    "persona": persona_name,
                    "type": "formality",
                    "current": chars.get('formality', 5),
                    "suggestion": "Increase formality score",
                    "reason": f"Ground truth emails tend to be more formal than persona predicts"
                })
            elif tone_hints.count('casual') > tone_hints.count('formal'):
                suggestions.append({
                    "persona": persona_name,
                    "type": "formality",
                    "current": chars.get('formality', 5),
                    "suggestion": "Decrease formality score",
                    "reason": f"Ground truth emails tend to be more casual than persona predicts"
                })

        # Analyze contraction mismatches
        contraction_scores = [r['tone_scores'].get('contractions', 0.5) for r in persona_results]
        avg_contractions = sum(contraction_scores) / len(contraction_scores)

        if avg_contractions < 0.6:
            actual_contractions = sum(
                1 for r in persona_results
                if r['ground_truth_summary'].get('tone_hints', []) and
                'uses_contractions' in r['ground_truth_summary']['tone_hints']
            )
            if actual_contractions > len(persona_results) / 2:
                suggestions.append({
                    "persona": persona_name,
                    "type": "contractions",
                    "current": chars.get('uses_contractions', True),
                    "suggestion": "Set uses_contractions to true",
                    "reason": "Ground truth emails frequently use contractions"
                })
            else:
                suggestions.append({
                    "persona": persona_name,
                    "type": "contractions",
                    "current": chars.get('uses_contractions', True),
                    "suggestion": "Set uses_contractions to false",
                    "reason": "Ground truth emails rarely use contractions"
                })

        # Analyze greeting patterns
        greeting_scores = [r['structure_scores'].get('greeting', 0.5) for r in persona_results]
        avg_greeting = sum(greeting_scores) / len(greeting_scores)

        if avg_greeting < 0.6:
            # Find most common greeting in ground truth
            greetings = [r['ground_truth_summary'].get('greeting', '') for r in persona_results]
            greetings = [g for g in greetings if g]
            if greetings:
                most_common = max(set(greetings), key=greetings.count)
                suggestions.append({
                    "persona": persona_name,
                    "type": "greeting",
                    "current": chars.get('typical_greeting', ''),
                    "suggestion": f"Update typical_greeting to match: '{most_common}'",
                    "reason": "Ground truth emails use different greeting pattern"
                })

        # Analyze closing patterns
        closing_scores = [r['structure_scores'].get('closing', 0.5) for r in persona_results]
        avg_closing = sum(closing_scores) / len(closing_scores)

        if avg_closing < 0.6:
            closings = [r['ground_truth_summary'].get('closing', '') for r in persona_results]
            closings = [c for c in closings if c]
            if closings:
                most_common = max(set(closings), key=closings.count)
                suggestions.append({
                    "persona": persona_name,
                    "type": "closing",
                    "current": chars.get('typical_closing', ''),
                    "suggestion": f"Update typical_closing to match: '{most_common}'",
                    "reason": "Ground truth emails use different closing pattern"
                })

    return suggestions


def find_top_mismatches(results: List[Dict], limit: int = 5) -> List[Dict]:
    """Identify validation pairs with lowest composite scores.

    Returns the worst-scoring pairs for manual review.
    """
    sorted_results = sorted(results, key=lambda r: r['composite_score'])

    mismatches = []
    for r in sorted_results[:limit]:
        # Find weakest scoring areas
        all_scores = {**r['tone_scores'], **r['structure_scores']}
        weakest = sorted(all_scores.items(), key=lambda x: x[1])[:2]

        mismatches.append({
            "pair_id": r['pair_id'],
            "inferred_persona": r['inferred_persona'],
            "composite_score": r['composite_score'],
            "weakest_areas": [name for name, _ in weakest],
            "ground_truth": r['ground_truth_summary']
        })

    return mismatches


def run_auto_validation() -> bool:
    """Run automatic validation using heuristics."""
    personas = load_personas()
    pairs = load_validation_pairs()

    if not personas:
        print("No personas found. Run the analysis pipeline first.")
        return False

    if not pairs:
        print("No validation pairs found. Run prepare_validation.py first.")
        return False

    print(f"Running blind validation...")
    print(f"  Personas: {len(personas)}")
    print(f"  Validation pairs: {len(pairs)}")
    print()

    results = []
    for i, pair in enumerate(pairs, 1):
        result = score_validation_pair(pair, personas)
        results.append(result)

        score_indicator = "+" if result['composite_score'] >= 0.7 else "?" if result['composite_score'] >= 0.5 else "-"
        print(f"  {score_indicator} {pair['id'][:25]}... -> {result['inferred_persona']} ({result['composite_score']:.0%})")

    # Calculate overall scores
    overall_composite = sum(r['composite_score'] for r in results) / len(results)

    # Get average scores by category
    tone_avg = {}
    structure_avg = {}
    for key in ['formality', 'contractions', 'warmth']:
        scores = [r['tone_scores'].get(key, 0.5) for r in results]
        tone_avg[key] = sum(scores) / len(scores)
    for key in ['greeting', 'closing']:
        scores = [r['structure_scores'].get(key, 0.5) for r in results]
        structure_avg[key] = sum(scores) / len(scores)

    # Generate suggestions
    suggestions = generate_refinement_suggestions(results, personas)

    # Find top mismatches for manual review
    top_mismatches = find_top_mismatches(results, limit=5)

    # Build report
    report = {
        "created": datetime.now().isoformat(),
        "summary": {
            "total_pairs": len(pairs),
            "overall_score": round(overall_composite * 100),
            "tone_scores": {k: round(v * 100) for k, v in tone_avg.items()},
            "structure_scores": {k: round(v * 100) for k, v in structure_avg.items()}
        },
        "persona_breakdown": {},
        "refinement_suggestions": suggestions,
        "top_mismatches": top_mismatches,
        "detailed_results": results
    }

    # Persona breakdown
    by_persona = defaultdict(list)
    for r in results:
        by_persona[r['inferred_persona']].append(r)

    for persona_name, persona_results in by_persona.items():
        avg_score = sum(r['composite_score'] for r in persona_results) / len(persona_results)
        report['persona_breakdown'][persona_name] = {
            "count": len(persona_results),
            "average_score": round(avg_score * 100)
        }

    # Save results and report
    with open(VALIDATION_RESULTS_FILE, 'w') as f:
        json.dump({"results": results}, f, indent=2)

    with open(VALIDATION_REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("VALIDATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"\nOverall Score: {report['summary']['overall_score']}/100")
    print(f"\nTone Match:")
    for k, v in report['summary']['tone_scores'].items():
        bar = "+" * (v // 10) + "-" * (10 - v // 10)
        print(f"  {k:15} [{bar}] {v}%")
    print(f"\nStructure Match:")
    for k, v in report['summary']['structure_scores'].items():
        bar = "+" * (v // 10) + "-" * (10 - v // 10)
        print(f"  {k:15} [{bar}] {v}%")

    print(f"\nPersona Breakdown:")
    for name, data in report['persona_breakdown'].items():
        print(f"  {name}: {data['count']} emails, {data['average_score']}% match")

    if suggestions:
        print(f"\n{'=' * 60}")
        print("SUGGESTED REFINEMENTS")
        print(f"{'=' * 60}")
        for s in suggestions:
            print(f"\n  [{s['persona']}] {s['type'].upper()}")
            print(f"    Current: {s['current']}")
            print(f"    Suggestion: {s['suggestion']}")
            print(f"    Reason: {s['reason']}")

    # Always show top mismatches for manual review
    if top_mismatches:
        print(f"\n{'=' * 60}")
        print("TOP 5 MISMATCHES - REVIEW THESE")
        print(f"{'=' * 60}")
        for i, m in enumerate(top_mismatches, 1):
            print(f"\n  {i}. {m['pair_id']}")
            print(f"     Persona: {m['inferred_persona']}")
            print(f"     Score: {m['composite_score']:.0%}")
            print(f"     Weak areas: {', '.join(m['weakest_areas'])}")
            gt = m['ground_truth']
            if gt.get('greeting'):
                print(f"     Ground truth greeting: \"{gt['greeting']}\"")
            if gt.get('closing'):
                print(f"     Ground truth closing: \"{gt['closing']}\"")

        print(f"\n{'─' * 60}")
        print("ACTION REQUIRED: Review mismatches above and either:")
        print("  1. Update persona_registry.json with fixes")
        print("  2. Re-run validation to verify improvements")
        print("  3. Document why mismatches are acceptable")
        print(f"{'─' * 60}")

    print(f"\n{'=' * 60}")
    print(f"Reports saved to:")
    print(f"  {VALIDATION_REPORT_FILE}")
    print(f"  {VALIDATION_RESULTS_FILE}")
    print(f"{'=' * 60}")

    # Session boundary - explicit STOP
    print(f"\n{'█' * 60}")
    print("█  STOP - VALIDATION PHASE COMPLETE                        █")
    print("█                                                          █")
    print("█  DO NOT continue in this chat session.                   █")
    print("█  START A NEW CHAT for:                                   █")
    print("█    • LinkedIn analysis (Session 3)                       █")
    print("█    • Skill generation (Session 4)                        █")
    print("█                                                          █")
    print("█  Reason: Clean context improves output quality.          █")
    print(f"{'█' * 60}\n")

    return True


def show_status():
    """Show validation status."""
    print(f"\n{'=' * 50}")
    print("VALIDATION STATUS")
    print(f"{'=' * 50}")

    # Check prerequisites
    personas = load_personas()
    pairs = load_validation_pairs()

    print(f"\nPrerequisites:")
    print(f"  Personas:         {len(personas)} found" if personas else "  Personas:         None found")
    print(f"  Validation pairs: {len(pairs)} found" if pairs else "  Validation pairs: None found")

    if VALIDATION_REPORT_FILE.exists():
        with open(VALIDATION_REPORT_FILE) as f:
            report = json.load(f)
        print(f"\nLast validation:")
        print(f"  Date:           {report.get('created', 'Unknown')}")
        print(f"  Overall score:  {report['summary']['overall_score']}/100")
        print(f"  Suggestions:    {len(report.get('refinement_suggestions', []))}")
    else:
        print(f"\nValidation:       Not yet run")
        if personas and pairs:
            print(f"\nReady to validate! Run:")
            print(f"  python validate_personas.py --auto")

    print(f"{'=' * 50}\n")


def show_report():
    """Display the validation report."""
    if not VALIDATION_REPORT_FILE.exists():
        print("No validation report found. Run validation first:")
        print("  python validate_personas.py --auto")
        return

    with open(VALIDATION_REPORT_FILE) as f:
        report = json.load(f)

    print(f"\n{'=' * 60}")
    print("VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"Generated: {report.get('created', 'Unknown')}")
    print(f"\n--- SUMMARY ---")
    print(f"Overall Score: {report['summary']['overall_score']}/100")

    print(f"\n--- TONE MATCH ---")
    for k, v in report['summary']['tone_scores'].items():
        print(f"  {k}: {v}%")

    print(f"\n--- STRUCTURE MATCH ---")
    for k, v in report['summary']['structure_scores'].items():
        print(f"  {k}: {v}%")

    print(f"\n--- PERSONA BREAKDOWN ---")
    for name, data in report['persona_breakdown'].items():
        print(f"  {name}: {data['count']} emails, {data['average_score']}% match")

    suggestions = report.get('refinement_suggestions', [])
    if suggestions:
        print(f"\n--- REFINEMENT SUGGESTIONS ({len(suggestions)}) ---")
        for i, s in enumerate(suggestions, 1):
            print(f"\n  {i}. [{s['persona']}] {s['type']}")
            print(f"     {s['suggestion']}")
            print(f"     Reason: {s['reason']}")
    else:
        print(f"\n--- NO REFINEMENTS SUGGESTED ---")
        print("  Personas match validation data well!")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run blind validation against held-out emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_personas.py --auto     # Run automatic validation
  python validate_personas.py --status   # Show validation status
  python validate_personas.py --report   # Display validation report
        """
    )
    parser.add_argument("--auto", action="store_true", help="Run automatic validation")
    parser.add_argument("--status", action="store_true", help="Show validation status")
    parser.add_argument("--report", action="store_true", help="Display validation report")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.report:
        show_report()
    elif args.auto:
        run_auto_validation()
    else:
        # Default to showing status with help
        show_status()
        print("To run validation:")
        print("  python validate_personas.py --auto")
