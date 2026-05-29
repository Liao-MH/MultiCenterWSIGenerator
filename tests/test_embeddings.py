import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.embeddings.cache import load_embedding_cache, save_embedding_cache
from he_wsi_generator.embeddings.cluster import cluster_embeddings
from he_wsi_generator.embeddings.embedder import (
    CheckpointPatchEmbedder,
    EmbeddingError,
    FixturePatchEmbedder,
)


class EmbeddingTests(unittest.TestCase):
    def create_checkpoint(self, directory: Path, embedding_dim: int = 4) -> Path:
        checkpoint_path = directory / "fixture_embedder.json"
        checkpoint_path.write_text(
            json.dumps(
                {
                    "model_id": "fixture-statistical-embedder",
                    "embedding_dim": embedding_dim,
                    "normalization": "unit-test",
                }
            ),
            encoding="utf-8",
        )
        return checkpoint_path

    def test_checkpoint_embedder_reports_missing_checkpoint(self):
        with self.assertRaisesRegex(EmbeddingError, "checkpoint does not exist"):
            CheckpointPatchEmbedder("/missing/checkpoint.json")

    def test_checkpoint_embedder_outputs_finite_embedding_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = self.create_checkpoint(Path(tmpdir), embedding_dim=4)
            embedder = CheckpointPatchEmbedder(checkpoint)
            patches = np.array(
                [
                    [[[0.0, 0.5, 1.0], [0.2, 0.4, 0.6]]],
                    [[[1.0, 0.5, 0.0], [0.8, 0.4, 0.2]]],
                ],
                dtype=np.float32,
            )

            result = embedder.embed(patches, magnification="40x", normalization={"mode": "none"})

        self.assertEqual(result.embeddings.shape, (2, 4))
        self.assertTrue(np.isfinite(result.embeddings).all())
        self.assertEqual(result.metadata["model_id"], "fixture-statistical-embedder")
        self.assertEqual(result.metadata["embedding_dim"], 4)
        self.assertEqual(result.metadata["patch_count"], 2)
        self.assertEqual(len(result.metadata["checkpoint_hash"]), 64)
        self.assertEqual(result.metadata["embedding_backend"], "statistical_patch_moments")
        self.assertEqual(
            result.metadata["embedder_kind"],
            "checkpoint_backed_statistical_patch_embedder",
        )
        self.assertFalse(result.metadata["production_ready"])
        self.assertIn("not_a_pathology_foundation_model", result.metadata["limitations"])

    def test_fixture_embedder_marks_low_confidence(self):
        embedder = FixturePatchEmbedder(embedding_dim=4)
        patches = np.ones((1, 2, 2, 3), dtype=np.float32)

        result = embedder.embed(patches, magnification="40x", normalization={})

        self.assertEqual(result.embeddings.shape, (1, 4))
        self.assertEqual(result.metadata["embedding_confidence"], "low")
        self.assertEqual(result.metadata["embedding_backend"], "statistical_patch_moments")
        self.assertEqual(result.metadata["embedder_kind"], "fixture_statistical_patch_embedder")
        self.assertIn("fixture_smoke_only", result.metadata["limitations"])

    def test_embedding_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            embeddings = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
            metadata = {
                "model_id": "fixture",
                "checkpoint_hash": "abc",
                "embedding_dim": 2,
                "patch_count": 2,
            }

            paths = save_embedding_cache(cache_dir, "slide-001", embeddings, metadata)
            loaded_embeddings, loaded_metadata = load_embedding_cache(cache_dir, "slide-001")

        self.assertTrue(paths["embeddings"].endswith("slide-001.embeddings.npy"))
        self.assertEqual(loaded_metadata["patch_count"], 2)
        np.testing.assert_array_equal(loaded_embeddings, embeddings)

    def test_cluster_embeddings_reports_counts_and_inertia(self):
        embeddings = np.array(
            [
                [0.0, 0.0],
                [0.1, 0.1],
                [10.0, 10.0],
                [10.1, 10.1],
            ],
            dtype=np.float32,
        )

        report = cluster_embeddings(embeddings, n_clusters=2, max_iter=10)

        self.assertEqual(report["n_clusters"], 2)
        self.assertEqual(sum(report["cluster_counts"].values()), 4)
        self.assertEqual(len(report["labels"]), 4)
        self.assertGreaterEqual(report["inertia"], 0.0)

    def test_cluster_embeddings_handles_duplicate_leading_rows(self):
        embeddings = np.array(
            [
                [0.0, 0.0],
                [0.0, 0.0],
                [10.0, 10.0],
                [10.0, 10.0],
            ],
            dtype=np.float32,
        )

        report = cluster_embeddings(embeddings, n_clusters=2, max_iter=10)

        self.assertEqual(report["cluster_counts"], {"0": 2, "1": 2})
        self.assertEqual(sorted(set(report["labels"])), [0, 1])

    def test_cluster_embeddings_rejects_empty_input(self):
        with self.assertRaisesRegex(ValueError, "embeddings must contain at least one row"):
            cluster_embeddings(np.empty((0, 4), dtype=np.float32), n_clusters=2)


if __name__ == "__main__":
    unittest.main()
