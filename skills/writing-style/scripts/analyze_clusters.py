#!/usr/bin/env python3
"""
Parallel Cluster Analysis - Analyze email clusters via OpenRouter API

Parallelizes the email cluster analysis phase using ThreadPoolExecutor,
replacing the sequential workflow where the main LLM processes one cluster at a time.

Usage:
    python analyze_clusters.py                    # Run full analysis pipeline
    python analyze_clusters.py --estimate         # Show cost estimate without running
    python analyze_clusters.py --dry-run          # Simulate without API calls
    python analyze_clusters.py --review           # Show draft results for review
    python analyze_clusters.py --approve          # Approve and ingest all drafts
    python analyze_clusters.py --reject           # Discard draft and reset

Requirements:
    - OpenRouter API key configured (via Chatwise or OPENROUTER_API_KEY env var)
    - Model selected via validate_personas.py --set-model
    - Completed clustering phase (clusters.json exists)
"""

import json
import argparse
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Local imports
from config import get_data_dir, get_path
from api_keys import get_openrouter_key
from email_analysis_v2 import (
    compute_deterministic_metrics,
    infer_email_types,
    select_example_bank,
    get_v2_schema_template
)
from json_repair import (
    safe_parse_json,
    validate_analysis_schema,
    get_retry_prompt
)

# Calibration reference (static path)
CALIBRATION_FILE = Path(__file__).parent.parent / "references" / "calibration.md"


# Dynamic path getters (for testability)
def _get_clusters_file() -> Path:
    return get_path("clusters.json")


def _get_enriched_dir() -> Path:
    return get_path("enriched_samples")


def _get_samples_dir() -> Path:
    return get_path("samples")


def _get_draft_file() -> Path:
    return get_path("analysis_draft.json")


def _get_model_config_file() -> Path:
    return get_path("openrouter_model.json")

# OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model pricing (per 1M tokens) - Updated January 2026
MODEL_PRICING = {
    # Gemini models (1M context - ideal for large batches)
    "google/gemini-3-flash-preview": {"input": 0.50, "output": 3.0},
    "google/gemini-2.5-flash": {"input": 0.30, "output": 2.5},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "google/gemini-2.0-flash-lite-001": {"input": 0.075, "output": 0.30},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    # Claude models
    "anthropic/claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
    "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "anthropic/claude-haiku-4.5": {"input": 1.0, "output": 5.0},
    "anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.0},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    # Other options
    "qwen/qwen-turbo": {"input": 0.05, "output": 0.20},
    "amazon/nova-lite-v1": {"input": 0.06, "output": 0.24},
    "default": {"input": 1.0, "output": 5.0}
}

# Recommended models by use case
RECOMMENDED_MODELS = {
    "cost_effective": "google/gemini-3-flash-preview",  # Best balance, 1M context
    "budget": "google/gemini-2.0-flash-lite-001",  # Cheapest with 1M context
    "quality": "anthropic/claude-sonnet-4.5",  # Highest quality
}

# Default model for new installations
DEFAULT_MODEL = "google/gemini-3-flash-preview"

# Default max emails per batch (to stay within token limits)
DEFAULT_MAX_EMAILS_PER_BATCH = 150


# =============================================================================
# Configuration and Model Management
# =============================================================================

def _get_selected_model() -> str:
    """Get the selected OpenRouter model from config or return default."""
    config_file = _get_model_config_file()
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get('model', DEFAULT_MODEL)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_MODEL


def check_model_configured() -> bool:
    """Check if an OpenRouter model has been configured."""
    config_file = _get_model_config_file()
    if not config_file.exists():
        return False
    try:
        with open(config_file) as f:
            config = json.load(f)
        return bool(config.get('model'))
    except (json.JSONDecodeError, IOError):
        return False


# =============================================================================
# Preparation Phase
# =============================================================================

