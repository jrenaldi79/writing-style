#!/usr/bin/env python3
"""
Email Clustering - Mathematical grouping based on embeddings

Replaces "agent decides clusters" with "math decides clusters, agent describes them."
Uses HDBSCAN (handles unknown cluster count) or K-Means with elbow method.

Usage:
    python cluster_emails.py                    # Auto-select algorithm and params
    python cluster_emails.py --algorithm kmeans --k 5
    python cluster_emails.py --algorithm hdbscan --min-cluster 5
    python cluster_emails.py --status           # Show clustering results

Requirements:
    pip install numpy scikit-learn hdbscan
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.npy"
INDEX_FILE = DATA_DIR / "embedding_index.json"
CLUSTERS_FILE = DATA_DIR / "clusters.json"
ENRICHED_DIR = DATA_DIR / "enriched_samples"


def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    try:
        import sklearn
    except ImportError:
        missing.append('scikit-learn')
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def load_embeddings() -> Tuple[any, Dict]:
    """Load embeddings and index."""
    import numpy as np
    
    if not EMBEDDINGS_FILE.exists():
        print(f"❌ Embeddings not found: {EMBEDDINGS_FILE}")
        print("   Run embed_emails.py first.")
        sys.exit(1)
    
    if not INDEX_FILE.exists():
        print(f"❌ Index not found: {INDEX_FILE}")
        sys.exit(1)
    
    embeddings = np.load(EMBEDDINGS_FILE)
    with open(INDEX_FILE) as f:
        index = json.load(f)
    
    return embeddings, index


def find_optimal_k(embeddings, max_k: int = 10) -> int:
    """Find optimal k using elbow method."""
    from sklearn.cluster import KMeans
    import numpy as np
    
    n_samples = len(embeddings)
    max_k = min(max_k, n_samples - 1)
    
    if max_k < 2:
        return 2
    
    inertias = []
    k_range = range(2, max_k + 1)
    
    print("🔍 Finding optimal k (elbow method)...")
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(embeddings)
        inertias.append(kmeans.inertia_)
    
    # Find elbow using second derivative
    if len(inertias) < 3:
        return 3
    
    # Calculate rate of change
    diffs = np.diff(inertias)
    diffs2 = np.diff(diffs)
    
    # Elbow is where second derivative is maximum (rate of decrease slows most)
    elbow_idx = np.argmax(diffs2) + 2  # +2 because of two diffs
    optimal_k = list(k_range)[elbow_idx] if elbow_idx < len(k_range) else list(k_range)[-1]
    
    # Sanity check: between 3 and 7 usually makes sense
    optimal_k = max(3, min(7, optimal_k))
    
    print(f"   Optimal k: {optimal_k}")
    return optimal_k


def cluster_kmeans(embeddings, k: Optional[int] = None) -> Tuple[List[int], Dict]:
    """Cluster using K-Means."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    import numpy as np
    
    if k is None:
        k = find_optimal_k(embeddings)
    
    print(f"\n🔮 Running K-Means with k={k}...")
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    # Calculate metrics
    silhouette = silhouette_score(embeddings, labels)
    inertia = kmeans.inertia_
    
    # Get centroids
    centroids = kmeans.cluster_centers_
    
    # Calculate distances to centroids for each point
    distances = []
    for i, label in enumerate(labels):
        dist = np.linalg.norm(embeddings[i] - centroids[label])
        distances.append(dist)
    
    metadata = {
        'algorithm': 'kmeans',
        'k': k,
        'silhouette_score': float(silhouette),
        'inertia': float(inertia),
        'centroids': centroids.tolist(),
        'distances': distances
    }
    
    print(f"   Silhouette score: {silhouette:.3f}")
    
    return labels.tolist(), metadata


def cluster_hdbscan(embeddings, min_cluster_size: int = 5) -> Tuple[List[int], Dict]:
    """Cluster using HDBSCAN."""
    try:
        import hdbscan
    except ImportError:
        print("❌ HDBSCAN not installed. Install with: pip install hdbscan")
        print("   Falling back to K-Means...")
        return cluster_kmeans(embeddings)
    
    from sklearn.metrics import silhouette_score
    import numpy as np
    
    print(f"\n🔮 Running HDBSCAN (min_cluster_size={min_cluster_size})...")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    labels = clusterer.fit_predict(embeddings)
    
    # Count clusters (excluding noise labeled as -1)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    # Calculate silhouette (only for non-noise points)
    non_noise_mask = labels != -1
    if non_noise_mask.sum() > 1 and n_clusters > 1:
        silhouette = silhouette_score(embeddings[non_noise_mask], labels[non_noise_mask])
    else:
        silhouette = 0.0
    
    metadata = {
        'algorithm': 'hdbscan',
        'min_cluster_size': min_cluster_size,
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'silhouette_score': float(silhouette),
        'probabilities': clusterer.probabilities_.tolist()
    }
    
    print(f"   Clusters found: {n_clusters}")
    print(f"   Noise points: {n_noise}")
    print(f"   Silhouette score: {silhouette:.3f}")
    
    return labels.tolist(), metadata


