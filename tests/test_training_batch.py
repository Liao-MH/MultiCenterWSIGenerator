import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.models.training_batch import (
    TrainingBatchError,
    load_training_batch,
)
from he_wsi_generator.models.training_index import build_training_index


REPO_ROOT = Path(__file__).resolve().parents[1]


class TrainingBatchTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512, 0] = 220
        image[:, :512, 1] = 40
        image[:, :512, 2] = 80
        image[:, 512:, 0] = 40
        image[:, 512:, 1] = 180
        image[:, 512:, 2] = 120
        Image.fromarray(image).save(slide_path)
        return slide_path

    def manifest(self, root: Path, mask_path: Path, slide_path: Path | None = None) -> dict:
        wsi_path = slide_path if slide_path is not None else root / "slide-001.svs"
        return {
            "schema_version": "v0.72.2",
            "dataset_id": "demo-training",
            "created_at": "2026-05-23T14:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(wsi_path),
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

    def audit(self, root: Path, slide_path: Path | None = None) -> dict:
        wsi_path = slide_path if slide_path is not None else root / "slide-001.svs"
        return {
            "schema_version": "v0.72.2",
            "dataset_id": "demo-training",
            "created_at": "2026-05-23T14:00:00Z",
            "backend": "fixture-image",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(wsi_path),
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
            "schema_version": "v0.72.2",
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

    def write_training_index(
        self,
        root: Path,
        mask_path: Path,
        slide_path: Path | None = None,
    ) -> Path:
        output_path = root / "training-index.jsonl"
        build_training_index(
            self.manifest(root, mask_path, slide_path=slide_path),
            self.audit(root, slide_path=slide_path),
            [self.label_mapping()],
            output_path,
        )
        return output_path

    def test_load_training_batch_reads_masks_and_maps_project_class_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            mask = np.zeros((512, 1024), dtype=np.uint8)
            mask[:, :512] = 2
            mask[:, 512:] = 5
            np.save(mask_path, mask)
            index_path = self.write_training_index(root, mask_path)

            batch = load_training_batch(
                index_path,
                batch_size=2,
                split="train",
                cascade_level="1/1",
            )

        self.assertEqual(batch["schema_version"], "v0.72.2")
        self.assertEqual(batch["batch_size"], 2)
        self.assertEqual(batch["mask_batch_shape"], [2, 512, 512])
        self.assertEqual(batch["cascade_levels"], ["1/1"])
        self.assertEqual(batch["wsi_ids"], ["slide-001"])
        self.assertEqual(batch["mask_class_ids"], [2, 5])
        self.assertEqual(batch["mask_batch"].shape, (2, 512, 512))
        self.assertTrue((batch["mask_batch"][0] == 2).all())
        self.assertTrue((batch["mask_batch"][1] == 5).all())

    def test_load_training_batch_reads_fixture_image_tiles_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            mask_path = root / "mask.npy"
            mask = np.zeros((512, 1024), dtype=np.uint8)
            mask[:, :512] = 2
            mask[:, 512:] = 5
            np.save(mask_path, mask)
            index_path = self.write_training_index(root, mask_path, slide_path=slide_path)

            batch = load_training_batch(
                index_path,
                batch_size=2,
                split="train",
                cascade_level="1/1",
                include_image=True,
            )
            summary = {
                key: value
                for key, value in batch.items()
                if key not in {"mask_batch", "image_batch"}
            }

        self.assertEqual(batch["image_batch_shape"], [2, 512, 512, 3])
        self.assertEqual(batch["image_dtype"], "uint8")
        self.assertEqual(batch["image_batch"].shape, (2, 512, 512, 3))
        self.assertEqual(batch["image_batch"][0, 0, 0].tolist(), [220, 40, 80])
        self.assertEqual(batch["image_batch"][1, 0, 0].tolist(), [40, 180, 120])
        self.assertNotIn("image_batch", summary)

    def test_load_training_batch_rejects_missing_wsi_when_image_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            np.save(mask_path, np.zeros((512, 1024), dtype=np.uint8))
            index_path = self.write_training_index(root, mask_path)

            with self.assertRaisesRegex(TrainingBatchError, "WSI image file does not exist"):
                load_training_batch(index_path, batch_size=1, include_image=True)

    def test_load_training_batch_rejects_missing_mask_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            np.save(mask_path, np.zeros((512, 1024), dtype=np.uint8))
            index_path = self.write_training_index(root, mask_path)
            mask_path.unlink()

            with self.assertRaisesRegex(TrainingBatchError, "mask file does not exist"):
                load_training_batch(index_path, batch_size=1)

    def test_cli_inspects_training_batch_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            mask = np.ones((512, 1024), dtype=np.uint8)
            mask[:, 512:] = 3
            np.save(mask_path, mask)
            slide_path = self.create_fixture_slide(root)
            index_path = self.write_training_index(root, mask_path, slide_path=slide_path)
            output_path = root / "batch-summary.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-training-batch",
                    str(index_path),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--include-image",
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
            summary = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("training batch summary written", result.stdout)
        self.assertEqual(summary["batch_size"], 2)
        self.assertEqual(summary["mask_batch_shape"], [2, 512, 512])
        self.assertEqual(summary["image_batch_shape"], [2, 512, 512, 3])
        self.assertEqual(summary["image_dtype"], "uint8")
        self.assertNotIn("mask_batch", summary)
        self.assertNotIn("image_batch", summary)


if __name__ == "__main__":
    unittest.main()