def load_cluster_data() -> Optional[Dict]:
    """Load clusters.json data."""
    clusters_file = _get_clusters_file()
    if not clusters_file.exists():
        return None
    try:
        with open(clusters_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_analyzed_ids() -> set:
    """Get set of email IDs that have already been analyzed."""
    analyzed = set()
    samples_dir = _get_samples_dir()
    if samples_dir.exists():
        for f in samples_dir.glob("*.json"):
            analyzed.add(f.stem)
    return analyzed


def load_unanalyzed_clusters() -> List[Dict]:
    """
    Load clusters.json and identify clusters that need analysis.

    Returns list of cluster dicts with additional 'remaining_ids' and 'remaining_count' fields.
    """
    clusters_data = load_cluster_data()
    if not clusters_data:
        return []

    analyzed_ids = get_analyzed_ids()

    result = []
    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue

        sample_ids = cluster.get('sample_ids', [])
        remaining = [sid for sid in sample_ids if sid not in analyzed_ids]

        if remaining:
            cluster_copy = dict(cluster)
            cluster_copy['remaining_ids'] = remaining
            cluster_copy['remaining_count'] = len(remaining)
            cluster_copy['analyzed_count'] = len(sample_ids) - len(remaining)
            result.append(cluster_copy)

    return result


def load_calibration() -> str:
    """Load calibration reference content."""
    if CALIBRATION_FILE.exists():
        return CALIBRATION_FILE.read_text()
    return "## Calibration Reference\n\nUse tone vectors on a scale of 1-10."


def get_cluster_emails(cluster: Dict) -> List[Dict]:
    """Load emails for a cluster from enriched_samples/."""
    emails = []
    sample_ids = cluster.get('remaining_ids', cluster.get('sample_ids', []))
    enriched_dir = _get_enriched_dir()

    for email_id in sample_ids:
        enriched_path = enriched_dir / f"{email_id}.json"
        if enriched_path.exists():
            try:
                with open(enriched_path) as f:
                    email_data = json.load(f)
                    email_data['id'] = email_id
                    emails.append(email_data)
            except (json.JSONDecodeError, IOError):
                continue

    return emails


def build_analysis_prompt(
    cluster: Dict,
    emails: List[Dict],
    calibration: str,
    deterministic_metrics: Optional[Dict] = None
) -> str:
    """
    Build the LLM prompt for analyzing a single cluster.

    V2 Enhanced: Includes pre-computed deterministic metrics and requests
    expanded schema fields with _instruction siblings.

    Args:
        cluster: Cluster metadata (id, size, enrichment_summary)
        emails: List of email dicts with body, subject, enrichment
        calibration: Calibration reference content
        deterministic_metrics: Pre-computed Python analysis (optional)

    Returns:
        Complete prompt string for LLM
    """
    prompt_parts = []

    # Calibration reference
    prompt_parts.append(calibration)
    prompt_parts.append("\n" + "=" * 60 + "\n")

    # Cluster context
    prompt_parts.append(f"# Cluster {cluster.get('id', 'Unknown')} Analysis\n")
    prompt_parts.append(f"**Cluster size:** {cluster.get('size', len(emails))} emails")
    prompt_parts.append(f"**Emails to analyze:** {len(emails)}")

    # Enrichment summary if available
    enrichment_summary = cluster.get('enrichment_summary', {})
    if enrichment_summary:
        prompt_parts.append(f"\n**Cluster characteristics:**")
        if enrichment_summary.get('recipient_types'):
            prompt_parts.append(f"- Recipient types: {enrichment_summary['recipient_types']}")
        if enrichment_summary.get('audiences'):
            prompt_parts.append(f"- Audiences: {enrichment_summary['audiences']}")
        if enrichment_summary.get('recipient_seniorities'):
            prompt_parts.append(f"- Recipient seniorities: {enrichment_summary['recipient_seniorities']}")

    # Include pre-computed deterministic metrics (v2)
    if deterministic_metrics:
        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("\n## Pre-Computed Metrics (Python Analysis)\n")
        prompt_parts.append("The following metrics were computed deterministically. Use these values as-is in your output:")
        prompt_parts.append(f"\n```json\n{json.dumps(deterministic_metrics, indent=2)}\n```\n")
        prompt_parts.append("**Focus your analysis on semantic fields** (tone instructions, guardrails, argumentation style).\n")

    prompt_parts.append("\n" + "=" * 60 + "\n")
    prompt_parts.append("# Emails to Analyze\n")

    # Each email
    for i, email in enumerate(emails, 1):
        email_id = email.get('id', f'email_{i}')
        original = email.get('original_data', email)
        enrichment = email.get('enrichment', {})

        subject = original.get('subject', 'No subject')
        body = original.get('body', '')

        prompt_parts.append(f"## Email {i}: {email_id}\n")
        prompt_parts.append(f"**Subject:** {subject}")
        prompt_parts.append(f"**Context:** {enrichment.get('recipient_type', 'unknown')}, "
                          f"{enrichment.get('audience', 'unknown')}, "
                          f"{enrichment.get('thread_position', 'unknown')}, "
                          f"seniority: {enrichment.get('recipient_seniority', 'unknown')}")
        prompt_parts.append(f"\n**Body:**\n```\n{body}\n```\n")
        prompt_parts.append("-" * 40 + "\n")

    # V2 JSON schema instructions
    prompt_parts.append("\n" + "=" * 60)
    prompt_parts.append("\n# V2 Schema Output Instructions\n")
    prompt_parts.append("""Analyze all emails and output a single JSON object with this V2 structure.

**KEY REQUIREMENT:** For each numeric score (1-10), provide BOTH the score AND a prose instruction.

```json
{
  "schema_version": "2.0",
  "batch_id": "batch_001",
  "cluster_id": CLUSTER_ID,
  "calibration_referenced": true,
  "calibration_notes": "Brief note on how you anchored scores",

  "new_personas": [
    {
      "name": "Persona Name",
      "description": "When this persona is used",
      "voice_fingerprint": {
        "formality": {
          "level": 6,
          "instruction": "Professional but conversational. Use contractions freely, avoid 'Please be advised'."
        },
        "tone_markers": {
          "warmth": {
            "level": 5,
            "instruction": "Polite and appreciative but efficient. Not overly chatty."
          },
          "authority": {
            "level": 7,
            "instruction": "Project confidence. Use 'I recommend' not 'I think maybe'."
          },
          "directness": {
            "level": 8,
            "instruction": "Get to the point quickly. Lead with the ask."
          }
        },
        "lexicon": {
          "signature_phrases": ["quick update", "sounds good"],
          "banned_words_or_phrases": ["synergy", "touch base", "delve"],
          "jargon_level": "medium"
        },
        "credibility_markers": {
          "uses_specifics_over_vague": true,
          "uses_numbers_when_available": true
        }
      },
      "cognitive_load_preferences": {
        "bottom_line_up_front": true,
        "action_item_isolation": "bullet_or_bold",
        "information_density": "low",
        "scannability_instruction": "Assume reader is skimming on mobile."
      },
      "body_dna": {
        "argumentation_style": "logical_sequential",
        "clarity_habits": {
          "defines_owner_and_deadline": true,
          "restates_decisions": true
        }
      },
      "cta_dna": {
        "urgency_style": {
          "uses_deadlines": true,
          "deadline_phrasing": "soft",
          "deadline_instruction": "Frame as 'needs' not demands. e.g. 'Can we target EOD?'"
        }
      },
      "relationship_calibration": {
        "to_executive": {"more_concise": true, "more_direct": true},
        "to_peer": {"baseline": true},
        "to_external": {"more_formal": true, "more_explanation": true}
      },
      "guardrails": {
        "structural_anti_patterns": [
          "Never start with 'I hope this email finds you well'",
          "Never use passive voice for action items"
        ],
        "never_do": [
          "invent prior conversations",
          "use aggressive sales language"
        ]
      }
    }
  ],

  "samples": [
    {
      "id": "email_id",
      "persona": "Persona Name",
      "confidence": 0.85,
      "analysis": {
        "tone_vectors": {
          "formality": 6,
          "warmth": 5,
          "authority": 7,
          "directness": 8
        },
        "tone_descriptors": ["direct", "confident", "efficient"],
        "greeting": "Hi Team,",
        "closing": "Best,"
      },
      "context": {
        "recipient_type": "team",
        "audience": "internal",
        "thread_position": "initiating",
        "recipient_seniority": "peer"
      }
    }
  ]
}
```

**SEMANTIC ANALYSIS FOCUS:**
1. **Tone Instructions**: For each dimension, explain in plain English what the score means
2. **Argumentation Style**: How arguments are built (logical_sequential, narrative, data_driven)
3. **Cognitive Load**: Is information BLUF? How are action items isolated?
4. **Guardrails**: Extract anti-patterns and "never do" rules from the writer's style
5. **Relationship Calibration**: Note any voice adjustments based on recipient seniority

**IMPORTANT:**
- Output ONLY valid JSON - no markdown code fences, no explanation text
- One `samples` entry per email with full analysis
- Create `new_personas` only for genuinely distinct writing styles
- Use pre-computed deterministic metrics where provided
- Set `calibration_referenced: true` after reading the calibration reference
""")

    return "\n".join(prompt_parts)


# =============================================================================
# Cost Estimation
# =============================================================================

def estimate_tokens(text: str, output_tokens: int = 2000) -> Dict:
    """
    Estimate token count for a text.

    Simple estimation: ~4 characters per token (rough approximation).
    """
    input_tokens = len(text) // 4
    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens
    }


