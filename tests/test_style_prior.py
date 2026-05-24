import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.style import (
    StylePriorBuildError,
    build_style_prior_from_training_index,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class StylePriorTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512] = [220, 40, 80]
        image[:, 512:] = [40, 180, 120]
        Image.fromarray(image).save(slide_path)
        return slide_path

    def manifest(self, root: Path, mask_path: Path, slide_path: Path) -> dict:
        return {
            "schema_version": "v0.67.0",
            "dataset_id": "demo-style",
            "created_at": "2026-05-23T14:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
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

    def audit(self, slide_path: Path) -> dict:
        return {
            "schema_version": "v0.67.0",
            "dataset_id": "demo-style",
            "created_at": "2026-05-23T14:00:00Z",
            "backend": "fixture-image",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
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
            "schema_version": "v0.67.0",
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

    def write_training_index(self, root: Path, slide_path: Path | None = None) -> Path:
        slide = slide_path if slide_path is not None else self.create_fixture_slide(root)
        mask_path = root / "mask.npy"
        mask = np.ones((512, 1024), dtype=np.uint8)
        mask[:, 512:] = 2
        np.save(mask_path, mask)
        output_path = root / "training-index.jsonl"
        build_training_index(
            self.manifest(root, mask_path, slide),
            self.audit(slide),
            [self.label_mapping()],
            output_path,
        )
        return output_path

    def test_build_style_prior_from_training_index_writes_rgb_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            output_path = root / "style_prior.json"

            style_prior = build_style_prior_from_training_index(
                index_path,
                output_path=output_path,
                batch_size=2,
                split="train",
                cascade_level="1/1",
            )
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(style_prior, saved)
        self.assertEqual(style_prior["schema_version"], "v0.67.0")
        self.assertEqual(style_prior["prior_type"], "style_prior")
        self.assertEqual(style_prior["source"]["training_index_path"], str(index_path))
        self.assertEqual(style_prior["source"]["batch_size"], 2)
        self.assertEqual(style_prior["source"]["split"], "train")
        self.assertEqual(style_prior["source"]["cascade_level"], "1/1")
        self.assertEqual(style_prior["image_batch_shape"], [2, 512, 512, 3])
        self.assertEqual(style_prior["image_dtype"], "uint8")
        self.assertNotIn("image_batch", style_prior)
        self.assertEqual(style_prior["wsi_ids"], ["slide-001"])
        self.assertEqual(style_prior["sample_count"], 2)
        self.assertEqual(style_prior["rgb_statistics"]["mean_rgb"], [130.0, 110.0, 100.0])
        self.assertEqual(style_prior["rgb_statistics"]["std_rgb"], [90.0, 70.0, 20.0])
        self.assertEqual(style_prior["rgb_statistics"]["min_rgb"], [40, 40, 80])
        self.assertEqual(style_prior["rgb_statistics"]["max_rgb"], [220, 180, 120])
        self.assertAlmostEqual(
            style_prior["rgb_statistics"]["mean_rgb_normalized"][0],
            130.0 / 255.0,
        )
        self.assertAlmostEqual(
            style_prior["rgb_statistics"]["std_rgb_normalized"][1],
            70.0 / 255.0,
        )
        self.assertEqual(
            [record["mean_rgb"] for record in style_prior["tile_style_records"]],
            [[220.0, 40.0, 80.0], [40.0, 180.0, 120.0]],
        )
        self.assertEqual(
            [record["wsi_id"] for record in style_prior["tile_style_records"]],
            ["slide-001", "slide-001"],
        )

    def test_build_style_prior_rejects_missing_wsi_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            index_path = self.write_training_index(root, slide_path=slide_path)
            slide_path.unlink()

            with self.assertRaisesRegex(StylePriorBuildError, "WSI image file does not exist"):
                build_style_prior_from_training_index(
                    index_path,
                    output_path=root / "style_prior.json",
                    batch_size=1,
                )

    def test_cli_builds_style_prior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            output_path = root / "style_prior.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-style-prior",
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
            style_prior = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("style prior written", result.stdout)
        self.assertEqual(style_prior["prior_type"], "style_prior")
        self.assertEqual(style_prior["rgb_statistics"]["mean_rgb"], [130.0, 110.0, 100.0])


if __name__ == "__main__":
    unittest.main()
