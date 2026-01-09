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
    python validate_personas.py --interactive    # Interactive validation with feedback
    python validate_personas.py --health         # Check persona health (file naming, schema)
    python validate_personas.py --report         # Generate report from existing results
    python validate_personas.py --status         # Show validation status
"""

import json
import os
import re
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from config import get_data_dir, get_path
from api_keys import get_openrouter_key

PERSONA_REGISTRY_FILE = get_path("persona_registry.json")
VALIDATION_PAIRS_FILE = get_path("validation_pairs.json")
VALIDATION_RESULTS_FILE = get_path("validation_results.json")
VALIDATION_REPORT_FILE = get_path("validation_report.json")

# Required tone vector fields for valid personas
REQUIRED_TONE_VECTORS = ['formality', 'warmth', 'directness']
RECOMMENDED_TONE_VECTORS = ['authority']


# =============================================================================
# Issue #1: Health Check for Persona File Naming
# =============================================================================

def check_persona_health() -> Dict[str, Any]:
    """
    Check health of persona configuration.

    Detects common issues:
    - Wrong filename (personas.json instead of persona_registry.json)
    - Missing persona file
    - Schema validation issues

    Returns:
        Dict with 'healthy' bool and 'issues' dict
    """
    data_dir = get_data_dir()
    issues = {}

    # Check for wrong filename
    wrong_file = data_dir / "personas.json"
    correct_file = PERSONA_REGISTRY_FILE

    if wrong_file.exists() and not correct_file.exists():
        issues['wrong_filename'] = (
            f"personas.json exists but persona_registry.json does not. "
            f"The pipeline uses persona_registry.json. "
            f"Either rename the file or re-run ingest.py to generate proper personas."
        )

    # Check if correct file exists
    if not correct_file.exists():
        if not wrong_file.exists():
            issues['missing_file'] = (
                f"No persona file found. Run the analysis pipeline: "
                f"prepare_batch.py -> [analyze] -> ingest.py"
            )
    else:
        # Validate schema
        try:
            with open(correct_file) as f:
                data = json.load(f)

            personas = data.get('personas', {})
            if not personas:
                issues['empty_personas'] = "persona_registry.json exists but contains no personas"
            else:
                # Validate each persona
                schema_issues = []
                for name, persona_data in personas.items():
                    result = validate_persona_schema(name, persona_data)
                    if not result['valid']:
                        schema_issues.extend(result['errors'])

                if schema_issues:
                    issues['schema_errors'] = schema_issues
        except json.JSONDecodeError as e:
            issues['invalid_json'] = f"persona_registry.json is not valid JSON: {e}"

    return {
        'healthy': len(issues) == 0,
        'issues': issues,
        'checked_at': datetime.now().isoformat()
    }


# =============================================================================
# Issue #2: Schema Validation for Characteristics
# =============================================================================

def validate_persona_schema(name: str, persona_data: Dict) -> Dict[str, Any]:
    """
    Validate a persona's schema.

    Checks:
    - characteristics is a dict (not list)
    - Required tone vectors exist (formality, warmth, directness)
    - Values are numeric (1-10 scale)

    Args:
        name: Persona name for error messages
        persona_data: The persona dict to validate

    Returns:
        Dict with 'valid' bool, 'errors' list, 'warnings' list
    """
    errors = []
    warnings = []

    characteristics = persona_data.get('characteristics')

    # Check characteristics exists
    if characteristics is None:
        errors.append(f"[{name}] Missing 'characteristics' field")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Check characteristics is dict (Issue #2 - the RCA bug)
    if isinstance(characteristics, list):
        errors.append(
            f"[{name}] characteristics must be a dict with tone vectors, not a list. "
            f"Got: {characteristics[:3]}... "
            f"Expected: {{'formality': 5, 'warmth': 6, 'directness': 8, ...}}"
        )
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    if not isinstance(characteristics, dict):
        errors.append(f"[{name}] characteristics must be a dict, got {type(characteristics).__name__}")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Check required tone vectors
    for field in REQUIRED_TONE_VECTORS:
        if field not in characteristics:
            errors.append(
                f"[{name}] Missing required tone vector '{field}'. "
                f"Run analysis with calibration reference to generate proper vectors."
            )
        elif not isinstance(characteristics[field], (int, float)):
            errors.append(
                f"[{name}] Tone vector '{field}' must be numeric (1-10), "
                f"got {type(characteristics[field]).__name__}: {characteristics[field]}"
            )

    # Check recommended fields
    for field in RECOMMENDED_TONE_VECTORS:
        if field not in characteristics:
            warnings.append(f"[{name}] Missing recommended tone vector '{field}'")

    # Check for suspicious patterns (all same value = likely inferred, not analyzed)
    tone_values = [
        characteristics.get(f) for f in REQUIRED_TONE_VECTORS + RECOMMENDED_TONE_VECTORS
        if f in characteristics and isinstance(characteristics.get(f), (int, float))
    ]
    if len(tone_values) >= 3 and len(set(tone_values)) == 1:
        warnings.append(
            f"[{name}] All tone vectors have same value ({tone_values[0]}). "
            f"This suggests values were inferred rather than analyzed from actual emails. "
            f"Re-run analysis with calibration reference for accurate scoring."
        )

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def load_personas_with_validation() -> Tuple[Dict, List[str]]:
    """
    Load personas and validate their schema.

    Returns:
        Tuple of (personas dict, list of issues)
    """
    issues = []

    if not PERSONA_REGISTRY_FILE.exists():
        return {}, ["Persona registry file not found"]

    try:
        with open(PERSONA_REGISTRY_FILE) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {}, [f"Invalid JSON in persona registry: {e}"]

    personas = data.get('personas', {})

    for name, persona_data in personas.items():
        result = validate_persona_schema(name, persona_data)
        issues.extend(result['errors'])
        issues.extend(result['warnings'])

    return personas, issues


# =============================================================================
# Issue #3: Generated Reply Previews (LLM-based for true blind validation)
# =============================================================================

# OpenRouter configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_MODEL_CONFIG_FILE = get_path("openrouter_model.json")
DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

# Global state for LLM availability
_llm_checked = False
_llm_available = False
_selected_model = None


def _get_selected_model() -> str:
    """Get the selected OpenRouter model from config or return default."""
    global _selected_model

    if _selected_model:
        return _selected_model

    if OPENROUTER_MODEL_CONFIG_FILE.exists():
        try:
            with open(OPENROUTER_MODEL_CONFIG_FILE) as f:
                config = json.load(f)
                _selected_model = config.get('model', DEFAULT_MODEL)
                return _selected_model
        except (json.JSONDecodeError, IOError):
            pass

    _selected_model = DEFAULT_MODEL
    return _selected_model


def _save_selected_model(model_id: str):
    """Save the selected model to config file."""
    global _selected_model
    _selected_model = model_id

    config = {
        'model': model_id,
        'selected_at': datetime.now().isoformat()
    }
    with open(OPENROUTER_MODEL_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def check_model_configured() -> bool:
    """
    Check if a model has been explicitly configured by the user.

    Returns False if:
    - Config file doesn't exist
    - Config file is empty or invalid
    - Model field is missing

    This ensures users explicitly select a model rather than
    relying on potentially outdated defaults.
    """
    if not OPENROUTER_MODEL_CONFIG_FILE.exists():
        return False

    try:
        with open(OPENROUTER_MODEL_CONFIG_FILE) as f:
            config = json.load(f)
        return bool(config.get('model'))
    except (json.JSONDecodeError, IOError):
        return False


def fetch_openrouter_models(months_back: int = 6) -> List[Dict]:
    """
    Fetch available models from OpenRouter API.

    Args:
        months_back: Only include models created in the last N months

    Returns:
        List of model dicts with id, name, created, pricing info
    """
    api_key = get_openrouter_key(require=False)
    if not api_key:
        print("Error: OpenRouter API key not found (check Chatwise settings or OPENROUTER_API_KEY)")
        return []

    try:
        response = requests.get(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30
        )

        if response.status_code != 200:
            print(f"Error: OpenRouter API returned {response.status_code}")
            return []

        data = response.json()
        models = data.get('data', [])

        # Calculate cutoff timestamp (6 months ago)
        import time
        cutoff_timestamp = time.time() - (months_back * 30 * 24 * 60 * 60)

        # Filter models:
        # - Text input/output only (for email generation)
        # - Created in the last N months
        # - Has reasonable pricing (not free-tier only)
        filtered = []
        for m in models:
            # Check creation date
            created = m.get('created', 0)
            if created < cutoff_timestamp:
                continue

            # Check it supports text input/output
            arch = m.get('architecture', {})
            input_mods = arch.get('input_modalities', [])
            output_mods = arch.get('output_modalities', [])
            if 'text' not in input_mods or 'text' not in output_mods:
                continue

            # Get pricing info
            pricing = m.get('pricing', {})
            prompt_cost = float(pricing.get('prompt', '0') or '0')
            completion_cost = float(pricing.get('completion', '0') or '0')

            filtered.append({
                'id': m.get('id'),
                'name': m.get('name'),
                'created': created,
                'context_length': m.get('context_length', 0),
                'prompt_cost': prompt_cost,
                'completion_cost': completion_cost,
                'description': m.get('description', '')[:100]
            })

        # Sort by creation date (newest first)
        filtered.sort(key=lambda x: x['created'], reverse=True)

        return filtered

    except requests.exceptions.Timeout:
        print("Error: OpenRouter API timed out")
        return []
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []


def list_available_models():
    """List available OpenRouter models for the user to choose from."""
    print(f"\n{'=' * 70}")
    print("AVAILABLE OPENROUTER MODELS (Last 6 Months)")
    print(f"{'=' * 70}")

    models = fetch_openrouter_models(months_back=6)

    if not models:
        print("\nNo models found. Check your OPENROUTER_API_KEY.")
        return

    # Group by provider
    by_provider = defaultdict(list)
    for m in models:
        provider = m['id'].split('/')[0] if '/' in m['id'] else 'other'
        by_provider[provider].append(m)

    # Show top models from major providers
    major_providers = ['anthropic', 'openai', 'google', 'meta-llama', 'mistralai']

    print(f"\nCurrent model: {_get_selected_model()}")
    print(f"\n{'─' * 70}")

    shown_count = 0
    for provider in major_providers:
        if provider not in by_provider:
            continue

        provider_models = by_provider[provider][:5]  # Top 5 per provider
        print(f"\n[{provider.upper()}]")

        for m in provider_models:
            # Format pricing (per 1M tokens)
            prompt_per_m = m['prompt_cost'] * 1_000_000
            completion_per_m = m['completion_cost'] * 1_000_000

            created_date = datetime.fromtimestamp(m['created']).strftime('%Y-%m-%d')
            context_k = m['context_length'] // 1000

            print(f"  {m['id']}")
            print(f"    Name: {m['name']}")
            print(f"    Created: {created_date} | Context: {context_k}K")
            print(f"    Cost: ${prompt_per_m:.2f}/${completion_per_m:.2f} per 1M tokens (in/out)")
            shown_count += 1

    # Show count of other models
    other_count = len(models) - shown_count
    if other_count > 0:
        print(f"\n  ... and {other_count} more models from other providers")

    print(f"\n{'─' * 70}")
    print("\nTo select a model, run:")
    print(f"  python validate_personas.py --set-model 'model-id'")
    print(f"\nExample:")
    print(f"  python validate_personas.py --set-model 'anthropic/claude-sonnet-4-20250514'")
    print(f"{'=' * 70}\n")


def set_model(model_id: str) -> bool:
    """Set the model to use for validation."""
    # Verify the model exists
    models = fetch_openrouter_models(months_back=12)  # Allow slightly older for verification

    model_ids = [m['id'] for m in models]
    if model_id not in model_ids:
        print(f"Error: Model '{model_id}' not found in OpenRouter.")
        print(f"\nAvailable models (showing first 10):")
        for mid in model_ids[:10]:
            print(f"  - {mid}")
        return False

    _save_selected_model(model_id)
    print(f"Model set to: {model_id}")
    print(f"Saved to: {OPENROUTER_MODEL_CONFIG_FILE}")
    return True


def _check_llm_available() -> bool:
    """Check if OpenRouter API is available."""
    global _llm_checked, _llm_available

    if _llm_checked:
        return _llm_available

    _llm_checked = True
    api_key = get_openrouter_key(require=False)

    if not api_key:
        _llm_available = False
        return False

    _llm_available = True
    return True


def _show_llm_setup_instructions():
    """Show instructions for setting up OpenRouter API key."""
    print("\n" + "=" * 60)
    print("LLM-BASED VALIDATION REQUIRES OPENROUTER API KEY")
    print("=" * 60)
    print("\nFor true blind validation, an LLM generates replies from")
    print("the persona (without seeing actual emails). This requires")
    print("an OpenRouter API key.")
    print("\nSetup Options:")
    print()
    print("  Option 1: Configure in Chatwise (Recommended)")
    print("    Open Chatwise settings and add your OpenRouter API key.")
    print("    The skill will automatically detect it.")
    print()
    print("  Option 2: Environment Variable")
    print("    export OPENROUTER_API_KEY='your-key-here'")
    print("    (Add to ~/.bashrc or ~/.zshrc for persistence)")
    print()
    print("  Get your key at: https://openrouter.ai/keys")
    print()
    print("  (Optional) Choose a model:")
    print("    python validate_personas.py --list-models")
    print("    python validate_personas.py --set-model 'model-id'")
    print("\nFalling back to template-based generation (less accurate).")
    print("=" * 60 + "\n")


def generate_persona_reply_llm(persona: Dict, context: Dict) -> Optional[str]:
    """
    Generate a reply using LLM with ONLY persona + context (true blind validation).

    The LLM never sees the actual email content - only:
    - The persona characteristics (tone vectors, patterns)
    - The context (subject, quoted text from thread)

    This ensures the validation is truly blind - the LLM generating
    the reply has no knowledge of what was actually written.

    Args:
        persona: The persona dict with characteristics
        context: The email context (subject, quoted_text)

    Returns:
        Generated reply string, or None if LLM unavailable
    """
    api_key = get_openrouter_key(require=False)
    if not api_key:
        return None

    chars = persona.get('characteristics', {})

    # Build the prompt - ONLY persona info + context, NO actual reply
    prompt = f"""You are writing an email reply. Match this persona exactly:

