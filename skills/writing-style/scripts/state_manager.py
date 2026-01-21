#!/usr/bin/env python3
"""
State Manager - Unified pipeline state tracking for Writing Style Clone

This module provides a DERIVED state view by reading existing report files.
Each script writes its own report file - state.json aggregates them into
a single dashboard view.

Usage:
    python state_manager.py --sync      # Rebuild state.json from report files
    python state_manager.py --status    # Show full pipeline status
    python state_manager.py --phase     # Show just the current phase
    python state_manager.py --json      # Output state as JSON
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from config import get_data_dir, get_path


# =============================================================================
# Report File Definitions
# =============================================================================

# Each step produces a report file that serves as proof of completion
REPORT_FILES = {
    # Preprocessing phase
    "fetch": {
        "file": "fetch_state.json",
        "extract": lambda d: {
            "emails": d.get("total_fetched", 0),
            "last_fetch": d.get("last_fetch")
        }
    },
    "filter": {
        "file": "filter_report.json",
        "extract": lambda d: {
            "passed": d.get("passed", 0),
            "rejected": d.get("rejected", 0),
            "pass_rate": d.get("pass_rate")
        }
    },
    "enrich": {
        "file": "enrichment_report.json",
        "extract": lambda d: {
            "enriched": d.get("total_enriched", d.get("enriched", 0)),
            "completed_at": d.get("completed_at")
        }
    },
    "embed": {
        "file": "embedding_report.json",
        "extract": lambda d: {
            "embedded": d.get("total_embedded", d.get("embedded", 0)),
            "model": d.get("model"),
            "completed_at": d.get("completed_at")
        }
    },
    "cluster": {
        "file": "clusters.json",
        "extract": lambda d: {
            "clusters": len(d.get("clusters", [])),
            "cluster_names": [c.get("name", f"Cluster {i}") for i, c in enumerate(d.get("clusters", []))]
        }
    },

    # Analysis phase
    "personas": {
        "file": "persona_registry.json",
        "extract": lambda d: {
            "count": len(d.get("personas", {})),
            "names": list(d.get("personas", {}).keys()),
            "created_at": d.get("created_at")
        }
    },

    # Validation phase
    "validation_pairs": {
        "file": "validation_pairs.json",
        "extract": lambda d: {
            "pairs": len(d) if isinstance(d, list) else d.get("count", 0)
        }
    },
    "validation_results": {
        "file": "validation_results.json",
        "extract": lambda d: {
            "tested": len(d) if isinstance(d, list) else d.get("count", 0)
        }
    },
    "validation_report": {
        "file": "validation_report.json",
        "extract": lambda d: {
            "score": d.get("summary", {}).get("overall_score", d.get("overall_score")),
            "recommendation": d.get("recommendation"),
            "completed_at": d.get("completed_at", d.get("created"))
        }
    },
    "validation_feedback": {
        "file": "validation_feedback.json",
        "extract": lambda d: {
            "feedback_count": len(d.get("feedback", [])),
            "reviews_completed": sum(1 for f in d.get("feedback", []) if f.get("reviewed")),
            "interactive_complete": d.get("interactive_complete", False)
        }
    },

    # LinkedIn phase (optional)
    "linkedin_fetch": {
        "file": "linkedin_fetch_state.json",
        "extract": lambda d: {
            "posts": d.get("total_fetched", 0),
            "profile": d.get("profile_url")
        }
    },
    "linkedin_persona": {
        "file": "linkedin_persona.json",
        "extract": lambda d: {
            "has_voice": "voice_profile" in d,
            "has_content": "content_patterns" in d
        }
    },

    # Generation phase
    "generated_skill": {
        "file": "generated_skill.json",  # Or check for output directory
        "extract": lambda d: {
            "name": d.get("skill_name"),
            "completed_at": d.get("generated_at")
        }
    },

    # Config files
    "openrouter_model": {
        "file": "openrouter_model.json",
        "extract": lambda d: {
            "model": d.get("model_id"),
            "set_at": d.get("set_at")
        }
    }
}


# =============================================================================
# State Sync Functions
# =============================================================================

def _read_report(filename: str) -> Optional[dict]:
    """Read a report file if it exists."""
    filepath = get_path(filename)
    if filepath.exists():
        try:
            with open(filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _check_step(step_name: str) -> dict:
    """Check status of a single step."""
    config = REPORT_FILES.get(step_name)
    if not config:
        return {"status": "unknown", "error": f"Unknown step: {step_name}"}

    data = _read_report(config["file"])
    if data is None:
        return {"status": "pending", "source": config["file"]}

    try:
        extracted = config["extract"](data)
        return {
            "status": "complete",
            "source": config["file"],
            **extracted
        }
    except Exception as e:
        return {
            "status": "error",
            "source": config["file"],
            "error": str(e)
        }


def _determine_current_phase(state: dict) -> str:
    """Determine the current pipeline phase based on what's complete."""

    # Check generation (final phase)
    gen = state.get("generation", {})
    if gen.get("skill", {}).get("status") == "complete":
        return "complete"

    # Check LinkedIn (optional phase)
    linkedin = state.get("linkedin", {})
    linkedin_started = linkedin.get("fetch", {}).get("status") == "complete"

    # Check validation
    val = state.get("validation", {})
    validation_complete = val.get("report", {}).get("status") == "complete"

    if validation_complete:
        if linkedin_started:
            return "linkedin"
        return "generation"

    # Check if validation started
    if val.get("pairs", {}).get("status") == "complete":
        return "validation"

    # Check analysis
    analysis = state.get("analysis", {})
    if analysis.get("personas", {}).get("status") == "complete":
        return "validation"  # Ready for validation

    # Check preprocessing
    prep = state.get("preprocessing", {})
    if prep.get("cluster", {}).get("status") == "complete":
        return "analysis"

    if prep.get("embed", {}).get("status") == "complete":
        return "preprocessing"  # Clustering pending

    if prep.get("fetch", {}).get("status") == "complete":
        return "preprocessing"

    return "setup"