def find_centroid_emails(embeddings, labels: List[int], index: Dict, n_examples: int = 3) -> Dict[int, List[str]]:
    """Find emails closest to each cluster centroid."""
    import numpy as np
    
    cluster_ids = set(labels)
    centroid_emails = {}
    
    for cluster_id in cluster_ids:
        if cluster_id == -1:  # Skip noise
            continue
        
        # Get indices of emails in this cluster
        cluster_indices = [i for i, l in enumerate(labels) if l == cluster_id]
        cluster_embeddings = embeddings[cluster_indices]
        
        # Calculate centroid
        centroid = cluster_embeddings.mean(axis=0)
        
        # Find closest emails to centroid
        distances = [np.linalg.norm(embeddings[i] - centroid) for i in cluster_indices]
        sorted_indices = np.argsort(distances)[:n_examples]
        
        # Map back to email IDs
        email_ids = [index['emails'][cluster_indices[i]]['id'] for i in sorted_indices]
        centroid_emails[cluster_id] = email_ids
    
    return centroid_emails


def get_cluster_enrichment_summary(cluster_indices: List[int], index: Dict) -> Dict:
    """Get summary of enrichment data for a cluster."""
    from collections import Counter
    
    recipient_types = Counter()
    audiences = Counter()
    thread_positions = Counter()
    
    for idx in cluster_indices:
        email_info = index['emails'][idx]
        enrichment = email_info.get('enrichment_summary', {})
        
        if enrichment.get('recipient_type'):
            recipient_types[enrichment['recipient_type']] += 1
        if enrichment.get('audience'):
            audiences[enrichment['audience']] += 1
        if enrichment.get('thread_position'):
            thread_positions[enrichment['thread_position']] += 1
    
    return {
        'recipient_types': dict(recipient_types),
        'audiences': dict(audiences),
        'thread_positions': dict(thread_positions)
    }


