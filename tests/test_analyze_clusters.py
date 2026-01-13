#!/usr/bin/env python3
"""
Unit Tests - Parallel Cluster Analysis

TDD tests for analyze_clusters.py - parallel email cluster analysis via OpenRouter API.

Tests for:
- Preparation phase (cluster loading, prompt building, cost estimation)
- Parallel execution (ThreadPoolExecutor pattern)
- Persona merging (embedding similarity)
- Approval workflow (draft save/load)
- Error handling (retries, partial results)
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add skill scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "writing-style" / "scripts"))

# Import config module for patching
import config


class TestPreparationPhase(unittest.TestCase):
    """Test cluster loading and prompt building."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()

        # Sample clusters.json structure
        self.sample_clusters = {
            "clustering_run": "2026-01-09T12:00:00Z",
            "algorithm": "hdbscan",
            "n_clusters": 2,
            "n_emails": 10,
            "silhouette_score": 0.42,
            "clusters": [
                {
                    "id": 0,
                    "size": 6,
                    "is_noise": False,
                    "sample_ids": ["email_001", "email_002", "email_003",
                                   "email_004", "email_005", "email_006"],
                    "centroid_emails": ["email_001", "email_002", "email_003"]
                },
                {
                    "id": 1,
                    "size": 4,
                    "is_noise": False,
                    "sample_ids": ["email_007", "email_008", "email_009", "email_010"],
                    "centroid_emails": ["email_007", "email_008", "email_009"]
                }
            ]
        }

        # Sample enriched email
        self.sample_email = {
            "id": "email_001",
            "original_data": {
                "body": "Team, Quick update on Q2 priorities. Best, John",
                "subject": "Q2 Update"
            },
            "enrichment": {
                "recipient_type": "team",
                "audience": "internal",
                "thread_position": "initiating"
            },
            "quality": {"quality_score": 0.75}
        }

    def test_load_unanalyzed_clusters_filters_analyzed(self):
        """Should exclude emails that are already in samples/."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create clusters.json
            (tmp_path / "clusters.json").write_text(json.dumps(self.sample_clusters))

            # Create samples/ dir with some already-analyzed emails
            (tmp_path / "samples").mkdir()
            (tmp_path / "samples" / "email_001.json").write_text('{}')
            (tmp_path / "samples" / "email_002.json").write_text('{}')

            # Create enriched_samples/ with all emails
            (tmp_path / "enriched_samples").mkdir()
            for i in range(1, 11):
                (tmp_path / "enriched_samples" / f"email_{i:03d}.json").write_text(
                    json.dumps(self.sample_email)
                )

            # Patch internal path functions
            with patch.object(analyze_clusters, '_get_clusters_file', return_value=tmp_path / "clusters.json"), \
                 patch.object(analyze_clusters, '_get_samples_dir', return_value=tmp_path / "samples"):
                clusters = analyze_clusters.load_unanalyzed_clusters()

            # Cluster 0 should have 4 remaining emails (6 - 2 analyzed)
            self.assertEqual(clusters[0]['remaining_count'], 4)

    def test_load_unanalyzed_clusters_returns_all_when_none_analyzed(self):
        """Should return all emails when no samples exist."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create clusters.json
            (tmp_path / "clusters.json").write_text(json.dumps(self.sample_clusters))

            # Create enriched_samples/ with all emails
            (tmp_path / "enriched_samples").mkdir()
            for i in range(1, 11):
                (tmp_path / "enriched_samples" / f"email_{i:03d}.json").write_text(
                    json.dumps(self.sample_email)
                )

            # Patch internal path functions (samples dir doesn't exist, so no analyzed)
            with patch.object(analyze_clusters, '_get_clusters_file', return_value=tmp_path / "clusters.json"), \
                 patch.object(analyze_clusters, '_get_samples_dir', return_value=tmp_path / "samples"):
                clusters = analyze_clusters.load_unanalyzed_clusters()

            # Both clusters should have all emails
            self.assertEqual(clusters[0]['remaining_count'], 6)
            self.assertEqual(clusters[1]['remaining_count'], 4)

    def test_build_analysis_prompt_includes_calibration(self):
        """Prompt should include calibration reference."""
        import analyze_clusters

        cluster = {"id": 0, "size": 6}
        emails = [self.sample_email]
        calibration = "## Calibration Reference\n\nFormality scale 1-10..."

        prompt = analyze_clusters.build_analysis_prompt(cluster, emails, calibration)

        self.assertIn("Calibration", prompt)
        self.assertIn("Formality", prompt)

    def test_build_analysis_prompt_includes_schema(self):
        """Prompt should include expected JSON output schema."""
        import analyze_clusters

        cluster = {"id": 0, "size": 6}
        emails = [self.sample_email]
        calibration = "## Calibration"

        prompt = analyze_clusters.build_analysis_prompt(cluster, emails, calibration)

        # Should include schema instructions
        self.assertIn("JSON", prompt)
        self.assertIn("new_personas", prompt)
        self.assertIn("samples", prompt)

    def test_build_analysis_prompt_includes_emails(self):
        """Prompt should include all email content."""
        import analyze_clusters

        cluster = {"id": 0, "size": 6}
        emails = [self.sample_email]
        calibration = "## Calibration"

        prompt = analyze_clusters.build_analysis_prompt(cluster, emails, calibration)

        # Should include email content
        self.assertIn("Q2 Update", prompt)
        self.assertIn("Team, Quick update", prompt)