def estimate_analysis_cost(clusters: List[Dict], model: str) -> Dict:
    """
    Estimate total cost for analyzing all clusters.

    Returns dict with token counts and cost breakdown.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING['default'])
    calibration = load_calibration()

    total_input = 0
    total_output = 0
    per_cluster = []

    for cluster in clusters:
        emails = get_cluster_emails(cluster)
        prompt = build_analysis_prompt(cluster, emails, calibration)

        # Estimate output based on email count (~100 tokens per email)
        output_estimate = max(1500, len(emails) * 100)

        tokens = estimate_tokens(prompt, output_estimate)
        total_input += tokens['input_tokens']
        total_output += tokens['output_tokens']

        cluster_cost = (
            (tokens['input_tokens'] / 1_000_000) * pricing['input'] +
            (tokens['output_tokens'] / 1_000_000) * pricing['output']
        )

        per_cluster.append({
            'cluster_id': cluster.get('id'),
            'email_count': len(emails),
            'input_tokens': tokens['input_tokens'],
            'output_tokens': tokens['output_tokens'],
            'estimated_cost': cluster_cost
        })

    total_cost = (
        (total_input / 1_000_000) * pricing['input'] +
        (total_output / 1_000_000) * pricing['output']
    )

    return {
        'model': model,
        'total_input_tokens': total_input,
        'total_output_tokens': total_output,
        'estimated_cost_usd': total_cost,
        'per_cluster': per_cluster
    }


# =============================================================================
# Parallel Analysis
# =============================================================================

def _call_openrouter_api(prompt: str, api_key: str, model: str, max_tokens: int = 4000) -> str:
    """
    Call OpenRouter API and return the response content.

    Raises exception on error.
    """
    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/writing-style-clone",
            "X-Title": "Writing Style Clone Analysis"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        },
        timeout=120  # 2 minute timeout for large clusters
    )

    if response.status_code != 200:
        raise Exception(f"API returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    return data['choices'][0]['message']['content'].strip()


def analyze_single_cluster(
    cluster_id: int,
    prompt: str,
    api_key: str,
    model: str,
    max_retries: int = 3
) -> Tuple[int, Optional[Dict], Optional[str]]:
    """
    Analyze a single cluster via OpenRouter API.

    Uses robust JSON parsing with repair strategies and retry with
    improved prompts on failure.

    Returns:
        (cluster_id, parsed_result_dict, error_message_or_none)
    """
    current_prompt = prompt
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            content = _call_openrouter_api(current_prompt, api_key, model)

            # Use robust JSON parsing with repair
            parse_result = safe_parse_json(content)

            if parse_result['success']:
                # Validate schema
                is_valid, validation_error = validate_analysis_schema(parse_result['data'])
                if is_valid:
                    if parse_result['repair_applied']:
                        print(f"    (Cluster {cluster_id}: JSON repaired successfully)")
                    return (cluster_id, parse_result['data'], None)
                else:
                    last_error = f"Schema validation failed: {validation_error}"
            else:
                last_error = parse_result['error']

            # If we have more retries, modify prompt to emphasize JSON-only output
            if attempt < max_retries:
                current_prompt = get_retry_prompt(prompt, last_error)
                time.sleep(2 ** attempt)  # Exponential backoff
                continue

            return (cluster_id, None, f"JSON parse error after {max_retries + 1} attempts: {last_error}")

        except requests.exceptions.Timeout:
            last_error = "API timeout"
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            return (cluster_id, None, f"API timeout after {max_retries + 1} attempts")

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            return (cluster_id, None, f"Error after {max_retries + 1} attempts: {last_error}")

    return (cluster_id, None, f"Max retries exceeded: {last_error}")


def merge_v2_analysis(
    deterministic_metrics: Dict,
    llm_result: Dict,
    emails: List[Dict],
    cluster: Dict
) -> Dict:
    """
    Merge deterministic Python analysis with LLM semantic analysis.

    Deterministic metrics take precedence for fields they compute.
    LLM results fill in semantic/nuanced fields.

    Args:
        deterministic_metrics: Output from compute_deterministic_metrics()
        llm_result: Parsed JSON from LLM analysis
        emails: Original emails for example selection
        cluster: Cluster metadata

    Returns:
        Merged v2 schema result
    """
    # Start with LLM result as base
    merged = dict(llm_result)
    merged["schema_version"] = "2.0"

    # Get or create new_personas list
    personas = merged.get("new_personas", [])

    for persona in personas:
        # Ensure voice_fingerprint exists
        if "voice_fingerprint" not in persona:
            persona["voice_fingerprint"] = {}

        vf = persona["voice_fingerprint"]

        # Inject deterministic rhythm metrics
        if deterministic_metrics.get("rhythm"):
            vf["rhythm"] = deterministic_metrics["rhythm"]

        # Inject deterministic mechanics
        if deterministic_metrics.get("mechanics"):
            if "mechanics" not in vf:
                vf["mechanics"] = {}
            vf["mechanics"].update(deterministic_metrics["mechanics"])

        # Inject deterministic formatting into body_dna
        if deterministic_metrics.get("formatting"):
            if "body_dna" not in persona:
                persona["body_dna"] = {}
            if "structure_preferences" not in persona["body_dna"]:
                persona["body_dna"]["structure_preferences"] = {}
            persona["body_dna"]["structure_preferences"].update({
                "uses_bullets_rate": deterministic_metrics["formatting"].get("uses_bullets_rate", 0),
                "uses_numbering_rate": deterministic_metrics["formatting"].get("uses_numbering_rate", 0)
            })

        # Inject greeting distribution into opening_dna
        if deterministic_metrics.get("greeting_distribution"):
            if "opening_dna" not in persona:
                persona["opening_dna"] = {}
            persona["opening_dna"]["greeting_distribution"] = deterministic_metrics["greeting_distribution"]["distribution"]
            persona["opening_dna"]["primary_style"] = deterministic_metrics["greeting_distribution"]["primary_style"]

        # Inject closing distribution into closing_dna
        if deterministic_metrics.get("closing_distribution"):
            if "closing_dna" not in persona:
                persona["closing_dna"] = {}
            persona["closing_dna"]["sign_off_distribution"] = deterministic_metrics["closing_distribution"]["distribution"]
            persona["closing_dna"]["primary_style"] = deterministic_metrics["closing_distribution"]["primary_style"]
            persona["closing_dna"]["uses_signature_block"] = deterministic_metrics["closing_distribution"]["uses_signature_block"]

        # Inject subject line patterns
        if deterministic_metrics.get("subject_line_patterns"):
            if "subject_line_dna" not in persona:
                persona["subject_line_dna"] = {}
            persona["subject_line_dna"].update(deterministic_metrics["subject_line_patterns"])

        # Infer email type from cluster
        email_type_info = infer_email_types(cluster, emails)
        if "email_types" not in persona:
            persona["email_types"] = {}
        persona["email_types"][email_type_info["detected_type"]] = {
            "confidence": email_type_info["confidence"],
            "required_elements": email_type_info["required_elements"],
            "typical_length": email_type_info["typical_length"],
            "structure_pattern": email_type_info["structure_pattern"]
        }

    # Select examples for example_bank
    samples = merged.get("samples", [])
    selected_examples = select_example_bank(samples, limit=5, min_confidence=0.85)

    for persona in personas:
        if "example_bank" not in persona:
            persona["example_bank"] = {
                "usage_guidance": {
                    "instruction": "Match rhythm, tone, and structural patterns of these examples.",
                    "what_to_match": ["Sentence length variation", "Opening style", "Closing pattern"],
                    "what_to_adapt": ["Topic and subject matter", "Specific names"],
                    "warning": "Do NOT copy examples verbatim."
                },
                "examples": []
            }

        # Add high-confidence examples
        for sample in selected_examples:
            if sample.get("persona") == persona.get("name"):
                # Find original email content
                email_content = next(
                    (e for e in emails if e.get("id") == sample.get("id")),
                    {}
                )
                original = email_content.get("original_data", {})
                persona["example_bank"]["examples"].append({
                    "type": email_type_info.get("detected_type", "general"),
                    "subject": original.get("subject", "[REDACTED]"),
                    "body": original.get("body", "")[:1000],  # Truncate for token efficiency
                    "confidence": sample.get("confidence"),
                    "context": sample.get("context", {})
                })

    merged["new_personas"] = personas
    return merged


def run_parallel_analysis(
    clusters: List[Dict],
    prompts: Dict[int, str],
    api_key: str,
    model: str,
    max_workers: Optional[int] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[Dict[int, Dict], Dict[int, str]]:
    """
    Run analysis on all clusters in parallel.

    Returns:
        (results_dict, errors_dict)
    """
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                analyze_single_cluster,
                cluster['id'],
                prompts[cluster['id']],
                api_key,
                model
            ): cluster['id']
            for cluster in clusters
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            cluster_id, result, error = future.result()

            if result:
                results[cluster_id] = result
            else:
                errors[cluster_id] = error or "Unknown error"

            if progress_callback:
                progress_callback(completed, len(clusters), cluster_id, result is not None)

    return results, errors


# =============================================================================
# Persona Merging
# =============================================================================

def _get_embedder():
    """Get or create SentenceTransformer embedder."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('all-MiniLM-L6-v2')
    except ImportError:
        return None


