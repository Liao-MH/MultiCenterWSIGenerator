import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.priors.sampler import (
    LayoutMaskSamplerError,
    sample_layout_mask_from_prior,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class LayoutMaskSamplerTests(unittest.TestCase):
    def layout_prior(self) -> dict:
        return {
            "schema_version": "v0.68.0",
            "prior_type": "layout_mask_prior",
            "created_at": "2026-05-23T15:00:00Z",
            "source": {"source_type": "unit_test"},
            "sample_count": 2,
            "class_names": [
                "background",
                "tissue",
                "target_pathology",
                "supporting_tissue",
                "necrosis_debris",
                "artifact",
            ],
            "class_fractions_by_id": [0.25, 0.5, 0.25, 0.0, 0.0, 0.0],
            "tile_layout_records": [
                {
                    "sample_id": "slide-001:0",
                    "dominant_class_id": 1,
                    "dominant_class_name": "tissue",
                    "class_fractions_by_id": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                },
                {
                    "sample_id": "slide-001:1",
                    "dominant_class_id": 2,
                    "dominant_class_name": "target_pathology",
                    "class_fractions_by_id": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                },
            ],
            "limitations": ["statistical_mask_layout_prior_only"],
        }

    def tissue_overview(self) -> dict:
        return {
            "schema_version": "v0.68.0",
            "artifact_type": "wsi_tissue_overview",
            "record_count": 1,
            "source": {
                "backend": "fixture-image",
                "thumbnail_max_size": [8, 8],
            },
            "records": [
                {
                    "wsi_id": "slide-001",
                    "tissue_mask_proxy": {
                        "thumbnail_size": [8, 4],
                        "tissue_fraction": 0.5,
                        "bounding_box_xywh": [2, 0, 4, 4],
                        "connected_component_count": 1,
                    },
                }
            ],
        }

    def test_sample_layout_mask_from_prior_writes_mask_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_path = root / "layout_mask_prior.json"
            overview_path = root / "wsi_tissue_overview.json"
            output_dir = root / "sampled-layout"
            prior_path.write_text(json.dumps(self.layout_prior()), encoding="utf-8")
            overview_path.write_text(json.dumps(self.tissue_overview()), encoding="utf-8")

            manifest = sample_layout_mask_from_prior(
                layout_mask_prior_path=prior_path,
                output_dir=output_dir,
                sample_id="layout-001",
                mask_shape=(4, 8),
                random_seed=11,
                wsi_tissue_overview_path=overview_path,
            )
            mask = np.load(manifest["mask_path"])
            saved_manifest = json.loads((output_dir / "sampled_layout_mask.json").read_text())

        self.assertEqual(manifest, saved_manifest)
        self.assertEqual(manifest["schema_version"], "v0.68.0")
        self.assertEqual(manifest["artifact_type"], "sampled_layout_mask")
        self.assertEqual(manifest["sample_id"], "layout-001")
        self.assertEqual(manifest["mask_shape"], [4, 8])
        self.assertEqual(manifest["random_seed"], 11)
        self.assertEqual(manifest["class_names"][2], "target_pathology")
        self.assertEqual(manifest["class_pixel_counts_by_id"], [16, 8, 8, 0, 0, 0])
        self.assertEqual(manifest["class_fractions_by_id"], [0.5, 0.25, 0.25, 0.0, 0.0, 0.0])
        self.assertEqual(manifest["tissue_overview_reference"]["wsi_id"], "slide-001")
        self.assertEqual(manifest["tissue_overview_reference"]["tissue_fraction"], 0.5)
        self.assertEqual(manifest["limitations"][0], "statistical_layout_sampler_only")
        self.assertEqual(mask.shape, (4, 8))
        self.assertEqual(sorted(int(value) for value in np.unique(mask).tolist()), [0, 1, 2])
        self.assertTrue(np.all(mask[:, :2] == 0))
        self.assertTrue(np.all(mask[:, 6:] == 0))

    def test_sample_layout_mask_from_prior_is_deterministic_for_seed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_path = root / "layout_mask_prior.json"
            prior_path.write_text(json.dumps(self.layout_prior()), encoding="utf-8")

            first = sample_layout_mask_from_prior(
                layout_mask_prior_path=prior_path,
                output_dir=root / "first",
                sample_id="layout-001",
                mask_shape=(4, 4),
                random_seed=5,
            )
            second = sample_layout_mask_from_prior(
                layout_mask_prior_path=prior_path,
                output_dir=root / "second",
                sample_id="layout-002",
                mask_shape=(4, 4),
                random_seed=5,
            )
            first_mask = np.load(first["mask_path"])
            second_mask = np.load(second["mask_path"])

        np.testing.assert_array_equal(first_mask, second_mask)

    def test_sample_layout_mask_from_prior_respects_background_fraction_without_tissue_overview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_path = root / "layout_mask_prior.json"
            prior_path.write_text(json.dumps(self.layout_prior()), encoding="utf-8")

            manifest = sample_layout_mask_from_prior(
                layout_mask_prior_path=prior_path,
                output_dir=root / "sampled-layout",
                sample_id="layout-001",
                mask_shape=(4, 4),
                random_seed=5,
            )
            mask = np.load(manifest["mask_path"])

        self.assertEqual(manifest["class_pixel_counts_by_id"], [4, 8, 4, 0, 0, 0])
        self.assertEqual(int((mask == 0).sum()), 4)

    def test_sample_layout_mask_from_prior_rejects_invalid_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_path = root / "layout_mask_prior.json"
            prior_path.write_text(json.dumps(self.layout_prior()), encoding="utf-8")

            with self.assertRaisesRegex(LayoutMaskSamplerError, "mask_shape"):
                sample_layout_mask_from_prior(
                    layout_mask_prior_path=prior_path,
                    output_dir=root / "sampled-layout",
                    sample_id="layout-001",
                    mask_shape=(0, 8),
                    random_seed=11,
                )

    def test_cli_samples_layout_mask(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_path = root / "layout_mask_prior.json"
            output_dir = root / "sampled-layout"
            prior_path.write_text(json.dumps(self.layout_prior()), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "sample-layout-mask",
                    str(prior_path),
                    "--output-dir",
                    str(output_dir),
                    "--sample-id",
                    "layout-cli",
                    "--height",
                    "4",
                    "--width",
                    "4",
                    "--random-seed",
                    "13",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "sampled_layout_mask.json").read_text())
            mask = np.load(output_dir / "sampled_layout_mask.npy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sampled layout mask written", result.stdout)
        self.assertEqual(manifest["sample_id"], "layout-cli")
        self.assertEqual(mask.shape, (4, 4))


if __name__ == "__main__":
    unittest.main()
