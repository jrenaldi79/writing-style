#!/usr/bin/env python3
"""
Email Embedding - Generate sentence embeddings for clustering

Uses sentence-transformers to create vector representations of emails.
These embeddings enable mathematical clustering instead of "vibes-based" grouping.

Usage:
    python embed_emails.py                    # Generate embeddings from enriched_samples
    python embed_emails.py --status           # Show embedding statistics
    python embed_emails.py --model <name>     # Use specific model

Requirements:
    pip install sentence-transformers numpy
"""

import json
import argparse
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import sys

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
ENRICHED_DIR = get_path("enriched_samples")
EMBEDDINGS_FILE = get_path("embeddings.npy")
INDEX_FILE = get_path("embedding_index.json")
REPORT_FILE = get_path("embedding_report.json")

# Default model - good balance of speed and quality
DEFAULT_MODEL = 'all-MiniLM-L6-v2'


def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import sentence_transformers
    except ImportError:
        missing.append('sentence-transformers')
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def extract_body(email_data: dict) -> str:
    """Extract plain text body from email data.

    Supports multiple formats:
    1. Simplified format: original_data.body (from fetch_emails.py)
    2. Direct attribute: body (plain text)
    3. Gmail API format: payload.body.data (base64 encoded)
    """
    # Priority 1: Check simplified/enriched format (original_data.body)
    if 'original_data' in email_data:
        body = email_data['original_data'].get('body', '')
        if body:
            return body

    # Priority 2: Direct body attribute
    if 'body' in email_data and isinstance(email_data['body'], str):
        return email_data['body']

    # Priority 3: Gmail API format (payload.body.data, base64 encoded)
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

    # Final fallback: snippet
    return email_data.get('snippet', '')


def get_subject(email_data: dict) -> str:
    """Extract subject from email headers."""
    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'subject':
            return header.get('value', '')
    return ''


def prepare_text_for_embedding(enriched_data: dict) -> str:
    """
    Prepare email text for embedding.
    Combines subject + body for richer representation.
    """
    email_data = enriched_data.get('original_data', enriched_data)
    
    subject = get_subject(email_data)
    body = extract_body(email_data)
    
    # Clean up body - remove excessive whitespace and quoted text
    lines = body.split('\n')
    clean_lines = []
    for line in lines:
        # Skip quoted lines
        if line.strip().startswith('>'):
            continue
        # Skip common quote markers
        if 'wrote:' in line and 'On ' in line:
            break  # Stop at quote start
        clean_lines.append(line)
    
    clean_body = '\n'.join(clean_lines).strip()
    
    # Combine subject and body
    if subject and not subject.lower().startswith('re:'):
        text = f"{subject}\n\n{clean_body}"
    else:
        text = clean_body
    
    # Truncate to reasonable length for embedding (most models have limits)
    max_chars = 2000  # ~500 tokens
    if len(text) > max_chars:
        text = text[:max_chars] + '...'
    
    return text


