"""
Style Manager - Core data management for Writing Style Clone

Handles personas, samples, and registry operations.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Module state
BASE_DIR: Path = None
REGISTRY_PATH: Path = None
SAMPLES_DIR: Path = None
CONFIG_PATH: Path = None
_initialized = False


def init(data_dir: str) -> Path:
    """Initialize with data directory path."""
    global BASE_DIR, REGISTRY_PATH, SAMPLES_DIR, CONFIG_PATH, _initialized
    
    BASE_DIR = Path(data_dir).expanduser().resolve()
    REGISTRY_PATH = BASE_DIR / "persona_registry.json"
    SAMPLES_DIR = BASE_DIR / "samples"
    CONFIG_PATH = BASE_DIR / "config.json"
    _initialized = True
    
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "prompts").mkdir(exist_ok=True)
    
    # Create default config if needed
    if not CONFIG_PATH.exists():
        config = {
            "project_name": "Writing Style Clone",
            "created_at": datetime.now().isoformat()[:10],
            "sources": {"email": {"batch_size": 20}, "linkedin": {"batch_size": 5}},
            "clustering": {
                "min_samples_for_persona": 3,
                "high_confidence_threshold": 0.80,
                "match_threshold_assign": 0.70,
                "match_threshold_review": 0.40
            }
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    
    # Create empty registry if needed
    if not REGISTRY_PATH.exists():
        registry = {
            "version": 1,
            "last_updated": None,
            "total_samples": 0,
            "samples_by_source": {"email": 0, "linkedin": 0},
            "personas": [],
            "unassigned_samples": [],
            "flagged_samples": [],
            "merge_history": []
        }
        with open(REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)
    
    print(f"✓ Style Manager initialized: {BASE_DIR}")
    return BASE_DIR


def _check_init():
    if not _initialized:
        raise RuntimeError("Call init(data_dir) first")


def load_registry() -> dict:
    _check_init()
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    _check_init()
    registry["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def hash_content(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def sample_exists(content_hash: str) -> bool:
    _check_init()
    for f in SAMPLES_DIR.glob("*.json"):
        with open(f) as fp:
            if json.load(fp).get("content_hash") == content_hash:
                return True
    return False


def save_sample(
    source: str,
    analysis: dict,
    excerpt: str,
    full_text: str,
    metadata: Optional[dict] = None,
    persona_id: Optional[str] = None
) -> Optional[dict]:
    """Save an analyzed sample. Returns None if duplicate."""
    _check_init()
    
    content_hash = hash_content(full_text)
    if sample_exists(content_hash):
        print(f"⚠ Duplicate (hash: {content_hash}), skipping")
        return None
    
    registry = load_registry()
    count = registry["samples_by_source"].get(source, 0) + 1
    sample_id = f"{source}_{count:03d}"
    
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
    
    with open(SAMPLES_DIR / f"{sample_id}.json", "w") as f:
        json.dump(sample, f, indent=2)
    
    registry["total_samples"] += 1
    registry["samples_by_source"][source] = count
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
    """Create a new persona from clustered samples."""
    _check_init()
    registry = load_registry()
    
    persona_id = f"persona_{len(registry['personas']) + 1:03d}"
    
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
        "confidence": min(0.5 + len(sample_ids) * 0.05, 0.95),
        "notes": ""
    }
    
    registry["personas"].append(persona)
    
    # Update sample assignments
    for sid in sample_ids:
        if sid in registry["unassigned_samples"]:
            registry["unassigned_samples"].remove(sid)
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
    new_excerpts: Optional[list] = None
) -> dict:
    """Update existing persona with new samples or characteristics."""
    _check_init()
    registry = load_registry()
    
    persona = next((p for p in registry["personas"] if p["id"] == persona_id), None)
    if not persona:
        raise ValueError(f"Persona {persona_id} not found")
    
    if new_sample_ids:
        persona["sample_ids"].extend(new_sample_ids)
        persona["sample_count"] = len(persona["sample_ids"])
        persona["confidence"] = min(0.5 + persona["sample_count"] * 0.05, 0.95)
        
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
        persona["best_excerpts"] = (persona["best_excerpts"] + new_excerpts)[:5]
    
    persona["updated_at"] = datetime.now().isoformat()
    save_registry(registry)
    print(f"✓ Updated {persona['name']}: {persona['sample_count']} samples")
    return persona


def flag_sample(sample_id: str, reason: str, scores: dict) -> None:
    """Flag a sample for manual review."""
    _check_init()
    registry = load_registry()
    registry["flagged_samples"].append({
        "sample_id": sample_id,
        "reason": reason,
        "scores": scores,
        "flagged_at": datetime.now().isoformat()
    })
    save_registry(registry)


def merge_personas(keep_id: str, merge_id: str, new_name: Optional[str] = None) -> dict:
    """Merge two personas, keeping the first."""
    _check_init()
    registry = load_registry()
    
    keep = next((p for p in registry["personas"] if p["id"] == keep_id), None)
    merge = next((p for p in registry["personas"] if p["id"] == merge_id), None)
    
    if not keep or not merge:
        raise ValueError("Persona not found")
    
    # Transfer samples
    keep["sample_ids"].extend(merge["sample_ids"])
    keep["sample_count"] = len(keep["sample_ids"])
    keep["confidence"] = min(0.5 + keep["sample_count"] * 0.05, 0.95)
    
    # Merge characteristics
    for key, val in merge["characteristics"].items():
        if key not in keep["characteristics"]:
            keep["characteristics"][key] = val
        elif isinstance(val, list):
            keep["characteristics"][key] = list(set(keep["characteristics"][key] + val))
    
    # Merge rules and excerpts
    keep["derived_rules"] = list(set(keep["derived_rules"] + merge["derived_rules"]))
    keep["best_excerpts"] = (keep["best_excerpts"] + merge["best_excerpts"])[:5]
    
    if new_name:
        keep["name"] = new_name
    
    # Record merge
    registry["merge_history"].append({
        "kept": keep_id,
        "merged": merge_id,
        "merged_name": merge["name"],
        "timestamp": datetime.now().isoformat()
    })
    
    # Remove merged persona
    registry["personas"] = [p for p in registry["personas"] if p["id"] != merge_id]
    
    # Update sample files
    for sid in merge["sample_ids"]:
        sample_path = SAMPLES_DIR / f"{sid}.json"
        if sample_path.exists():
            with open(sample_path) as f:
                sample = json.load(f)
            sample["persona_id"] = keep_id
            with open(sample_path, "w") as f:
                json.dump(sample, f, indent=2)
    
    save_registry(registry)
    print(f"✓ Merged '{merge['name']}' into '{keep['name']}'")
    return keep


def get_persona_summary() -> str:
    """Human-readable summary of all personas."""
    _check_init()
    registry = load_registry()
    
    if not registry["personas"]:
        return "No personas discovered yet."
    
    lines = [
        "═" * 40,
        "PERSONA SUMMARY",
        "═" * 40,
        f"Total samples: {registry['total_samples']}",
        f"  Email: {registry['samples_by_source'].get('email', 0)}",
        f"  LinkedIn: {registry['samples_by_source'].get('linkedin', 0)}",
        f"Unassigned: {len(registry['unassigned_samples'])}",
        f"Flagged: {len(registry.get('flagged_samples', []))}",
        "",
        f"PERSONAS ({len(registry['personas'])}):",
        "─" * 40
    ]
    
    for p in registry["personas"]:
        lines.append(f"\n{p['name']} [{p['id']}]")
        lines.append(f"  Samples: {p['sample_count']} | Confidence: {p['confidence']:.0%}")
        lines.append(f"  Tone: {', '.join(p['characteristics'].get('tone', []))}")
        lines.append(f"  Formality: {p['characteristics'].get('formality', 'unknown')}")
    
    lines.append("═" * 40)
    return "\n".join(lines)


def get_all_samples(source: Optional[str] = None) -> list:
    """Load all samples, optionally filtered by source."""
    _check_init()
    samples = []
    for f in sorted(SAMPLES_DIR.glob("*.json")):
        with open(f) as fp:
            sample = json.load(fp)
            if source is None or sample["source"] == source:
                samples.append(sample)
    return samples


def get_persona_samples(persona_id: str) -> list:
    """Get all samples for a persona."""
    _check_init()
    registry = load_registry()
    persona = next((p for p in registry["personas"] if p["id"] == persona_id), None)
    if not persona:
        return []
    
    samples = []
    for sid in persona["sample_ids"]:
        path = SAMPLES_DIR / f"{sid}.json"
        if path.exists():
            with open(path) as f:
                samples.append(json.load(f))
    return samples


def export_for_prompt_generation() -> dict:
    """Export all data for generation phase."""
    _check_init()
    registry = load_registry()
    
    export = {
        "generated_at": datetime.now().isoformat(),
        "total_samples": registry["total_samples"],
        "personas": []
    }
    
    for persona in registry["personas"]:
        samples = get_persona_samples(persona["id"])
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
            "all_excerpts": [s["excerpt"] for s in samples]
        })
    
    return export
