import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.models.training import (
    ModelRunError,
    create_training_run,
    load_checkpoint_manifest,
)
from he_wsi_generator.generation.planner import create_generation_plan
from he_wsi_generator.priors.artifacts import create_prior_artifact_entry, save_prior_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]


class ModelGenerationSkeletonTests(unittest.TestCase):
    def create_prior_manifest(self, root: Path) -> Path:
        artifacts = {}
        for name in (
            "layout_mask_prior",
            "style_prior",
            "texture_prior",
            "qc_reference_distribution",
        ):
            path = root / f"{name}.json"
            path.write_text(json.dumps({"name": name}), encoding="utf-8")
            artifacts[name] = create_prior_artifact_entry(path, kind="json", metadata={})
        manifest = {
            "schema_version": "v0.65.1",
            "prior_id": "prior-demo",
            "created_at": "2026-05-23T11:00:00Z",
            "random_seed": 11,
            "input_data": {
                "dataset_id": "demo",
                "manifest_path": "inputs/manifest.json",
                "training_data_version": "train-v1",
                "wsi_ids": ["slide-001"],
            },
            "artifacts": artifacts,
        }
        return save_prior_manifest(root, manifest)

    def training_config(self, prior_manifest_path: Path, output_dir: Path) -> dict:
        return {
            "schema_version": "v0.65.1",
            "run_id": "train-demo",
            "random_seed": 11,
            "model_family": "latent_diffusion_unet",
            "prior_manifest_path": str(prior_manifest_path),
            "training_index_path": "inputs/training-index.jsonl",
            "output_dir": str(output_dir),
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "tile_size_40x": [512, 512],
            "max_magnification": "40x",
            "condition_dropout": "enabled",
            "source_condition": "required_when_anchor_gt_0",
        }

    def generation_config(self) -> dict:
        return {
            "schema_version": "v0.65.1",
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

    def test_create_training_run_writes_manifest_and_untrained_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            output_dir = root / "training-output"

            run = create_training_run(self.training_config(prior_manifest_path, output_dir))
            checkpoint = load_checkpoint_manifest(run["checkpoint_manifest_path"])

        self.assertEqual(run["schema_version"], "v0.65.1")
        self.assertEqual(run["model_family"], "latent_diffusion_unet")
        self.assertEqual(run["stages"], ["prior_ready", "image_generator", "wsi_consistency"])
        self.assertEqual(checkpoint["status"], "not_trained")
        self.assertFalse(checkpoint["usable_for_inference"])

    def test_create_training_run_rejects_missing_prior_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self.training_config(Path(tmpdir) / "missing_prior.json", Path(tmpdir) / "out")

            with self.assertRaisesRegex(ModelRunError, "prior manifest does not exist"):
                create_training_run(config)

    def test_generation_plan_rejects_untrained_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            run = create_training_run(self.training_config(prior_manifest_path, root / "out"))

            with self.assertRaisesRegex(ModelRunError, "checkpoint is not trained"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=run["checkpoint_manifest_path"],
                )

    def test_generation_plan_accepts_trained_checkpoint_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = root / "trained-checkpoint.json"
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.65.1",
                        "model_family": "latent_diffusion_unet",
                        "status": "trained",
                        "usable_for_inference": True,
                        "model_version": "unit-test",
                        "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                        "tile_size_40x": [512, 512],
                    }
                ),
                encoding="utf-8",
            )

            plan = create_generation_plan(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_path,
            )

        self.assertEqual(plan["schema_version"], "v0.65.1")
        self.assertEqual([stage["level"] for stage in plan["stages"]], ["1/32", "1/16", "1/4", "1/1"])
        self.assertEqual(plan["tile_traversal"], "row_major_with_resume_index")
        self.assertEqual(plan["tile_traversal_plan"]["tile_count"], 1)
        self.assertEqual(plan["tile_traversal_plan"]["tiles"][0]["tile_origin_40x"], [0, 0])
        self.assertEqual(plan["tile_traversal_plan"]["tiles"][0]["write_region_40x"], [0, 0, 512, 512])
        self.assertEqual(plan["write_mode"], "chunked_pyramid_write")

    def test_cli_initializes_training_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config_path = root / "training-config.json"
            output_dir = root / "training-output"
            config_path.write_text(
                json.dumps(self.training_config(prior_manifest_path, output_dir)),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "init-training-run",
                    str(config_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("training run initialized", result.stdout)

    def test_cli_writes_generation_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = root / "trained-checkpoint.json"
            generation_config_path = root / "generation-config.json"
            plan_path = root / "generation-plan.json"
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.65.1",
                        "model_family": "latent_diffusion_unet",
                        "status": "trained",
                        "usable_for_inference": True,
                        "model_version": "unit-test",
                        "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                        "tile_size_40x": [512, 512],
                    }
                ),
                encoding="utf-8",
            )
            generation_config_path.write_text(
                json.dumps(self.generation_config()),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "plan-generation",
                    str(generation_config_path),
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    str(checkpoint_path),
                    "--output",
                    str(plan_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generation plan written", result.stdout)
        self.assertEqual(plan["stages"][0]["level"], "1/32")
        self.assertEqual(plan["stages"][-1]["level"], "1/1")


if __name__ == "__main__":
    unittest.main()
