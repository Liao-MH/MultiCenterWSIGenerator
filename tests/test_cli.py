import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


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
            "schema_version": "v0.80.0",
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

    def test_cli_command_dispatcher_validates_generation_config_file(self):
        from he_wsi_generator.cli import build_parser
        from he_wsi_generator.cli_commands import run_command

        config = {
            "schema_version": "v0.80.0",
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
            args = build_parser().parse_args(["validate", "generation-config", str(config_path)])
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = run_command(args)

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertEqual(stdout.getvalue(), f"generation-config valid: {config_path}\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_reports_validation_error(self):
        config = {
            "schema_version": "v0.80.0",
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

    def test_cli_validates_generation_output_diagnostics_file(self):
        diagnostics = {
            "schema_version": "v0.80.0",
            "manifest_type": "generation_output_diagnostics",
            "generated_id": "gen-001",
            "backend": "smoke-cascade",
            "status": "completed",
            "created_at": "2026-05-25T08:00:00+00:00",
            "artifacts": {
                "wsi_path": "outputs/gen-001/generated.ome.tiff",
                "mask_path": "outputs/gen-001/generated_mask/mask.npy",
                "metadata_path": "outputs/gen-001/metadata.json",
                "qc_json_path": "outputs/gen-001/qc.json",
                "batch_index_path": "outputs/gen-001/batch.jsonl",
                "diagnostics_manifest_path": "outputs/gen-001/generation_output_diagnostics.json",
            },
            "pyramid_summary": {"write_mode": "chunked_pyramid_write"},
            "writer_summary": {
                "write_mode": "chunked_pyramid_write",
                "production_streaming": False,
                "resume_capable": False,
            },
            "tile_execution": {
                "applicable": False,
                "reason": "torch_diffusion_smoke_uses_training_batch_sampling",
            },
            "tile_source": {
                "applicable": False,
                "reason": "torch_diffusion_smoke_writes_from_sampled_pyramid_arrays",
            },
            "qc_summary": {"overall_status": "pass"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "generation_output_diagnostics.json"
            path.write_text(json.dumps(diagnostics), encoding="utf-8")

            result = self.run_cli("validate", "generation-output-diagnostics", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generation-output-diagnostics valid", result.stdout)

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
                "schema_version": "v0.80.0",
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

    def test_cli_builds_six_class_mask_summary(self):
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover
            self.skipTest(f"Pillow unavailable: {exc}")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = root / "slide-001.png"
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
            mask_path = root / "mask.npy"
            np.save(mask_path, np.array([[0, 1, 1, 0, 0, 0, 0, 0]] * 4, dtype=np.uint8))
            manifest = {
                "schema_version": "v0.80.0",
                "dataset_id": "demo",
                "created_at": "2026-05-26T10:00:00Z",
                "records": [
                    {
                        "wsi_id": "slide-001",
                        "wsi_path": str(slide_path),
                        "center_id": "center-a",
                        "cancer_type": "lung",
                        "tissue_type": "lung",
                        "split": "train",
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
            mapping = {
                "schema_version": "v0.80.0",
                "wsi_id": "slide-001",
                "source_annotation_id": "ann-001",
                "classes": {"0": "background", "1": "tissue"},
                "mapping_source": "manual",
                "confidence": {"0": "high", "1": "high"},
            }
            manifest_path = root / "manifest.json"
            audit_path = root / "audit.json"
            mapping_path = root / "mapping.json"
            output_dir = root / "mask-artifacts"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
            audit_result = self.run_cli(
                "audit-manifest",
                str(manifest_path),
                "--backend",
                "fixture-image",
                "--output",
                str(audit_path),
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stderr)

            result = self.run_cli(
                "build-six-class-mask",
                str(manifest_path),
                "--audit",
                str(audit_path),
                "--label-mapping",
                str(mapping_path),
                "--output-dir",
                str(output_dir),
            )
            summary = json.loads((output_dir / "six_class_mask_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("six-class mask summary written", result.stdout)
        self.assertEqual(summary["record_count"], 1)
        self.assertEqual(summary["records"][0]["wsi_id"], "slide-001")
        self.assertTrue(summary["records"][0]["temporary_intermediate"])
        self.assertIn("compact_provenance_summary", summary["records"][0])
        self.assertEqual(
            summary["records"][0]["compact_provenance_summary"]["annotation_pixel_counts_by_id"]["ann-001"],
            {"1": 8},
        )

    def test_cli_builds_pseudo_mask(self):
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover
            self.skipTest(f"Pillow unavailable: {exc}")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
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
            manifest = {
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
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_cli(
                "build-pseudo-mask",
                str(manifest_path),
                "--backend",
                "fixture-image",
                "--output-dir",
                str(root / "pseudo-mask"),
                "--patch-width",
                "4",
                "--patch-height",
                "4",
                "--batch-size",
                "3",
                "--n-clusters",
                "2",
            )
            pseudo_manifest = json.loads(
                (root / "pseudo-mask" / "cluster_pseudo_mask.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pseudo mask written", result.stdout)
        self.assertEqual(pseudo_manifest["annotation_type"], "cluster_pseudo_mask")
        self.assertEqual(pseudo_manifest["cluster_count"], 2)
        self.assertEqual(pseudo_manifest["batch_size"], 3)
        self.assertTrue(pseudo_manifest["streaming_patch_embedding"])
        self.assertEqual(
            pseudo_manifest["embedding_summary"]["embedding_backend"],
            "statistical_patch_moments",
        )
        self.assertIn(
            "not_a_pathology_foundation_model",
            pseudo_manifest["embedding_summary"]["limitations"],
        )


if __name__ == "__main__":
    unittest.main()