def find_similar_personas(personas: List[Dict], threshold: float = 0.85) -> List[Tuple[int, int, float]]:
    """
    Find pairs of similar personas using embedding cosine similarity.

    Returns list of (idx1, idx2, similarity) tuples.
    """
    if len(personas) < 2:
        return []

    embedder = _get_embedder()
    if not embedder:
        # Fallback: simple string matching
        return _find_similar_by_name(personas, threshold)

    # Generate embeddings from name + description
    texts = [f"{p.get('name', '')} {p.get('description', '')}" for p in personas]

    try:
        import numpy as np
        embeddings = embedder.encode(texts, normalize_embeddings=True)

        similar_pairs = []
        for i in range(len(personas)):
            for j in range(i + 1, len(personas)):
                similarity = float(np.dot(embeddings[i], embeddings[j]))
                if similarity >= threshold:
                    similar_pairs.append((i, j, similarity))

        return sorted(similar_pairs, key=lambda x: -x[2])  # Sort by similarity desc

    except Exception:
        return _find_similar_by_name(personas, threshold)


def _find_similar_by_name(personas: List[Dict], threshold: float) -> List[Tuple[int, int, float]]:
    """Fallback similarity check using string matching."""
    from difflib import SequenceMatcher

    similar_pairs = []
    for i in range(len(personas)):
        for j in range(i + 1, len(personas)):
            name1 = personas[i].get('name', '').lower()
            name2 = personas[j].get('name', '').lower()
            similarity = SequenceMatcher(None, name1, name2).ratio()
            if similarity >= threshold:
                similar_pairs.append((i, j, similarity))

    return sorted(similar_pairs, key=lambda x: -x[2])


