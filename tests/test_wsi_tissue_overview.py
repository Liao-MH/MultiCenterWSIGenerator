import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from he_wsi_generator.priors.tissue import (
    WSITissueOverviewBuildError,
    build_wsi_tissue_overview_from_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class WSITissueOverviewTests(unittest.TestCase):
    def create_fixture_slide(self, directory: Path, tissue: bool = True) -> Path:
        slide_path = directory / "slide-001.png"
        image = Image.new("RGB", (16, 12), color=(248, 248, 248))
        if tissue:
            for x in range(4, 12):
                for y in range(3, 9):
                    image.putpixel((x, y), (150, 70, 130))
        image.save(slide_path)
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
            "schema_version": "v0.72.32",
            "dataset_id": "demo-tissue-overview",
            "created_at": "2026-05-23T16:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
                    "cancer_type": "breast_cancer",
                    "tissue_type": "breast",
                    "center_id": "center-a",
                    "split": "train",
                    "annotations": [],
                }
            ],
        }

    def test_build_wsi_tissue_overview_records_thumbnail_and_contour_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            manifest_path = root / "manifest.json"
            output_path = root / "wsi_tissue_overview.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")

            overview = build_wsi_tissue_overview_from_manifest(
                manifest_path,
                output_path=output_path,
                backend="fixture-image",
                thumbnail_max_size=(16, 16),
            )
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(overview, saved)
        self.assertEqual(overview["schema_version"], "v0.72.32")
        self.assertEqual(overview["artifact_type"], "wsi_tissue_overview")
        self.assertEqual(overview["source"]["manifest_path"], str(manifest_path))
        self.assertEqual(overview["source"]["backend"], "fixture-image")
        self.assertEqual(overview["record_count"], 1)
        record = overview["records"][0]
        self.assertEqual(record["wsi_id"], "slide-001")
        self.assertEqual(
            record["manifest"],
            {
                "split": "train",
                "cancer_type": "breast_cancer",
                "tissue_type": "breast",
                "center_id": "center-a",
                "annotation_count": 0,
            },
        )
        self.assertEqual(record["slide"]["dimensions"], [16, 12])
        self.assertEqual(record["thumbnail"]["size"], [16, 12])
        self.assertEqual(record["thumbnail"]["rgb_mean"], [223.5, 203.5, 218.5])
        self.assertEqual(record["tissue_mask_proxy"]["tissue_pixel_count"], 48)
        self.assertEqual(record["tissue_mask_proxy"]["tissue_fraction"], 0.25)
        self.assertEqual(record["tissue_mask_proxy"]["bounding_box_xywh"], [4, 3, 8, 6])
        self.assertEqual(record["tissue_mask_proxy"]["connected_component_count"], 1)
        self.assertIn("not_a_semantic_segmentation_mask", overview["limitations"])

    def test_build_wsi_tissue_overview_rejects_empty_tissue_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root, tissue=False)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")

            with self.assertRaisesRegex(WSITissueOverviewBuildError, "no tissue pixels detected"):
                build_wsi_tissue_overview_from_manifest(
                    manifest_path,
                    output_path=root / "wsi_tissue_overview.json",
                    backend="fixture-image",
                    thumbnail_max_size=(16, 16),
                )

    def test_cli_builds_wsi_tissue_overview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            manifest_path = root / "manifest.json"
            output_path = root / "wsi_tissue_overview.json"
            manifest_path.write_text(json.dumps(self.manifest(slide_path)), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-wsi-tissue-overview",
                    str(manifest_path),
                    "--backend",
                    "fixture-image",
                    "--thumbnail-max-size",
                    "16",
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
            overview = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WSI tissue overview written", result.stdout)
        self.assertEqual(overview["artifact_type"], "wsi_tissue_overview")
        self.assertEqual(overview["records"][0]["tissue_mask_proxy"]["tissue_fraction"], 0.25)


if __name__ == "__main__":
    unittest.main()
