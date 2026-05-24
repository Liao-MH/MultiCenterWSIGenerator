import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from he_wsi_generator.io.audit import audit_manifest
from he_wsi_generator.io.readers import FixtureImageSlideReader, OpenSlideReader, WSIReadError


class WSIIOTests(unittest.TestCase):
    def create_fixture_slide(self, directory: Path) -> Path:
        slide_path = directory / "slide-001.png"
        image = Image.new("RGB", (16, 8), color=(220, 120, 180))
        image.save(slide_path)
        sidecar = {
            "mpp_x": 0.25,
            "mpp_y": 0.25,
            "max_magnification": "40x",
        }
        slide_path.with_suffix(slide_path.suffix + ".json").write_text(
            json.dumps(sidecar),
            encoding="utf-8",
        )
        return slide_path

    def test_fixture_reader_extracts_metadata_and_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = self.create_fixture_slide(Path(tmpdir))
            reader = FixtureImageSlideReader()

            metadata = reader.read_metadata(slide_path, wsi_id="slide-001")
            thumbnail = reader.read_thumbnail(slide_path, max_size=(4, 4))

        self.assertEqual(metadata.wsi_id, "slide-001")
        self.assertEqual(metadata.dimensions, (16, 8))
        self.assertEqual(metadata.level_dimensions, [(16, 8)])
        self.assertEqual(metadata.mpp_x, 0.25)
        self.assertEqual(metadata.backend, "fixture-image")
        self.assertLessEqual(thumbnail.size[0], 4)
        self.assertLessEqual(thumbnail.size[1], 4)

    def test_fixture_reader_requires_mpp_sidecar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            slide_path = Path(tmpdir) / "slide-001.png"
            Image.new("RGB", (16, 8)).save(slide_path)
            reader = FixtureImageSlideReader()

            with self.assertRaisesRegex(WSIReadError, "MPP metadata is required"):
                reader.read_metadata(slide_path, wsi_id="slide-001")

    def test_openslide_reader_reports_missing_path_before_backend_read(self):
        reader = OpenSlideReader()

        with self.assertRaisesRegex(WSIReadError, "does not exist"):
            reader.read_metadata("/missing/slide.svs", wsi_id="missing")

    def test_audit_manifest_fills_metadata_from_reader(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            slide_path = self.create_fixture_slide(tmp_path)
            manifest = {
                "schema_version": "v0.65.0",
                "dataset_id": "demo",
                "created_at": "2026-05-23T09:00:00",
                "records": [
                    {
                        "wsi_id": "slide-001",
                        "wsi_path": str(slide_path),
                        "cancer_type": "lung",
                        "split": "train",
                        "annotations": [],
                    }
                ],
            }

            audit = audit_manifest(manifest, reader=FixtureImageSlideReader())

        self.assertEqual(audit["schema_version"], "v0.65.0")
        self.assertEqual(audit["dataset_id"], "demo")
        self.assertEqual(audit["records"][0]["wsi_id"], "slide-001")
        self.assertEqual(audit["records"][0]["dimensions"], [16, 8])
        self.assertEqual(audit["records"][0]["mpp_x"], 0.25)
        self.assertEqual(audit["records"][0]["backend"], "fixture-image")

    def test_audit_manifest_records_read_errors(self):
        manifest = {
            "schema_version": "v0.65.0",
            "dataset_id": "demo",
            "created_at": "2026-05-23T09:00:00",
            "records": [
                {
                    "wsi_id": "missing",
                    "wsi_path": "/missing/slide.svs",
                    "cancer_type": "lung",
                    "split": "train",
                    "annotations": [],
                }
            ],
        }

        audit = audit_manifest(manifest, reader=FixtureImageSlideReader())

        self.assertEqual(audit["records"][0]["status"], "error")
        self.assertIn("does not exist", audit["records"][0]["error"])


if __name__ == "__main__":
    unittest.main()
