import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.layout import (
    LayoutMaskPriorBuildError,
    build_layout_mask_prior_from_training_index,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class LayoutMaskPriorTests(unittest.TestCase):
    def manifest(self, root: Path, mask_path: Path) -> dict:
        return {
            "schema_version": "v0.69.0",
            "dataset_id": "demo-layout",
            "created_at": "2026-05-23T15:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(root / "slide-001.svs"),
                    "cancer_type": "lung",
                    "tissue_type": "lung",
                    "split": "train",
                    "mpp_x": 0.25,
                    "mpp_y": 0.25,
                    "max_magnification": "40x",
                    "annotations": [
                        {
                            "annotation_id": "ann-001",
                            "annotation_path": str(mask_path),
                            "annotation_type": "numpy_mask",
                            "coordinate_level": 0,
                            "label_encoding": "integer_index",
                            "transform_to_level0": {
                                "scale_x": 1.0,
                                "scale_y": 1.0,
                                "offset_x": 0,
                                "offset_y": 0,
                            },
                            "status": "validated",
                        }
                    ],
                }
            ],
        }

    def audit(self, root: Path) -> dict:
        return {
            "schema_version": "v0.69.0",
            "dataset_id": "demo-layout",
            "created_at": "2026-05-23T15:00:00Z",
            "backend": "fixture-image",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(root / "slide-001.svs"),
                    "status": "ok",
                    "split": "train",
                    "cancer_type": "lung",
                    "dimensions": [1024, 512],
                    "level_dimensions": [[1024, 512]],
                    "level_downsamples": [1.0],
                    "mpp_x": 0.25,
                    "mpp_y": 0.25,
                    "max_magnification": "40x",
                    "backend": "fixture-image",
                    "format": "svs",
                    "annotation_count": 1,
                }
            ],
        }

    def label_mapping(self) -> dict:
        return {
            "schema_version": "v0.69.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-001",
            "classes": {
                "0": "background",
                "1": "tissue",
                "2": "target_pathology",
                "3": "supporting_tissue",
                "4": "necrosis_debris",
                "5": "artifact",
            },
            "mapping_source": "manual",
            "confidence": {
                "0": "high",
                "1": "high",
                "2": "high",
                "3": "medium",
                "4": "medium",
                "5": "medium",
            },
        }

    def write_training_index(self, root: Path) -> tuple[Path, Path]:
        mask_path = root / "mask.npy"
        mask = np.ones((512, 1024), dtype=np.uint8)
        mask[:, 512:] = 2
        np.save(mask_path, mask)
        output_path = root / "training-index.jsonl"
        build_training_index(
            self.manifest(root, mask_path),
            self.audit(root),
            [self.label_mapping()],
            output_path,
        )
        return output_path, mask_path

    def test_build_layout_mask_prior_from_training_index_writes_mask_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path, _ = self.write_training_index(root)
            output_path = root / "layout_mask_prior.json"

            prior = build_layout_mask_prior_from_training_index(
                index_path,
                output_path=output_path,
                batch_size=2,
                split="train",
                cascade_level="1/1",
            )
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(prior, saved)
        self.assertEqual(prior["schema_version"], "v0.69.0")
        self.assertEqual(prior["prior_type"], "layout_mask_prior")
        self.assertEqual(prior["source"]["training_index_path"], str(index_path))
        self.assertEqual(prior["source"]["batch_size"], 2)
        self.assertEqual(prior["source"]["split"], "train")
        self.assertEqual(prior["source"]["cascade_level"], "1/1")
        self.assertEqual(prior["sample_count"], 2)
        self.assertEqual(prior["wsi_ids"], ["slide-001"])
        self.assertEqual(prior["mask_batch_shape"], [2, 512, 512])
        self.assertNotIn("mask_batch", prior)
        self.assertEqual(prior["class_names"][1], "tissue")
        self.assertEqual(prior["class_names"][2], "target_pathology")
        self.assertEqual(prior["class_pixel_counts_by_id"], [0, 262144, 262144, 0, 0, 0])
        self.assertEqual(prior["class_fractions_by_id"], [0.0, 0.5, 0.5, 0.0, 0.0, 0.0])
        self.assertEqual(prior["class_present_by_id"], [False, True, True, False, False, False])
        self.assertEqual(prior["non_background_fraction"], 1.0)
        self.assertEqual(
            [record["dominant_class_name"] for record in prior["tile_layout_records"]],
            ["tissue", "target_pathology"],
        )
        self.assertEqual(
            [record["class_fractions_by_id"] for record in prior["tile_layout_records"]],
            [
                [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            ],
        )
        self.assertEqual(prior["adjacency_counts"]["horizontal"]["1:1"], 261632)
        self.assertEqual(prior["adjacency_counts"]["horizontal"]["2:2"], 261632)
        self.assertEqual(prior["adjacency_counts"]["vertical"]["1:1"], 261632)
        self.assertEqual(prior["adjacency_counts"]["vertical"]["2:2"], 261632)

    def test_build_layout_mask_prior_rejects_missing_mask(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path, mask_path = self.write_training_index(root)
            mask_path.unlink()

            with self.assertRaisesRegex(LayoutMaskPriorBuildError, "mask file does not exist"):
                build_layout_mask_prior_from_training_index(
                    index_path,
                    output_path=root / "layout_mask_prior.json",
                    batch_size=1,
                )

    def test_cli_builds_layout_mask_prior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path, _ = self.write_training_index(root)
            output_path = root / "layout_mask_prior.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-layout-mask-prior",
                    str(index_path),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
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
        self.assertIn("layout/mask prior written", result.stdout)
        self.assertEqual(prior["prior_type"], "layout_mask_prior")
        self.assertEqual(prior["class_fractions_by_id"], [0.0, 0.5, 0.5, 0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
