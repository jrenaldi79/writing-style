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

from config import get_data_dir, get_path
from email_analysis_v2 import detect_schema_version, migrate_v1_to_v2

DATA_DIR = get_data_dir()
SAMPLES_DIR = get_path("samples")
RAW_SAMPLES_DIR = get_path("raw_samples")
PERSONA_FILE = get_path("persona_registry.json")
STATE_FILE = get_path("state.json")
CLUSTERS_FILE = get_path("clusters.json")

# Minimum coverage threshold for persona quality
MIN_COVERAGE_THRESHOLD = 0.8


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


def validate_batch_coverage(batch_data: dict, force: bool = False) -> tuple:
    """Validate that batch ingestion meets coverage requirements.

    Checks if the batch covers a cluster and whether ingesting it would
    result in sub-threshold coverage (< 80%).

    Args:
        batch_data: The batch JSON data with samples
        force: If True, return warnings but don't block

    Returns:
        tuple: (should_proceed: bool, message: str)
    """
    if not CLUSTERS_FILE.exists():
        # No clusters - legacy mode, allow ingestion
        return True, ""

    clusters_data = load_json(CLUSTERS_FILE)
    if not clusters_data:
        return True, ""

    cluster_id = batch_data.get("cluster_id")
    if cluster_id is None:
        # No cluster_id in batch - legacy mode, allow
        return True, ""

    # Find the cluster
    cluster = None
    for c in clusters_data.get('clusters', []):
        if c.get('id') == cluster_id:
            cluster = c
            break

    if not cluster:
        return True, f"Warning: Cluster {cluster_id} not found in clusters.json"

    # Count already analyzed samples
    analyzed_ids = set()
    if SAMPLES_DIR.exists():
        for f in SAMPLES_DIR.glob("*.json"):
            analyzed_ids.add(f.stem)

    sample_ids = cluster.get('sample_ids', [])
    total_in_cluster = len(sample_ids)

    if total_in_cluster == 0:
        return True, ""

    # Count samples in this batch that belong to this cluster
    batch_samples = batch_data.get("samples", [])
    batch_sample_ids = set()
    for s in batch_samples:
        sid = s.get("id", "")
        # Handle both "email_xxx" and "xxx" formats
        if sid.startswith("email_"):
            batch_sample_ids.add(sid)
            batch_sample_ids.add(sid[6:])  # Also add without prefix
        else:
            batch_sample_ids.add(sid)
            batch_sample_ids.add(f"email_{sid}")  # Also add with prefix

    # Current coverage before this batch
    already_analyzed = sum(1 for s in sample_ids if s in analyzed_ids)
    current_coverage = already_analyzed / total_in_cluster

    # New samples from this batch (not already ingested)
    new_from_batch = sum(1 for s in sample_ids
                        if s in batch_sample_ids and s not in analyzed_ids)

    # Projected coverage after this batch
    projected_analyzed = already_analyzed + new_from_batch
    projected_coverage = projected_analyzed / total_in_cluster

    required = int(total_in_cluster * MIN_COVERAGE_THRESHOLD + 0.999)  # ceil

    # Check if this is a partial batch that would leave coverage below threshold
    if projected_coverage < MIN_COVERAGE_THRESHOLD:
        remaining = total_in_cluster - projected_analyzed
        deficit = required - projected_analyzed

        warning = f"""
{'═' * 60}
⚠️  COVERAGE VALIDATION FAILED
{'═' * 60}

Cluster {cluster_id}: {total_in_cluster} emails
  Required for {MIN_COVERAGE_THRESHOLD:.0%} coverage: {required} emails
  Already analyzed: {already_analyzed}
  In this batch: {new_from_batch}
  Projected total: {projected_analyzed} ({projected_coverage:.0%})

  ❌ Still need {deficit} more emails to reach threshold

{'─' * 60}
OPTIONS:

1. RECOMMENDED: Include more emails in this batch
   Run: python prepare_batch.py --cluster {cluster_id}
   This will show remaining emails in the cluster.

2. FORCE: Proceed anyway (not recommended - degrades persona quality)
   Run: python ingest.py {batch_data.get('batch_id', 'batch_XXX')}.json --force

{'═' * 60}
"""

        if force:
            return True, warning.replace("FAILED", "WARNING (bypassed with --force)")
        else:
            return False, warning

    return True, ""