class TestCostEstimation(unittest.TestCase):
    """Test cost estimation accuracy."""

    def test_estimate_tokens_reasonable_range(self):
        """Token estimate should be within reasonable range."""
        import analyze_clusters

        # A moderate prompt (~2000 characters, ~500 tokens at 4 chars/token)
        prompt = "This is a test prompt with some content. " * 50  # ~2100 chars

        estimate = analyze_clusters.estimate_tokens(prompt)

        # Should estimate ~400-700 tokens for ~2000 chars
        self.assertGreater(estimate['input_tokens'], 400)
        self.assertLess(estimate['input_tokens'], 700)

    def test_estimate_cost_uses_model_pricing(self):
        """Should use correct pricing for selected model."""
        import analyze_clusters

        model = "anthropic/claude-sonnet-4-20250514"
        clusters = [{"id": 0, "size": 10, "sample_ids": [f"email_{i}" for i in range(10)]}]

        # Mock get_emails to return sample emails
        mock_emails = [{"id": f"email_{i}", "original_data": {"body": "Test " * 100, "subject": "Test"}}
                       for i in range(10)]

        with patch.object(analyze_clusters, 'get_cluster_emails', return_value=mock_emails):
            estimate = analyze_clusters.estimate_analysis_cost(clusters, model)

        # Should have cost estimate
        self.assertIn('estimated_cost_usd', estimate)
        self.assertGreater(estimate['estimated_cost_usd'], 0)

    def test_estimate_handles_unknown_model(self):
        """Should use default pricing for unknown models."""
        import analyze_clusters

        model = "unknown/model-xyz"
        clusters = [{"id": 0, "size": 5, "sample_ids": [f"email_{i}" for i in range(5)]}]

        mock_emails = [{"id": f"email_{i}", "original_data": {"body": "Test " * 50, "subject": "Test"}}
                       for i in range(5)]

        with patch.object(analyze_clusters, 'get_cluster_emails', return_value=mock_emails):
            estimate = analyze_clusters.estimate_analysis_cost(clusters, model)

        # Should still return an estimate using default pricing
        self.assertIn('estimated_cost_usd', estimate)
        self.assertGreater(estimate['estimated_cost_usd'], 0)


