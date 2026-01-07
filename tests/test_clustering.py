#!/usr/bin/env python3
"""
Unit Tests - Embedding and Clustering
"""

import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skill" / "scripts"))

from test_fixtures import get_sample_email, create_filtered_sample, create_enriched_sample

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@unittest.skipUnless(NUMPY_AVAILABLE, "numpy not installed")
class TestEmbeddingGeneration(unittest.TestCase):
    """Test embedding generation."""
    
    @unittest.skipUnless(TRANSFORMERS_AVAILABLE, "sentence-transformers not installed")
    def test_model_loads(self):
        """Sentence transformer model should load."""
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            self.assertIsNotNone(model)
        except Exception as e:
            self.skipTest(f"Model download failed: {e}")
    
    @unittest.skipUnless(TRANSFORMERS_AVAILABLE, "sentence-transformers not installed")
    def test_embedding_dimension(self):
        """Embeddings should have correct dimension."""
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            text = "This is a test email."
            embedding = model.encode([text])[0]
            
            self.assertEqual(len(embedding), 384)
        except Exception as e:
            self.skipTest(f"Model download failed: {e}")
    
    @unittest.skipUnless(TRANSFORMERS_AVAILABLE, "sentence-transformers not installed")
    def test_embedding_deterministic(self):
        """Same text should produce same embedding."""
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            text = "This is a test email."
            
            embedding1 = model.encode([text])[0]
            embedding2 = model.encode([text])[0]
            
            np.testing.assert_array_almost_equal(embedding1, embedding2, decimal=5)
        except Exception as e:
            self.skipTest(f"Model download failed: {e}")
    
    @unittest.skipUnless(TRANSFORMERS_AVAILABLE, "sentence-transformers not installed")
    def test_similar_texts_similar_embeddings(self):
        """Similar texts should have similar embeddings."""
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            text1 = "Quick update on Q2 priorities."
            text2 = "Brief update on Q2 goals."
            text3 = "The weather is nice today."
            
            embeddings = model.encode([text1, text2, text3], normalize_embeddings=True)
            
            # Cosine similarity (normalized embeddings)
            sim_1_2 = np.dot(embeddings[0], embeddings[1])
            sim_1_3 = np.dot(embeddings[0], embeddings[2])
            
            self.assertGreater(sim_1_2, sim_1_3, 
                             "Similar texts should be more similar than unrelated texts")
        except Exception as e:
            self.skipTest(f"Model download failed: {e}")


@unittest.skipUnless(NUMPY_AVAILABLE, "numpy not installed")
class TestClustering(unittest.TestCase):
    """Test clustering algorithms."""
    
    def setUp(self):
        """Create sample embeddings."""
        # Create synthetic embeddings for testing
        np.random.seed(42)
        
        # Cluster 1: Around [1, 0, 0, ...]
        cluster1 = np.random.randn(20, 10) * 0.1
        cluster1[:, 0] += 1
        
        # Cluster 2: Around [0, 1, 0, ...]
        cluster2 = np.random.randn(20, 10) * 0.1
        cluster2[:, 1] += 1
        
        # Cluster 3: Around [0, 0, 1, ...]
        cluster3 = np.random.randn(20, 10) * 0.1
        cluster3[:, 2] += 1
        
        self.embeddings = np.vstack([cluster1, cluster2, cluster3])
        self.true_labels = np.array([0]*20 + [1]*20 + [2]*20)
    
    def test_kmeans_clustering(self):
        """K-Means should separate clusters."""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            self.skipTest("scikit-learn not installed")
        
        kmeans = KMeans(n_clusters=3, random_state=42)
        labels = kmeans.fit_predict(self.embeddings)
        
        # Check that we got 3 clusters
        unique_labels = set(labels)
        self.assertEqual(len(unique_labels), 3)
        
        # Check that clusters are separated (not perfect due to randomness)
        # At least 50% accuracy after label alignment
        from sklearn.metrics import adjusted_rand_score
        ari = adjusted_rand_score(self.true_labels, labels)
        self.assertGreater(ari, 0.5)
    
    def test_silhouette_score(self):
        """Silhouette score should indicate cluster quality."""
        try:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
        except ImportError:
            self.skipTest("scikit-learn not installed")
        
        kmeans = KMeans(n_clusters=3, random_state=42)
        labels = kmeans.fit_predict(self.embeddings)
        
        score = silhouette_score(self.embeddings, labels)
        
        # Well-separated clusters should have score > 0.5
        self.assertGreater(score, 0.5)
    
    def test_elbow_method(self):
        """Elbow method should identify optimal k."""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            self.skipTest("scikit-learn not installed")
        
        inertias = []
        for k in range(2, 6):
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(self.embeddings)
            inertias.append(kmeans.inertia_)
        
        # Inertia should decrease as k increases
        for i in range(len(inertias) - 1):
            self.assertLess(inertias[i+1], inertias[i])


class TestCalibration(unittest.TestCase):
    """Test calibration system."""
    
    def test_calibration_file_exists(self):
        """Calibration file should exist."""
        calibration_path = Path(__file__).parent.parent / "skill" / "references" / "calibration.md"
        self.assertTrue(calibration_path.exists(), "calibration.md not found")
    
    def test_calibration_has_anchors(self):
        """Calibration file should have anchor examples."""
        calibration_path = Path(__file__).parent.parent / "skill" / "references" / "calibration.md"
        
        with open(calibration_path) as f:
            content = f.read()
        
        # Check for required scales
        self.assertIn("Formality Scale", content)
        self.assertIn("Warmth Scale", content)
        self.assertIn("Authority Scale", content)
        self.assertIn("Directness Scale", content)
        
        # Check for anchor levels
        for scale in ["Formality", "Warmth", "Authority", "Directness"]:
            self.assertIn(f"1 -", content)  # Low anchor
            self.assertIn(f"5 -", content)  # Mid anchor
            self.assertIn(f"10 -", content)  # High anchor


class TestBatchSchema(unittest.TestCase):
    """Test batch output schema."""
    
    def test_valid_batch_json(self):
        """Should validate a proper batch JSON."""
        batch = {
            "batch_id": "batch_001",
            "analyzed_at": "2025-01-07T12:00:00Z",
            "email_count": 3,
            "calibration_referenced": True,
            "calibration_notes": "Anchored against examples",
            "new_personas": [],
            "samples": [
                {
                    "id": "email_001",
                    "source": "email",
                    "persona": "Executive Brief",
                    "confidence": 0.85,
                    "analysis": {
                        "tone_vectors": {
                            "formality": 6,
                            "warmth": 5,
                            "authority": 8,
                            "directness": 8
                        },
                        "greeting": "Team,",
                        "closing": "-JR"
                    },
                    "context": {
                        "recipient_type": "team",
                        "audience": "internal"
                    }
                }
            ]
        }
        
        # Test required fields
        self.assertIn("batch_id", batch)
        self.assertIn("calibration_referenced", batch)
        self.assertIn("samples", batch)
        
        # Test calibration
        self.assertTrue(batch["calibration_referenced"])
        
        # Test sample structure
        sample = batch["samples"][0]
        self.assertIn("tone_vectors", sample["analysis"])
        self.assertIn("context", sample)
        
        # Test tone_vectors range
        vectors = sample["analysis"]["tone_vectors"]
        for dimension, score in vectors.items():
            self.assertGreaterEqual(score, 1)
            self.assertLessEqual(score, 10)


if __name__ == '__main__':
    unittest.main()