def merge_persona_pair(persona1: Dict, persona2: Dict) -> Dict:
    """
    Merge two similar personas into one.

    Keeps name from persona1 (first occurrence).
    Averages numeric characteristics.
    """
    merged = {
        'name': persona1.get('name'),
        'description': persona1.get('description'),
        'characteristics': {}
    }

    # Average numeric characteristics
    chars1 = persona1.get('characteristics', {})
    chars2 = persona2.get('characteristics', {})

    numeric_fields = ['formality', 'warmth', 'authority', 'directness']
    for field in numeric_fields:
        val1 = chars1.get(field)
        val2 = chars2.get(field)
        if val1 is not None and val2 is not None:
            merged['characteristics'][field] = round((val1 + val2) / 2)
        elif val1 is not None:
            merged['characteristics'][field] = val1
        elif val2 is not None:
            merged['characteristics'][field] = val2

    # Keep other characteristics from first persona
    for key, val in chars1.items():
        if key not in merged['characteristics']:
            merged['characteristics'][key] = val

    return merged


def apply_persona_merges(
    analysis_results: Dict[int, Dict],
    merge_mapping: Dict[str, str]
) -> Dict[int, Dict]:
    """
    Apply persona merges to all analysis results.

    Updates sample persona assignments to use merged names.

    Args:
        analysis_results: Dict of cluster_id -> analysis result
        merge_mapping: Dict of old_name -> new_name

    Returns:
        Updated analysis results
    """
    updated = {}

    for cluster_id, result in analysis_results.items():
        result_copy = json.loads(json.dumps(result))  # Deep copy

        # Update sample persona assignments
        for sample in result_copy.get('samples', []):
            old_persona = sample.get('persona')
            if old_persona in merge_mapping:
                sample['persona'] = merge_mapping[old_persona]

        # Remove merged personas from new_personas
        new_personas = []
        seen_names = set()
        for persona in result_copy.get('new_personas', []):
            name = persona.get('name')
            # Skip if this persona was merged into another
            if name in merge_mapping and merge_mapping[name] != name:
                continue
            # Skip duplicates
            if name in seen_names:
                continue
            seen_names.add(name)
            new_personas.append(persona)

        result_copy['new_personas'] = new_personas
        updated[cluster_id] = result_copy

    return updated


