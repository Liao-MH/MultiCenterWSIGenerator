import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile

from he_wsi_generator.generation.executor import run_torch_diffusion_smoke_generation
import he_wsi_generator.models.torch_training as torch_training
from he_wsi_generator.models.torch_training import (
    sample_torch_diffusion_smoke_model,
    train_torch_diffusion_smoke_model,
    train_torch_smoke_model,
)
from he_wsi_generator.models.training import load_checkpoint_manifest
from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.artifacts import create_prior_artifact_entry, save_prior_manifest
from he_wsi_generator.schemas import validate_metadata, validate_qc_report


REPO_ROOT = Path(__file__).resolve().parents[1]
TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


class TorchSmokeTrainingTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512, 0] = 215
        image[:, :512, 1] = 50
        image[:, :512, 2] = 90
        image[:, 512:, 0] = 45
        image[:, 512:, 1] = 175
        image[:, 512:, 2] = 125
        Image.fromarray(image).save(slide_path)
        return slide_path

    def manifest(self, root: Path, mask_path: Path, slide_path: Path) -> dict:
        return {
            "schema_version": "v0.47.0",
            "dataset_id": "demo-training",
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
            "schema_version": "v0.47.0",
            "dataset_id": "demo-training",
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
            "schema_version": "v0.47.0",
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

    def create_prior_manifest(self, root: Path) -> Path:
        artifacts = {}
        for name, payload in {
            "layout_mask_prior": {"area_fraction": 0.55},
            "style_prior": {"mean_rgb": [186, 126, 166]},
            "texture_prior": {"cluster_count": 3},
            "qc_reference_distribution": {
                "metrics": {
                    "mask_tissue_fraction": {
                        "warning_min": 0.0,
                        "warning_max": 1.0,
                        "fail_min": 0.0,
                        "fail_max": 1.0,
                    }
                }
            },
        }.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            artifacts[name] = create_prior_artifact_entry(path, kind="json", metadata={})
        return save_prior_manifest(
            root,
            {
                "schema_version": "v0.47.0",
                "prior_id": "prior-torch-smoke",
                "created_at": "2026-05-23T13:00:00Z",
                "random_seed": 17,
                "input_data": {
                    "dataset_id": "demo",
                    "manifest_path": "inputs/manifest.json",
                    "training_data_version": "train-v1",
                    "wsi_ids": ["slide-001"],
                },
                "artifacts": artifacts,
            },
        )

    def generation_config(self) -> dict:
        return {
            "schema_version": "v0.47.0",
            "random_seed": 3,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.0,
            "anchor_preset": "fully_de_novo",
            "style_seed": 9,
            "source_wsi_id": None,
            "sample_steps": 4,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

    def write_condition_packet(self, root: Path, prior_id: str = "prior-torch-smoke") -> Path:
        path = root / "condition_packet.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.47.0",
                    "condition_packet_type": "generation_condition_packet",
                    "created_at": "2026-05-23T16:00:00Z",
                    "prior_manifest_path": str(root / "prior_manifest.json"),
                    "prior_id": prior_id,
                    "conditions": {
                        "layout": {"source": "layout_mask_prior"},
                        "mask": {"source": "layout_mask_prior"},
                        "style_seed": {"value": 19, "source": "generation_config"},
                        "texture_token": {
                            "cluster_id": 1,
                            "selection_policy": "unit-test",
                            "representative_embedding_index": 4,
                        },
                        "coord": {
                            "cascade_level": "1/1",
                            "tile_origin_40x": [0, 0],
                            "tile_size_40x": [512, 512],
                            "max_magnification": "40x",
                        },
                        "source_condition": {
                            "enabled": False,
                            "source_wsi_id": None,
                            "strength": 0.0,
                        },
                        "structure_anchor": {
                            "value": 0.0,
                            "anchor_preset": "fully_de_novo",
                            "source_condition_required": False,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def write_training_index(self, root: Path) -> Path:
        slide_path = self.create_fixture_slide(root)
        mask_path = root / "mask.npy"
        mask = np.ones((512, 1024), dtype=np.uint8)
        mask[:, 256:512] = 2
        mask[:, 512:768] = 4
        mask[:, 768:] = 5
        np.save(mask_path, mask)
        output_path = root / "training-index.jsonl"
        build_training_index(
            self.manifest(root, mask_path, slide_path),
            self.audit(slide_path),
            [self.label_mapping()],
            output_path,
        )
        return output_path

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_torch_smoke_model_writes_checkpoint_and_manifest(self):
        import torch

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)

            run = train_torch_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=2,
                learning_rate=0.01,
                random_seed=7,
            )
            manifest = load_checkpoint_manifest(run["checkpoint_manifest_path"])
            payload = torch.load(run["checkpoint_path"], map_location="cpu", weights_only=False)
            log_exists = Path(run["training_log_path"]).exists()
            checkpoint_exists = Path(run["checkpoint_path"]).exists()

        self.assertEqual(run["schema_version"], "v0.47.0")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(manifest["status"], "trained")
        self.assertFalse(manifest["usable_for_inference"])
        self.assertEqual(
            manifest["training_backend"],
            "torch-smoke-mask-conditioned-rgb-reconstructor",
        )
        self.assertEqual(manifest["target_type"], "rgb_image")
        self.assertEqual(manifest["input_channels"], 6)
        self.assertEqual(manifest["output_channels"], 3)
        self.assertEqual(manifest["batch_summary"]["image_batch_shape"], [2, 512, 512, 3])
        self.assertEqual(manifest["batch_summary"]["image_dtype"], "uint8")
        self.assertNotIn("image_batch", manifest["batch_summary"])
        self.assertTrue(log_exists)
        self.assertTrue(checkpoint_exists)
        self.assertIn("state_dict", payload)
        self.assertEqual(payload["target_type"], "rgb_image")
        self.assertEqual(payload["output_channels"], 3)
        self.assertEqual(len(run["loss_history"]), 2)
        self.assertTrue(all(math.isfinite(value) for value in run["loss_history"]))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_trains_torch_smoke_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            output_dir = root / "torch-cli-run"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "train-torch-smoke",
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--epochs",
                    "1",
                    "--learning-rate",
                    "0.01",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "checkpoint_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("torch smoke training completed", result.stdout)
        self.assertEqual(
            manifest["training_backend"],
            "torch-smoke-mask-conditioned-rgb-reconstructor",
        )
        self.assertEqual(manifest["target_type"], "rgb_image")
        self.assertEqual(manifest["batch_summary"]["image_batch_shape"], [2, 512, 512, 3])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest(self):
        import torch

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)

            run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=2,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            manifest = load_checkpoint_manifest(run["checkpoint_manifest_path"])
            payload = torch.load(run["checkpoint_path"], map_location="cpu", weights_only=False)

        self.assertEqual(run["status"], "completed")
        self.assertEqual(
            manifest["training_backend"],
            "torch-smoke-mask-conditioned-latent-diffusion",
        )
        self.assertEqual(manifest["target_type"], "diffusion_noise")
        expected_feature_names = [
            "style_seed_value_norm",
            "texture_cluster_id_norm",
            "tile_origin_x_40x_norm",
            "tile_origin_y_40x_norm",
            "cascade_level_scale",
            "source_condition_enabled",
            "structure_anchor",
        ]
        self.assertEqual(manifest["input_channels"], 20)
        self.assertEqual(manifest["output_channels"], 3)
        self.assertEqual(manifest["condition_feature_schema"]["feature_names"], expected_feature_names)
        self.assertEqual(manifest["condition_feature_schema"]["feature_count"], 7)
        self.assertEqual(manifest["training_parameters"]["condition_feature_count"], 7)
        self.assertEqual(manifest["training_parameters"]["cross_scale_condition_channels"], 3)
        self.assertEqual(manifest["training_parameters"]["loss_name"], "mse_noise_prediction")
        self.assertEqual(
            manifest["cross_scale_condition_schema"]["condition_name"],
            "previous_scale_rgb_proxy",
        )
        self.assertEqual(manifest["cross_scale_condition_schema"]["channel_count"], 3)
        self.assertEqual(
            manifest["cross_scale_condition_schema"]["spatial_injection"],
            "concat_previous_scale_rgb_proxy_channels",
        )
        self.assertEqual(
            manifest["cross_scale_condition_schema"]["training_source"],
            "real_rgb_tile_coarse_to_target_proxy",
        )
        self.assertEqual(
            manifest["cross_scale_condition_schema"]["root_cascade_policy"],
            "zero_previous_scale_condition_for_1/32",
        )
        self.assertEqual(manifest["denoiser_architecture"]["architecture"], "smoke_latent_unet")
        self.assertEqual(manifest["denoiser_architecture"]["base_channels"], 32)
        self.assertEqual(manifest["denoiser_architecture"]["bottleneck_channels"], 64)
        self.assertEqual(manifest["denoiser_architecture"]["downsample_stages"], 1)
        self.assertEqual(
            manifest["denoiser_architecture"]["skip_connections"],
            "encoder_decoder_concat",
        )
        self.assertEqual(
            manifest["denoiser_architecture"]["input_source"],
            "latent_previous_scale_mask_timestep_condition_concat",
        )
        self.assertEqual(
            manifest["denoiser_architecture"]["production_status"],
            "smoke_unet_only_not_production",
        )
        self.assertEqual(manifest["diffusion"]["scheduler"], "linear_ddpm")
        self.assertEqual(manifest["diffusion"]["timesteps"], 8)
        self.assertEqual(manifest["diffusion"]["latent_source"], "rgb_downsample_proxy")
        self.assertEqual(manifest["diffusion"]["latent_batch_shape"], [2, 3, 64, 64])
        self.assertEqual(manifest["batch_summary"]["image_batch_shape"], [2, 512, 512, 3])
        self.assertNotIn("image_batch", manifest["batch_summary"])
        self.assertEqual(payload["target_type"], "diffusion_noise")
        self.assertEqual(payload["diffusion"]["timesteps"], 8)
        self.assertEqual(payload["input_channels"], 20)
        self.assertEqual(payload["denoiser_architecture"], manifest["denoiser_architecture"])
        self.assertEqual(payload["condition_feature_schema"]["feature_names"], expected_feature_names)
        self.assertEqual(
            payload["cross_scale_condition_schema"],
            manifest["cross_scale_condition_schema"],
        )
        state_dict_keys = payload["state_dict"].keys()
        for expected_key in (
            "encoder_block",
            "downsample",
            "bottleneck",
            "upsample",
            "decoder_block",
            "output_block",
        ):
            self.assertTrue(
                any(key.startswith(expected_key) for key in state_dict_keys),
                f"missing U-Net state_dict block prefix: {expected_key}",
            )
        self.assertEqual(len(run["loss_history"]), 2)
        self.assertTrue(all(math.isfinite(value) for value in run["loss_history"]))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_trains_torch_diffusion_smoke_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            output_dir = root / "torch-diffusion-cli-run"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "train-torch-diffusion-smoke",
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--epochs",
                    "1",
                    "--learning-rate",
                    "0.01",
                    "--diffusion-timesteps",
                    "8",
                    "--latent-size",
                    "64",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "checkpoint_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("torch diffusion smoke training completed", result.stdout)
        self.assertEqual(
            manifest["training_backend"],
            "torch-smoke-mask-conditioned-latent-diffusion",
        )
        self.assertEqual(manifest["target_type"], "diffusion_noise")
        self.assertEqual(manifest["diffusion"]["latent_batch_shape"], [2, 3, 64, 64])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_torch_vae_smoke_model_writes_latent_autoencoder_manifest(self):
        import torch

        self.assertTrue(hasattr(torch_training, "train_torch_vae_smoke_model"))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)

            run = torch_training.train_torch_vae_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=2,
                learning_rate=0.01,
                random_seed=23,
                latent_channels=4,
                latent_size=64,
                kl_weight=0.0001,
            )
            manifest = load_checkpoint_manifest(run["checkpoint_manifest_path"])
            payload = torch.load(run["checkpoint_path"], map_location="cpu", weights_only=False)
            latent_preview = np.load(run["latent_preview_path"])
            reconstruction_preview = np.load(run["reconstruction_preview_path"])

        self.assertEqual(run["schema_version"], "v0.47.0")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(manifest["training_backend"], "torch-smoke-rgb-vae-latent-autoencoder")
        self.assertEqual(manifest["target_type"], "vae_rgb_reconstruction")
        self.assertEqual(manifest["latent_source"], "trainable_vae_smoke")
        self.assertEqual(manifest["latent_channels"], 4)
        self.assertEqual(manifest["latent_size"], 64)
        self.assertEqual(manifest["latent_batch_shape"], [2, 4, 64, 64])
        self.assertEqual(manifest["input_channels"], 3)
        self.assertEqual(manifest["output_channels"], 3)
        self.assertFalse(manifest["usable_for_inference"])
        self.assertEqual(manifest["training_parameters"]["kl_weight"], 0.0001)
        self.assertEqual(manifest["batch_summary"]["image_batch_shape"], [2, 512, 512, 3])
        self.assertEqual(payload["latent_source"], "trainable_vae_smoke")
        self.assertEqual(payload["latent_channels"], 4)
        self.assertEqual(payload["latent_size"], 64)
        self.assertEqual(latent_preview.shape, (2, 64, 64, 4))
        self.assertEqual(reconstruction_preview.shape, (2, 64, 64, 3))
        self.assertEqual(len(run["loss_history"]), 2)
        self.assertTrue(all(math.isfinite(value) for value in run["loss_history"]))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_trains_torch_vae_smoke_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            output_dir = root / "torch-vae-cli-run"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "train-torch-vae-smoke",
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--epochs",
                    "1",
                    "--learning-rate",
                    "0.01",
                    "--latent-channels",
                    "4",
                    "--latent-size",
                    "64",
                    "--kl-weight",
                    "0.0001",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "checkpoint_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("torch VAE smoke training completed", result.stdout)
        self.assertEqual(manifest["training_backend"], "torch-smoke-rgb-vae-latent-autoencoder")
        self.assertEqual(manifest["latent_source"], "trainable_vae_smoke")

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint(self):
        import torch

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            vae_run = torch_training.train_torch_vae_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=23,
                latent_channels=4,
                latent_size=64,
                kl_weight=0.0001,
            )

            diffusion_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=29,
                diffusion_timesteps=8,
                latent_size=64,
                vae_checkpoint_manifest_path=vae_run["checkpoint_manifest_path"],
            )
            manifest = load_checkpoint_manifest(diffusion_run["checkpoint_manifest_path"])
            payload = torch.load(
                diffusion_run["checkpoint_path"],
                map_location="cpu",
                weights_only=False,
            )

        self.assertEqual(manifest["diffusion"]["latent_source"], "trainable_vae_smoke")
        self.assertEqual(
            manifest["diffusion"]["vae_checkpoint_manifest_path"],
            vae_run["checkpoint_manifest_path"],
        )
        self.assertEqual(manifest["diffusion"]["latent_batch_shape"], [2, 4, 64, 64])
        self.assertEqual(manifest["input_channels"], 21)
        self.assertEqual(manifest["output_channels"], 4)
        self.assertEqual(manifest["denoiser_architecture"]["architecture"], "smoke_latent_unet")
        self.assertEqual(manifest["denoiser_architecture"]["input_channels"], 21)
        self.assertEqual(manifest["denoiser_architecture"]["output_channels"], 4)
        self.assertEqual(manifest["cross_scale_condition_schema"]["channel_count"], 3)
        self.assertEqual(payload["diffusion"]["latent_source"], "trainable_vae_smoke")
        self.assertEqual(payload["output_channels"], 4)
        self.assertEqual(payload["denoiser_architecture"], manifest["denoiser_architecture"])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_decodes_vae_latent_preview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            vae_run = torch_training.train_torch_vae_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=23,
                latent_channels=4,
                latent_size=64,
                kl_weight=0.0001,
            )
            diffusion_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=29,
                diffusion_timesteps=8,
                latent_size=64,
                vae_checkpoint_manifest_path=vae_run["checkpoint_manifest_path"],
            )

            sample_run = sample_torch_diffusion_smoke_model(
                checkpoint_manifest_path=diffusion_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-vae-sample",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                sample_steps=4,
                random_seed=31,
            )
            preview = np.load(sample_run["sample_preview_path"])
            manifest = json.loads(Path(sample_run["sample_manifest_path"]).read_text())

        self.assertEqual(manifest["diffusion"]["latent_source"], "trainable_vae_smoke")
        self.assertEqual(
            manifest["diffusion"]["vae_checkpoint_manifest_path"],
            vae_run["checkpoint_manifest_path"],
        )
        self.assertEqual(manifest["latent_sample_shape"], [2, 64, 64, 4])
        self.assertEqual(manifest["sample_shape"], [2, 64, 64, 3])
        self.assertEqual(preview.shape, (2, 64, 64, 3))
        self.assertEqual(preview.dtype, np.uint8)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_trains_torch_diffusion_smoke_model_with_vae_latent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            vae_run = torch_training.train_torch_vae_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-vae-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=23,
                latent_channels=4,
                latent_size=64,
                kl_weight=0.0001,
            )
            output_dir = root / "torch-diffusion-vae-cli-run"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "train-torch-diffusion-smoke",
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--epochs",
                    "1",
                    "--learning-rate",
                    "0.01",
                    "--diffusion-timesteps",
                    "8",
                    "--latent-size",
                    "64",
                    "--vae-checkpoint-manifest",
                    vae_run["checkpoint_manifest_path"],
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "checkpoint_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["diffusion"]["latent_source"], "trainable_vae_smoke")
        self.assertEqual(manifest["output_channels"], 4)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_writes_proxy_preview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )

            sample_run = sample_torch_diffusion_smoke_model(
                checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-sample",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                sample_steps=4,
                random_seed=13,
            )
            preview = np.load(sample_run["sample_preview_path"])
            manifest = json.loads(Path(sample_run["sample_manifest_path"]).read_text())

        self.assertEqual(sample_run["status"], "completed")
        self.assertEqual(
            manifest["sampling_backend"],
            "torch-smoke-mask-conditioned-latent-diffusion-sampler",
        )
        self.assertEqual(
            manifest["checkpoint_training_backend"],
            "torch-smoke-mask-conditioned-latent-diffusion",
        )
        self.assertEqual(manifest["sample_steps"], 4)
        self.assertEqual(manifest["sample_shape"], [2, 64, 64, 3])
        self.assertEqual(manifest["sample_dtype"], "uint8")
        self.assertEqual(manifest["condition_feature_source"], "default_zero")
        self.assertEqual(
            manifest["condition_feature_schema"]["feature_names"],
            [
                "style_seed_value_norm",
                "texture_cluster_id_norm",
                "tile_origin_x_40x_norm",
                "tile_origin_y_40x_norm",
                "cascade_level_scale",
                "source_condition_enabled",
                "structure_anchor",
            ],
        )
        self.assertEqual(manifest["condition_feature_vector"], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(manifest["cross_scale_condition_schema"]["channel_count"], 3)
        self.assertEqual(manifest["cross_scale_condition_source"], "default_zero_previous_scale")
        self.assertEqual(manifest["cross_scale_condition_shape"], [2, 3, 64, 64])
        self.assertNotIn("previous_scale_condition_path", manifest)
        self.assertFalse(manifest["usable_for_production"])
        self.assertNotIn("mask_batch", manifest["batch_summary"])
        self.assertEqual(preview.shape, (2, 64, 64, 3))
        self.assertEqual(preview.dtype, np.uint8)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_records_previous_scale_condition(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            previous_scale = np.zeros((2, 64, 64, 3), dtype=np.uint8)
            previous_scale[0, :, :, 0] = 128
            previous_scale_path = root / "previous-scale.npy"
            np.save(previous_scale_path, previous_scale)

            sample_run = sample_torch_diffusion_smoke_model(
                checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-sample",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                sample_steps=4,
                random_seed=13,
                previous_scale_condition_path=previous_scale_path,
            )
            manifest = json.loads(Path(sample_run["sample_manifest_path"]).read_text())

        self.assertEqual(manifest["previous_scale_condition_path"], str(previous_scale_path))
        self.assertEqual(manifest["cross_scale_condition_source"], "previous_scale_condition_path")
        self.assertEqual(manifest["cross_scale_condition_shape"], [2, 3, 64, 64])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_records_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            condition_packet_path = self.write_condition_packet(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )

            sample_run = sample_torch_diffusion_smoke_model(
                checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-sample",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                sample_steps=4,
                random_seed=13,
                condition_packet_path=condition_packet_path,
            )
            manifest = json.loads(Path(sample_run["sample_manifest_path"]).read_text())

        self.assertEqual(manifest["condition_packet_path"], str(condition_packet_path))
        self.assertEqual(manifest["condition_summary"]["style_seed_value"], 19)
        self.assertEqual(manifest["condition_summary"]["texture_cluster_id"], 1)
        self.assertEqual(manifest["condition_summary"]["cascade_level"], "1/1")
        self.assertEqual(manifest["condition_feature_source"], "condition_packet")
        self.assertEqual(manifest["condition_feature_vector"][0], 0.0019)
        self.assertEqual(manifest["condition_feature_vector"][1], 0.001)
        self.assertEqual(manifest["condition_feature_vector"][4], 1.0)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_rejects_missing_condition_feature_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            manifest_path = Path(train_run["checkpoint_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("condition_feature_schema")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(Exception, "condition_feature_schema"):
                sample_torch_diffusion_smoke_model(
                    checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                    training_index_path=index_path,
                    output_dir=root / "torch-diffusion-sample",
                    batch_size=2,
                    split="train",
                    cascade_level="1/1",
                    sample_steps=4,
                    random_seed=13,
                )

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_rejects_missing_cross_scale_condition_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            manifest_path = Path(train_run["checkpoint_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("cross_scale_condition_schema")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(Exception, "cross_scale_condition_schema"):
                sample_torch_diffusion_smoke_model(
                    checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                    training_index_path=index_path,
                    output_dir=root / "torch-diffusion-sample",
                    batch_size=2,
                    split="train",
                    cascade_level="1/1",
                    sample_steps=4,
                    random_seed=13,
                )

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_sample_torch_diffusion_smoke_model_rejects_missing_denoiser_architecture(self):
        import torch

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            manifest_path = Path(train_run["checkpoint_manifest_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            denoiser_architecture = manifest.pop("denoiser_architecture")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(Exception, "denoiser_architecture"):
                sample_torch_diffusion_smoke_model(
                    checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                    training_index_path=index_path,
                    output_dir=root / "torch-diffusion-missing-manifest-architecture",
                    batch_size=2,
                    split="train",
                    cascade_level="1/1",
                    sample_steps=4,
                    random_seed=13,
                )

            manifest["denoiser_architecture"] = denoiser_architecture
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            payload = torch.load(train_run["checkpoint_path"], map_location="cpu", weights_only=False)
            payload.pop("denoiser_architecture")
            torch.save(payload, train_run["checkpoint_path"])

            with self.assertRaisesRegex(Exception, "denoiser_architecture"):
                sample_torch_diffusion_smoke_model(
                    checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                    training_index_path=index_path,
                    output_dir=root / "torch-diffusion-missing-payload-architecture",
                    batch_size=2,
                    split="train",
                    cascade_level="1/1",
                    sample_steps=4,
                    random_seed=13,
                )

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_samples_torch_diffusion_smoke_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            output_dir = root / "torch-diffusion-cli-sample"
            previous_scale = np.zeros((2, 64, 64, 3), dtype=np.uint8)
            previous_scale[:, :, :, 1] = 96
            previous_scale_path = root / "previous-scale.npy"
            np.save(previous_scale_path, previous_scale)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "sample-torch-diffusion-smoke",
                    train_run["checkpoint_manifest_path"],
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--sample-steps",
                    "4",
                    "--previous-scale-condition",
                    str(previous_scale_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "sample_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("torch diffusion smoke sample completed", result.stdout)
        self.assertEqual(manifest["sample_shape"], [2, 64, 64, 3])
        self.assertEqual(manifest["previous_scale_condition_path"], str(previous_scale_path))
        self.assertEqual(manifest["cross_scale_condition_source"], "previous_scale_condition_path")
        self.assertFalse(manifest["usable_for_production"])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_samples_torch_diffusion_smoke_model_with_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            index_path = self.write_training_index(root)
            condition_packet_path = self.write_condition_packet(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            output_dir = root / "torch-diffusion-cli-sample"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "sample-torch-diffusion-smoke",
                    train_run["checkpoint_manifest_path"],
                    str(index_path),
                    "--output-dir",
                    str(output_dir),
                    "--batch-size",
                    "2",
                    "--split",
                    "train",
                    "--cascade-level",
                    "1/1",
                    "--sample-steps",
                    "4",
                    "--condition-packet",
                    str(condition_packet_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = json.loads((output_dir / "sample_manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["condition_packet_path"], str(condition_packet_path))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_run_torch_diffusion_smoke_generation_writes_archived_sample(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )

            result = run_torch_diffusion_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_root=root / "generated" / "gen-torch-smoke",
                generated_id="gen-torch-smoke",
                batch_size=1,
            )
            metadata = validate_metadata(
                json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            )
            qc = validate_qc_report(
                json.loads(Path(result["qc_json_path"]).read_text(encoding="utf-8"))
            )
            batch_line = json.loads(Path(result["batch_index_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))
            cascade_records = run_summary["cascade_sample_manifests"]
            sample_manifests = [
                json.loads(Path(record["sample_manifest_path"]).read_text(encoding="utf-8"))
                for record in cascade_records
            ]
            with tifffile.TiffFile(metadata["output"]["wsi_path"]) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(result["backend"], "torch-diffusion-smoke")
        self.assertEqual(metadata["generation"]["generation_backend"], "torch-diffusion-smoke")
        self.assertEqual(metadata["generation"]["model_checkpoint"], train_run["checkpoint_manifest_path"])
        self.assertEqual(qc["levels"]["wsi"]["status"], "pass")
        self.assertEqual(batch_line["generated_id"], "gen-torch-smoke")
        self.assertEqual([record["cascade_level"] for record in cascade_records], ["1/32", "1/16", "1/4", "1/1"])
        self.assertEqual(
            metadata["generation"]["cascade_sample_manifests"],
            cascade_records,
        )
        self.assertEqual(run_summary["plan"]["stages"][0]["status"], "completed")
        self.assertIn("previous_scale_rgb_proxy", run_summary["plan"]["stages"][0]["condition_inputs"])
        self.assertEqual(sample_manifests[0]["cross_scale_condition_source"], "default_zero_previous_scale")
        for index, manifest in enumerate(sample_manifests):
            self.assertEqual(manifest["sample_shape"], [1, 64, 64, 3])
            self.assertFalse(manifest["usable_for_production"])
            if index > 0:
                self.assertEqual(
                    manifest["cross_scale_condition_source"],
                    "previous_scale_condition_path",
                )
                self.assertEqual(
                    manifest["previous_scale_condition_path"],
                    sample_manifests[index - 1]["sample_preview_path"],
                )
        self.assertEqual(shapes, [(512, 512, 3), (128, 128, 3), (32, 32, 3), (16, 16, 3)])

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_run_torch_diffusion_smoke_generation_records_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            condition_packet_path = self.write_condition_packet(root)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )

            result = run_torch_diffusion_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                training_index_path=index_path,
                output_root=root / "generated" / "gen-torch-smoke",
                generated_id="gen-torch-smoke",
                batch_size=1,
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))
            cascade_records = run_summary["cascade_sample_manifests"]
            sample_manifests = [
                json.loads(Path(record["sample_manifest_path"]).read_text(encoding="utf-8"))
                for record in cascade_records
            ]

        self.assertEqual(result["condition_packet_path"], str(condition_packet_path))
        self.assertEqual(metadata["generation"]["condition_packet_path"], str(condition_packet_path))
        self.assertEqual(metadata["generation"]["condition_summary"]["texture_cluster_id"], 1)
        self.assertEqual(run_summary["condition_packet"]["summary"]["style_seed_value"], 19)
        self.assertEqual([record["cascade_level"] for record in cascade_records], ["1/32", "1/16", "1/4", "1/1"])
        for sample_manifest in sample_manifests:
            self.assertEqual(sample_manifest["condition_packet_path"], str(condition_packet_path))
            self.assertEqual(sample_manifest["condition_feature_source"], "condition_packet")
            self.assertEqual(sample_manifest["condition_feature_vector"][0], 0.0019)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_run_torch_diffusion_smoke_generation_rejects_condition_prior_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            condition_packet_path = self.write_condition_packet(root, prior_id="other-prior")
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )

            with self.assertRaisesRegex(Exception, "condition packet prior_id"):
                run_torch_diffusion_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=train_run["checkpoint_manifest_path"],
                    training_index_path=index_path,
                    output_root=root / "generated" / "gen-torch-smoke",
                    generated_id="gen-torch-smoke",
                    batch_size=1,
                    condition_packet_path=condition_packet_path,
                )

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_cli_runs_torch_diffusion_smoke_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            index_path = self.write_training_index(root)
            train_run = train_torch_diffusion_smoke_model(
                training_index_path=index_path,
                output_dir=root / "torch-diffusion-run",
                batch_size=2,
                split="train",
                cascade_level="1/1",
                epochs=1,
                learning_rate=0.01,
                random_seed=11,
                diffusion_timesteps=8,
                latent_size=64,
            )
            config_path = root / "generation-config.json"
            output_root = root / "generated" / "gen-cli-torch-smoke"
            config_path.write_text(json.dumps(self.generation_config()), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "run-generation",
                    str(config_path),
                    "--backend",
                    "torch-diffusion-smoke",
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    train_run["checkpoint_manifest_path"],
                    "--training-index",
                    str(index_path),
                    "--output-root",
                    str(output_root),
                    "--generated-id",
                    "gen-cli-torch-smoke",
                    "--batch-size",
                    "1",
                    "--condition-packet",
                    str(self.write_condition_packet(root)),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            metadata = json.loads((output_root / "metadata.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generation run completed", result.stdout)
        self.assertEqual(metadata["generation"]["generation_backend"], "torch-diffusion-smoke")
        self.assertIn("condition_packet_path", metadata["generation"])


if __name__ == "__main__":
    unittest.main()
