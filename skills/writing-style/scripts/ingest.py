#!/usr/bin/env python3
"""
Ingest - Process batch analysis results from Claude

Takes a JSON file with analysis results and:
- Updates persona_registry.json
- Saves individual sample files WITH full email content (NEW: 2026-01-07)
- Updates state.json

The sample files now include the full email content (subject, body, snippet, etc.)
under a 'content' field, eliminating the need to cross-reference raw_samples/
during the generation phase.

Usage:
    python ingest.py batch_001.json
    python ingest.py batch_002.json --dry-run
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "Documents" / "my-writing-style"
SAMPLES_DIR = DATA_DIR / "samples"
RAW_SAMPLES_DIR = DATA_DIR / "raw_samples"
PERSONA_FILE = DATA_DIR / "persona_registry.json"
STATE_FILE = DATA_DIR / "state.json"


def load_json(path):
    """Load JSON file, return empty dict if not found."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    """Save data to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def ingest_batch(batch_file, dry_run=False):
    """Process a batch analysis file."""
    
    # Load batch data
    with open(batch_file) as f:
        batch = json.load(f)
    
    samples = batch.get("samples", [])
    new_personas = batch.get("new_personas", [])
    
    if not samples:
        print("❌ No samples found in batch file")
        return False
    
    print(f"📦 Processing batch: {len(samples)} samples, {len(new_personas)} new personas")
    
    if dry_run:
        print("\n🔍 DRY RUN - no changes will be made\n")
    
    # Load existing data
    personas = load_json(PERSONA_FILE) if PERSONA_FILE.exists() else {"personas": {}, "created": datetime.now().isoformat()}
    state = load_json(STATE_FILE)
    
    # Process new personas
    for persona in new_personas:
        name = persona.get("name")
        if name and name not in personas.get("personas", {}):
            print(f"  ✨ New persona: {name}")
            if not dry_run:
                if "personas" not in personas:
                    personas["personas"] = {}
                personas["personas"][name] = {
                    "description": persona.get("description", ""),
                    "sample_count": 0,
                    "created": datetime.now().isoformat(),
                    "characteristics": persona.get("characteristics", {})
                }
    
    # Process samples
    saved_count = 0
    persona_counts = {}
    
    for sample in samples:
        sample_id = sample.get("id")
        if not sample_id:
            continue
        
        persona_name = sample.get("persona", "Unassigned")
        persona_counts[persona_name] = persona_counts.get(persona_name, 0) + 1
        
        # Load email content from raw_samples
        raw_email_file = RAW_SAMPLES_DIR / f"email_{sample_id}.json"
        email_content = {}
        if raw_email_file.exists():
            with open(raw_email_file) as f:
                raw_data = json.load(f)
                # Extract essential fields for generation phase
                email_content = {
                    "subject": raw_data.get("subject", ""),
                    "body": raw_data.get("body", ""),
                    "snippet": raw_data.get("snippet", ""),
                    "from": raw_data.get("from", ""),
                    "to": raw_data.get("to", ""),
                    "date": raw_data.get("date", "")
                }
        
        # Save sample file
        sample_file = SAMPLES_DIR / f"{sample_id}.json"
        
        sample_data = {
            "id": sample_id,
            "source": sample.get("source", "email"),
            "persona": persona_name,
            "confidence": sample.get("confidence", 0.0),
            "analysis": sample.get("analysis", {}),
            "content": email_content,
            "ingested": datetime.now().isoformat()
        }
        
        if not dry_run:
            SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
            save_json(sample_file, sample_data)
        
        saved_count += 1
        conf = sample.get("confidence", 0)
        conf_indicator = "✓" if conf >= 0.7 else "?" if conf >= 0.4 else "⚠"
        print(f"  {conf_indicator} {sample_id[:20]}... → {persona_name} ({conf:.0%})")
    
    # Update persona counts
    if not dry_run:
        for persona_name, count in persona_counts.items():
            if persona_name in personas.get("personas", {}):
                personas["personas"][persona_name]["sample_count"] = \
                    personas["personas"][persona_name].get("sample_count", 0) + count
        
        personas["updated"] = datetime.now().isoformat()
        save_json(PERSONA_FILE, personas)
    
    # Update state
    if not dry_run:
        state["batches_completed"] = state.get("batches_completed", 0) + 1
        state["total_samples"] = state.get("total_samples", 0) + saved_count
        state["last_ingest"] = datetime.now().isoformat()
        state["current_phase"] = "analysis"
        save_json(STATE_FILE, state)
    
    # Summary
    print(f"\n{'═' * 50}")
    print("INGEST COMPLETE" if not dry_run else "DRY RUN COMPLETE")
    print(f"{'═' * 50}")
    print(f"Samples processed: {saved_count}")
    print(f"Personas: {', '.join(f'{k} ({v})' for k, v in persona_counts.items())}")
    
    if not dry_run:
        print(f"Total samples: {state['total_samples']}")
        print(f"Batches completed: {state['batches_completed']}")
    
    print(f"{'═' * 50}")
    
    return True


def show_status():
    """Show current ingest status."""
    state = load_json(STATE_FILE)
    personas = load_json(PERSONA_FILE)
    
    # Count actual sample files
    sample_count = len(list(SAMPLES_DIR.glob("*.json"))) if SAMPLES_DIR.exists() else 0
    
    print(f"\n{'═' * 50}")
    print("INGEST STATUS")
    print(f"{'═' * 50}")
    print(f"Total samples: {sample_count}")
    print(f"Batches completed: {state.get('batches_completed', 0)}")
    print(f"Current phase: {state.get('current_phase', 'unknown')}")
    
    if personas.get("personas"):
        print(f"\nPersonas:")
        for name, data in personas["personas"].items():
            print(f"  • {name}: {data.get('sample_count', 0)} samples")
    
    print(f"{'═' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest batch analysis results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py batch_001.json           # Process a batch
  python ingest.py batch_001.json --dry-run # Preview without saving
  python ingest.py --status                 # Show current status
        """
    )
    parser.add_argument("batch_file", nargs="?", help="JSON file with batch analysis")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--status", action="store_true", help="Show ingest status")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.batch_file:
        ingest_batch(args.batch_file, dry_run=args.dry_run)
    else:
        parser.print_help()
