import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.models.training_index import (
    TrainingIndexError,
    build_training_index,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class TrainingIndexTests(unittest.TestCase):
    def manifest(self, root: Path, mask_path: Path) -> dict:
        return {
            "schema_version": "v0.72.3",
            "dataset_id": "demo-training",
            "created_at": "2026-05-23T14:00:00Z",
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
            "schema_version": "v0.72.3",
            "dataset_id": "demo-training",
            "created_at": "2026-05-23T14:00:00Z",
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
            "schema_version": "v0.72.3",
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

    def test_build_training_index_writes_four_level_tile_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            np.save(mask_path, np.zeros((512, 1024), dtype=np.uint8))
            output_path = root / "training-index.jsonl"

            summary = build_training_index(
                self.manifest(root, mask_path),
                self.audit(root),
                [self.label_mapping()],
                output_path,
            )
            records = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(summary["schema_version"], "v0.72.3")
        self.assertEqual(summary["sample_count"], 8)
        self.assertEqual(summary["records_by_level"]["1/1"], 2)
        self.assertEqual(records[0]["wsi_id"], "slide-001")
        self.assertEqual(records[0]["cascade_level"], "1/32")
        self.assertEqual(records[-1]["cascade_level"], "1/1")
        self.assertEqual(records[-1]["tile"]["width"], 512)
        self.assertEqual(records[-1]["mask"]["source_annotation_id"], "ann-001")
        self.assertEqual(records[-1]["mask"]["class_mapping"]["5"], "artifact")

    def test_build_training_index_rejects_missing_label_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            np.save(mask_path, np.zeros((512, 1024), dtype=np.uint8))

            with self.assertRaisesRegex(TrainingIndexError, "missing label mapping"):
                build_training_index(
                    self.manifest(root, mask_path),
                    self.audit(root),
                    [],
                    root / "training-index.jsonl",
                )

    def test_cli_builds_training_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mask_path = root / "mask.npy"
            np.save(mask_path, np.zeros((512, 1024), dtype=np.uint8))
            manifest_path = root / "manifest.json"
            audit_path = root / "audit.json"
            mapping_path = root / "label-mapping.json"
            output_path = root / "training-index.jsonl"
            manifest_path.write_text(json.dumps(self.manifest(root, mask_path)), encoding="utf-8")
            audit_path.write_text(json.dumps(self.audit(root)), encoding="utf-8")
            mapping_path.write_text(json.dumps(self.label_mapping()), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-training-index",
                    str(manifest_path),
                    "--audit",
                    str(audit_path),
                    "--label-mapping",
                    str(mapping_path),
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
            line_count = len(output_path.read_text(encoding="utf-8").splitlines())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("training index written", result.stdout)
        self.assertEqual(line_count, 8)


if __name__ == "__main__":
    unittest.main()