# =============================================================================
# Token Limit Handling
# =============================================================================

def split_large_cluster(cluster: Dict, max_emails_per_batch: int = DEFAULT_MAX_EMAILS_PER_BATCH) -> List[Dict]:
    """
    Split a large cluster into smaller batches if needed.

    Returns list of sub-cluster dicts.
    """
    sample_ids = cluster.get('remaining_ids', cluster.get('sample_ids', []))

    if len(sample_ids) <= max_emails_per_batch:
        return [cluster]

    sub_clusters = []
    for i in range(0, len(sample_ids), max_emails_per_batch):
        sub = dict(cluster)
        batch_ids = sample_ids[i:i + max_emails_per_batch]
        sub['sample_ids'] = batch_ids
        sub['remaining_ids'] = batch_ids
        sub['size'] = len(batch_ids)
        sub['is_sub_cluster'] = True
        sub['sub_index'] = len(sub_clusters)
        sub['original_id'] = cluster.get('id')
        # Generate unique ID for sub-cluster
        sub['id'] = f"{cluster.get('id')}_{len(sub_clusters)}"
        sub_clusters.append(sub)

    return sub_clusters


# =============================================================================
# Approval Workflow
# =============================================================================

def has_pending_draft() -> bool:
    """Check if an analysis draft exists."""
    return _get_draft_file().exists()


def save_draft(
    results: Dict[int, Dict],
    merged_personas: List[Dict],
    metadata: Dict
):
    """Save draft analysis results for review."""
    draft = {
        'results': {str(k): v for k, v in results.items()},  # JSON keys must be strings
        'merged_personas': merged_personas,
        'metadata': metadata,
        'created_at': datetime.now().isoformat()
    }

    draft_file = _get_draft_file()
    draft_file.parent.mkdir(parents=True, exist_ok=True)
    with open(draft_file, 'w') as f:
        json.dump(draft, f, indent=2)


def load_draft() -> Optional[Dict]:
    """Load draft from file."""
    draft_file = _get_draft_file()
    if not draft_file.exists():
        return None
    try:
        with open(draft_file) as f:
            draft = json.load(f)
        # Convert string keys back to int for results
        if 'results' in draft:
            draft['results'] = {int(k) if k.isdigit() else k: v for k, v in draft['results'].items()}
        return draft
    except (json.JSONDecodeError, IOError):
        return None


def reject_draft():
    """Discard draft and allow re-analysis."""
    draft_file = _get_draft_file()
    if draft_file.exists():
        draft_file.unlink()