class TestParallelAnalysis(unittest.TestCase):
    """Test ThreadPoolExecutor-based parallel analysis."""

    def test_analyze_single_cluster_returns_result(self):
        """Single cluster analysis should return parsed result."""
        import analyze_clusters

        mock_response = {
            "batch_id": "batch_001",
            "cluster_id": 0,
            "calibration_referenced": True,
            "new_personas": [{"name": "Executive Brief", "description": "Short updates"}],
            "samples": [{"id": "email_001", "persona": "Executive Brief", "confidence": 0.85}]
        }

        with patch.object(analyze_clusters, '_call_openrouter_api',
                         return_value=json.dumps(mock_response)):
            cluster_id, result, error = analyze_clusters.analyze_single_cluster(
                cluster_id=0,
                prompt="Test prompt",
                api_key="test-key",
                model="test-model"
            )

        self.assertEqual(cluster_id, 0)
        self.assertIsNotNone(result)
        self.assertIsNone(error)
        self.assertEqual(result['new_personas'][0]['name'], "Executive Brief")

    def test_analyze_single_cluster_handles_api_error(self):
        """Should handle API errors gracefully."""
        import analyze_clusters

        with patch.object(analyze_clusters, '_call_openrouter_api',
                         side_effect=Exception("API Error")):
            cluster_id, result, error = analyze_clusters.analyze_single_cluster(
                cluster_id=0,
                prompt="Test prompt",
                api_key="test-key",
                model="test-model",
                max_retries=0
            )

        self.assertEqual(cluster_id, 0)
        self.assertIsNone(result)
        self.assertIn("API Error", error)

    def test_parallel_analysis_all_succeed(self):
        """All clusters should complete when API calls succeed."""
        import analyze_clusters

        mock_results = {
            0: {"batch_id": "batch_001", "cluster_id": 0, "samples": []},
            1: {"batch_id": "batch_002", "cluster_id": 1, "samples": []}
        }

        def mock_analyze(cluster_id, prompt, api_key, model, max_retries=3):
            return (cluster_id, mock_results[cluster_id], None)

        clusters = [{"id": 0}, {"id": 1}]
        prompts = {0: "Prompt 0", 1: "Prompt 1"}

        with patch.object(analyze_clusters, 'analyze_single_cluster', side_effect=mock_analyze):
            results, errors = analyze_clusters.run_parallel_analysis(
                clusters=clusters,
                prompts=prompts,
                api_key="test-key",
                model="test-model"
            )

        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 0)

    def test_parallel_analysis_partial_failure(self):
        """Should handle partial failures gracefully."""
        import analyze_clusters

        def mock_analyze(cluster_id, prompt, api_key, model, max_retries=3):
            if cluster_id == 0:
                return (0, {"batch_id": "batch_001", "samples": []}, None)
            else:
                return (1, None, "API timeout")

        clusters = [{"id": 0}, {"id": 1}]
        prompts = {0: "Prompt 0", 1: "Prompt 1"}

        with patch.object(analyze_clusters, 'analyze_single_cluster', side_effect=mock_analyze):
            results, errors = analyze_clusters.run_parallel_analysis(
                clusters=clusters,
                prompts=prompts,
                api_key="test-key",
                model="test-model"
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn(1, errors)


class TestPersonaMerging(unittest.TestCase):
    """Test embedding-based persona similarity detection."""

    def test_find_similar_personas_above_threshold(self):
        """Should identify personas with similarity > threshold."""
        import analyze_clusters

        # Use very similar personas to ensure they're found
        personas = [
            {"name": "Executive Brief", "description": "Short executive updates to leadership team"},
            {"name": "Executive Brief Update", "description": "Short executive updates to leadership"},
            {"name": "Casual Friend Chat", "description": "Informal casual messages to personal friends"}
        ]

        # Use lower threshold for more reliable detection
        similar_pairs = analyze_clusters.find_similar_personas(personas, threshold=0.70)

        # Executive Brief and Executive Brief Update should be similar
        # Casual Friend Chat should NOT be similar to either
        found_exec_pair = any(
            (p[0] == 0 and p[1] == 1) or (p[0] == 1 and p[1] == 0)
            for p in similar_pairs
        )
        self.assertTrue(found_exec_pair, "Executive Brief personas should be similar")

    def test_find_similar_personas_no_match_below_threshold(self):
        """Should not match very different personas."""
        import analyze_clusters

        personas = [
            {"name": "Formal Legal", "description": "Official legal correspondence"},
            {"name": "Casual Friend", "description": "Chatty messages to close friends"}
        ]

        similar_pairs = analyze_clusters.find_similar_personas(personas, threshold=0.85)

        # These should NOT be similar
        self.assertEqual(len(similar_pairs), 0)

    def test_merge_persona_keeps_first_name(self):
        """Merged persona should keep name from first occurrence."""
        import analyze_clusters

        persona1 = {
            "name": "Executive Brief",
            "description": "Short updates to leadership",
            "characteristics": {"formality": 7, "warmth": 5}
        }
        persona2 = {
            "name": "Executive Update",
            "description": "Brief updates to executives",
            "characteristics": {"formality": 8, "warmth": 4}
        }

        merged = analyze_clusters.merge_persona_pair(persona1, persona2)

        self.assertEqual(merged['name'], "Executive Brief")

    def test_merge_persona_averages_numeric_values(self):
        """Merged persona should average formality, warmth, etc."""
        import analyze_clusters

        persona1 = {
            "name": "Persona A",
            "description": "Description A",
            "characteristics": {"formality": 6, "warmth": 8, "authority": 7, "directness": 5}
        }
        persona2 = {
            "name": "Persona B",
            "description": "Description B",
            "characteristics": {"formality": 8, "warmth": 4, "authority": 9, "directness": 7}
        }

        merged = analyze_clusters.merge_persona_pair(persona1, persona2)

        self.assertEqual(merged['characteristics']['formality'], 7)  # (6+8)/2
        self.assertEqual(merged['characteristics']['warmth'], 6)     # (8+4)/2
        self.assertEqual(merged['characteristics']['authority'], 8)  # (7+9)/2
        self.assertEqual(merged['characteristics']['directness'], 6) # (5+7)/2

    def test_apply_merges_updates_sample_assignments(self):
        """Sample persona references should update after merge."""
        import analyze_clusters

        analysis_results = {
            0: {
                "new_personas": [
                    {"name": "Executive Brief", "description": "Brief updates"}
                ],
                "samples": [
                    {"id": "email_001", "persona": "Executive Brief"},
                    {"id": "email_002", "persona": "Executive Brief"}
                ]
            },
            1: {
                "new_personas": [
                    {"name": "Executive Update", "description": "Update emails"}
                ],
                "samples": [
                    {"id": "email_003", "persona": "Executive Update"},
                    {"id": "email_004", "persona": "Executive Update"}
                ]
            }
        }

        # Merge "Executive Update" -> "Executive Brief"
        merge_mapping = {"Executive Update": "Executive Brief"}

        updated = analyze_clusters.apply_persona_merges(analysis_results, merge_mapping)

        # All samples should now reference "Executive Brief"
        for cluster_id, result in updated.items():
            for sample in result['samples']:
                self.assertEqual(sample['persona'], "Executive Brief")


class TestApprovalWorkflow(unittest.TestCase):
    """Test draft save/load and approval workflow."""

    def test_save_draft_creates_file(self):
        """Should save draft to analysis_draft.json."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            draft_file = tmp_path / "analysis_draft.json"

            results = {0: {"batch_id": "batch_001", "samples": []}}
            merged_personas = [{"name": "Test Persona"}]
            metadata = {"model": "test-model", "timestamp": "2026-01-09T12:00:00Z"}

            with patch.object(analyze_clusters, '_get_draft_file', return_value=draft_file):
                analyze_clusters.save_draft(results, merged_personas, metadata)

            self.assertTrue(draft_file.exists())

            draft = json.loads(draft_file.read_text())
            self.assertIn('results', draft)
            self.assertIn('merged_personas', draft)

    def test_load_draft_returns_saved_data(self):
        """Should load draft from analysis_draft.json."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            draft_file = tmp_path / "analysis_draft.json"

            draft_data = {
                "results": {"0": {"batch_id": "batch_001"}},
                "merged_personas": [{"name": "Test"}],
                "metadata": {"model": "test"}
            }
            draft_file.write_text(json.dumps(draft_data))

            with patch.object(analyze_clusters, '_get_draft_file', return_value=draft_file):
                draft = analyze_clusters.load_draft()

            self.assertIsNotNone(draft)
            self.assertEqual(draft['results'][0]['batch_id'], "batch_001")

    def test_reject_draft_removes_file(self):
        """Reject should remove draft file."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            draft_file = tmp_path / "analysis_draft.json"
            draft_file.write_text('{}')

            with patch.object(analyze_clusters, '_get_draft_file', return_value=draft_file):
                analyze_clusters.reject_draft()

            self.assertFalse(draft_file.exists())

    def test_has_pending_draft(self):
        """Should detect when a draft exists."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            draft_file = tmp_path / "analysis_draft.json"

            # No draft
            with patch.object(analyze_clusters, '_get_draft_file', return_value=draft_file):
                self.assertFalse(analyze_clusters.has_pending_draft())

            # With draft
            draft_file.write_text('{}')
            with patch.object(analyze_clusters, '_get_draft_file', return_value=draft_file):
                self.assertTrue(analyze_clusters.has_pending_draft())


class TestTokenLimitHandling(unittest.TestCase):
    """Test large cluster splitting."""

    def test_split_large_cluster(self):
        """Should split cluster exceeding token limit."""
        import analyze_clusters

        # Large cluster with 300 emails
        large_cluster = {
            'id': 1,
            'size': 300,
            'sample_ids': [f'email_{i}' for i in range(300)]
        }

        sub_clusters = analyze_clusters.split_large_cluster(large_cluster, max_emails_per_batch=100)

        # Should split into 3 sub-clusters
        self.assertEqual(len(sub_clusters), 3)

        # Each should have at most 100 emails
        for sub in sub_clusters:
            self.assertLessEqual(len(sub['sample_ids']), 100)

    def test_small_cluster_not_split(self):
        """Should NOT split cluster within token limit."""
        import analyze_clusters

        small_cluster = {
            'id': 0,
            'size': 50,
            'sample_ids': [f'email_{i}' for i in range(50)]
        }

        sub_clusters = analyze_clusters.split_large_cluster(small_cluster, max_emails_per_batch=100)

        # Should return single cluster unchanged
        self.assertEqual(len(sub_clusters), 1)
        self.assertEqual(len(sub_clusters[0]['sample_ids']), 50)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery."""

    def test_invalid_json_response_handled(self):
        """Should handle invalid JSON from LLM gracefully."""
        import analyze_clusters

        with patch.object(analyze_clusters, '_call_openrouter_api',
                         return_value="This is not valid JSON {{{"):
            cluster_id, result, error = analyze_clusters.analyze_single_cluster(
                cluster_id=0,
                prompt="Test prompt",
                api_key="test-key",
                model="test-model",
                max_retries=0
            )

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("JSON", error)

    def test_missing_model_config_detected(self):
        """Should detect when model not configured."""
        import analyze_clusters

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Point to non-existent file
            fake_config = tmp_path / "openrouter_model.json"

            with patch.object(analyze_clusters, '_get_model_config_file', return_value=fake_config):
                configured = analyze_clusters.check_model_configured()

            self.assertFalse(configured)


class TestReviewSummary(unittest.TestCase):
    """Test review summary generation."""

    def test_show_review_summary_includes_cluster_counts(self):
        """Summary should show clusters analyzed."""
        import analyze_clusters

        draft = {
            "results": {
                "0": {"batch_id": "batch_001", "samples": [{"id": "e1"}, {"id": "e2"}]},
                "1": {"batch_id": "batch_002", "samples": [{"id": "e3"}]}
            },
            "merged_personas": [{"name": "Persona A"}, {"name": "Persona B"}],
            "metadata": {"model": "test-model"}
        }

        summary = analyze_clusters.show_review_summary(draft)

        self.assertIn("2", summary)  # 2 clusters
        self.assertIn("3", summary)  # 3 total samples
        self.assertIn("2", summary)  # 2 personas (may overlap with cluster count)


if __name__ == '__main__':
    unittest.main()