def sync_state() -> dict:
    """
    Build state.json by reading all report files.

    This is the main function that aggregates status from all
    the individual report files into a unified state view.
    """
    state = {
        "last_synced": datetime.now().isoformat(),
        "data_dir": str(get_data_dir()),

        "preprocessing": {
            "fetch": _check_step("fetch"),
            "filter": _check_step("filter"),
            "enrich": _check_step("enrich"),
            "embed": _check_step("embed"),
            "cluster": _check_step("cluster")
        },

        "analysis": {
            "personas": _check_step("personas")
        },

        "validation": {
            "pairs": _check_step("validation_pairs"),
            "results": _check_step("validation_results"),
            "report": _check_step("validation_report"),
            "feedback": _check_step("validation_feedback")
        },

        "linkedin": {
            "fetch": _check_step("linkedin_fetch"),
            "persona": _check_step("linkedin_persona")
        },

        "generation": {
            "skill": _check_step("generated_skill")
        },

        "config": {
            "openrouter_model": _check_step("openrouter_model")
        }
    }

    # Determine current phase
    state["current_phase"] = _determine_current_phase(state)

    # Save to state.json
    state_path = get_path("state.json")
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    return state


def load_state(sync_first: bool = False) -> dict:
    """
    Load the current state.

    Args:
        sync_first: If True, rebuild state from report files before loading
    """
    if sync_first:
        return sync_state()

    state_path = get_path("state.json")
    if not state_path.exists():
        # Auto-sync if state.json doesn't exist
        return sync_state()

    with open(state_path) as f:
        return json.load(f)


def get_current_phase(sync_first: bool = True) -> str:
    """Get the current pipeline phase."""
    state = load_state(sync_first=sync_first)
    return state.get("current_phase", "unknown")


# =============================================================================
# Status Display Functions
# =============================================================================

def _status_icon(status: str) -> str:
    """Get icon for status."""
    icons = {
        "complete": "[OK]",
        "pending": "⬚",
        "error": "[ERROR]",
        "unknown": "?"
    }
    return icons.get(status, "?")


def _format_step(name: str, step: dict, indent: int = 2) -> list[str]:
    """Format a step for display."""
    lines = []
    icon = _status_icon(step.get("status", "unknown"))
    prefix = " " * indent

    # Main status line
    status_line = f"{prefix}{icon} {name}"

    # Add key details on same line
    details = []
    for key, val in step.items():
        if key in ("status", "source", "error"):
            continue
        if val is not None and val != "" and val != []:
            if isinstance(val, list):
                details.append(f"{key}: {len(val)}")
            else:
                details.append(f"{key}: {val}")

    if details:
        status_line += f" ({', '.join(details[:3])})"  # Limit to 3 details

    lines.append(status_line)

    # Show error if any
    if step.get("error"):
        lines.append(f"{prefix}  [WARNING]  {step['error']}")

    return lines