def generate_embeddings(model_name: str = DEFAULT_MODEL) -> Dict:
    """
    Generate embeddings for all enriched emails.
    """
    check_dependencies()
    
    from sentence_transformers import SentenceTransformer
    import numpy as np
    
    if not ENRICHED_DIR.exists():
        print(f"❌ Enriched samples directory not found: {ENRICHED_DIR}")
        print("   Run enrich_emails.py first.")
        return {}
    
    enriched_files = sorted(ENRICHED_DIR.glob('email_*.json'))
    print(f"📧 Found {len(enriched_files)} enriched emails")
    
    if not enriched_files:
        print("❌ No enriched emails found.")
        return {}
    
    # Load model
    print(f"🤖 Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"   Embedding dimension: {model.get_sentence_embedding_dimension()}")
    
    # Prepare texts and index
    texts = []
    index = {
        'model': model_name,
        'dimension': model.get_sentence_embedding_dimension(),
        'created_at': datetime.now().isoformat(),
        'emails': []
    }
    
    print(f"\n📝 Preparing texts...")
    for filepath in enriched_files:
        try:
            with open(filepath) as f:
                enriched_data = json.load(f)
        except json.JSONDecodeError:
            print(f"  ✗ {filepath.stem} → invalid JSON")
            continue
        
        email_id = enriched_data.get('id', filepath.stem)
        text = prepare_text_for_embedding(enriched_data)
        
        if len(text.strip()) < 10:
            print(f"  ⚠ {email_id} → very short ({len(text.strip())} chars), skipping")
            continue
        
        texts.append(text)
        index['emails'].append({
            'index': len(texts) - 1,
            'id': email_id,
            'text_length': len(text),
            'enrichment_summary': {
                'recipient_type': enriched_data.get('enrichment', {}).get('recipient_type'),
                'audience': enriched_data.get('enrichment', {}).get('audience'),
                'thread_position': enriched_data.get('enrichment', {}).get('thread_position')
            }
        })
    
    print(f"   Prepared {len(texts)} texts for embedding")
    
    # Generate embeddings
    print(f"\n⚡ Generating embeddings...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # For cosine similarity
    )
    
    print(f"   Shape: {embeddings.shape}")
    
    # Save embeddings
    np.save(EMBEDDINGS_FILE, embeddings)
    print(f"💾 Saved embeddings to: {EMBEDDINGS_FILE}")
    
    # Save index
    index['count'] = len(texts)
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)
    print(f"💾 Saved index to: {INDEX_FILE}")
    
    # Generate report
    report = {
        'embedding_run': datetime.now().isoformat(),
        'model': model_name,
        'dimension': model.get_sentence_embedding_dimension(),
        'email_count': len(texts),
        'avg_text_length': sum(len(t) for t in texts) / len(texts) if texts else 0,
        'embeddings_file': str(EMBEDDINGS_FILE),
        'index_file': str(INDEX_FILE)
    }
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'═' * 50}")
    print("EMBEDDING COMPLETE")
    print(f"{'═' * 50}")
    print(f"Model: {model_name}")
    print(f"Emails embedded: {len(texts)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Avg text length: {report['avg_text_length']:.0f} chars")
    print(f"{'═' * 50}")
    print(f"\n📁 Files created:")
    print(f"   • {EMBEDDINGS_FILE}")
    print(f"   • {INDEX_FILE}")
    print(f"\n💡 Next step: Run cluster_emails.py")
    
    return report


def show_status():
    """Show current embedding status."""
    enriched_count = len(list(ENRICHED_DIR.glob('email_*.json'))) if ENRICHED_DIR.exists() else 0
    
    print(f"\n{'═' * 50}")
    print("EMBEDDING STATUS")
    print(f"{'═' * 50}")
    print(f"Enriched emails available: {enriched_count}")
    
    if EMBEDDINGS_FILE.exists() and INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            index = json.load(f)
        
        print(f"\n✅ Embeddings exist")
        print(f"   Model: {index.get('model', 'unknown')}")
        print(f"   Dimension: {index.get('dimension', 'unknown')}")
        print(f"   Email count: {index.get('count', 'unknown')}")
        print(f"   Created: {index.get('created_at', 'unknown')}")
        
        # Check if embeddings are stale
        if enriched_count > index.get('count', 0):
            print(f"\n⚠️  {enriched_count - index.get('count', 0)} new emails not embedded")
            print("   Re-run embed_emails.py to update")
    else:
        print(f"\n❌ No embeddings found")
        print("   Run: python embed_emails.py")
    
    print(f"{'═' * 50}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate embeddings for enriched emails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_emails.py                           # Generate embeddings
  python embed_emails.py --model all-mpnet-base-v2 # Use different model
  python embed_emails.py --status                  # Show current status

Recommended models:
  all-MiniLM-L6-v2      (default) Fast, good quality, 384 dimensions
  all-mpnet-base-v2     Higher quality, slower, 768 dimensions
  paraphrase-MiniLM-L6-v2  Good for short texts
        """
    )
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                        help=f'Sentence transformer model (default: {DEFAULT_MODEL})')
    parser.add_argument('--status', action='store_true', help='Show embedding status')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        generate_embeddings(model_name=args.model)
