#!/usr/bin/env python3
"""
Prepare Batch - Format clustered emails for agent analysis

Reads pre-computed clusters and formats emails for analysis.
Includes calibration reference for consistent scoring.

Usage:
    python prepare_batch.py                     # Prepare next unanalyzed cluster
    python prepare_batch.py --cluster 2         # Prepare specific cluster
    python prepare_batch.py --all               # Show all clusters status
    python prepare_batch.py --legacy --count 30 # Legacy mode (random emails)
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import argparse
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
CLUSTERS_FILE = get_path("clusters.json")
ENRICHED_DIR = get_path("enriched_samples")
RAW_DIR = get_path("raw_samples")
BATCHES_DIR = get_path("batches")
SAMPLES_DIR = get_path("samples")

# Calibration reference path (in skill repo)
SKILL_DIR = Path(__file__).parent.parent
CALIBRATION_FILE = SKILL_DIR / "references" / "calibration.md"


def extract_body(email_data: dict) -> str:
    """Extract plain text body from email data."""
    payload = email_data.get('payload', {})
    
    def find_text_part(parts):
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    try:
                        return base64.urlsafe_b64decode(body_data).decode('utf-8')
                    except:
                        pass
            if 'parts' in part:
                result = find_text_part(part['parts'])
                if result:
                    return result
        return None
    
    if 'parts' in payload:
        body = find_text_part(payload['parts'])
        if body:
            return body
    
    body_data = payload.get('body', {}).get('data', '')
    if body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode('utf-8')
        except:
            pass
    
    return email_data.get('snippet', '')


def get_header(email_data: dict, header_name: str) -> str:
    """Get a specific header value from email."""
    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == header_name.lower():
            return header.get('value', '')
    return ''


def get_analyzed_ids() -> set:
    """Get set of already-analyzed email IDs."""
    analyzed = set()
    
    # Check samples directory
    if SAMPLES_DIR.exists():
        for f in SAMPLES_DIR.glob('*.json'):
            analyzed.add(f.stem)
    
    # Check batches for submitted analyses
    if BATCHES_DIR.exists():
        for batch_file in BATCHES_DIR.glob('batch_*.json'):
            try:
                with open(batch_file) as f:
                    batch = json.load(f)
                for sample in batch.get('samples', []):
                    analyzed.add(sample.get('id', ''))
            except:
                continue
    
    return analyzed


def load_cluster_data() -> Optional[Dict]:
    """Load cluster assignments."""
    if not CLUSTERS_FILE.exists():
        return None
    
    with open(CLUSTERS_FILE) as f:
        return json.load(f)


def load_calibration() -> str:
    """Load calibration reference content."""
    if CALIBRATION_FILE.exists():
        with open(CALIBRATION_FILE) as f:
            return f.read()
    
    # Fallback minimal calibration
    return """# Calibration Reference

Use consistent scoring scales:
- Formality: 1 (very casual) to 10 (highly formal)
- Warmth: 1 (cold) to 10 (effusive)
- Authority: 1 (deferential) to 10 (directive)
- Directness: 1 (very indirect) to 10 (blunt)