PERSONA: {persona.get('name', 'Unknown')}
Description: {persona.get('description', 'N/A')}

TONE CHARACTERISTICS (1-10 scale):
- Formality: {chars.get('formality', 5)}/10
- Warmth: {chars.get('warmth', 5)}/10
- Directness: {chars.get('directness', 5)}/10
- Authority: {chars.get('authority', 5)}/10

STRUCTURAL PATTERNS:
- Typical greeting: {chars.get('typical_greeting', 'varies')}
- Typical closing: {chars.get('typical_closing', 'varies')}
- Uses contractions: {chars.get('uses_contractions', True)}

EMAIL CONTEXT TO REPLY TO:
Subject: {context.get('subject', 'No subject')}
Message from sender: {context.get('quoted_text', 'N/A')[:500]}

Write a SHORT reply (2-4 sentences max) that matches this persona's voice exactly.
Use the greeting/closing patterns shown above.
Match the formality and tone levels precisely.
Do NOT explain or add commentary - just write the email reply itself."""

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/writing-style-clone",
                "X-Title": "Writing Style Clone Validation"
            },
            json={
                "model": _get_selected_model(),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"Warning: OpenRouter API returned {response.status_code}")
            return None

        data = response.json()
        return data['choices'][0]['message']['content'].strip()

    except requests.exceptions.Timeout:
        print("Warning: OpenRouter API timed out")
        return None
    except Exception as e:
        print(f"Warning: LLM generation failed: {e}")
        return None


def generate_persona_reply_template(persona: Dict, context: Dict) -> str:
    """
    Generate a sample reply using templates (fallback when LLM unavailable).

    This creates a template-based reply that reflects the persona's
    greeting/closing patterns and tone characteristics.

    Args:
        persona: The persona dict with characteristics
        context: The email context (subject, quoted_text)

    Returns:
        A sample reply string
    """
    chars = persona.get('characteristics', {})

    # Get greeting
    greeting = chars.get('typical_greeting', '')
    if not greeting:
        formality = chars.get('formality', 5)
        if formality >= 7:
            greeting = "Good afternoon,"
        elif formality >= 5:
            greeting = "Hi,"
        else:
            greeting = "Hey"

    # Get closing
    closing = chars.get('typical_closing', '')
    if not closing:
        formality = chars.get('formality', 5)
        if formality >= 7:
            closing = "Best regards,"
        elif formality >= 5:
            closing = "Best,"
        else:
            closing = "Thanks"

    # Build body based on characteristics
    directness = chars.get('directness', 5)
    warmth = chars.get('warmth', 5)
    authority = chars.get('authority', 5)

    # Subject-aware opener
    subject = context.get('subject', '')
    if 'update' in subject.lower():
        if directness >= 7:
            body = "Here's the update:"
        else:
            body = "I wanted to share an update on this."
    elif 'question' in subject.lower() or '?' in context.get('quoted_text', ''):
        if directness >= 7:
            body = "Quick answer:"
        elif warmth >= 6:
            body = "Happy to help with this."
        else:
            body = "Here's what I can share:"
    else:
        if directness >= 7:
            body = "Three things:"
        elif authority >= 7:
            body = "Here's my take:"
        else:
            body = "Thanks for reaching out."

    # Add contractions based on setting
    uses_contractions = chars.get('uses_contractions', True)
    if not uses_contractions:
        body = body.replace("Here's", "Here is").replace("I'm", "I am")

    # Assemble reply
    parts = []
    if greeting:
        parts.append(greeting)
    parts.append("")
    parts.append(body)
    parts.append("")
    if closing:
        parts.append(closing)

    return "\n".join(parts)


def generate_persona_reply(persona: Dict, context: Dict, use_llm: bool = True) -> str:
    """
    Generate a reply based on persona characteristics.

    For true blind validation, uses OpenRouter LLM when OPENROUTER_API_KEY is set.
    The LLM only sees the persona + context, never the actual email - ensuring
    the validation is truly blind.

    Falls back to template-based generation if no API key is configured.

    Args:
        persona: The persona dict with characteristics
        context: The email context (subject, quoted_text)
        use_llm: Whether to attempt LLM generation (default True)

    Returns:
        A sample reply string
    """
    if use_llm and _check_llm_available():
        llm_reply = generate_persona_reply_llm(persona, context)
        if llm_reply:
            return llm_reply

    # Fallback to template
    return generate_persona_reply_template(persona, context)


# =============================================================================
# Issue #4: Interactive Validation
# =============================================================================

class InteractiveValidator:
    """
    Interactive validation session manager.

    Tracks user feedback on mismatches and generates refinement suggestions.
    """

    def __init__(self):
        self.feedback: List[Dict] = []
        self.session_started = datetime.now().isoformat()

    def record_feedback(
        self,
        pair_id: str,
        persona: str,
        sounds_like_me: bool,
        user_notes: Optional[str] = None
    ):
        """Record user feedback on a validation pair."""
        self.feedback.append({
            'pair_id': pair_id,
            'persona': persona,
            'sounds_like_me': sounds_like_me,
            'user_notes': user_notes,
            'recorded_at': datetime.now().isoformat()
        })

    def get_refinement_suggestions(self) -> List[Dict]:
        """Generate refinement suggestions based on collected feedback."""
        suggestions = []

        # Group feedback by persona
        by_persona = defaultdict(list)
        for fb in self.feedback:
            by_persona[fb['persona']].append(fb)

        for persona_name, persona_feedback in by_persona.items():
            negative = [f for f in persona_feedback if not f['sounds_like_me']]
            positive = [f for f in persona_feedback if f['sounds_like_me']]

            if len(negative) > len(positive):
                # More negative than positive - persona needs work
                notes = [f['user_notes'] for f in negative if f['user_notes']]
                suggestions.append({
                    'persona': persona_name,
                    'type': 'needs_refinement',
                    'confidence': len(negative) / len(persona_feedback),
                    'negative_count': len(negative),
                    'positive_count': len(positive),
                    'user_notes': notes,
                    'suggestion': (
                        f"Persona '{persona_name}' had {len(negative)} negative responses. "
                        f"Review the tone vectors and adjust based on user feedback."
                    )
                })
            elif len(positive) >= 3 and len(negative) == 0:
                suggestions.append({
                    'persona': persona_name,
                    'type': 'well_calibrated',
                    'positive_count': len(positive),
                    'suggestion': f"Persona '{persona_name}' is well-calibrated."
                })

        return suggestions

    def save_feedback(self, filepath: Path):
        """Save feedback to file."""
        data = {
            'session_started': self.session_started,
            'feedback': self.feedback,
            'suggestions': self.get_refinement_suggestions()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def format_mismatch_comparison(mismatch: Dict) -> str:
    """
    Format a mismatch for display, showing actual vs generated reply.

    Args:
        mismatch: Dict with ground_truth, generated_reply, context

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"MISMATCH: {mismatch.get('pair_id', mismatch.get('id', 'Unknown'))}")
    lines.append(f"Persona: {mismatch.get('inferred_persona', 'Unknown')}")
    lines.append(f"Score: {mismatch.get('composite_score', 0):.0%}")
    lines.append("=" * 60)

    # Context
    context = mismatch.get('context', {})
    lines.append(f"\n--- CONTEXT ---")
    lines.append(f"Subject: {context.get('subject', 'N/A')}")
    if context.get('quoted_text'):
        quoted = context['quoted_text'][:200]
        if len(context['quoted_text']) > 200:
            quoted += "..."
        lines.append(f"Quoted: {quoted}")

    # Ground truth (actual)
    gt = mismatch.get('ground_truth', {})
    lines.append(f"\n--- ACTUAL (Ground Truth) ---")
    reply_text = gt.get('reply_text', '')
    if reply_text:
        lines.append(reply_text[:500])
        if len(reply_text) > 500:
            lines.append("...")
    else:
        lines.append(f"Greeting: {gt.get('greeting', 'N/A')}")
        lines.append(f"Closing: {gt.get('closing', 'N/A')}")

    # Generated (what persona would write)
    generated = mismatch.get('generated_reply', '')
    if generated:
        lines.append(f"\n--- GENERATED (Persona Would Write) ---")
        lines.append(generated)

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


