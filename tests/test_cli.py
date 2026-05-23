import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CliValidationTests(unittest.TestCase):
    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "he_wsi_generator.cli", *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_validates_generation_config_file(self):
        config = {
            "schema_version": "v0.43.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.0,
            "anchor_preset": "fully_de_novo",
            "style_seed": "auto",
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "generation-config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = self.run_cli("validate", "generation-config", str(config_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generation-config valid", result.stdout)

    def test_cli_reports_validation_error(self):
        config = {
            "schema_version": "v0.43.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": -0.1,
            "anchor_preset": "fully_de_novo",
            "style_seed": "auto",
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "generation-config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = self.run_cli("validate", "generation-config", str(config_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("structure_anchor must be between 0 and 1", result.stderr)

    def test_cli_audits_manifest_with_fixture_reader(self):
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - test environment should have Pillow
            self.skipTest(f"Pillow unavailable: {exc}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            slide_path = tmp_path / "slide-001.png"
            Image.new("RGB", (8, 4), color=(100, 100, 180)).save(slide_path)
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
            manifest = {
                "schema_version": "v0.43.0",
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
            manifest_path = tmp_path / "manifest.json"
            output_path = tmp_path / "audit.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_cli(
                "audit-manifest",
                str(manifest_path),
                "--backend",
                "fixture-image",
                "--output",
                str(output_path),
            )

            audit = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("manifest audit written", result.stdout)
        self.assertEqual(audit["records"][0]["status"], "ok")
        self.assertEqual(audit["records"][0]["dimensions"], [8, 4])


if __name__ == "__main__":
    unittest.main()