Reference your previous batch scores to maintain consistency.
"""


def format_email_for_analysis(email_id: str, enriched_data: Dict) -> Dict:
    """Format a single email for agent analysis."""
    email_data = enriched_data.get('original_data', enriched_data)
    enrichment = enriched_data.get('enrichment', {})
    quality = enriched_data.get('quality', {})
    
    subject = get_header(email_data, 'subject')
    to_header = get_header(email_data, 'to')
    body = extract_body(email_data)
    
    return {
        'id': email_id,
        'subject': subject,
        'to': to_header[:100] if to_header else '',
        'body': body,
        'enrichment': {
            'recipient_type': enrichment.get('recipient_type'),
            'audience': enrichment.get('audience'),
            'thread_position': enrichment.get('thread_position'),
            'has_bullets': enrichment.get('has_bullets'),
            'paragraph_count': enrichment.get('paragraph_count')
        },
        'quality_score': quality.get('score', 0)
    }


def prepare_cluster_batch(cluster_id: int) -> str:
    """Prepare a batch from a specific cluster."""
    clusters_data = load_cluster_data()
    if not clusters_data:
        return "[ERROR] No clusters found. Run: python cluster_emails.py"
    
    # Find the cluster
    cluster = None
    for c in clusters_data.get('clusters', []):
        if c['id'] == cluster_id:
            cluster = c
            break
    
    if not cluster:
        return f"[ERROR] Cluster {cluster_id} not found"
    
    if cluster.get('is_noise'):
        return f"[WARNING] Cluster {cluster_id} is noise (unclustered emails)"
    
    # Get already analyzed IDs
    analyzed = get_analyzed_ids()
    
    # Get unanalyzed emails from this cluster
    sample_ids = cluster.get('sample_ids', [])
    unanalyzed = [sid for sid in sample_ids if sid not in analyzed]

    # Calculate and show coverage
    analyzed_count = len(sample_ids) - len(unanalyzed)
    coverage = analyzed_count / len(sample_ids) if sample_ids else 0

    if coverage > 0 and coverage < 1.0:
        print(f"\n{'-' * 50}")
        print(f"[STATS] CLUSTER {cluster_id} COVERAGE: {coverage:.0%}")
        print(f"   Analyzed: {analyzed_count} / {len(sample_ids)} emails")
        print(f"   Remaining: {len(unanalyzed)} emails")
        if coverage < 0.8:
            print(f"\n   [WARNING]  WARNING: Coverage below 80%")
            print(f"   Persona quality may suffer with incomplete data.")
            print(f"   Run prepare_batch.py again after ingest to get remaining emails.")
        print(f"{'-' * 50}\n")

    if not unanalyzed:
        return f"[OK] Cluster {cluster_id} fully analyzed ({len(sample_ids)} emails)"
    
    # Load and format emails
    emails = []
    for email_id in unanalyzed:
        # Try enriched first
        enriched_path = ENRICHED_DIR / f"{email_id}.json"
        if enriched_path.exists():
            with open(enriched_path) as f:
                enriched_data = json.load(f)
            emails.append(format_email_for_analysis(email_id, enriched_data))
    
    if not emails:
        return f"[WARNING] No loadable emails in cluster {cluster_id}"
    
    # Build output
    output = []
    
    # Add calibration header
    calibration = load_calibration()
    output.append(calibration)
    output.append("\n" + "=" * 60 + "\n")
    
    # Add cluster context
    output.append(f"# Cluster {cluster_id} Analysis\n")
    output.append(f"**Cluster size:** {cluster['size']} emails")
    output.append(f"**Unanalyzed:** {len(emails)} emails")
    output.append(f"**Centroid examples:** {', '.join(cluster.get('centroid_emails', [])[:3])}")
    
    # Add enrichment summary
    enrichment_summary = cluster.get('enrichment_summary', {})
    if enrichment_summary:
        output.append(f"\n**Cluster characteristics:**")
        if enrichment_summary.get('recipient_types'):
            output.append(f"- Recipient types: {enrichment_summary['recipient_types']}")
        if enrichment_summary.get('audiences'):
            output.append(f"- Audiences: {enrichment_summary['audiences']}")
        if enrichment_summary.get('thread_positions'):
            output.append(f"- Thread positions: {enrichment_summary['thread_positions']}")
    
    output.append("\n" + "=" * 60 + "\n")
    output.append("# Emails to Analyze\n")
    
    # Add each email
    for i, email in enumerate(emails, 1):
        output.append(f"## Email {i}: {email['id']}\n")
        output.append(f"**Subject:** {email['subject']}")
        output.append(f"**To:** {email['to']}")
        output.append(f"**Context:** {email['enrichment']['recipient_type']}, {email['enrichment']['audience']}, {email['enrichment']['thread_position']}")
        output.append(f"**Quality Score:** {email['quality_score']:.2f}")
        output.append(f"\n**Body:**\n```\n{email['body']}\n```\n")
        output.append("-" * 40 + "\n")
    
    # Add instructions
    output.append("\n" + "=" * 60)
    output.append("\n# Analysis Instructions\n")
    output.append("""1. **Read calibration reference** above for scoring consistency
