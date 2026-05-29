import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]

from he_wsi_generator.annotations.pipeline import build_six_class_mask_artifact
from he_wsi_generator.embeddings.embedder import CheckpointPatchEmbedder
from he_wsi_generator.io.audit import audit_manifest
from he_wsi_generator.io.readers import FixtureImageSlideReader
from he_wsi_generator.models.latent_diffusion_training import train_latent_diffusion_unet
from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.artifacts import build_prior_manifest_from_artifacts
from he_wsi_generator.priors.layout import build_layout_mask_prior_from_training_index
from he_wsi_generator.priors.pseudo_mask import build_pseudo_mask_from_manifest
from he_wsi_generator.priors.style import build_style_prior_from_training_index
from he_wsi_generator.priors.texture import build_texture_prior_from_embedding_cache
from he_wsi_generator.priors.tissue import build_wsi_tissue_overview_from_manifest
from he_wsi_generator.ui.workflow import (
    build_generation_config_from_form,
    collect_generation_job_output_summary,
    create_run_generation_job,
    load_generation_job_status,
    run_queued_generation_job,
)
from he_wsi_generator.generation.conditioning import build_generation_condition_packet


try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False


class Stage1To7RealBackendE2ETests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512] = [220, 40, 80]
        image[:, 512:] = [40, 180, 120]
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
            "dataset_id": "stage1-7-real-backend-e2e",
            "created_at": "2026-05-27T18:00:00Z",
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

    def training_config(self, root: Path, prior_manifest_path: Path, training_index_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "run_id": "stage1-7-real-backend-e2e",
            "random_seed": 17,
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
                "split": "train",
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

    def form_state(self, *, prior_manifest_path: Path, checkpoint_manifest_path: Path, output_root: Path, condition_packet_path: Path, job_root: Path) -> dict:
        return {
            "backend": "production-tile-stream",
            "prior_manifest_path": str(prior_manifest_path),
            "checkpoint_manifest_path": str(checkpoint_manifest_path),
            "output_root": str(output_root),
            "generated_id": "gen-stage1-7-real-e2e",
            "random_seed": "17",
            "anchor_preset": "fully_de_novo",
            "structure_anchor": "0.0",
            "source_wsi_id": "",
            "style_seed": "23",
            "sample_steps": "8",
            "overlap_px_40x": "64",
            "non_copy_patch_nearest_neighbor_search": False,
            "condition_packet_path": str(condition_packet_path),
            "job_root": str(job_root),
            "label_mapping_rows": [
                {"raw_label": "1", "class_name": "tissue"},
                {"raw_label": "2", "class_name": "target_pathology"},
            ],
        }

    def write_sampled_layout_mask(self, root: Path) -> Path:
        mask = np.ones((512, 512), dtype=np.uint8)
        mask[:, 256:] = 2
        mask_path = root / "sampled_layout_mask.npy"
        np.save(mask_path, mask)
        manifest_path = root / "sampled_layout_mask.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.80.0",
                    "artifact_type": "sampled_layout_mask",
                    "created_at": "2026-05-27T18:00:00Z",
                    "sample_id": "layout-stage1-7-real-e2e",
                    "random_seed": 7,
                    "mask_path": str(mask_path),
                    "mask_shape": [512, 512],
                    "class_names": [
                        "background",
                        "tissue",
                        "target_pathology",
                        "supporting_tissue",
                        "necrosis_debris",
                        "artifact",
                    ],
                    "class_pixel_counts_by_id": [0, 131072, 131072, 0, 0, 0],
                    "class_fractions_by_id": [0.0, 0.5, 0.5, 0.0, 0.0, 0.0],
                    "limitations": ["real_backend_e2e_condition_mask"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest_path

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            slide_path = self.create_fixture_slide(root)
            mask_path = root / "mask.npy"
            mask = np.ones((512, 1024), dtype=np.uint8)
            mask[:, 512:] = 2
            np.save(mask_path, mask)

            manifest = self.manifest(slide_path, mask_path)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            mapping = self.label_mapping()
            mapping_path = root / "label-mapping.json"
            mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")

            audit = audit_manifest(manifest, reader=FixtureImageSlideReader())
            audit_path = root / "audit.json"
            audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

            build_six_class_mask_artifact(
                manifest_path=manifest_path,
                audit_path=audit_path,
                label_mapping_paths=[mapping_path],
                output_dir=root / "mask-artifacts",
            )

            checkpoint_json = root / "embedder.json"
            checkpoint_json.write_text(
                json.dumps(
                    {
                        "model_id": "stage1-7-real-backend-statistical-embedder",
                        "embedding_dim": 4,
                        "normalization": "unit-test",
                    }
                ),
                encoding="utf-8",
            )
            pseudo_output = build_pseudo_mask_from_manifest(
                manifest_path=manifest_path,
                output_dir=root / "pseudo-mask",
                backend="fixture-image",
                embedder=CheckpointPatchEmbedder(checkpoint_json),
                patch_size=(256, 256),
                n_clusters=2,
            )

            training_index_path = root / "training-index.jsonl"
            build_training_index(manifest, audit, [mapping], training_index_path)

            build_wsi_tissue_overview_from_manifest(
                manifest_path,
                output_path=root / "wsi_tissue_overview.json",
                backend="fixture-image",
            )
            build_layout_mask_prior_from_training_index(
                training_index_path,
                output_path=root / "layout_mask_prior.json",
                batch_size=2,
                split="train",
                cascade_level="1/1",
            )
            build_style_prior_from_training_index(
                training_index_path,
                output_path=root / "style_prior.json",
                batch_size=2,
                split="train",
                cascade_level="1/1",
            )
            build_texture_prior_from_embedding_cache(
                cache_dir=root / "pseudo-mask" / "embedding_cache",
                cache_key="slide-001-pseudo-mask",
                cluster_report_path=pseudo_output["cluster_report_path"],
                output_path=root / "texture_prior.json",
            )

            qc_reference_path = root / "qc_reference_distribution.json"
            qc_reference_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.80.0",
                        "source": "qc_report_metric_distribution",
                        "created_at": "2026-05-27T18:00:00Z",
                        "sample_count": 1,
                        "metrics": {
                            "mask_tissue_fraction": {
                                "warning_min": 0.0,
                                "warning_max": 1.0,
                                "fail_min": 0.0,
                                "fail_max": 1.0,
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            prior_manifest = build_prior_manifest_from_artifacts(
                output_dir=root / "prior",
                prior_id="prior-stage1-7-real-e2e",
                dataset_id="stage1-7-real-backend-e2e",
                input_manifest_path=manifest_path,
                training_data_version="train-v1",
                wsi_ids=["slide-001"],
                random_seed=11,
                layout_mask_prior_path=root / "layout_mask_prior.json",
                style_prior_path=root / "style_prior.json",
                texture_prior_path=root / "texture_prior.json",
                qc_reference_distribution_path=qc_reference_path,
                wsi_tissue_overview_path=root / "wsi_tissue_overview.json",
            )

            training_config = self.training_config(
                root,
                Path(root / "prior" / "prior_manifest.json"),
                training_index_path,
            )
            checkpoint_run = train_latent_diffusion_unet(training_config)
            checkpoint_manifest_path = Path(checkpoint_run["checkpoint_manifest_path"])

            sampled_layout_mask_path = self.write_sampled_layout_mask(root)
            condition_packet_path = root / "condition_packet.json"
            build_generation_condition_packet(
                generation_config={
                    "schema_version": "v0.80.0",
                    "random_seed": 17,
                    "model_family": "latent_diffusion_unet",
                    "max_magnification": "40x",
                    "tile_size_40x": [512, 512],
                    "canvas_size_40x": [512, 512],
                    "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                    "structure_anchor": 0.0,
                    "anchor_preset": "fully_de_novo",
                    "style_seed": 23,
                    "source_wsi_id": None,
                    "sample_steps": 8,
                    "overlap_px_40x": 64,
                    "non_copy_patch_nearest_neighbor_search": False,
                },
                prior_manifest_path=Path(root / "prior" / "prior_manifest.json"),
                output_path=condition_packet_path,
                cascade_level="1/1",
                tile_origin_40x=(0, 0),
                sampled_layout_mask_path=sampled_layout_mask_path,
            )

            workflow_root = root / "generated" / "workflow"
            output_root = workflow_root / "run-artifacts"
            job_root = workflow_root / "ui_jobs"
            generation_config_path = root / "generation.json"
            form_state = self.form_state(
                prior_manifest_path=Path(root / "prior" / "prior_manifest.json"),
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                condition_packet_path=condition_packet_path,
                job_root=job_root,
            )
            generation_config = build_generation_config_from_form(form_state)
            generation_config_path.write_text(
                json.dumps(generation_config, indent=2) + "\n",
                encoding="utf-8",
            )

            record = create_run_generation_job(
                form_state,
                job_root,
                generation_config_path,
                cwd=REPO_ROOT,
            )
            completed = run_queued_generation_job(form_state)
            refreshed = load_generation_job_status(form_state)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(refreshed["status"], "completed")
            summary = collect_generation_job_output_summary(form_state)
            tile_source_manifest = json.loads(
                (output_root / "tile_source_manifest.streaming.json").read_text(encoding="utf-8")
            )

        self.assertEqual(record["status"], "queued")
        self.assertEqual(summary["generated_id"], "gen-stage1-7-real-e2e")
        self.assertIn("metadata.json", summary["outputs"]["metadata_path"])
        self.assertIn("generated.ome.tiff", summary["outputs"]["wsi_path"])
        # M16/M26 boundary: the internal latent backend now writes a tile_grid
        # entry on every cascade level so reviewers can distinguish a small
        # canvas fixture run from a slide-level tile-grid inference run.
        self.assertIn("tile_grid", tile_source_manifest)
        self.assertEqual(
            tile_source_manifest["source"],
            "internal_latent_diffusion_unet_cascade_tile_streaming_manifest",
        )
        self.assertIn(
            "stage4_latent_diffusion_checkpoint_not_full_stage5_production_validation",
            tile_source_manifest["limitations"],
        )


if __name__ == "__main__":
    unittest.main()
