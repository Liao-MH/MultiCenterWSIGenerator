import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.embeddings.embedder import FixturePatchEmbedder
from he_wsi_generator.priors.pseudo_mask import (
    PseudoMaskBuildError,
    build_pseudo_mask_from_manifest,
)


class SpyBatchEmbedder:
    def __init__(self):
        self.delegate = FixturePatchEmbedder(embedding_dim=4)
        self.batch_lengths = []

    def embed(self, patches, magnification: str, normalization: dict):
        self.batch_lengths.append(len(patches))
        return self.delegate.embed(patches, magnification=magnification, normalization=normalization)


class PseudoMaskPipelineTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        image[:4, :] = [220, 40, 80]
        image[4:, :] = [40, 180, 120]
        Image.fromarray(image).save(slide_path)
        slide_path.with_suffix(slide_path.suffix + ".json").write_text(
            json.dumps(
                {
                    "mpp_x": 0.25,
                    "mpp_y": 0.25,
                    "max_magnification": "40x",
                }
            ),
            encoding="utf-8",
        )
        return slide_path

    def manifest(self, slide_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "dataset_id": "demo-pseudo",
            "created_at": "2026-05-26T10:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
                    "center_id": "center-a",
                    "cancer_type": "breast",
                    "tissue_type": "breast",
                    "split": "train",
                    "annotations": [],
                }
            ],
        }

    def test_build_pseudo_mask_from_manifest_writes_embedding_cache_and_cluster_mask(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")

            output = build_pseudo_mask_from_manifest(
                manifest_path=manifest_path,
                output_dir=root / "pseudo-mask",
                backend="fixture-image",
                embedder=FixturePatchEmbedder(embedding_dim=4),
                patch_size=(4, 4),
                n_clusters=2,
            )

            pseudo_mask = np.load(output["pseudo_mask_path"])
            cluster_report = json.loads(Path(output["cluster_report_path"]).read_text(encoding="utf-8"))
            pseudo_manifest = json.loads(Path(output["annotation_manifest_path"]).read_text(encoding="utf-8"))

        self.assertEqual(pseudo_mask.shape, (8, 8))
        self.assertEqual(sorted(int(v) for v in np.unique(pseudo_mask).tolist()), [0, 1])
        self.assertEqual(cluster_report["embedding_count"], 4)
        self.assertEqual(cluster_report["n_clusters"], 2)
        self.assertEqual(pseudo_manifest["annotation_type"], "cluster_pseudo_mask")
        self.assertEqual(pseudo_manifest["wsi_id"], "slide-001")
        self.assertEqual(pseudo_manifest["mask_shape"], [8, 8])
        self.assertEqual(pseudo_manifest["patch_size"], [4, 4])
        self.assertEqual(pseudo_manifest["batch_size"], 512)
        self.assertTrue(pseudo_manifest["streaming_patch_embedding"])
        self.assertEqual(
            pseudo_manifest["embedding_summary"]["embedder_kind"],
            "fixture_statistical_patch_embedder",
        )
        self.assertEqual(
            pseudo_manifest["embedding_summary"]["embedding_backend"],
            "statistical_patch_moments",
        )
        self.assertIn(
            "not_a_pathology_foundation_model",
            pseudo_manifest["embedding_summary"]["limitations"],
        )

    def test_build_pseudo_mask_from_manifest_streams_patch_embedding_batches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")
            embedder = SpyBatchEmbedder()

            output = build_pseudo_mask_from_manifest(
                manifest_path=manifest_path,
                output_dir=root / "pseudo-mask",
                backend="fixture-image",
                embedder=embedder,
                patch_size=(2, 2),
                n_clusters=2,
                batch_size=3,
            )
            pseudo_manifest = json.loads(Path(output["annotation_manifest_path"]).read_text(encoding="utf-8"))

        self.assertEqual(embedder.batch_lengths, [3, 3, 3, 3, 3, 1])
        self.assertEqual(pseudo_manifest["patch_count"], 16)
        self.assertEqual(pseudo_manifest["batch_size"], 3)
        self.assertEqual(pseudo_manifest["embedding_batch_count"], 6)
        self.assertTrue(pseudo_manifest["streaming_patch_embedding"])

    def test_build_pseudo_mask_from_manifest_rejects_cluster_count_above_patch_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")

            with self.assertRaisesRegex(PseudoMaskBuildError, "n_clusters cannot exceed"):
                build_pseudo_mask_from_manifest(
                    manifest_path=manifest_path,
                    output_dir=root / "pseudo-mask",
                    backend="fixture-image",
                    embedder=FixturePatchEmbedder(embedding_dim=4),
                    patch_size=(4, 4),
                    n_clusters=5,
                )


if __name__ == "__main__":
    unittest.main()