def run_clustering(algorithm: str = 'auto', k: Optional[int] = None, 
                   min_cluster_size: int = 5) -> Dict:
    """Run clustering and save results."""
    check_dependencies()
    import numpy as np
    
    embeddings, index = load_embeddings()
    print(f"📊 Loaded {len(embeddings)} embeddings")
    
    # Auto-select algorithm
    if algorithm == 'auto':
        # Use HDBSCAN if available and enough data, else K-Means
        try:
            import hdbscan
            if len(embeddings) >= 20:
                algorithm = 'hdbscan'
            else:
                algorithm = 'kmeans'
        except ImportError:
            algorithm = 'kmeans'
        print(f"🤖 Auto-selected algorithm: {algorithm}")
    
    # Run clustering
    if algorithm == 'hdbscan':
        labels, metadata = cluster_hdbscan(embeddings, min_cluster_size)
    else:
        labels, metadata = cluster_kmeans(embeddings, k)
    
    # Find centroid emails for each cluster
    centroid_emails = find_centroid_emails(embeddings, labels, index)
    
    # Build cluster summaries
    cluster_ids = sorted(set(labels))
    clusters = []
    
    for cluster_id in cluster_ids:
        cluster_indices = [i for i, l in enumerate(labels) if l == cluster_id]
        
        cluster_info = {
            'id': cluster_id,
            'size': len(cluster_indices),
            'is_noise': cluster_id == -1,
            'sample_ids': [index['emails'][i]['id'] for i in cluster_indices],
            'centroid_emails': centroid_emails.get(cluster_id, []),
            'enrichment_summary': get_cluster_enrichment_summary(cluster_indices, index)
        }
        
        # Add average distance to centroid for non-noise clusters
        if cluster_id != -1 and 'distances' in metadata:
            cluster_distances = [metadata['distances'][i] for i in cluster_indices]
            cluster_info['avg_distance_to_centroid'] = float(np.mean(cluster_distances))
        
        clusters.append(cluster_info)
    
    # Sort: valid clusters first (by size), then noise
    clusters.sort(key=lambda c: (c['is_noise'], -c['size']))
    
    # Build final output
    result = {
        'clustering_run': datetime.now().isoformat(),
        'algorithm': metadata['algorithm'],
        'n_emails': len(embeddings),
        'n_clusters': len([c for c in clusters if not c['is_noise']]),
        'n_noise': len([c for c in clusters if c['is_noise']]),
        'silhouette_score': metadata.get('silhouette_score', 0),
        'parameters': {
            'k': metadata.get('k'),
            'min_cluster_size': metadata.get('min_cluster_size')
        },
        'clusters': clusters,
        'labels': labels
    }
    
    # Save results
    with open(CLUSTERS_FILE, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Print summary
    print(f"\n{'═' * 50}")
    print("CLUSTERING COMPLETE")
    print(f"{'═' * 50}")
    print(f"Algorithm: {metadata['algorithm']}")
    print(f"Emails: {len(embeddings)}")
    print(f"Clusters: {result['n_clusters']}")
    if result['n_noise'] > 0:
        print(f"Noise: {result['n_noise']} emails")
    print(f"Silhouette: {result['silhouette_score']:.3f}")
    print(f"\nCluster breakdown:")
    for c in clusters:
        if c['is_noise']:
            print(f"  • [NOISE]: {c['size']} emails")
        else:
            top_audience = max(c['enrichment_summary']['audiences'].items(), 
                             key=lambda x: x[1])[0] if c['enrichment_summary']['audiences'] else '?'
            top_type = max(c['enrichment_summary']['recipient_types'].items(),
                          key=lambda x: x[1])[0] if c['enrichment_summary']['recipient_types'] else '?'
            print(f"  • Cluster {c['id']}: {c['size']} emails ({top_type}, {top_audience})")
            print(f"    Examples: {', '.join(c['centroid_emails'][:2])}")
    print(f"{'═' * 50}")
    print(f"\n💾 Results saved to: {CLUSTERS_FILE}")
    print(f"\n💡 Next step: Run prepare_batch.py to analyze clusters")
    
    return result


def show_status():
    """Show current clustering status."""
    print(f"\n{'═' * 50}")
    print("CLUSTERING STATUS")
    print(f"{'═' * 50}")
    
    if EMBEDDINGS_FILE.exists():
        with open(INDEX_FILE) as f:
            index = json.load(f)
        print(f"Embeddings: {index.get('count', '?')} emails")
    else:
        print("❌ No embeddings found. Run embed_emails.py first.")
        print(f"{'═' * 50}\n")
        return
    
    if CLUSTERS_FILE.exists():
        with open(CLUSTERS_FILE) as f:
            clusters = json.load(f)
        
        print(f"\n✅ Clusters exist")
        print(f"   Algorithm: {clusters.get('algorithm', '?')}")
        print(f"   Clusters: {clusters.get('n_clusters', '?')}")
        print(f"   Noise: {clusters.get('n_noise', 0)}")
        print(f"   Silhouette: {clusters.get('silhouette_score', 0):.3f}")
        print(f"   Created: {clusters.get('clustering_run', '?')}")
        
        print(f"\nCluster sizes:")
        for c in clusters.get('clusters', []):
            if c['is_noise']:
                print(f"  • [NOISE]: {c['size']} emails")
            else:
                print(f"  • Cluster {c['id']}: {c['size']} emails")
    else:
        print("\n❌ No clusters found. Run cluster_emails.py")
    
    print(f"{'═' * 50}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cluster emails based on embeddings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cluster_emails.py                         # Auto-select algorithm
  python cluster_emails.py --algorithm kmeans -k 5 # K-Means with 5 clusters
  python cluster_emails.py --algorithm hdbscan     # HDBSCAN (auto cluster count)
  python cluster_emails.py --status                # Show current clusters
        """
    )
    parser.add_argument('--algorithm', type=str, default='auto',
                        choices=['auto', 'kmeans', 'hdbscan'],
                        help='Clustering algorithm (default: auto)')
    parser.add_argument('-k', type=int, default=None,
                        help='Number of clusters for K-Means (default: auto via elbow)')
    parser.add_argument('--min-cluster', type=int, default=5,
                        help='Minimum cluster size for HDBSCAN (default: 5)')
    parser.add_argument('--status', action='store_true', help='Show clustering status')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        run_clustering(
            algorithm=args.algorithm,
            k=args.k,
            min_cluster_size=args.min_cluster
        )