def run_interactive_validation() -> bool:
    """
    Output detailed mismatch review for LLM analysis.

    Since this script is called by an LLM via shell command,
    this outputs structured data rather than using stdin.
    The LLM can then use --feedback to record responses.

    Uses OpenRouter LLM to generate truly blind replies (LLM only sees
    persona + context, never the actual email).
    """
    personas = load_personas()
    pairs = load_validation_pairs()

    if not personas:
        print("No personas found. Run the analysis pipeline first.")
        return False

    if not pairs:
        print("No validation pairs found. Run prepare_validation.py first.")
        return False

    # Check LLM availability and show instructions if needed
    llm_available = _check_llm_available()
    if not llm_available:
        _show_llm_setup_instructions()

    # Score all pairs first
    results = []
    for pair in pairs:
        result = score_validation_pair(pair, personas)
        results.append(result)

    # Find mismatches (low scores)
    mismatches = find_top_mismatches(results, personas, pairs, limit=10)

    if not mismatches:
        print("No significant mismatches found. Personas look well-calibrated!")
        return True

    print(f"\n{'=' * 60}")
    print("MISMATCH REVIEW - ANALYZE THESE")
    print(f"{'=' * 60}")
    print(f"Personas: {len(personas)}")
    print(f"Mismatches found: {len(mismatches)}")
    print(f"Generation mode: {'LLM (true blind)' if llm_available else 'Template (fallback)'}")
    print(f"\nFor each mismatch, determine:")
    print("  1. Does the GENERATED reply sound like the user?")
    print("  2. If not, what's wrong with the persona?")
    print(f"{'=' * 60}\n")

    for i, mismatch in enumerate(mismatches, 1):
        print(f"\n[{i}/{len(mismatches)}]")
        print(format_mismatch_comparison(mismatch))

    # Output JSON for programmatic processing
    review_file = get_path("validation_review.json")
    review_data = {
        "created": datetime.now().isoformat(),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "instructions": (
            "Review each mismatch. Use --feedback to record responses: "
            "python validate_personas.py --feedback '<pair_id>' --sounds-like-me false --notes 'reason'"
        )
    }
    with open(review_file, 'w') as f:
        json.dump(review_data, f, indent=2)

    print(f"\n{'=' * 60}")
    print("NEXT STEPS")
    print(f"{'=' * 60}")
    print(f"\nReview data saved to: {review_file}")
    print(f"\nTo record feedback on a mismatch:")
    print(f"  python validate_personas.py --feedback '<pair_id>' --sounds-like-me true")
    print(f"  python validate_personas.py --feedback '<pair_id>' --sounds-like-me false --notes 'too formal'")
    print(f"\nTo see accumulated suggestions:")
    print(f"  python validate_personas.py --suggestions")
    print(f"{'=' * 60}\n")

    return True


