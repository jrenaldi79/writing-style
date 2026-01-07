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

import json
import argparse
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
CLUSTERS_FILE = DATA_DIR / "clusters.json"
ENRICHED_DIR = DATA_DIR / "enriched_samples"
RAW_DIR = DATA_DIR / "raw_samples"
BATCHES_DIR = DATA_DIR / "batches"
SAMPLES_DIR = DATA_DIR / "samples"

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
        return "❌ No clusters found. Run: python cluster_emails.py"
    
    # Find the cluster
    cluster = None
    for c in clusters_data.get('clusters', []):
        if c['id'] == cluster_id:
            cluster = c
            break
    
    if not cluster:
        return f"❌ Cluster {cluster_id} not found"
    
    if cluster.get('is_noise'):
        return f"⚠️ Cluster {cluster_id} is noise (unclustered emails)"
    
    # Get already analyzed IDs
    analyzed = get_analyzed_ids()
    
    # Get unanalyzed emails from this cluster
    sample_ids = cluster.get('sample_ids', [])
    unanalyzed = [sid for sid in sample_ids if sid not in analyzed]
    
    if not unanalyzed:
        return f"✅ Cluster {cluster_id} fully analyzed ({len(sample_ids)} emails)"
    
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
        return f"⚠️ No loadable emails in cluster {cluster_id}"
    
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
4. **Output JSON** following batch_schema.md format
5. **Save as** batches/batch_NNN.json
6. **Run ingest:** python ingest.py batches/batch_NNN.json

**Remember:** Include `calibration_referenced: true` in your output.""")
    
    return "\n".join(output)


def prepare_legacy_batch(count: int = 30) -> str:
    """Legacy mode: prepare random unanalyzed emails (no clustering)."""
    analyzed = get_analyzed_ids()
    
    # Find source directory
    source_dir = ENRICHED_DIR if ENRICHED_DIR.exists() else RAW_DIR
    if not source_dir.exists():
        return f"❌ No email samples found in {source_dir}"
    
    # Get unanalyzed emails
    all_files = list(source_dir.glob('email_*.json'))
    unanalyzed = [f for f in all_files if f.stem not in analyzed]
    
    if not unanalyzed:
        return "✅ All emails have been analyzed!"
    
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
        return "❌ No loadable emails found"
    
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
    
    print(f"\n{'═' * 50}")
    print("CLUSTER STATUS")
    print(f"{'═' * 50}")
    
    if not clusters_data:
        print("❌ No clusters found. Run: python cluster_emails.py")
        print(f"{'═' * 50}\n")
        return
    
    print(f"Algorithm: {clusters_data.get('algorithm', '?')}")
    print(f"Total emails: {clusters_data.get('n_emails', '?')}")
    print(f"Already analyzed: {len(analyzed)}")
    print(f"\nClusters:")
    
    for cluster in clusters_data.get('clusters', []):
        if cluster.get('is_noise'):
            continue
        
        sample_ids = cluster.get('sample_ids', [])
        unanalyzed = len([s for s in sample_ids if s not in analyzed])
        
        status = "✅" if unanalyzed == 0 else f"⏳ {unanalyzed} remaining"
        
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
    
    print(f"\n{'═' * 50}")
    print("\nCommands:")
    print("  python prepare_batch.py                # Next unanalyzed cluster")
    print("  python prepare_batch.py --cluster N    # Specific cluster")
    print(f"{'═' * 50}\n")


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prepare email batch for analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prepare_batch.py                # Prepare next unanalyzed cluster
  python prepare_batch.py --cluster 2    # Prepare cluster 2
  python prepare_batch.py --all          # Show all clusters status
  python prepare_batch.py --legacy -c 30 # Legacy mode (random emails)
        """
    )
    parser.add_argument('--cluster', '-C', type=int, help='Specific cluster ID')
    parser.add_argument('--all', '-a', action='store_true', help='Show all clusters status')
    parser.add_argument('--legacy', action='store_true', help='Legacy mode (no clustering)')
    parser.add_argument('--count', '-c', type=int, default=30, help='Email count for legacy mode')
    
    args = parser.parse_args()
    
    if args.all:
        show_clusters_status()
    elif args.legacy:
        print(prepare_legacy_batch(args.count))
    elif args.cluster is not None:
        print(prepare_cluster_batch(args.cluster))
    else:
        # Auto-find next cluster
        next_cluster = find_next_cluster()
        if next_cluster is not None:
            print(prepare_cluster_batch(next_cluster))
        else:
            clusters_data = load_cluster_data()
            if clusters_data:
                print("✅ All clusters have been analyzed!")
                print("\nRun: python ingest.py --status")
            else:
                print("❌ No clusters found.")
                print("\nRun the preprocessing pipeline first:")
                print("  1. python filter_emails.py")
                print("  2. python enrich_emails.py")
                print("  3. python embed_emails.py")
                print("  4. python cluster_emails.py")