def show_status(state: dict = None) -> str:
    """Generate human-readable status output."""
    if state is None:
        state = load_state(sync_first=True)

    lines = [
        "=" * 60,
        "WRITING STYLE CLONE - PIPELINE STATUS",
        "=" * 60,
        f"Current Phase: {state.get('current_phase', 'unknown').upper()}",
        f"Data Directory: {state.get('data_dir', 'unknown')}",
        f"Last Synced: {state.get('last_synced', 'never')}",
        ""
    ]

    # Preprocessing
    lines.append("[IMPORT] PREPROCESSING")
    prep = state.get("preprocessing", {})
    for step_name in ["fetch", "filter", "enrich", "embed", "cluster"]:
        lines.extend(_format_step(step_name, prep.get(step_name, {})))
    lines.append("")

    # Analysis
    lines.append("[SEARCH] ANALYSIS")
    analysis = state.get("analysis", {})
    lines.extend(_format_step("personas", analysis.get("personas", {})))
    lines.append("")

    # Validation
    lines.append("[OK] VALIDATION (Two Phases)")
    val = state.get("validation", {})
    lines.extend(_format_step("pairs", val.get("pairs", {})))
    lines.extend(_format_step("Phase 1: auto", val.get("report", {})))
    lines.extend(_format_step("Phase 2: interactive", val.get("feedback", {})))
    lines.append("")

    # LinkedIn
    lines.append("[WORK] LINKEDIN (Optional)")
    linkedin = state.get("linkedin", {})
    lines.extend(_format_step("fetch", linkedin.get("fetch", {})))
    lines.extend(_format_step("persona", linkedin.get("persona", {})))
    lines.append("")

    # Generation
    lines.append("[PACKAGE] GENERATION")
    gen = state.get("generation", {})
    lines.extend(_format_step("skill", gen.get("skill", {})))
    lines.append("")

    # Config
    config = state.get("config", {})
    model_config = config.get("openrouter_model", {})
    if model_config.get("status") == "complete":
        lines.append(f"[CONFIG]  OpenRouter Model: {model_config.get('model', 'default')}")

    lines.append("=" * 60)

    # Next step suggestion
    phase = state.get("current_phase", "setup")
    next_steps = {
        "setup": "Run: python fetch_emails.py --count 300 --holdout 0.15",
        "preprocessing": _get_next_preprocessing_step(prep),
        "analysis": "Run: python prepare_batch.py && python ingest.py batches/batch_*.json",
        "validation": "Run: python validate_personas.py --auto (Phase 1), then --review (Phase 2 required)",
        "linkedin": "Run: python fetch_linkedin_mcp.py --profile <url> (or skip to generation)",
        "generation": "Run: python generate_skill.py --name <your-name>",
        "complete": "Pipeline complete! Your skill is ready."
    }
    lines.append(f"\n[TIP] Next: {next_steps.get(phase, 'Unknown phase')}")

    return "\n".join(lines)


def _get_next_preprocessing_step(prep: dict) -> str:
    """Get the next preprocessing step to run."""
    steps = [
        ("fetch", "python fetch_emails.py --count 300 --holdout 0.15"),
        ("filter", "python filter_emails.py"),
        ("enrich", "python enrich_emails.py"),
        ("embed", "python embed_emails.py"),
        ("cluster", "python cluster_emails.py")
    ]

    for step_name, command in steps:
        if prep.get(step_name, {}).get("status") != "complete":
            return f"Run: {command}"

    return "Preprocessing complete. Run: python prepare_batch.py"


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Writing Style Clone - Pipeline State Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python state_manager.py --sync      # Rebuild state from report files
  python state_manager.py --status    # Show full pipeline status
  python state_manager.py --phase     # Show just the current phase
  python state_manager.py --json      # Output raw state as JSON
        """
    )
    parser.add_argument("--sync", action="store_true",
                        help="Rebuild state.json from report files")
    parser.add_argument("--status", action="store_true",
                        help="Show full pipeline status")
    parser.add_argument("--phase", action="store_true",
                        help="Show just the current phase")
    parser.add_argument("--json", action="store_true",
                        help="Output state as JSON")

    args = parser.parse_args()

    if args.sync:
        print("[UPDATE] Syncing state from report files...")
        state = sync_state()
        print(f"[OK] State synced. Current phase: {state['current_phase'].upper()}")
        print(f"   Saved to: {get_path('state.json')}")

    elif args.status:
        print(show_status())

    elif args.phase:
        phase = get_current_phase(sync_first=True)
        print(phase)

    elif args.json:
        state = load_state(sync_first=True)
        print(json.dumps(state, indent=2))

    else:
        # Default: show status
        print(show_status())