def record_feedback_cli(pair_id: str, sounds_like_me: bool, notes: Optional[str] = None) -> bool:
    """
    Record feedback for a validation pair via CLI.

    This allows the LLM to record feedback without interactive stdin.
    """
    feedback_file = get_path("validation_feedback.json")

    # Load existing feedback
    existing_feedback = []
    if feedback_file.exists():
        try:
            with open(feedback_file) as f:
                data = json.load(f)
                existing_feedback = data.get('feedback', [])
        except (json.JSONDecodeError, IOError):
            pass

    # Find the persona for this pair
    personas = load_personas()
    pairs = load_validation_pairs()

    inferred_persona = "Unknown"
    for pair in pairs:
        pid = pair.get('id') or pair.get('pair_id', '')
        if pid == pair_id:
            result = score_validation_pair(pair, personas)
            inferred_persona = result.get('inferred_persona', 'Unknown')
            break

    # Add new feedback
    existing_feedback.append({
        'pair_id': pair_id,
        'persona': inferred_persona,
        'sounds_like_me': sounds_like_me,
        'user_notes': notes,
        'recorded_at': datetime.now().isoformat()
    })

    # Save
    with open(feedback_file, 'w') as f:
        json.dump({
            'feedback': existing_feedback,
            'updated': datetime.now().isoformat()
        }, f, indent=2)

    status = "POSITIVE" if sounds_like_me else "NEGATIVE"
    print(f"Feedback recorded: {pair_id} -> {status}")
    if notes:
        print(f"  Notes: {notes}")

    return True


