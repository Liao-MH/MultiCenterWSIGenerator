import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile

from he_wsi_generator.generation.conditioning import build_generation_condition_packet
from he_wsi_generator.generation.executor import run_production_tile_stream_generation
from he_wsi_generator.models.latent_diffusion_training import train_latent_diffusion_unet
from he_wsi_generator.models.training import load_checkpoint_manifest
from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.artifacts import build_prior_manifest_from_artifacts
from he_wsi_generator.priors.layout import build_layout_mask_prior_from_training_index
from he_wsi_generator.priors.style import build_style_prior_from_training_index
from he_wsi_generator.priors.texture import build_texture_prior_from_embedding_cache
from he_wsi_generator.priors.tissue import build_wsi_tissue_overview_from_manifest
from he_wsi_generator.embeddings.cache import save_embedding_cache


try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    TORCH_AVAILABLE = False


class ProductionLatentGenerationTests(unittest.TestCase):
    def create_fixture_slide(self, root: Path) -> Path:
        slide_path = root / "slide-001.png"
        image = np.zeros((512, 1024, 3), dtype=np.uint8)
        image[:, :512] = [210, 60, 110]
        image[:, 512:] = [65, 175, 125]
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
            "dataset_id": "production-latent-generation",
            "created_at": "2026-05-27T16:00:00Z",
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
            "dataset_id": "production-latent-generation",
            "created_at": "2026-05-27T16:00:00Z",
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

    def write_qc_reference_distribution(self, root: Path) -> Path:
        path = root / "qc_reference_distribution.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.80.0",
                    "source": "qc_report_metric_distribution",
                    "created_at": "2026-05-27T16:00:00Z",
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
                    "created_at": "2026-05-27T16:00:00Z",
                    "sample_id": "layout-001",
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
                    "limitations": ["test_condition_mask"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def generation_config(self, *, structure_anchor: float, source_wsi_id: str | None) -> dict:
        return {
            "schema_version": "v0.80.0",
            "random_seed": 17,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "canvas_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": structure_anchor,
            "anchor_preset": "fully_de_novo" if structure_anchor <= 0.3 else "structure_preserving",
            "style_seed": 23,
            "source_wsi_id": source_wsi_id,
            "sample_steps": 8,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

    def training_config(self, root: Path, prior_manifest_path: Path, training_index_path: Path) -> dict:
        return {
            "schema_version": "v0.80.0",
            "run_id": "production-latent-checkpoint",
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

    def prepare_artifacts(self, root: Path) -> dict[str, Path]:
        slide_path = self.create_fixture_slide(root)
        mask_path = root / "mask.npy"
        mask = np.ones((512, 1024), dtype=np.uint8)
        mask[:, 512:] = 2
        np.save(mask_path, mask)
        manifest = self.manifest(slide_path, mask_path)
        audit = self.audit(slide_path)
        training_index_path = root / "training-index.jsonl"
        build_training_index(manifest, audit, [self.label_mapping()], training_index_path)
        layout_path = root / "layout_mask_prior.json"
        style_path = root / "style_prior.json"
        texture_path = self.write_texture_prior(root)
        build_layout_mask_prior_from_training_index(
            training_index_path,
            output_path=layout_path,
            batch_size=2,
            split="train",
            cascade_level="1/1",
        )
        build_style_prior_from_training_index(
            training_index_path,
            output_path=style_path,
            batch_size=2,
            split="train",
            cascade_level="1/1",
        )
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        wsi_tissue_overview_path = root / "wsi_tissue_overview.json"
        build_wsi_tissue_overview_from_manifest(
            manifest_path,
            output_path=wsi_tissue_overview_path,
            backend="fixture-image",
        )
        prior_manifest = build_prior_manifest_from_artifacts(
            output_dir=root / "prior",
            prior_id="prior-production-latent",
            dataset_id="production-latent-generation",
            input_manifest_path=manifest_path,
            training_data_version="v1",
            wsi_ids=["slide-001"],
            random_seed=11,
            layout_mask_prior_path=layout_path,
            style_prior_path=style_path,
            texture_prior_path=texture_path,
            qc_reference_distribution_path=self.write_qc_reference_distribution(root),
            wsi_tissue_overview_path=wsi_tissue_overview_path,
        )
        prior_manifest_path = Path(prior_manifest["path"]) if "path" in prior_manifest else root / "prior" / "prior_manifest.json"
        sampled_layout_mask_path = self.write_sampled_layout_mask(root)
        training_config_path = root / "training-config.json"
        training_config_path.write_text(
            json.dumps(self.training_config(root, prior_manifest_path, training_index_path), indent=2) + "\n",
            encoding="utf-8",
        )
        checkpoint_run = train_latent_diffusion_unet(
            self.training_config(root, prior_manifest_path, training_index_path)
        )
        checkpoint_manifest_path = Path(checkpoint_run["checkpoint_manifest_path"])
        return {
            "slide_path": slide_path,
            "manifest_path": manifest_path,
            "prior_manifest_path": prior_manifest_path,
            "sampled_layout_mask_path": sampled_layout_mask_path,
            "checkpoint_manifest_path": checkpoint_manifest_path,
        }

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_run_production_tile_stream_generation_with_internal_latent_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifacts = self.prepare_artifacts(root)
            condition_packet_path = root / "condition_packet.json"
            build_generation_condition_packet(
                generation_config=self.generation_config(structure_anchor=0.0, source_wsi_id=None),
                prior_manifest_path=artifacts["prior_manifest_path"],
                output_path=condition_packet_path,
                cascade_level="1/1",
                tile_origin_40x=(0, 0),
                sampled_layout_mask_path=artifacts["sampled_layout_mask_path"],
            )
            output_root = root / "generated" / "gen-production-latent"

            result = run_production_tile_stream_generation(
                self.generation_config(structure_anchor=0.0, source_wsi_id=None),
                prior_manifest_path=artifacts["prior_manifest_path"],
                checkpoint_manifest_path=artifacts["checkpoint_manifest_path"],
                output_root=output_root,
                generated_id="gen-production-latent",
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))
            diagnostics = json.loads(Path(result["diagnostics_manifest_path"]).read_text(encoding="utf-8"))
            tile_source_manifest = json.loads(
                Path(run_summary["plan"]["tile_source_manifest_path"]).read_text(encoding="utf-8")
            )
            mask = np.load(metadata["output"]["mask_path"], mmap_mode="r")
            with tifffile.TiffFile(metadata["output"]["wsi_path"]) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(result["backend"], "production-tile-stream")
        self.assertEqual(metadata["generation"]["generation_backend"], "production-tile-stream")
        self.assertEqual(
            metadata["generation"]["checkpoint_inference_contract"]["backend_type"],
            "latent_diffusion_unet_checkpoint",
        )
        self.assertFalse(
            metadata["generation"]["checkpoint_inference_contract"]["production_ready"]
        )
        self.assertEqual(
            run_summary["plan"]["production_tile_backend"]["backend_name"],
            "internal_latent_diffusion_unet",
        )
        self.assertEqual(
            tile_source_manifest["source"],
            "internal_latent_diffusion_unet_cascade_tile_streaming_manifest",
        )
        self.assertEqual(tile_source_manifest["completed_tile_count"], 4)
        self.assertEqual(tuple(mask.shape), (512, 512))
        self.assertEqual(shapes, [(512, 512, 3), (128, 128, 3), (32, 32, 3), (16, 16, 3)])
        self.assertTrue(diagnostics["writer_summary"]["production_streaming"])
        self.assertEqual(diagnostics["backend"], "production-tile-stream")

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed in this environment")
    def test_internal_latent_generation_records_real_source_conditioning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifacts = self.prepare_artifacts(root)
            output_root_de_novo = root / "generated" / "de-novo"
            output_root_source = root / "generated" / "source-conditioned"
            de_novo_packet = root / "condition_packet_de_novo.json"
            source_packet = root / "condition_packet_source.json"
            build_generation_condition_packet(
                generation_config=self.generation_config(structure_anchor=0.0, source_wsi_id=None),
                prior_manifest_path=artifacts["prior_manifest_path"],
                output_path=de_novo_packet,
                cascade_level="1/1",
                tile_origin_40x=(0, 0),
                sampled_layout_mask_path=artifacts["sampled_layout_mask_path"],
            )
            build_generation_condition_packet(
                generation_config=self.generation_config(structure_anchor=0.8, source_wsi_id="slide-001"),
                prior_manifest_path=artifacts["prior_manifest_path"],
                output_path=source_packet,
                cascade_level="1/1",
                tile_origin_40x=(0, 0),
                sampled_layout_mask_path=artifacts["sampled_layout_mask_path"],
            )

            de_novo = run_production_tile_stream_generation(
                self.generation_config(structure_anchor=0.0, source_wsi_id=None),
                prior_manifest_path=artifacts["prior_manifest_path"],
                checkpoint_manifest_path=artifacts["checkpoint_manifest_path"],
                output_root=output_root_de_novo,
                generated_id="gen-de-novo",
                condition_packet_path=de_novo_packet,
            )
            conditioned = run_production_tile_stream_generation(
                self.generation_config(structure_anchor=0.8, source_wsi_id="slide-001"),
                prior_manifest_path=artifacts["prior_manifest_path"],
                checkpoint_manifest_path=artifacts["checkpoint_manifest_path"],
                output_root=output_root_source,
                generated_id="gen-source",
                condition_packet_path=source_packet,
            )
            de_novo_metadata = json.loads(Path(de_novo["metadata_path"]).read_text(encoding="utf-8"))
            conditioned_metadata = json.loads(
                Path(conditioned["metadata_path"]).read_text(encoding="utf-8")
            )
            de_novo_summary = json.loads(Path(de_novo["generation_run_path"]).read_text(encoding="utf-8"))
            conditioned_summary = json.loads(
                Path(conditioned["generation_run_path"]).read_text(encoding="utf-8")
            )
            with tifffile.TiffFile(de_novo_metadata["output"]["wsi_path"]) as tiff:
                de_novo_level0 = tiff.series[0].levels[0].asarray()
            with tifffile.TiffFile(conditioned_metadata["output"]["wsi_path"]) as tiff:
                conditioned_level0 = tiff.series[0].levels[0].asarray()

        self.assertEqual(
            conditioned_summary["plan"]["cascade_generation"]["source_condition"]["mode"],
            "source_tile_rgb_model_condition_per_tile",
        )
        self.assertEqual(
            conditioned_metadata["source"]["source_wsi_path"],
            str(artifacts["slide_path"]),
        )
        self.assertEqual(conditioned_metadata["source"]["source_region"], [0, 0, 512, 512])
        self.assertFalse(np.array_equal(de_novo_level0, conditioned_level0))


if __name__ == "__main__":
    unittest.main()