2. **Analyze each email** for tone, formality, structure, patterns
3. **Determine persona** - create new if needed, or assign to existing
4. **Output JSON** using the schema below
5. **Save as** batches/batch_NNN.json
6. **Run ingest:** python ingest.py batches/batch_NNN.json

**Remember:** Include `calibration_referenced: true` in your output.

## Required JSON Schema

```json
{
  "batch_id": "batch_001",
  "analyzed_at": "2026-01-07T12:00:00Z",
  "email_count": 35,
  "cluster_id": 1,
  "calibration_referenced": true,
  "calibration_notes": "Anchored formality against examples 3/5, authority against 7/9",
  "new_personas": [
    {
      "name": "Persona Name",
      "description": "When this persona is used",
      "characteristics": {
        "tone": ["word1", "word2"],
        "formality": 5,
        "warmth": 6,
        "authority": 7,
        "directness": 8,
        "typical_greeting": "Hey / Hi there",
        "typical_closing": "JR",
        "uses_contractions": true
      }
    }
  ],
  "samples": [
    {
      "id": "email_abc123def456",
      "source": "email",
      "persona": "Persona Name",
      "confidence": 0.85,
      "analysis": {
        "tone_vectors": {"formality": 5, "warmth": 6, "authority": 7, "directness": 8},
        "tone_descriptors": ["warm", "direct"],
        "sentence_style": "short, punchy",
        "paragraph_style": "single topic",
        "greeting": "Hey / none",
        "closing": "JR / none",
        "punctuation": ["em-dashes", "exclamations"],
        "contractions": true,
        "notable_phrases": ["phrase1", "phrase2"],
        "structure": "greeting -> content -> close"
      },
      "context": {
        "recipient_type": "small_group",
        "audience": "unknown",
        "thread_position": "initiating"
      }
    }
  ]
}
```

**IMPORTANT:**
- `samples` must be an array with one object per email (not just IDs)
- Each sample needs `id`, `persona`, `confidence`, `analysis`, and `context`
- `new_personas` is only needed when discovering NEW personas""")
    
    return "\n".join(output)


def prepare_legacy_batch(count: int = 30) -> str:
    """Legacy mode: prepare random unanalyzed emails (no clustering)."""
    analyzed = get_analyzed_ids()
    
    # Find source directory
    source_dir = ENRICHED_DIR if ENRICHED_DIR.exists() else RAW_DIR
    if not source_dir.exists():
        return f"[ERROR] No email samples found in {source_dir}"
    
    # Get unanalyzed emails
    all_files = list(source_dir.glob('email_*.json'))
    unanalyzed = [f for f in all_files if f.stem not in analyzed]
    
    if not unanalyzed:
        return "[OK] All emails have been analyzed!"
    
    # Take requested count
    batch_files = unanalyzed[:count]
    
    # Load and format
    emails = []
    for filepath in batch_files:
        try:
            with open(filepath) as f:
                data = json.load(f)
            emails.append(format_email_for_analysis(filepath.stem, data))
        except:
            continue
    
    if not emails:
        return "[ERROR] No loadable emails found"
    
    # Build output
    output = []
    
    # Add calibration
    calibration = load_calibration()
    output.append(calibration)
    output.append("\n" + "=" * 60 + "\n")
    
    output.append(f"# Batch Analysis ({len(emails)} emails)\n")
    output.append(f"Remaining unanalyzed: {len(unanalyzed) - len(emails)}\n")
    output.append("=" * 60 + "\n")
    
    for i, email in enumerate(emails, 1):
        output.append(f"## Email {i}: {email['id']}\n")
        output.append(f"**Subject:** {email['subject']}")
        output.append(f"**To:** {email['to']}")
        if email.get('enrichment', {}).get('recipient_type'):
            output.append(f"**Context:** {email['enrichment']['recipient_type']}, {email['enrichment']['audience']}")
        output.append(f"\n**Body:**\n```\n{email['body']}\n```\n")
        output.append("-" * 40 + "\n")
    
    output.append("\n" + "=" * 60)
    output.append("\n# Instructions\n")
    output.append("""Analyze and output JSON per batch_schema.md.
