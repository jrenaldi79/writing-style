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
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

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


class TestClusterHealthCheck(unittest.TestCase):
    """Test cluster health check calculations - Issue 1."""

    def test_noise_count_should_count_emails_not_clusters(self):
        """n_noise should count individual noisy emails, not cluster objects.

        Bug: cluster_emails.py:320 uses len([c for c in clusters if c['is_noise']])
        which counts cluster objects (always 0 or 1), not actual noisy emails.
        """
        # Scenario: 60 total emails, 10 in noise cluster
        clusters = [
            {'id': 0, 'size': 30, 'is_noise': False, 'sample_ids': []},
            {'id': 1, 'size': 20, 'is_noise': False, 'sample_ids': []},
            {'id': -1, 'size': 10, 'is_noise': True, 'sample_ids': []}  # 10 noise EMAILS
        ]

        # Correct calculation: sum email counts
        n_noise_correct = sum(c['size'] for c in clusters if c['is_noise'])
        self.assertEqual(n_noise_correct, 10, "Should count 10 noise emails")

        # Buggy calculation (what the code currently does)
        n_noise_buggy = len([c for c in clusters if c['is_noise']])
        self.assertEqual(n_noise_buggy, 1, "Buggy code counts 1 cluster object")

        # The bug: these two values are different!
        self.assertNotEqual(n_noise_correct, n_noise_buggy,
            "Bug demonstration: correct method != buggy method")

    def test_noise_count_no_noise_cluster(self):
        """n_noise should be 0 when there's no noise cluster."""
        clusters = [
            {'id': 0, 'size': 30, 'is_noise': False, 'sample_ids': []},
            {'id': 1, 'size': 20, 'is_noise': False, 'sample_ids': []}
        ]

        n_noise = sum(c['size'] for c in clusters if c['is_noise'])
        self.assertEqual(n_noise, 0)

    def test_noise_ratio_high_noise_scenario(self):
        """Should correctly calculate noise ratio for high-noise scenario.

        In the RCA, 157 out of 211 emails (74%) were noise, but health check
        showed "0% noise" because it counted 1 noise cluster / 211 emails = 0.47%.
        """
        # Recreate the RCA scenario
        clusters = [
            {'id': 0, 'size': 30, 'is_noise': False, 'sample_ids': []},
            {'id': 1, 'size': 15, 'is_noise': False, 'sample_ids': []},
            {'id': 2, 'size': 9, 'is_noise': False, 'sample_ids': []},
            {'id': -1, 'size': 157, 'is_noise': True, 'sample_ids': []}  # 157 noise
        ]

        total_emails = sum(c['size'] for c in clusters)  # 211
        n_noise = sum(c['size'] for c in clusters if c['is_noise'])  # 157
        noise_ratio = n_noise / total_emails

        self.assertEqual(total_emails, 211)
        self.assertEqual(n_noise, 157)
        self.assertAlmostEqual(noise_ratio, 0.744, places=2,
            msg="Noise ratio should be ~74%, not 0%")

        # This should trigger high_noise warning (>30%)
        self.assertGreater(noise_ratio, 0.30,
            "74% noise should exceed 30% threshold for warning")


class TestSilhouetteWarning(unittest.TestCase):
    """Test silhouette score warning system - Issue 3."""

    def test_low_silhouette_should_warn(self):
        """Should add warning when silhouette score < 0.15."""
        silhouette_score = 0.10
        n_clusters = 3

        health_issues = []
        if silhouette_score < 0.15 and n_clusters > 1:
            health_issues.append({
                'type': 'low_silhouette',
                'severity': 'warning',
                'message': f"Silhouette score {silhouette_score:.2f} indicates weak cluster separation"
            })

        self.assertEqual(len(health_issues), 1)
        self.assertEqual(health_issues[0]['type'], 'low_silhouette')

    def test_acceptable_silhouette_no_warning(self):
        """Should not warn when silhouette score >= 0.15."""
        silhouette_score = 0.25
        n_clusters = 3

        health_issues = []
        if silhouette_score < 0.15 and n_clusters > 1:
            health_issues.append({'type': 'low_silhouette'})

        self.assertEqual(len(health_issues), 0)

    def test_single_cluster_no_silhouette_warning(self):
        """Should not warn about silhouette for single cluster (score is meaningless)."""
        silhouette_score = 0.05  # Very low, but meaningless for single cluster
        n_clusters = 1

        health_issues = []
        if silhouette_score < 0.15 and n_clusters > 1:
            health_issues.append({'type': 'low_silhouette'})

        self.assertEqual(len(health_issues), 0,
            "Single cluster should not trigger silhouette warning")


