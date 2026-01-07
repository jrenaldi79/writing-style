"""
Style Manager - Core data management for Writing Style Clone project

GitHub: https://github.com/jrenaldi79/writing-style

Usage:
    from style_manager import init, get_persona_summary
    
    # Initialize with your data directory
    init("~/Documents/my-writing-style")
    
    # Now all functions use that directory
    print(get_persona_summary())
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Module-level state (set by init())
BASE_DIR: Path = None
REGISTRY_PATH: Path = None
SAMPLES_DIR: Path = None
CONFIG_PATH: Path = None
_initialized = False


def init(data_dir: str) -> Path:
    """
    Initialize the style manager with a data directory.
    
    Args:
        data_dir: Path to the data directory (e.g., "~/Documents/my-writing-style")
    
    Returns:
        The resolved base directory path
        
    Example:
        init("~/Documents/my-writing-style")
    """
    global BASE_DIR, REGISTRY_PATH, SAMPLES_DIR, CONFIG_PATH, _initialized
    
    BASE_DIR = Path(data_dir).expanduser().resolve()
    REGISTRY_PATH = BASE_DIR / "persona_registry.json"
    SAMPLES_DIR = BASE_DIR / "samples"
    CONFIG_PATH = BASE_DIR / "config.json"
    _initialized = True
    
    # Ensure directories exist
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "prompts").mkdir(exist_ok=True)
    
    print(f"✓ Style Manager initialized")
    print(f"  Data directory: {BASE_DIR}")
    
    return BASE_DIR


def _check_init():
    """Verify init() has been called."""
    if not _initialized:
        raise RuntimeError(
            "Style Manager not initialized. Call init('your/data/path') first.\n"
            "Example: init('~/Documents/my-writing-style')"
        )


def load_config() -> dict:
    """Load project configuration. Creates default if doesn't exist."""
    _check_init()
    
    if not CONFIG_PATH.exists():
        default_config = {
            "project_name": "Writing Style Clone",
            "created_at": datetime.now().isoformat()[:10],
            "sources": {
                "email": {"batch_size": 20},
                "linkedin": {"batch_size": 5}
            },
            "clustering": {
                "min_samples_for_persona": 3,
                "high_confidence_threshold": 0.80,
                "match_threshold_assign": 0.70,
                "match_threshold_review": 0.40
            }
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"✓ Created default config at {CONFIG_PATH}")
        return default_config
    
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_registry() -> dict:
    """Load the persona registry. Creates empty registry if doesn't exist."""
    _check_init()
    
    if not REGISTRY_PATH.exists():
        empty_registry = {
            "version": 1,
            "last_updated": None,
            "total_samples": 0,
            "samples_by_source": {"email": 0, "linkedin": 0},
            "personas": [],
            "unassigned_samples": [],
            "merge_history": []
        }
        with open(REGISTRY_PATH, "w") as f:
            json.dump(empty_registry, f, indent=2)
        print(f"✓ Created empty registry at {REGISTRY_PATH}")
        return empty_registry
    
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    """Save the persona registry with updated timestamp."""
    _check_init()
    registry["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"✓ Registry saved at {datetime.now().strftime('%H:%M:%S')}")


def get_next_sample_id(source: str) -> str:
    """Generate next sequential sample ID for a source."""
    _check_init()
    registry = load_registry()
    count = registry["samples_by_source"].get(source, 0) + 1
    return f"{source}_{count:03d}"


def hash_content(text: str) -> str:
    """Generate hash of content for deduplication."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def sample_exists(content_hash: str) -> bool:
    """Check if a sample with this content hash already exists."""
    _check_init()
    for sample_file in SAMPLES_DIR.glob("*.json"):
        with open(sample_file) as f:
            sample = json.load(f)
            if sample.get("content_hash") == content_hash:
                return True
    return False


def save_sample(
    source: str,
    analysis: dict,
    excerpt: str,
    full_text: str,
    metadata: Optional[dict] = None,
    persona_id: Optional[str] = None
) -> dict:
    """
    Save an analyzed sample to disk.
    
    Args:
        source: 'email' or 'linkedin'
        analysis: Dict with tone, formality, patterns, etc.
        excerpt: Best representative excerpt (2-4 sentences)
        full_text: Original full text (used for hashing, not stored)
        metadata: Source-specific metadata (subject, recipients, etc.)
        persona_id: Assigned persona ID (can be None if unassigned)
    
    Returns:
        The saved sample dict
    """
    content_hash = hash_content(full_text)
    
    if sample_exists(content_hash):
        print(f"⚠ Duplicate detected (hash: {content_hash}), skipping")
        return None
    
    sample_id = get_next_sample_id(source)
    
    sample = {
        "id": sample_id,
        "source": source,
        "persona_id": persona_id,
        "content_hash": content_hash,
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "analysis": analysis,
        "excerpt": excerpt
    }
    
    sample_path = SAMPLES_DIR / f"{sample_id}.json"
    with open(sample_path, "w") as f:
        json.dump(sample, f, indent=2)
    
    # Update registry counts
    registry = load_registry()
    registry["total_samples"] += 1
    registry["samples_by_source"][source] = registry["samples_by_source"].get(source, 0) + 1
    
    if persona_id is None:
        registry["unassigned_samples"].append(sample_id)
    
    save_registry(registry)
    
    print(f"✓ Saved {sample_id}")
    return sample


def create_persona(
    name: str,
    description: str,
    characteristics: dict,
    sample_ids: list,
    derived_rules: list,
    best_excerpts: list,
    source_breakdown: Optional[dict] = None
) -> dict:
    """
    Create a new persona in the registry.
    
    Returns:
        The created persona dict
    """
    registry = load_registry()
    
    persona_num = len(registry["personas"]) + 1
    persona_id = f"persona_{persona_num:03d}"
    
    persona = {
        "id": persona_id,
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "sample_count": len(sample_ids),
        "sample_ids": sample_ids,
        "source_breakdown": source_breakdown or {},
        "characteristics": characteristics,
        "derived_rules": derived_rules,
        "best_excerpts": best_excerpts,
        "confidence": min(0.5 + (len(sample_ids) * 0.05), 0.95),
        "notes": ""
    }
    
    registry["personas"].append(persona)
    
    # Update sample assignments and remove from unassigned
    for sid in sample_ids:
        if sid in registry["unassigned_samples"]:
            registry["unassigned_samples"].remove(sid)
        # Update the sample file
        sample_path = SAMPLES_DIR / f"{sid}.json"
        if sample_path.exists():
            with open(sample_path) as f:
                sample = json.load(f)
            sample["persona_id"] = persona_id
            with open(sample_path, "w") as f:
                json.dump(sample, f, indent=2)
    
    save_registry(registry)
    print(f"✓ Created persona: {name} ({persona_id}) with {len(sample_ids)} samples")
    
    return persona


def update_persona(
    persona_id: str,
    new_sample_ids: Optional[list] = None,
    updated_characteristics: Optional[dict] = None,
    new_rules: Optional[list] = None,
    new_excerpts: Optional[list] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Update an existing persona with new samples or refined characteristics.
    """
    registry = load_registry()
    
    persona = None
    for p in registry["personas"]:
        if p["id"] == persona_id:
            persona = p
            break
    
    if not persona:
        raise ValueError(f"Persona {persona_id} not found")
    
    if new_sample_ids:
        persona["sample_ids"].extend(new_sample_ids)
        persona["sample_count"] = len(persona["sample_ids"])
        persona["confidence"] = min(0.5 + (persona["sample_count"] * 0.05), 0.95)
        
        # Remove from unassigned and update sample files
        for sid in new_sample_ids:
            if sid in registry["unassigned_samples"]:
                registry["unassigned_samples"].remove(sid)
            sample_path = SAMPLES_DIR / f"{sid}.json"
            if sample_path.exists():
                with open(sample_path) as f:
                    sample = json.load(f)
                sample["persona_id"] = persona_id
                with open(sample_path, "w") as f:
                    json.dump(sample, f, indent=2)
    
    if updated_characteristics:
        persona["characteristics"].update(updated_characteristics)
    
    if new_rules:
        existing = set(persona["derived_rules"])
        persona["derived_rules"].extend([r for r in new_rules if r not in existing])
    
    if new_excerpts:
        persona["best_excerpts"].extend(new_excerpts)
        # Keep only best 5
        persona["best_excerpts"] = persona["best_excerpts"][:5]
    
    if notes:
        persona["notes"] = notes
    
    persona["updated_at"] = datetime.now().isoformat()
    save_registry(registry)
    
    print(f"✓ Updated {persona['name']} ({persona_id}): now {persona['sample_count']} samples")
    return persona


def get_persona_summary() -> str:
    """Generate a readable summary of all personas for the LLM."""
    registry = load_registry()
    
    if not registry["personas"]:
        return "No personas discovered yet. Registry is empty."
    
    lines = [
        f"PERSONA REGISTRY SUMMARY",
        f"========================",
        f"Total samples: {registry['total_samples']}",
        f"  - Email: {registry['samples_by_source'].get('email', 0)}",
        f"  - LinkedIn: {registry['samples_by_source'].get('linkedin', 0)}",
        f"Unassigned: {len(registry['unassigned_samples'])}",
        f"",
        f"PERSONAS ({len(registry['personas'])}):",
        f"-" * 40
    ]
    
    for p in registry["personas"]:
        lines.append(f"\n{p['name']} [{p['id']}]")
        lines.append(f"  Samples: {p['sample_count']} | Confidence: {p['confidence']:.0%}")
        lines.append(f"  Description: {p['description']}")
        lines.append(f"  Key traits: {', '.join(p['characteristics'].get('tone', []))}")
        lines.append(f"  Formality: {p['characteristics'].get('formality', 'unknown')}")
        if p.get('source_breakdown'):
            breakdown = ", ".join(f"{k}: {v}" for k, v in p['source_breakdown'].items())
            lines.append(f"  Sources: {breakdown}")
    
    if registry["unassigned_samples"]:
        lines.append(f"\n⚠ UNASSIGNED SAMPLES: {', '.join(registry['unassigned_samples'])}")
    
    return "\n".join(lines)


def get_all_samples(source: Optional[str] = None) -> list:
    """Load all samples, optionally filtered by source."""
    samples = []
    for sample_file in sorted(SAMPLES_DIR.glob("*.json")):
        with open(sample_file) as f:
            sample = json.load(f)
            if source is None or sample["source"] == source:
                samples.append(sample)
    return samples


def get_persona_samples(persona_id: str) -> list:
    """Get all samples assigned to a persona."""
    registry = load_registry()
    persona = None
    for p in registry["personas"]:
        if p["id"] == persona_id:
            persona = p
            break
    
    if not persona:
        return []
    
    samples = []
    for sid in persona["sample_ids"]:
        sample_path = SAMPLES_DIR / f"{sid}.json"
        if sample_path.exists():
            with open(sample_path) as f:
                samples.append(json.load(f))
    return samples


def merge_personas(persona_id_keep: str, persona_id_merge: str, new_name: Optional[str] = None) -> dict:
    """Merge two personas, keeping the first and absorbing the second."""
    registry = load_registry()
    
    keep = None
    merge = None
    merge_idx = None
    
    for i, p in enumerate(registry["personas"]):
        if p["id"] == persona_id_keep:
            keep = p
        if p["id"] == persona_id_merge:
            merge = p
            merge_idx = i
    
    if not keep or not merge:
        raise ValueError("One or both persona IDs not found")
    
    # Transfer samples
    keep["sample_ids"].extend(merge["sample_ids"])
    keep["sample_count"] = len(keep["sample_ids"])
    
    # Merge characteristics (keep's values take precedence for conflicts)
    for key, value in merge["characteristics"].items():
        if key not in keep["characteristics"]:
            keep["characteristics"][key] = value
        elif isinstance(value, list):
            existing = set(keep["characteristics"][key])
            keep["characteristics"][key].extend([v for v in value if v not in existing])
    
    # Add any unique rules
    existing_rules = set(keep["derived_rules"])
    keep["derived_rules"].extend([r for r in merge["derived_rules"] if r not in existing_rules])
    
    # Combine excerpts (keep best 5)
    keep["best_excerpts"].extend(merge["best_excerpts"])
    keep["best_excerpts"] = keep["best_excerpts"][:5]
    
    if new_name:
        keep["name"] = new_name
    
    keep["confidence"] = min(0.5 + (keep["sample_count"] * 0.05), 0.95)
    keep["updated_at"] = datetime.now().isoformat()
    
    # Record merge history
    registry["merge_history"].append({
        "kept": persona_id_keep,
        "merged": persona_id_merge,
        "merged_name": merge["name"],
        "timestamp": datetime.now().isoformat()
    })
    
    # Remove merged persona
    registry["personas"].pop(merge_idx)
    
    # Update sample files
    for sid in merge["sample_ids"]:
        sample_path = SAMPLES_DIR / f"{sid}.json"
        if sample_path.exists():
            with open(sample_path) as f:
                sample = json.load(f)
            sample["persona_id"] = persona_id_keep
            with open(sample_path, "w") as f:
                json.dump(sample, f, indent=2)
    
    save_registry(registry)
    print(f"✓ Merged '{merge['name']}' into '{keep['name']}' (now {keep['sample_count']} samples)")
    
    return keep


def export_for_prompt_generation() -> dict:
    """Export all data in a format optimized for prompt generation."""
    registry = load_registry()
    
    export = {
        "generated_at": datetime.now().isoformat(),
        "total_samples": registry["total_samples"],
        "personas": []
    }
    
    for persona in registry["personas"]:
        samples = get_persona_samples(persona["id"])
        
        # Aggregate source breakdown
        source_counts = {}
        for s in samples:
            src = s["source"]
            source_counts[src] = source_counts.get(src, 0) + 1
        
        export["personas"].append({
            "name": persona["name"],
            "description": persona["description"],
            "sample_count": persona["sample_count"],
            "source_breakdown": source_counts,
            "confidence": persona["confidence"],
            "characteristics": persona["characteristics"],
            "derived_rules": persona["derived_rules"],
            "best_excerpts": persona["best_excerpts"],
            "sample_excerpts": [s["excerpt"] for s in samples[:5]]
        })
    
    return export


def get_data_dir() -> Path:
    """Return the current data directory (after init)."""
    _check_init()
    return BASE_DIR


# Quick CLI for testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Initialize with provided path
        init(sys.argv[1])
        print(get_persona_summary())
    else:
        print("Usage: python style_manager.py <data_directory>")
        print("Example: python style_manager.py ~/Documents/my-writing-style")