def show_review_summary(draft: Dict) -> str:
    """Generate human-readable summary of draft results."""
    results = draft.get('results', {})
    merged_personas = draft.get('merged_personas', [])
    metadata = draft.get('metadata', {})

    lines = []
    lines.append("=" * 60)
    lines.append("PARALLEL CLUSTER ANALYSIS - DRAFT REVIEW")
    lines.append("=" * 60)
    lines.append("")

    # Summary stats
    total_samples = sum(len(r.get('samples', [])) for r in results.values())
    lines.append(f"Clusters analyzed: {len(results)}")
    lines.append(f"Total emails analyzed: {total_samples}")
    lines.append(f"Personas discovered: {len(merged_personas)}")
    lines.append(f"Model used: {metadata.get('model', 'unknown')}")
    lines.append("")

    # Personas
    if merged_personas:
        lines.append("PERSONAS:")
        for p in merged_personas:
            lines.append(f"  - {p.get('name')}: {p.get('description', 'No description')[:50]}")
    lines.append("")

    # Per-cluster breakdown
    lines.append("PER-CLUSTER BREAKDOWN:")
    for cluster_id, result in sorted(results.items()):
        sample_count = len(result.get('samples', []))
        persona_count = len(result.get('new_personas', []))
        lines.append(f"  Cluster {cluster_id}: {sample_count} emails, {persona_count} personas")

    lines.append("")
    lines.append("=" * 60)
    lines.append("Run --approve to ingest all results, or --reject to discard.")
    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Parallel cluster analysis via OpenRouter API"
    )

    # Actions
    parser.add_argument("--estimate", action="store_true",
                       help="Show cost estimate without running")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate without API calls")
    parser.add_argument("--review", action="store_true",
                       help="Show draft results for review")
    parser.add_argument("--approve", action="store_true",
                       help="Approve and ingest all draft results")
    parser.add_argument("--reject", action="store_true",
                       help="Discard draft and reset")
    parser.add_argument("--status", action="store_true",
                       help="Show current analysis status")
    parser.add_argument("--recommend", action="store_true",
                       help="Show recommended models for different use cases")

    # Configuration
    parser.add_argument("--model", type=str,
                       help="Override model selection")
    parser.add_argument("--max-workers", type=int,
                       help="Maximum parallel workers (default: unlimited)")
    parser.add_argument("--similarity-threshold", type=float, default=0.85,
                       help="Persona merge similarity threshold (default: 0.85)")
    parser.add_argument("--max-emails-per-batch", type=int, default=DEFAULT_MAX_EMAILS_PER_BATCH,
                       help=f"Max emails per API call (default: {DEFAULT_MAX_EMAILS_PER_BATCH})")

    args = parser.parse_args()

    # Handle --recommend
    if args.recommend:
        print("\n" + "=" * 60)
        print("MODEL RECOMMENDATIONS")
        print("=" * 60)
        print("\nChoose based on your priorities:\n")
        print("  COST-EFFECTIVE (Recommended):")
        print(f"    {RECOMMENDED_MODELS['cost_effective']}")
        pricing = MODEL_PRICING.get(RECOMMENDED_MODELS['cost_effective'], {})
        print(f"    ${pricing.get('input', '?')}/1M input, ${pricing.get('output', '?')}/1M output")
        print("    Best balance of quality and cost for persona analysis.")
        print()
        print("  BUDGET (Testing/Development):")
        print(f"    {RECOMMENDED_MODELS['budget']}")
        pricing = MODEL_PRICING.get(RECOMMENDED_MODELS['budget'], {})
        print(f"    ${pricing.get('input', '?')}/1M input, ${pricing.get('output', '?')}/1M output")
        print("    Cheapest option, good for testing workflow.")
        print()
        print("  QUALITY (Best Results):")
        print(f"    {RECOMMENDED_MODELS['quality']}")
        pricing = MODEL_PRICING.get(RECOMMENDED_MODELS['quality'], {})
        print(f"    ${pricing.get('input', '?')}/1M input, ${pricing.get('output', '?')}/1M output")
        print("    Highest quality analysis, recommended for final runs.")
        print()
        print("To set a model:")
        print("  python validate_personas.py --set-model 'anthropic/claude-3-5-haiku-20241022'")
        print()
        print("Or override per-run:")
        print("  python analyze_clusters.py --model 'openai/gpt-4o-mini'")
        print("=" * 60)
        return 0

    # Handle status
    if args.status:
        clusters = load_unanalyzed_clusters()
        if not clusters:
            print("No unanalyzed clusters found.")
            if has_pending_draft():
                print("Note: A draft exists. Use --review to see it.")
        else:
            print(f"Unanalyzed clusters: {len(clusters)}")
            for c in clusters:
                print(f"  Cluster {c['id']}: {c['remaining_count']} emails remaining")
        return 0

    # Handle review
    if args.review:
        draft = load_draft()
        if not draft:
            print("No draft found. Run analysis first.")
            return 1
        print(show_review_summary(draft))
        return 0

    # Handle reject
    if args.reject:
        if has_pending_draft():
            reject_draft()
            print("Draft discarded. You can now run a new analysis.")
        else:
            print("No draft to reject.")
        return 0

    # Handle approve
    if args.approve:
        draft = load_draft()
        if not draft:
            print("No draft found. Run analysis first.")
            return 1

        # TODO: Implement actual ingestion (integrate with ingest.py)
        print("Approval and ingestion not yet implemented.")
        print("For now, export the draft manually and use ingest.py.")
        return 1

    # Check prerequisites for analysis
    if has_pending_draft() and not args.dry_run:
        print("A draft already exists. Use --review, --approve, or --reject first.")
        return 1

    if not check_model_configured():
        print("No OpenRouter model configured.")
        print("Run: python validate_personas.py --set-model")
        return 1

    model = args.model or _get_selected_model()

    # Load clusters
    clusters = load_unanalyzed_clusters()
    if not clusters:
        print("No unanalyzed clusters found.")
        print("Ensure clustering is complete (clusters.json exists)")
        return 0

    # Split large clusters
    all_batches = []
    for cluster in clusters:
        sub_clusters = split_large_cluster(cluster, args.max_emails_per_batch)
        all_batches.extend(sub_clusters)

    print(f"Found {len(clusters)} clusters ({len(all_batches)} batches after splitting)")

    # Handle estimate
    if args.estimate:
        estimate = estimate_analysis_cost(all_batches, model)
        print("\nCOST ESTIMATE")
        print("=" * 60)
        print(f"Selected model: {model}")
        print(f"Input tokens: {estimate['total_input_tokens']:,}")
        print(f"Output tokens: {estimate['total_output_tokens']:,}")
        print(f"Estimated cost: ${estimate['estimated_cost_usd']:.4f}")
        print("\nPer cluster:")
        for pc in estimate['per_cluster']:
            print(f"  Cluster {pc['cluster_id']}: {pc['email_count']} emails, ${pc['estimated_cost']:.4f}")

        # Show comparison with other models
        print("\n" + "-" * 60)
        print("COST COMPARISON (same workload, different models):")
        print("-" * 60)
        comparison_models = [
            ("google/gemini-2.0-flash-lite-001", "Gemini 2.0 Flash Lite (Budget)"),
            ("google/gemini-3-flash-preview", "Gemini 3 Flash (Recommended)"),
            ("anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5 (Quality)"),
        ]
        for model_id, label in comparison_models:
            alt_estimate = estimate_analysis_cost(all_batches, model_id)
            marker = " <-- selected" if model_id == model else ""
            marker = " <-- RECOMMENDED" if model_id == RECOMMENDED_MODELS['cost_effective'] and model != model_id else marker
            print(f"  {label}: ${alt_estimate['estimated_cost_usd']:.4f}{marker}")

        print("\nTo use a different model:")
        print(f"  python analyze_clusters.py --model '{RECOMMENDED_MODELS['cost_effective']}'")
        print("=" * 60)
        return 0

    # Handle dry-run
    if args.dry_run:
        print("\nDRY RUN - No API calls will be made")
        print("=" * 40)
        calibration = load_calibration()
        for batch in all_batches:
            emails = get_cluster_emails(batch)
            prompt = build_analysis_prompt(batch, emails, calibration)
            print(f"\nCluster {batch['id']}: {len(emails)} emails, {len(prompt)} chars prompt")
        return 0

    # Run analysis
    api_key = get_openrouter_key()
    calibration = load_calibration()

    # Build prompts with v2 deterministic metrics
    prompts = {}
    batch_emails = {}  # Store emails for merge step
    batch_metrics = {}  # Store deterministic metrics for merge step

    for batch in all_batches:
        emails = get_cluster_emails(batch)
        batch_emails[batch['id']] = emails

        # Compute deterministic metrics (v2)
        metrics = compute_deterministic_metrics(emails)
        batch_metrics[batch['id']] = metrics

        # Build prompt with metrics included
        prompts[batch['id']] = build_analysis_prompt(batch, emails, calibration, metrics)

    print(f"\nRunning parallel analysis with model: {model}")
    print("=" * 40)

    def progress(completed, total, cluster_id, success):
        status = "Done" if success else "FAILED"
        print(f"  [{completed}/{total}] Cluster {cluster_id}: {status}")

    results, errors = run_parallel_analysis(
        all_batches,
        prompts,
        api_key,
        model,
        max_workers=args.max_workers,
        progress_callback=progress
    )

    print(f"\nCompleted: {len(results)} succeeded, {len(errors)} failed")

    if errors:
        print("\nErrors:")
        for cluster_id, error in errors.items():
            print(f"  Cluster {cluster_id}: {error}")

    if not results:
        print("No results to save.")
        return 1

    # V2: Merge deterministic metrics with LLM results
    print("\nMerging deterministic metrics with LLM analysis...")
    merged_results = {}
    for cluster_id, llm_result in results.items():
        # Find the corresponding batch
        batch = next((b for b in all_batches if b['id'] == cluster_id), {})
        emails = batch_emails.get(cluster_id, [])
        metrics = batch_metrics.get(cluster_id, {})

        merged_results[cluster_id] = merge_v2_analysis(metrics, llm_result, emails, batch)

    # Use merged results going forward
    results = merged_results

    # Collect and merge personas
    all_personas = []
    for result in results.values():
        all_personas.extend(result.get('new_personas', []))

    print(f"\nDiscovered {len(all_personas)} personas across all clusters")

    # Find similar personas
    similar_pairs = find_similar_personas(all_personas, args.similarity_threshold)

    merge_mapping = {}
    if similar_pairs:
        print(f"Found {len(similar_pairs)} similar persona pairs:")
        for i, j, sim in similar_pairs:
            name1 = all_personas[i].get('name')
            name2 = all_personas[j].get('name')
            print(f"  '{name1}' ~ '{name2}' (similarity: {sim:.2f})")
            # Merge second into first
            merge_mapping[name2] = name1

    # Apply merges
    if merge_mapping:
        results = apply_persona_merges(results, merge_mapping)

    # Deduplicate merged personas
    seen_names = set()
    merged_personas = []
    for persona in all_personas:
        name = persona.get('name')
        # Skip if merged into another
        if name in merge_mapping and merge_mapping[name] != name:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        merged_personas.append(persona)

    print(f"Final personas after merging: {len(merged_personas)}")

    # Save draft
    metadata = {
        'model': model,
        'timestamp': datetime.now().isoformat(),
        'clusters_analyzed': len(results),
        'clusters_failed': len(errors),
        'merge_threshold': args.similarity_threshold
    }

    save_draft(results, merged_personas, metadata)

    print(f"\nDraft saved to: {_get_draft_file()}")
    print("\nNext steps:")
    print("  python analyze_clusters.py --review   # Review results")
    print("  python analyze_clusters.py --approve  # Approve and ingest")
    print("  python analyze_clusters.py --reject   # Discard and retry")

    return 0


if __name__ == "__main__":
    sys.exit(main())