def show_suggestions() -> bool:
    """
    Show refinement suggestions based on accumulated feedback.
    """
    feedback_file = get_path("validation_feedback.json")

    if not feedback_file.exists():
        print("No feedback recorded yet.")
        print("Run: python validate_personas.py --review")
        print("Then: python validate_personas.py --feedback '<pair_id>' --sounds-like-me true/false")
        return False

    with open(feedback_file) as f:
        data = json.load(f)

    feedback_list = data.get('feedback', [])

    if not feedback_list:
        print("No feedback recorded yet.")
        return False

    # Use InteractiveValidator to generate suggestions
    validator = InteractiveValidator()
    validator.feedback = feedback_list

    suggestions = validator.get_refinement_suggestions()

    print(f"\n{'=' * 60}")
    print("REFINEMENT SUGGESTIONS")
    print(f"{'=' * 60}")
    print(f"Based on {len(feedback_list)} feedback items")

    if not suggestions:
        print("\nNo strong suggestions yet. Need more feedback data.")
    else:
        for s in suggestions:
            print(f"\n[{s['persona']}] {s['type'].upper()}")
            print(f"  {s['suggestion']}")
            if s.get('user_notes'):
                print(f"  User notes: {', '.join(s['user_notes'][:3])}")
            if s.get('positive_count'):
                print(f"  Positive responses: {s['positive_count']}")
            if s.get('negative_count'):
                print(f"  Negative responses: {s['negative_count']}")

    print(f"\n{'=' * 60}\n")

    return True


