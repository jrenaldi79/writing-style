"""
State Manager - Workflow state persistence for Writing Style Clone

Tracks which phase the user is in across multiple conversations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import get_data_dir

_state_path: Path = None
_data_dir: Path = None


def init_state(data_dir: str = None) -> dict:
    """Initialize state.json for a new project."""
    global _state_path, _data_dir

    if data_dir is None:
        _data_dir = get_data_dir()
    else:
        _data_dir = Path(data_dir).expanduser().resolve()
    _state_path = _data_dir / "state.json"
    
    state = {
        "current_phase": "analysis",  # Setup is complete when this is called
        "data_dir": str(_data_dir),
        "created_at": datetime.now().isoformat(),
        "setup": {
            "completed_at": datetime.now().isoformat()
        },
        "analysis": {
            "started_at": None,
            "batches_completed": 0,
            "total_samples": 0,
            "ready_for_generation": False
        },
        "generation": {
            "completed_at": None,
            "output_file": None
        }
    }
    
    with open(_state_path, "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"✓ State initialized at {_state_path}")
    return state


def load_state(data_dir: Optional[str] = None) -> dict:
    """Load existing state."""
    global _state_path, _data_dir

    if data_dir:
        _data_dir = Path(data_dir).expanduser().resolve()
    elif _data_dir is None:
        _data_dir = get_data_dir()
    _state_path = _data_dir / "state.json"

    if not _state_path.exists():
        raise FileNotFoundError(
            "No state.json found. Run Phase 1: Setup first, or provide data_dir."
        )
    
    with open(_state_path) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    """Save state to disk."""
    if not _state_path:
        raise RuntimeError("State not initialized. Call load_state(data_dir) first.")
    
    state["last_updated"] = datetime.now().isoformat()
    with open(_state_path, "w") as f:
        json.dump(state, f, indent=2)


def get_current_phase(data_dir: Optional[str] = None) -> str:
    """Get current workflow phase."""
    state = load_state(data_dir)
    return state.get("current_phase", "setup")


def update_analysis_progress(
    batches_completed: int,
    total_samples: int,
    data_dir: Optional[str] = None
) -> dict:
    """Update analysis progress after a batch."""
    state = load_state(data_dir)
    
    if state["analysis"]["started_at"] is None:
        state["analysis"]["started_at"] = datetime.now().isoformat()
    
    state["analysis"]["batches_completed"] = batches_completed
    state["analysis"]["total_samples"] = total_samples
    state["current_phase"] = "analysis"
    
    save_state(state)
    print(f"✓ Progress: {batches_completed} batches, {total_samples} samples")
    return state


def mark_ready_for_generation(data_dir: Optional[str] = None) -> dict:
    """Mark analysis as complete, ready for generation phase."""
    state = load_state(data_dir)
    
    state["analysis"]["ready_for_generation"] = True
    state["analysis"]["completed_at"] = datetime.now().isoformat()
    state["current_phase"] = "generation"
    
    save_state(state)
    print("✓ Analysis complete. Ready for generation phase.")
    return state


def complete_generation(output_path: str, data_dir: Optional[str] = None) -> dict:
    """Mark generation as complete."""
    state = load_state(data_dir)
    
    state["generation"]["completed_at"] = datetime.now().isoformat()
    state["generation"]["output_file"] = output_path
    state["current_phase"] = "complete"
    
    save_state(state)
    print(f"✓ Generation complete. Output: {output_path}")
    return state


def reset_to_phase(phase: str, data_dir: Optional[str] = None) -> dict:
    """Reset state to a specific phase (for re-running)."""
    valid_phases = ["setup", "analysis", "generation"]
    if phase not in valid_phases:
        raise ValueError(f"Phase must be one of: {valid_phases}")
    
    state = load_state(data_dir)
    state["current_phase"] = phase
    
    if phase == "analysis":
        state["analysis"]["ready_for_generation"] = False
    elif phase == "generation":
        state["generation"]["completed_at"] = None
        state["generation"]["output_file"] = None
    
    save_state(state)
    print(f"✓ Reset to phase: {phase}")
    return state


def get_state_summary(data_dir: Optional[str] = None) -> str:
    """Get human-readable state summary."""
    try:
        state = load_state(data_dir)
    except FileNotFoundError:
        return "No project found. Start with Phase 1: Setup."
    
    phase = state["current_phase"]
    lines = [
        "═" * 40,
        "WRITING STYLE CLONE - STATUS",
        "═" * 40,
        f"Current phase: {phase.upper()}",
        f"Data directory: {state['data_dir']}",
        ""
    ]
    
    if phase in ["analysis", "generation", "complete"]:
        a = state["analysis"]
        lines.append(f"Analysis: {a['batches_completed']} batches, {a['total_samples']} samples")
        if a["ready_for_generation"]:
            lines.append("  → Ready for generation")
    
    if phase == "complete":
        g = state["generation"]
        lines.append(f"Output: {g['output_file']}")
    
    lines.append("═" * 40)
    return "\n".join(lines)
