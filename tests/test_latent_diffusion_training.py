import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.embeddings.cache import save_embedding_cache
from he_wsi_generator.models.latent_diffusion_training import (
    LatentDiffusionTrainingError,
    train_latent_diffusion_unet,
)
from he_wsi_generator.models.training import load_checkpoint_manifest
from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.artifacts import build_prior_manifest_from_artifacts
from he_wsi_generator.priors.layout import build_layout_mask_prior_from_training_index
from he_wsi_generator.priors.style import build_style_prior_from_training_index
from he_wsi_generator.priors.texture import build_texture_prior_from_embedding_cache


REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False


class LatentDiffusionTrainingTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512] = [210, 60, 100]
        image[:, 512:] = [60, 175, 125]
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
        return slide_path

    def manifest(self, slide_path: Path, mask_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "dataset_id": "demo-stage4-real-backend",
            "created_at": "2026-05-27T12:00:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
                    "center_id": "center-a",
                    "cancer_type": "breast",
                    "tissue_type": "breast",
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

    def audit(self, slide_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "dataset_id": "demo-stage4-real-backend",
            "created_at": "2026-05-27T12:00:00Z",
            "backend": "fixture-image",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
                    "status": "ok",
                    "split": "train",
                    "cancer_type": "breast",
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
            "schema_version": "v0.80.0",
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

    def write_training_index(self, root: Path) -> Path:
        slide_path = self.create_fixture_slide(root)
        mask_path = root / "mask.npy"
        mask = np.zeros((512, 1024), dtype=np.uint8)
        mask[:, :512] = 2
        mask[:, 512:] = 3
        np.save(mask_path, mask)
        output_path = root / "training-index.jsonl"
        build_training_index(
            self.manifest(slide_path, mask_path),
            self.audit(slide_path),
            [self.label_mapping()],
            output_path,
        )
        return output_path

    def write_qc_reference_distribution(self, root: Path) -> Path:
        path = root / "qc_reference_distribution.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.80.0",
                    "source": "qc_report_metric_distribution",
                    "created_at": "2026-05-27T12:00:00Z",
                    "sample_count": 1,
                    "metrics": {
                        "mask_tissue_fraction": {
                            "warning_min": 0.0,
                            "warning_max": 1.0,
                            "fail_min": 0.0,
                            "fail_max": 1.0,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def write_texture_prior(self, root: Path) -> Path:
        embeddings = np.array(
            [
                [0.1, 0.2, 0.3, 0.4],
                [0.2, 0.3, 0.4, 0.5],
                [1.0, 1.1, 1.2, 1.3],
                [1.1, 1.2, 1.3, 1.4],
            ],
            dtype=np.float32,
        )
        cache_dir = root / "embedding-cache"
        save_embedding_cache(
            cache_dir,
            "demo-texture",
            embeddings,
            {
                "model_id": "checkpoint-backed-statistical-embedder",
                "checkpoint_hash": "a" * 64,
                "embedding_dim": 4,
                "patch_count": 4,
                "embedding_backend": "statistical_patch_moments",
                "embedder_kind": "checkpoint_backed_statistical_patch_embedder",
                "production_ready": False,
                "limitations": ["statistical_patch_moments_only"],
            },
        )
        cluster_report_path = root / "cluster-report.json"
        cluster_report_path.write_text(
            json.dumps(
                {
                    "n_clusters": 2,
                    "labels": [0, 0, 1, 1],
                    "cluster_counts": {"0": 2, "1": 2},
                    "inertia": 0.12,
                    "embedding_count": 4,
                    "embedding_dim": 4,
                }
            ),
            encoding="utf-8",
        )
        output_path = root / "texture_prior.json"
        build_texture_prior_from_embedding_cache(
            cache_dir=cache_dir,
            cache_key="demo-texture",
            cluster_report_path=cluster_report_path,
            output_path=output_path,
        )
        return output_path

    def write_prior_manifest(self, root: Path, training_index_path: Path) -> Path:
        layout_path = root / "layout_mask_prior.json"
        style_path = root / "style_prior.json"
        texture_path = self.write_texture_prior(root)
        qc_reference_path = self.write_qc_reference_distribution(root)

        build_layout_mask_prior_from_training_index(
            training_index_path=training_index_path,
            output_path=layout_path,
            batch_size=2,
            split="train",
            cascade_level="1/1",
        )
        build_style_prior_from_training_index(
            training_index_path=training_index_path,
            output_path=style_path,
            batch_size=2,
            split="train",
            cascade_level="1/1",
        )
        manifest = build_prior_manifest_from_artifacts(
            output_dir=root / "prior",
            prior_id="prior-stage4-real-backend",
            dataset_id="demo-stage4-real-backend",
            input_manifest_path=root / "manifest.json",
            training_data_version="stage4-real-backend-v1",
            wsi_ids=["slide-001"],
            random_seed=17,
            layout_mask_prior_path=layout_path,
            style_prior_path=style_path,
            texture_prior_path=texture_path,
            qc_reference_distribution_path=qc_reference_path,
        )
        return Path(manifest["path"]) if "path" in manifest else root / "prior" / "prior_manifest.json"

    def training_config(self, root: Path, prior_manifest_path: Path, training_index_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "run_id": "latent-diffusion-stage4-demo",
            "random_seed": 13,
            "model_family": "latent_diffusion_unet",
            "training_backend": "latent_diffusion_unet",
            "prior_manifest_path": str(prior_manifest_path),
            "training_index_path": str(training_index_path),
            "output_dir": str(root / "training-run"),
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "tile_size_40x": [512, 512],
            "max_magnification": "40x",
            "condition_dropout": "enabled",
            "source_condition": "required_when_anchor_gt_0",
            "dataset_contract": {
                "training_index_path": str(training_index_path),
                "production_readiness_declared": True,
                "minimum_sample_count": 4,
                "sample_count": 8,
                "records_by_split": {"train": 8},
                "records_by_level": {"1/32": 2, "1/16": 2, "1/4": 2, "1/1": 2},
                "required_condition_inputs": [
                    "mask",
                    "style",
                    "texture",
                    "coord",
                    "source_condition",
                    "structure_anchor",
                ],
                "mask_class_schema": {
                    "label_encoding": "integer_index",
                    "classes": [
                        "background",
                        "tissue",
                        "target_pathology",
                        "supporting_tissue",
                        "necrosis_debris",
                        "artifact",
                    ],
                },
            },
            "training_objective_contract": {
                "objective_schema": "five_training_constraints_v1",
                "required_objectives": [
                    "diffusion_generation",
                    "semantic_mask_consistency",
                    "cross_scale_consistency",
                    "tile_seam_consistency",
                    "slide_style_consistency",
                ],
                "loss_weights": {
                    "diffusion_generation": 1.0,
                    "semantic_mask_consistency": 1.0,
                    "cross_scale_consistency": 0.5,
                    "tile_seam_consistency": 0.5,
                    "slide_style_consistency": 0.5,
                },
                "objectives_by_stage": {
                    "image_generator": [
                        "diffusion_generation",
                        "semantic_mask_consistency",
                        "cross_scale_consistency",
                    ],
                    "wsi_consistency": [
                        "cross_scale_consistency",
                        "tile_seam_consistency",
                        "slide_style_consistency",
                    ],
                },
                "qc_mapping": {
                    "diffusion_generation": [
                        "color_distribution",
                        "sharpness",
                        "texture_quality",
                    ],
                    "semantic_mask_consistency": [
                        "mask_region_validity",
                        "mask_image_semantic_alignment",
                    ],
                    "cross_scale_consistency": ["pyramid_consistency"],
                    "tile_seam_consistency": [
                        "seam_score",
                        "overlap_region_delta",
                    ],
                    "slide_style_consistency": ["slide_style_consistency"],
                },
            },
            "runtime": {
                "batch_size": 2,
                "device": "cpu",
                "latent_channels": 4,
                "latent_size": 32,
                "vae_epochs": 1,
                "image_generator_epochs": 1,
                "wsi_consistency_epochs": 1,
                "learning_rate": 0.001,
                "diffusion_timesteps": 8,
                "beta_start": 0.0001,
                "beta_end": 0.02,
            },
        }

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_latent_diffusion_unet_writes_trained_checkpoint_and_stage_execution(self):
        import torch

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            training_index_path = self.write_training_index(root)
            prior_manifest_path = self.write_prior_manifest(root, training_index_path)
            config = self.training_config(root, prior_manifest_path, training_index_path)

            run = train_latent_diffusion_unet(config)
            manifest = load_checkpoint_manifest(run["checkpoint_manifest_path"])
            payload = torch.load(run["checkpoint_path"], map_location="cpu", weights_only=False)
            training_plan = json.loads(Path(run["training_plan_path"]).read_text(encoding="utf-8"))
            log_lines = [
                json.loads(line)
                for line in Path(run["training_log_path"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(run["status"], "completed")
        self.assertEqual(manifest["training_backend"], "latent_diffusion_unet")
        self.assertEqual(manifest["target_type"], "latent_diffusion_unet_generation")
        self.assertTrue(manifest["usable_for_inference"])
        self.assertFalse(manifest["inference_contract"]["production_ready"])
        self.assertEqual(
            manifest["inference_contract"]["compatible_generation_backends"],
            ["production-tile-stream"],
        )
        self.assertEqual(
            [stage["stage"] for stage in manifest["stage_execution"]["stages"]],
            ["prior_ready", "image_generator", "wsi_consistency"],
        )
        self.assertEqual(
            [stage["status"] for stage in training_plan["stages"]],
            ["completed", "completed", "completed"],
        )
        self.assertEqual(
            [preset["name"] for preset in manifest["anchor_training"]["presets"]],
            ["low", "medium", "high"],
        )
        self.assertGreater(manifest["anchor_training"]["sample_count_by_preset"]["high"], 0)
        self.assertIn("vae", payload["model_components"])
        self.assertIn("denoiser", payload["model_components"])
        self.assertIn("mask_head", payload["model_components"])
        self.assertIn("style_target", payload["conditioning_reference"])
        self.assertIn("texture_target", payload["conditioning_reference"])
        style_target = payload["conditioning_reference"]["style_target"]
        texture_target = payload["conditioning_reference"]["texture_target"]
        self.assertEqual(
            style_target.get("prior_kind"),
            "statistical_rgb_style_prior_v1",
        )
        self.assertEqual(
            texture_target.get("prior_kind"),
            "statistical_embedding_cluster_texture_prior_v1",
        )
        self.assertIn("coverage", style_target)
        self.assertIn("coverage", texture_target)
        self.assertIn(
            "slide_level_style_seed_with_local_perturbation",
            style_target["coverage"]["uncovered_dimensions"],
        )
        self.assertIn(
            "no_sharpness_focus_plane_distribution",
            style_target["limitations"],
        )
        self.assertIn(
            "trainable_codebook",
            texture_target["coverage"]["uncovered_dimensions"],
        )
        self.assertIn(
            "no_morphology_semantic_class_label",
            texture_target["limitations"],
        )
        self.assertTrue(any(line["stage"] == "image_generator" for line in log_lines))
        self.assertTrue(any(line["stage"] == "wsi_consistency" for line in log_lines))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_trains_latent_diffusion_unet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            training_index_path = self.write_training_index(root)
            prior_manifest_path = self.write_prior_manifest(root, training_index_path)
            config_path = root / "training-config.json"
            config_path.write_text(
                json.dumps(
                    self.training_config(root, prior_manifest_path, training_index_path),
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "train-latent-diffusion-unet",
                    str(config_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((root / "training-run" / "checkpoint_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("latent diffusion training completed", result.stdout)
        self.assertEqual(manifest["training_backend"], "latent_diffusion_unet")
        self.assertEqual(manifest["target_type"], "latent_diffusion_unet_generation")

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_latent_diffusion_unet_respects_runtime_batch_size_per_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            training_index_path = self.write_training_index(root)
            prior_manifest_path = self.write_prior_manifest(root, training_index_path)
            config = self.training_config(root, prior_manifest_path, training_index_path)
            config["runtime"]["batch_size"] = 1

            run = train_latent_diffusion_unet(config)
            manifest = load_checkpoint_manifest(run["checkpoint_manifest_path"])

        self.assertEqual(
            manifest["dataset_sampling"]["batch_size_by_level"],
            {"1/32": 1, "1/16": 1, "1/4": 1, "1/1": 1},
        )


if __name__ == "__main__":
    unittest.main()