# =============================================================================
# Issue #5: Field Name Consistency
# =============================================================================

def normalize_validation_pair(pair: Dict) -> Dict:
    """
    Normalize field names in validation pair.

    Handles various ID field names: id, pair_id, email_id
    Always outputs 'id' for consistency.

    Args:
        pair: Validation pair dict with any ID field format

    Returns:
        Normalized pair with 'id' field
    """
    normalized = dict(pair)

    # Find ID from various possible fields
    pair_id = (
        pair.get('id') or
        pair.get('pair_id') or
        pair.get('email_id') or
        ''
    )

    # Set consistent 'id' field
    normalized['id'] = pair_id

    # Remove inconsistent fields if present
    for field in ['pair_id', 'email_id']:
        if field in normalized and field != 'id':
            # Keep for backwards compatibility but ensure 'id' exists
            pass

    return normalized


def extract_mismatch_details(result: Dict, pairs: List[Dict]) -> Optional[Dict]:
    """
    Extract mismatch details by finding the corresponding validation pair.

    Handles both 'id' and 'pair_id' field names.

    Args:
        result: Scoring result dict
        pairs: List of validation pairs

    Returns:
        Dict with merged details, or None if not found
    """
    # Get ID from result (might be 'pair_id' or 'id')
    result_id = result.get('id') or result.get('pair_id', '')

    # Find matching pair
    for pair in pairs:
        pair_id = pair.get('id') or pair.get('pair_id') or pair.get('email_id', '')
        if pair_id == result_id:
            return {
                'id': result_id,
                'pair_id': result_id,  # Keep for backwards compatibility
                'inferred_persona': result.get('inferred_persona'),
                'composite_score': result.get('composite_score', 0),
                'context': pair.get('context', {}),
                'ground_truth': pair.get('ground_truth', {}),
                'tone_scores': result.get('tone_scores', {}),
                'structure_scores': result.get('structure_scores', {})
            }

    return None


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
    # Normalize pair to ensure consistent 'id' field (Issue #5)
    pair = normalize_validation_pair(pair)

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

    # Use consistent 'id' field (Issue #5)
    return {
        "id": pair.get('id'),  # Consistent field name
        "pair_id": pair.get('id'),  # Keep for backwards compatibility
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


def find_top_mismatches(
    results: List[Dict],
    personas: Optional[Dict] = None,
    validation_pairs: Optional[List[Dict]] = None,
    limit: int = 5
) -> List[Dict]:
    """Identify validation pairs with lowest composite scores.

    Returns the worst-scoring pairs for manual review, including
    generated reply previews (Issue #3).

    Args:
        results: List of scoring results
        personas: Dict of personas (for generating replies)
        validation_pairs: Original validation pairs (for context)
        limit: Max number of mismatches to return
    """
    sorted_results = sorted(results, key=lambda r: r['composite_score'])

    # Build lookup for validation pairs
    pairs_by_id = {}
    if validation_pairs:
        for pair in validation_pairs:
            pair_id = pair.get('id') or pair.get('pair_id') or pair.get('email_id', '')
            pairs_by_id[pair_id] = pair

    mismatches = []
    for r in sorted_results[:limit]:
        # Find weakest scoring areas
        all_scores = {**r['tone_scores'], **r['structure_scores']}
        weakest = sorted(all_scores.items(), key=lambda x: x[1])[:2]

        # Get the ID consistently (Issue #5)
        result_id = r.get('id') or r.get('pair_id', '')

        mismatch = {
            "id": result_id,  # Consistent field name
            "pair_id": result_id,  # Keep for backwards compatibility
            "inferred_persona": r['inferred_persona'],
            "composite_score": r['composite_score'],
            "weakest_areas": [name for name, _ in weakest],
            "ground_truth": r['ground_truth_summary']
        }

        # Add context from validation pair if available
        if result_id in pairs_by_id:
            pair = pairs_by_id[result_id]
            mismatch['context'] = pair.get('context', {})
            # Include full ground truth for display
            mismatch['ground_truth'] = pair.get('ground_truth', r['ground_truth_summary'])

        # Generate reply preview (Issue #3)
        if personas and r['inferred_persona'] in personas:
            persona = personas[r['inferred_persona']]
            context = mismatch.get('context', {})
            mismatch['generated_reply'] = generate_persona_reply(persona, context)

        mismatches.append(mismatch)

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

    # Check if model selection is required (when OpenRouter API is available)
    if _check_llm_available() and not check_model_configured():
        print(f"\n{'═' * 60}")
        print("⚠️  MODEL SELECTION REQUIRED")
        print(f"{'═' * 60}")
        print("""
OpenRouter API key found, but no model has been selected.

Models can become unavailable or outdated. You must explicitly
select a model before running LLM-based validation.

REQUIRED STEPS:

1. List available models (fetches from OpenRouter):
   python validate_personas.py --list-models

2. Select your preferred model:
   python validate_personas.py --set-model 'anthropic/claude-sonnet-4-20250514'

Then re-run validation.
""")
        print(f"{'═' * 60}\n")
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

    # Find top mismatches for manual review (Issue #3: include generated replies)
    top_mismatches = find_top_mismatches(results, personas, pairs, limit=5)

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
    print("PHASE 1 COMPLETE: Automatic Validation")
    print(f"{'=' * 60}")
    print(f"\nOverall Score: {report['summary']['overall_score']}/100")
    print(f"(Heuristic-based estimate - see Phase 2 for accurate validation)")
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

    # Always show top mismatches for manual review (Issue #3: show generated replies)
    if top_mismatches:
        print(f"\n{'=' * 60}")
        print("TOP 5 MISMATCHES - REVIEW THESE")
        print(f"{'=' * 60}")
        for i, m in enumerate(top_mismatches, 1):
            print(f"\n  {i}. {m.get('id', m.get('pair_id', 'Unknown'))}")
            print(f"     Persona: {m['inferred_persona']}")
            print(f"     Score: {m['composite_score']:.0%}")
            print(f"     Weak areas: {', '.join(m['weakest_areas'])}")
            gt = m['ground_truth']
            if gt.get('greeting'):
                print(f"     Actual greeting: \"{gt['greeting']}\"")
            if gt.get('closing'):
                print(f"     Actual closing: \"{gt['closing']}\"")

            # Issue #3: Show generated reply preview
            if m.get('generated_reply'):
                print(f"\n     --- PERSONA WOULD WRITE ---")
                for line in m['generated_reply'].split('\n')[:5]:
                    print(f"     {line}")
                print(f"     --- END PREVIEW ---")

        print(f"\n{'─' * 60}")
        print("ACTION REQUIRED: Review mismatches above and either:")
        print("  1. Update persona_registry.json with fixes")
        print("  2. Run interactive validation: python validate_personas.py --interactive")
        print("  3. Re-run validation to verify improvements")
        print(f"{'─' * 60}")

    print(f"\n{'=' * 60}")
    print(f"Reports saved to:")
    print(f"  {VALIDATION_REPORT_FILE}")
    print(f"  {VALIDATION_RESULTS_FILE}")
    print(f"{'=' * 60}")

    # Phase 2 requirement message
    print(f"\n{'=' * 60}")
    print("PHASE 2 REQUIRED: Interactive Validation")
    print(f"{'=' * 60}")
    print("""
The automatic validation provides a BASELINE score using heuristics,
but does NOT test real generated text. To properly calibrate your
personas, you MUST complete the interactive validation phase.

NEXT STEPS (REQUIRED):

1. Review generated replies side-by-side with your actual emails:
   python validate_personas.py --review

2. Judge each mismatch: "Does this sound like me?"
   python validate_personas.py --feedback <email_id> --sounds-like-me true
   python validate_personas.py --feedback <email_id> --sounds-like-me false --notes "why"

3. Get refinement suggestions based on your feedback:
   python validate_personas.py --suggestions

4. Apply refinements to persona_registry.json and re-validate

This is the FINE-TUNING phase - critical for persona accuracy.
""")
    print(f"{'=' * 60}")
    print("DO NOT PROCEED TO GENERATION UNTIL PHASE 2 IS COMPLETE")
    print(f"{'=' * 60}\n")

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


def show_health():
    """Display persona health check results (Issue #1)."""
    print(f"\n{'=' * 60}")
    print("PERSONA HEALTH CHECK")
    print(f"{'=' * 60}")

    result = check_persona_health()

    if result['healthy']:
        print("\nStatus: HEALTHY")
        print("All checks passed.")
    else:
        print("\nStatus: ISSUES DETECTED")
        print(f"\nProblems found: {len(result['issues'])}")

        for issue_type, issue_desc in result['issues'].items():
            print(f"\n[{issue_type.upper()}]")
            if isinstance(issue_desc, list):
                for item in issue_desc:
                    print(f"  - {item}")
            else:
                print(f"  {issue_desc}")

    print(f"\n{'=' * 60}")

    # Also validate schema if file exists
    personas, schema_issues = load_personas_with_validation()
    if schema_issues:
        print("\nSCHEMA VALIDATION:")
        for issue in schema_issues:
            print(f"  - {issue}")
    elif personas:
        print(f"\nPersonas loaded: {len(personas)}")
        for name, data in personas.items():
            chars = data.get('characteristics', {})
            if isinstance(chars, dict):
                vectors = [f"{k}={v}" for k, v in chars.items()
                          if k in REQUIRED_TONE_VECTORS + RECOMMENDED_TONE_VECTORS]
                print(f"  - {name}: {', '.join(vectors)}")

    print(f"\n{'=' * 60}\n")

    return result['healthy']


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run blind validation against held-out emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_personas.py --auto        # Run automatic validation
  python validate_personas.py --review      # Review mismatches with generated replies
  python validate_personas.py --health      # Check persona health (file naming, schema)
  python validate_personas.py --status      # Show validation status
  python validate_personas.py --report      # Display validation report

Model selection (for LLM-based validation):
  python validate_personas.py --list-models                               # See available models
  python validate_personas.py --set-model 'anthropic/claude-sonnet-4-20250514'

Feedback workflow (for LLM-driven refinement):
  python validate_personas.py --review                                    # See mismatches
  python validate_personas.py --feedback 'email_001' --sounds-like-me true
  python validate_personas.py --feedback 'email_002' --sounds-like-me false --notes 'too formal'
  python validate_personas.py --suggestions                               # See refinement suggestions
        """
    )
    parser.add_argument("--auto", action="store_true", help="Run automatic validation")
    parser.add_argument("--review", action="store_true", help="Review mismatches with generated replies")
    parser.add_argument("--health", action="store_true", help="Check persona health (file naming, schema)")
    parser.add_argument("--status", action="store_true", help="Show validation status")
    parser.add_argument("--report", action="store_true", help="Display validation report")

    # Model selection options
    parser.add_argument("--list-models", action="store_true", help="List available OpenRouter models (last 6 months)")
    parser.add_argument("--set-model", metavar="MODEL_ID", help="Set the model to use for LLM validation")

    # Feedback options (for LLM-driven refinement)
    parser.add_argument("--feedback", metavar="PAIR_ID", help="Record feedback for a validation pair")
    parser.add_argument("--sounds-like-me", type=lambda x: x.lower() == 'true',
                        help="Whether the generated reply sounds like the user (true/false)")
    parser.add_argument("--notes", help="Optional notes about why feedback is negative")
    parser.add_argument("--suggestions", action="store_true", help="Show refinement suggestions from feedback")

    args = parser.parse_args()

    if args.list_models:
        list_available_models()
    elif args.set_model:
        set_model(args.set_model)
    elif args.health:
        show_health()
    elif args.feedback:
        if args.sounds_like_me is None:
            print("Error: --sounds-like-me is required with --feedback")
            print("Usage: python validate_personas.py --feedback 'pair_id' --sounds-like-me true/false")
            sys.exit(1)
        record_feedback_cli(args.feedback, args.sounds_like_me, args.notes)
    elif args.suggestions:
        show_suggestions()
    elif args.review:
        run_interactive_validation()
    elif args.status:
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
        print("  python validate_personas.py --review      # Review with generated replies")
        print("  python validate_personas.py --health      # Check for issues")
        print("  python validate_personas.py --list-models # Choose LLM model")