def ingest_batch(batch_file, dry_run=False, force=False):
    """Process a batch analysis file.

    Args:
        batch_file: Path to the batch JSON file
        dry_run: If True, preview without saving
        force: If True, bypass coverage validation
    """

    # Load batch data
    with open(batch_file) as f:
        batch = json.load(f)

    # Validate coverage requirements (unless dry-run)
    if not dry_run:
        should_proceed, message = validate_batch_coverage(batch, force=force)
        if message:
            print(message)
        if not should_proceed:
            return False

    samples = batch.get("samples", [])
    new_personas = batch.get("new_personas", [])
    
    if not samples:
        print("❌ No 'samples' array found in batch file")
        print("\n📋 Expected format:")
        print('  "samples": [')
        print('    {"id": "email_xxx", "source": "email", "persona": "Name", "confidence": 0.85, "analysis": {...}, "context": {...}}')
        print('  ]')
        
        # Check for common mistakes
        if "sample_ids" in batch:
            print("\n⚠️  Found 'sample_ids' - did you mean 'samples'?")
            print("    Each sample needs full analysis object, not just IDs.")
        if "persona" in batch and "new_personas" not in batch:
            print("\n⚠️  Found 'persona' (singular) - did you mean 'new_personas' (array)?")
        if batch.get("samples") == []:
            print("\n⚠️  'samples' array exists but is empty.")
        
        print("\n📖 Run: python prepare_batch.py")
        print("    The output includes the required JSON schema.")
        return False
    
    print(f"📦 Processing batch: {len(samples)} samples, {len(new_personas)} new personas")
    
    if dry_run:
        print("\n🔍 DRY RUN - no changes will be made\n")
    
    # Load existing data
    personas = load_json(PERSONA_FILE) if PERSONA_FILE.exists() else {"personas": {}, "created": datetime.now().isoformat()}
    state = load_json(STATE_FILE)
    
    # Detect batch schema version
    batch_version = detect_schema_version(batch)
    if batch_version == "1.0":
        print(f"  📦 Detected v1.0 schema - will migrate to v2.0")

    # Process new personas
    for persona in new_personas:
        name = persona.get("name")
        if name and name not in personas.get("personas", {}):
            print(f"  ✨ New persona: {name}")
            if not dry_run:
                if "personas" not in personas:
                    personas["personas"] = {}

                # Check if persona needs migration (v1 -> v2)
                characteristics = persona.get("characteristics", {})
                if characteristics and "voice_fingerprint" not in characteristics:
                    # V1 format - migrate to v2
                    print(f"    ↳ Migrating {name} from v1 to v2 schema")
                    characteristics = migrate_v1_to_v2(characteristics)

                personas["personas"][name] = {
                    "description": persona.get("description", ""),
                    "sample_count": 0,
                    "created": datetime.now().isoformat(),
                    "characteristics": characteristics
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

        # Migrate sample analysis if v1 format
        analysis = sample.get("analysis", {})
        if analysis and "voice_fingerprint" not in analysis:
            # V1 format - migrate to v2
            analysis = migrate_v1_to_v2(analysis)

        sample_data = {
            "id": sample_id,
            "source": sample.get("source", "email"),
            "persona": persona_name,
            "confidence": sample.get("confidence", 0.0),
            "analysis": analysis,
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

    # Check remaining clusters and provide guidance
    if not dry_run:
        clusters_file = get_path("clusters.json")
        remaining_clusters = 0
        total_clusters = 0

        if clusters_file.exists():
            with open(clusters_file) as f:
                clusters_data = json.load(f)

            # Count clusters that still need analysis
            analyzed_ids = set()
            if SAMPLES_DIR.exists():
                for f in SAMPLES_DIR.glob("*.json"):
                    analyzed_ids.add(f.stem)

            for cluster in clusters_data.get('clusters', []):
                if cluster.get('is_noise'):
                    continue
                total_clusters += 1
                sample_ids = cluster.get('sample_ids', [])
                unanalyzed = [s for s in sample_ids if s not in analyzed_ids]
                if unanalyzed:
                    remaining_clusters += 1

        if remaining_clusters > 0:
            print(f"\n📊 PROGRESS: {total_clusters - remaining_clusters}/{total_clusters} clusters analyzed")
            print(f"\n💡 Next step:")
            print(f"   Run: python prepare_batch.py")
            print(f"   Remaining clusters: {remaining_clusters}")
        else:
            # Check for validation set
            validation_dir = get_path("validation_set")
            validation_count = len(list(validation_dir.glob("*.json"))) if validation_dir.exists() else 0

            print(f"\n{'═' * 60}")
            print("✅ ALL CLUSTERS ANALYZED!")
            print(f"{'═' * 60}")
            print(f"\nEmail personas are ready.")

            if validation_count > 0:
                print(f"\n📊 VALIDATION DATA AVAILABLE: {validation_count} held-out emails")
                print(f"\nRecommended next steps:")
                print(f"   1. VALIDATE personas first (blind test):")
                print(f"      python prepare_validation.py")
                print(f"      python validate_personas.py --auto")
                print(f"\n   2. THEN generate your writing clone skill:")
                print(f"      python generate_skill.py --name <your-name>")
                print(f"\n   3. Or add LinkedIn voice (optional):")
                print(f"      python fetch_linkedin_mcp.py --profile \"URL\"")
            else:
                print(f"\nYou can now:")
                print(f"   1. Generate your writing clone skill:")
                print(f"      python generate_skill.py --name <your-name>")
                print(f"   2. Or add LinkedIn voice first (optional):")
                print(f"      python fetch_linkedin_mcp.py --profile \"URL\"")
            print(f"{'═' * 60}")

            # Session boundary - explicit STOP
            print(f"\n{'█' * 60}")
            print("█  STOP - EMAIL ANALYSIS COMPLETE                          █")
            print("█                                                          █")
            print("█  START A NEW CHAT before proceeding to:                  █")
            print("█    • Validation (Session 2b: Judge)                      █")
            print("█    • LinkedIn (Session 3)                                █")
            print("█    • Generation (Session 4)                              █")
            print("█                                                          █")
            print("█  Reason: Clean context improves output quality.          █")
            print(f"{'█' * 60}\n")

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
  python ingest.py batch_001.json --force   # Bypass coverage validation
  python ingest.py --status                 # Show current status
        """
    )
    parser.add_argument("batch_file", nargs="?", help="JSON file with batch analysis")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Bypass coverage validation (not recommended)")
    parser.add_argument("--status", action="store_true", help="Show ingest status")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.batch_file:
        ingest_batch(args.batch_file, dry_run=args.dry_run, force=args.force)
    else:
        parser.print_help()
