import hashlib
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
            "schema_version": "v0.72.32",
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

    def write_training_index(
        self,
        root: Path,
        *,
        records: int = 4,
        split: str = "train",
        omit_conditioning_key: str | None = None,
        mask_class_mapping: dict[str, str] | None = None,
    ) -> Path:
        path = root / "training-index.jsonl"
        lines = []
        for index in range(records):
            level = ["1/32", "1/16", "1/4", "1/1"][index % 4]
            conditioning = {
                "structure_anchor_policy": "source_condition_required_when_anchor_gt_0",
                "style_seed_source": "training_or_generation_config",
                "texture_token_source": "training_or_generation_config",
            }
            if omit_conditioning_key is not None:
                del conditioning[omit_conditioning_key]
            lines.append(
                json.dumps(
                    {
                        "schema_version": "v0.72.32",
                        "sample_id": f"sample-{index}",
                        "dataset_id": "unit-test",
                        "wsi_id": "slide-001",
                        "split": split,
                        "cascade_level": level,
                        "tile": {
                            "x": index * 512,
                            "y": 0,
                            "width": 512,
                            "height": 512,
                            "coordinate_level": 0,
                        },
                        "mask": {
                            "class_mapping": mask_class_mapping or {
                                "0": "background",
                                "1": "tissue",
                                "2": "target_pathology",
                                "3": "supporting_tissue",
                                "4": "necrosis_debris",
                                "5": "artifact",
                            }
                        },
                        "conditioning": conditioning,
                    }
                )
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def training_config(self, prior_manifest_path: Path, output_dir: Path) -> dict:
        training_index_path = self.write_training_index(output_dir.parent)
        return {
            "schema_version": "v0.72.32",
            "run_id": "train-demo",
            "random_seed": 11,
            "model_family": "latent_diffusion_unet",
            "training_backend": "latent_diffusion_unet",
            "prior_manifest_path": str(prior_manifest_path),
            "training_index_path": str(training_index_path),
            "output_dir": str(output_dir),
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "tile_size_40x": [512, 512],
            "max_magnification": "40x",
            "condition_dropout": "enabled",
            "source_condition": "required_when_anchor_gt_0",
            "dataset_contract": {
                "training_index_path": str(training_index_path),
                "production_readiness_declared": True,
                "minimum_sample_count": 4,
                "sample_count": 4,
                "records_by_split": {"train": 4},
                "records_by_level": {"1/32": 1, "1/16": 1, "1/4": 1, "1/1": 1},
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
        }

    def generation_config(self) -> dict:
        return {
            "schema_version": "v0.72.32",
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

    def checkpoint_manifest(
        self,
        root: Path,
        name: str = "trained-checkpoint",
        checkpoint_hash: str | None = None,
        write_checkpoint_file: bool = True,
        relative_checkpoint_path: bool = False,
        status: str = "trained",
        compatible_generation_backends: list[str] | None = None,
        include_model_architecture_contract: bool = True,
        include_condition_input_contract: bool = True,
    ) -> Path:
        checkpoint_file = root / f"{name}.bin"
        if write_checkpoint_file:
            checkpoint_file.write_bytes(b"unit-test checkpoint artifact\n")
        actual_hash = (
            hashlib.sha256(checkpoint_file.read_bytes()).hexdigest()
            if checkpoint_file.exists()
            else ""
        )
        manifest_path = root / f"{name}.json"
        checkpoint_path = checkpoint_file.name if relative_checkpoint_path else str(checkpoint_file)
        inference_contract = {
            "backend_type": "smoke_contract_fixture",
            "artifact_role": "generation_plan_fixture",
            "production_ready": False,
            "limitations": ["unit_test_fixture_not_production_backend"],
        }
        if compatible_generation_backends is not None:
            inference_contract["compatible_generation_backends"] = compatible_generation_backends
            if include_model_architecture_contract:
                inference_contract["model_architecture_contract"] = {
                    "model_family": "latent_diffusion_unet",
                    "architecture_name": "smoke_cascade_contract_fixture",
                    "input_space": "rgb_tile_proxy",
                    "output_space": "rgb_pyramid_tile",
                }
            if include_condition_input_contract:
                inference_contract["condition_input_contract"] = {
                    "required_condition_inputs": [
                        "mask",
                        "style_seed",
                        "texture_token",
                        "coord",
                        "structure_anchor",
                        "source_condition",
                        "previous_scale",
                    ],
                    "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                    "condition_feature_policy": "smoke_fixture_contract_only",
                }
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.72.32",
                    "model_family": "latent_diffusion_unet",
                    "status": status,
                    "usable_for_inference": True,
                    "model_version": "unit-test",
                    "training_backend": "unit-test-contract-backend",
                    "target_type": "unit_test_generation",
                    "checkpoint_path": checkpoint_path,
                    "checkpoint_sha256": checkpoint_hash or actual_hash,
                    "inference_contract": inference_contract,
                    "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                    "tile_size_40x": [512, 512],
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_create_training_run_writes_manifest_and_untrained_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            output_dir = root / "training-output"

            run = create_training_run(self.training_config(prior_manifest_path, output_dir))
            checkpoint = load_checkpoint_manifest(run["checkpoint_manifest_path"])
            training_plan = json.loads(Path(run["training_plan_path"]).read_text(encoding="utf-8"))

        self.assertEqual(run["schema_version"], "v0.72.32")
        self.assertEqual(run["model_family"], "latent_diffusion_unet")
        self.assertEqual(run["training_backend"], "latent_diffusion_unet")
        self.assertEqual(training_plan["artifact_type"], "production_training_plan")
        self.assertEqual(training_plan["implementation_status"], "plan_only_no_production_training_loop")
        self.assertEqual([stage["stage"] for stage in training_plan["stages"]], list(run["stages"]))
        self.assertEqual(
            training_plan["stages"][1]["objectives"],
            [
                "diffusion_generation",
                "semantic_mask_consistency",
                "cross_scale_consistency",
            ],
        )
        self.assertEqual(
            training_plan["stages"][2]["qc_mapping"]["tile_seam_consistency"],
            ["seam_score", "overlap_region_delta"],
        )
        self.assertEqual(checkpoint["training_plan_path"], run["training_plan_path"])
        self.assertEqual(run["dataset_contract"]["sample_count"], 4)
        self.assertEqual(
            run["training_objective_contract"]["required_objectives"],
            [
                "diffusion_generation",
                "semantic_mask_consistency",
                "cross_scale_consistency",
                "tile_seam_consistency",
                "slide_style_consistency",
            ],
        )
        self.assertEqual(run["stages"], ["prior_ready", "image_generator", "wsi_consistency"])
        self.assertEqual(checkpoint["training_backend"], "latent_diffusion_unet")
        self.assertEqual(checkpoint["target_type"], "latent_diffusion_unet_generation")
        self.assertEqual(checkpoint["dataset_contract_summary"]["sample_count"], 4)
        self.assertEqual(
            checkpoint["training_objective_contract_summary"]["loss_weights"][
                "diffusion_generation"
            ],
            1.0,
        )
        self.assertEqual(checkpoint["status"], "not_trained")
        self.assertFalse(checkpoint["usable_for_inference"])

    def test_create_training_run_rejects_missing_prior_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = self.training_config(Path(tmpdir) / "missing_prior.json", Path(tmpdir) / "out")

            with self.assertRaisesRegex(ModelRunError, "prior manifest does not exist"):
                create_training_run(config)

    def test_create_training_run_rejects_missing_dataset_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            del config["dataset_contract"]

            with self.assertRaisesRegex(ModelRunError, "dataset_contract"):
                create_training_run(config)

    def test_create_training_run_rejects_missing_training_objective_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            del config["training_objective_contract"]

            with self.assertRaisesRegex(ModelRunError, "training_objective_contract"):
                create_training_run(config)

    def test_create_training_run_rejects_training_objective_missing_loss_weight(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            del config["training_objective_contract"]["loss_weights"]["tile_seam_consistency"]

            with self.assertRaisesRegex(ModelRunError, "loss_weights.tile_seam_consistency"):
                create_training_run(config)

    def test_create_training_run_rejects_training_objective_missing_stage_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            del config["training_objective_contract"]["objectives_by_stage"]["wsi_consistency"]

            with self.assertRaisesRegex(ModelRunError, "objectives_by_stage.wsi_consistency"):
                create_training_run(config)

    def test_create_training_run_rejects_training_objective_qc_mapping_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["training_objective_contract"]["qc_mapping"]["tile_seam_consistency"] = [
                "overlap_region_delta"
            ]

            with self.assertRaisesRegex(ModelRunError, "qc_mapping.tile_seam_consistency"):
                create_training_run(config)

    def test_create_training_run_rejects_incomplete_dataset_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            del config["dataset_contract"]["records_by_level"]["1/1"]

            with self.assertRaisesRegex(ModelRunError, "dataset_contract.records_by_level"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_sample_count_below_minimum(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["sample_count"] = 3

            with self.assertRaisesRegex(ModelRunError, "dataset_contract.sample_count"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_mask_schema_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["mask_class_schema"]["classes"] = ["background"]

            with self.assertRaisesRegex(ModelRunError, "dataset_contract.mask_class_schema.classes"):
                create_training_run(config)

    def test_create_training_run_rejects_unsupported_training_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["training_backend"] = "torch-diffusion-smoke"

            with self.assertRaisesRegex(ModelRunError, "training_backend"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_training_index_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["training_index_path"] = "other/training-index.jsonl"

            with self.assertRaisesRegex(ModelRunError, "dataset_contract.training_index_path"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_without_readiness_declaration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["production_readiness_declared"] = False

            with self.assertRaisesRegex(ModelRunError, "production_readiness_declared"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_missing_condition_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["required_condition_inputs"].remove("texture")

            with self.assertRaisesRegex(ModelRunError, "required_condition_inputs missing: texture"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_missing_train_split(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["records_by_split"] = {"val": 4}

            with self.assertRaisesRegex(ModelRunError, "records_by_split.train"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_sample_count_mismatch_with_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            self.write_training_index(root, records=2)

            with self.assertRaisesRegex(ModelRunError, "sample_count"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_split_mismatch_with_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            self.write_training_index(root, split="val")

            with self.assertRaisesRegex(ModelRunError, "records_by_split"):
                create_training_run(config)

    def test_create_training_run_rejects_dataset_contract_level_mismatch_with_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            config["dataset_contract"]["records_by_level"]["1/32"] = 2
            config["dataset_contract"]["records_by_level"]["1/1"] = 0

            with self.assertRaisesRegex(ModelRunError, "records_by_level.1/1"):
                create_training_run(config)

    def test_create_training_run_rejects_training_index_missing_condition_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            self.write_training_index(root, omit_conditioning_key="texture_token_source")

            with self.assertRaisesRegex(ModelRunError, "conditioning.texture_token_source"):
                create_training_run(config)

    def test_create_training_run_rejects_training_index_mask_mapping_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config = self.training_config(prior_manifest_path, root / "out")
            self.write_training_index(root, mask_class_mapping={"0": "background"})

            with self.assertRaisesRegex(ModelRunError, "mask.class_mapping"):
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

    def test_generation_plan_rejects_thin_inference_checkpoint_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = root / "thin-trained-checkpoint.json"
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.72.32",
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

            with self.assertRaisesRegex(ModelRunError, "training_backend"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_missing_inference_checkpoint_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="missing-artifact-checkpoint",
                checkpoint_hash="0" * 64,
                write_checkpoint_file=False,
            )

            with self.assertRaisesRegex(ModelRunError, "checkpoint_path must exist"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_inference_checkpoint_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="bad-hash-checkpoint",
                checkpoint_hash="0" * 64,
            )

            with self.assertRaisesRegex(ModelRunError, "checkpoint_sha256"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_missing_inference_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="missing-contract-checkpoint",
                compatible_generation_backends=["smoke-cascade"],
            )
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            del checkpoint["inference_contract"]
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

            with self.assertRaisesRegex(ModelRunError, "inference_contract"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_checkpoint_without_compatible_generation_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(root, name="missing-compatible-backend")

            with self.assertRaisesRegex(ModelRunError, "compatible_generation_backends"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_checkpoint_without_model_architecture_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="missing-architecture-contract",
                compatible_generation_backends=["smoke-cascade"],
                include_model_architecture_contract=False,
            )

            with self.assertRaisesRegex(ModelRunError, "model_architecture_contract"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_checkpoint_missing_required_condition_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="missing-condition-input",
                compatible_generation_backends=["smoke-cascade"],
            )
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["inference_contract"]["condition_input_contract"][
                "required_condition_inputs"
            ].remove("source_condition")
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

            with self.assertRaisesRegex(ModelRunError, "condition_input_contract"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_rejects_incompatible_generation_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="incompatible-backend-checkpoint",
                compatible_generation_backends=["torch-diffusion-smoke"],
            )

            with self.assertRaisesRegex(ModelRunError, "not compatible"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                    generation_backend="smoke-cascade",
                )

    def test_generation_plan_rejects_untrained_usable_checkpoint_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="contradictory-checkpoint",
                status="not_trained",
                compatible_generation_backends=["smoke-cascade"],
            )

            with self.assertRaisesRegex(ModelRunError, "status must be trained"):
                create_generation_plan(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_path,
                )

    def test_generation_plan_accepts_relative_checkpoint_artifact_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                relative_checkpoint_path=True,
                compatible_generation_backends=["smoke-cascade"],
            )

            plan = create_generation_plan(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_path,
            )

        self.assertEqual(plan["checkpoint_manifest_path"], str(checkpoint_path))

    def test_generation_plan_accepts_trained_checkpoint_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_path = self.checkpoint_manifest(
                root,
                compatible_generation_backends=["smoke-cascade"],
            )

            plan = create_generation_plan(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_path,
            )

        self.assertEqual(plan["schema_version"], "v0.72.32")
        self.assertEqual([stage["level"] for stage in plan["stages"]], ["1/32", "1/16", "1/4", "1/1"])
        self.assertEqual(plan["tile_traversal"], "row_major_with_resume_index")
        self.assertEqual(plan["tile_traversal_plan"]["tile_count"], 1)
        self.assertEqual(plan["tile_traversal_plan"]["tiles"][0]["tile_origin_40x"], [0, 0])
        self.assertEqual(plan["tile_traversal_plan"]["tiles"][0]["write_region_40x"], [0, 0, 512, 512])
        self.assertEqual(plan["generation_backend"], "smoke-cascade")
        self.assertEqual(
            plan["checkpoint_inference_contract"]["compatible_generation_backends"],
            ["smoke-cascade"],
        )
        self.assertEqual(
            plan["checkpoint_inference_contract"]["model_architecture_contract"][
                "architecture_name"
            ],
            "smoke_cascade_contract_fixture",
        )
        self.assertEqual(
            plan["checkpoint_inference_contract"]["condition_input_contract"][
                "required_condition_inputs"
            ],
            [
                "mask",
                "style_seed",
                "texture_token",
                "coord",
                "structure_anchor",
                "source_condition",
                "previous_scale",
            ],
        )
        self.assertIn("previous_scale", plan["stages"][0]["condition_inputs"])
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
            checkpoint_path = self.checkpoint_manifest(
                root,
                name="trained-checkpoint-cli",
                compatible_generation_backends=["smoke-cascade"],
            )
            generation_config_path = root / "generation-config.json"
            plan_path = root / "generation-plan.json"
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