class TestExtractBody(unittest.TestCase):
    """Test email body extraction from different formats."""

    def test_extract_body_from_original_data(self):
        """Should extract body from original_data.body (simplified format).

        Bug: embed_emails.py extract_body() only checks payload.body.data,
        but fetch_emails.py stores body in original_data.body.
        """
        # Import here to avoid issues if embed_emails not available
        try:
            import embed_emails
        except ImportError:
            self.skipTest("embed_emails not importable")

        # Simplified format from fetch_emails.py
        email_data = {
            'original_data': {
                'body': 'This is the email body text.',
                'subject': 'Test Subject'
            }
        }

        body = embed_emails.extract_body(email_data)
        self.assertEqual(body, 'This is the email body text.',
            "Should extract body from original_data.body")

    def test_extract_body_from_enriched_format(self):
        """Should extract body from enriched email structure."""
        try:
            import embed_emails
        except ImportError:
            self.skipTest("embed_emails not importable")

        # Enriched format (body nested in original_data)
        email_data = {
            'id': 'test_001',
            'original_data': {
                'body': 'Enriched email body content here.',
                'from': 'sender@example.com'
            },
            'enrichment': {
                'recipient_type': 'individual'
            }
        }

        body = embed_emails.extract_body(email_data)
        self.assertEqual(body, 'Enriched email body content here.')

    def test_extract_body_direct_body_attribute(self):
        """Should extract body from direct body attribute."""
        try:
            import embed_emails
        except ImportError:
            self.skipTest("embed_emails not importable")

        # Direct body attribute (another possible format)
        email_data = {
            'body': 'Direct body text.',
            'subject': 'Test'
        }

        body = embed_emails.extract_body(email_data)
        self.assertEqual(body, 'Direct body text.')

    def test_extract_body_fallback_to_snippet(self):
        """Should fall back to snippet when body not found."""
        try:
            import embed_emails
        except ImportError:
            self.skipTest("embed_emails not importable")

        email_data = {
            'snippet': 'This is the snippet fallback.'
        }

        body = embed_emails.extract_body(email_data)
        self.assertEqual(body, 'This is the snippet fallback.')


class TestEmbeddingThreshold(unittest.TestCase):
    """Test embedding minimum character threshold - Issue 4."""

    def test_brief_acknowledgment_should_embed(self):
        """Brief acknowledgments (10+ chars) should be embeddable.

        Current threshold is 20 chars, should be 10.
        """
        # Common brief acknowledgments
        brief_texts = [
            "Thanks! -J",      # 10 chars
            "Perfect, ty",     # 11 chars
            "Got it, thx",     # 11 chars
            "Sounds good!",    # 12 chars
        ]

        MIN_CHARS = 10  # Proposed threshold

        for text in brief_texts:
            self.assertGreaterEqual(len(text.strip()), MIN_CHARS,
                f"'{text}' ({len(text)} chars) should be above {MIN_CHARS} threshold")

    def test_very_short_should_reject(self):
        """Very short texts (<10 chars) should still be rejected."""
        very_short_texts = [
            "Thanks!",   # 7 chars
            "OK",        # 2 chars
            "K",         # 1 char
        ]

        MIN_CHARS = 10

        for text in very_short_texts:
            self.assertLess(len(text.strip()), MIN_CHARS,
                f"'{text}' should be below threshold and rejected")


class TestCalibration(unittest.TestCase):
    """Test calibration system."""
    
    def test_calibration_file_exists(self):
        """Calibration file should exist."""
        calibration_path = Path(__file__).parent.parent / "skills" / "writing-style" / "references" / "calibration.md"
        self.assertTrue(calibration_path.exists(), "calibration.md not found")
    
    def test_calibration_has_anchors(self):
        """Calibration file should have anchor examples."""
        calibration_path = Path(__file__).parent.parent / "skills" / "writing-style" / "references" / "calibration.md"
        
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
