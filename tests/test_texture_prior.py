import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.embeddings.cache import save_embedding_cache
from he_wsi_generator.embeddings.cluster import cluster_embeddings
from he_wsi_generator.priors.texture import (
    TexturePriorBuildError,
    build_texture_prior_from_embedding_cache,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class TexturePriorTests(unittest.TestCase):
    def write_embedding_inputs(self, root: Path) -> tuple[Path, str, Path]:
        cache_dir = root / "embedding-cache"
        cache_key = "slide-001"
        embeddings = np.array(
            [
                [0.0, 0.0],
                [0.2, 0.2],
                [10.0, 10.0],
                [10.2, 10.2],
            ],
            dtype=np.float32,
        )
        save_embedding_cache(
            cache_dir,
            cache_key,
            embeddings,
            {
                "model_id": "fixture-texture-embedder",
                "checkpoint_hash": "a" * 64,
                "embedding_dim": 2,
                "patch_count": 4,
                "magnification": "40x",
            },
        )
        cluster_report = cluster_embeddings(embeddings, n_clusters=2, max_iter=10)
        cluster_path = root / "cluster-report.json"
        cluster_path.write_text(json.dumps(cluster_report), encoding="utf-8")
        return cache_dir, cache_key, cluster_path

    def test_build_texture_prior_from_embedding_cache_writes_cluster_prototypes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_dir, cache_key, cluster_path = self.write_embedding_inputs(root)
            output_path = root / "texture_prior.json"

            prior = build_texture_prior_from_embedding_cache(
                cache_dir=cache_dir,
                cache_key=cache_key,
                cluster_report_path=cluster_path,
                output_path=output_path,
            )
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(prior, saved)
        self.assertEqual(prior["schema_version"], "v0.61.0")
        self.assertEqual(prior["prior_type"], "texture_prior")
        self.assertEqual(prior["source"]["cache_dir"], str(cache_dir))
        self.assertEqual(prior["source"]["cache_key"], cache_key)
        self.assertEqual(prior["source"]["cluster_report_path"], str(cluster_path))
        self.assertEqual(prior["embedding_count"], 4)
        self.assertEqual(prior["embedding_dim"], 2)
        self.assertEqual(prior["cluster_count"], 2)
        self.assertEqual(prior["embedding_metadata"]["model_id"], "fixture-texture-embedder")
        self.assertEqual(prior["cluster_report_summary"]["cluster_counts"], {"0": 2, "1": 2})
        self.assertEqual(prior["global_embedding_mean"], [5.1, 5.1])
        self.assertEqual(prior["global_embedding_std"], [5.0009999, 5.0009999])
        self.assertEqual(
            prior["texture_prototypes"],
            [
                {
                    "cluster_id": 0,
                    "sample_count": 2,
                    "fraction": 0.5,
                    "mean_embedding": [0.1, 0.1],
                    "std_embedding": [0.1, 0.1],
                    "representative_embedding_index": 0,
                },
                {
                    "cluster_id": 1,
                    "sample_count": 2,
                    "fraction": 0.5,
                    "mean_embedding": [10.1, 10.1],
                    "std_embedding": [0.1, 0.1],
                    "representative_embedding_index": 2,
                },
            ],
        )

    def test_build_texture_prior_rejects_label_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_dir, cache_key, cluster_path = self.write_embedding_inputs(root)
            cluster_report = json.loads(cluster_path.read_text(encoding="utf-8"))
            cluster_report["labels"] = cluster_report["labels"][:-1]
            cluster_path.write_text(json.dumps(cluster_report), encoding="utf-8")

            with self.assertRaisesRegex(TexturePriorBuildError, "labels length"):
                build_texture_prior_from_embedding_cache(
                    cache_dir=cache_dir,
                    cache_key=cache_key,
                    cluster_report_path=cluster_path,
                    output_path=root / "texture_prior.json",
                )

    def test_cli_builds_texture_prior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_dir, cache_key, cluster_path = self.write_embedding_inputs(root)
            output_path = root / "texture_prior.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-texture-prior",
                    "--cache-dir",
                    str(cache_dir),
                    "--cache-key",
                    cache_key,
                    "--cluster-report",
                    str(cluster_path),
                    "--output",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            prior = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("texture prior written", result.stdout)
        self.assertEqual(prior["prior_type"], "texture_prior")
        self.assertEqual(prior["cluster_count"], 2)


if __name__ == "__main__":
    unittest.main()