Include `calibration_referenced: true` in output.""")
    
    return "\n".join(output)


def show_clusters_status():
    """Show status of all clusters."""
    clusters_data = load_cluster_data()
    analyzed = get_analyzed_ids()
    
    print(f"\n{'=' * 50}")
    print("CLUSTER STATUS")
    print(f"{'=' * 50}")
    
    if not clusters_data:
        print("[ERROR] No clusters found. Run: python cluster_emails.py")
        print(f"{'=' * 50}\n")
        return
    
    print(f"Algorithm: {clusters_data.get('algorithm', '?')}")
    print(f"Total emails: {clusters_data.get('n_emails', '?')}")
    print(f"Already analyzed: {len(analyzed)}")
    print(f"\nClusters:")
    
    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue

        sample_ids = cluster.get('sample_ids', [])
        analyzed_count = sum(1 for s in sample_ids if s in analyzed)
        unanalyzed = len(sample_ids) - analyzed_count
        coverage = analyzed_count / len(sample_ids) if sample_ids else 0

        # Status with coverage indicator
        if unanalyzed == 0:
            status = "[OK] Complete"
        elif analyzed_count == 0:
            status = f"[WAIT] Not started ({len(sample_ids)} emails)"
        elif coverage >= 0.8:
            status = f"[WAIT] {coverage:.0%} coverage ({unanalyzed} remaining)"
        else:
            status = f"[WARNING]  {coverage:.0%} coverage ({unanalyzed} remaining) - BELOW 80%"

        # Get top characteristics
        enrichment = cluster.get('enrichment_summary', {})
        top_audience = ''
        if enrichment.get('audiences'):
            top_audience = max(enrichment['audiences'].items(), key=lambda x: x[1])[0]

        print(f"\n  Cluster {cluster['id']}: {cluster['size']} emails ({top_audience})")
        print(f"    Status: {status}")
        print(f"    Examples: {', '.join(cluster.get('centroid_emails', [])[:2])}")
    
    # Show noise
    noise_clusters = [c for c in clusters_data.get('clusters', []) if c.get('is_noise')]
    if noise_clusters:
        noise = noise_clusters[0]
        print(f"\n  [NOISE]: {noise['size']} unclustered emails")
    
    print(f"\n{'=' * 50}")
    print("\nCommands:")
    print("  python prepare_batch.py                # Next unanalyzed cluster")
    print("  python prepare_batch.py --cluster N    # Specific cluster")
    print(f"{'=' * 50}\n")


def find_next_cluster() -> Optional[int]:
    """Find next cluster that needs analysis."""
    clusters_data = load_cluster_data()
    if not clusters_data:
        return None

    analyzed = get_analyzed_ids()

    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue

        sample_ids = cluster.get('sample_ids', [])
        unanalyzed = [s for s in sample_ids if s not in analyzed]

        if unanalyzed:
            return cluster['id']

    return None


def check_incomplete_clusters(target_cluster: int, analyzed: set) -> List[tuple]:
    """Check for incomplete clusters before the target cluster.

    Returns list of (cluster_id, remaining_count) for clusters that are
    started but not complete (have some analysis but not 80%+ coverage).
    """
    clusters_data = load_cluster_data()
    if not clusters_data:
        return []

    incomplete = []
    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue

        cid = cluster['id']
        if cid >= target_cluster:
            break

        sample_ids = cluster.get('sample_ids', [])
        analyzed_count = sum(1 for s in sample_ids if s in analyzed)

        # Only flag if cluster was started but is incomplete
        if analyzed_count > 0:
            coverage = analyzed_count / len(sample_ids) if sample_ids else 0
            if coverage < 0.8:
                remaining = len(sample_ids) - analyzed_count
                incomplete.append((cid, remaining, coverage))

    return incomplete


def show_coverage_calculation(target_coverage: float = 0.8):
    """Show batch size requirements for achieving target coverage.

    Displays a banner with:
    - Cluster sizes and required batch sizes
    - Total emails needed for target coverage
    - Current progress if any analysis exists

    Args:
        target_coverage: Target coverage percentage (default 0.8 = 80%)
    """
    clusters_data = load_cluster_data()
    if not clusters_data:
        print("[ERROR] No clusters found. Run: python cluster_emails.py")
        return

    analyzed = get_analyzed_ids()

    print(f"\n{'=' * 60}")
    print(f"BATCH SIZE REQUIREMENTS ({target_coverage:.0%} COVERAGE TARGET)")
    print(f"{'=' * 60}")
    print(f"\nFormula: Required Emails = ceil(Cluster Size × {target_coverage})")
    print(f"\n{'-' * 60}")

    total_required = 0
    total_analyzed = 0
    total_emails = 0

    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue

        cid = cluster['id']
        sample_ids = cluster.get('sample_ids', [])
        size = len(sample_ids)
        required = int(size * target_coverage + 0.999)  # ceil
        analyzed_count = sum(1 for s in sample_ids if s in analyzed)
        coverage = analyzed_count / size if size else 0

        total_required += required
        total_analyzed += analyzed_count
        total_emails += size

        # Status indicator
        if analyzed_count >= required:
            status = "[OK]"
        elif analyzed_count > 0:
            status = "[WAIT]"
        else:
            status = "⬚"

        print(f"  {status} Cluster {cid}: {size} emails -> Need {required} ({analyzed_count} done, {coverage:.0%})")

    print(f"{'-' * 60}")
    overall_coverage = total_analyzed / total_emails if total_emails else 0
    print(f"\n  TOTAL: {total_emails} emails -> Need {total_required} for {target_coverage:.0%} coverage")
    print(f"  CURRENT: {total_analyzed} analyzed ({overall_coverage:.0%} overall)")

    if total_analyzed < total_required:
        remaining = total_required - total_analyzed
        print(f"\n  [STATS] Still need: {remaining} more emails")
    else:
        print(f"\n  [OK] Coverage target met!")

    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prepare email batch for analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prepare_batch.py                # Prepare next unanalyzed cluster
  python prepare_batch.py --cluster 2    # Prepare cluster 2
  python prepare_batch.py --all          # Show all clusters status
  python prepare_batch.py --coverage     # Show batch size requirements
  python prepare_batch.py --legacy -c 30 # Legacy mode (random emails)
        """
    )
    parser.add_argument('--cluster', '-C', type=int, help='Specific cluster ID')
    parser.add_argument('--all', '-a', action='store_true', help='Show all clusters status')
    parser.add_argument('--coverage', action='store_true',
                        help='Show batch size requirements for target coverage')
    parser.add_argument('--target-coverage', type=float, default=0.8,
                        help='Target coverage percentage (default: 0.8 = 80%%)')
    parser.add_argument('--legacy', action='store_true', help='Legacy mode (no clustering)')
    parser.add_argument('--count', '-c', type=int, default=30, help='Email count for legacy mode')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Skip coverage warnings and proceed anyway')
    
    args = parser.parse_args()

    if args.all:
        show_clusters_status()
    elif args.coverage:
        show_coverage_calculation(args.target_coverage)
    elif args.legacy:
        print(prepare_legacy_batch(args.count))
    elif args.cluster is not None:
        # Check for incomplete earlier clusters
        if not args.force:
            analyzed = get_analyzed_ids()
            incomplete = check_incomplete_clusters(args.cluster, analyzed)
            if incomplete:
                print(f"\n{'=' * 60}")
                print("[WARNING]  WARNING: Incomplete clusters detected")
                print(f"{'=' * 60}")
                for cid, remaining, coverage in incomplete:
                    print(f"   Cluster {cid}: {remaining} emails unanalyzed ({coverage:.0%} coverage)")
                print(f"\n   Consider completing these first for better persona quality.")
                print(f"   Or proceed with: python prepare_batch.py --cluster {args.cluster} --force")
                print(f"{'=' * 60}\n")
                exit(0)
        print(prepare_cluster_batch(args.cluster))
    else:
        # Auto-find next cluster
        next_cluster = find_next_cluster()
        if next_cluster is not None:
            print(prepare_cluster_batch(next_cluster))
        else:
            clusters_data = load_cluster_data()
            if clusters_data:
                print("[OK] All clusters have been analyzed!")
                print("\nRun: python ingest.py --status")
            else:
                print("[ERROR] No clusters found.")
                print("\nRun the preprocessing pipeline first:")
                print("  1. python filter_emails.py")
                print("  2. python enrich_emails.py")
                print("  3. python embed_emails.py")
                print("  4. python cluster_emails.py")
