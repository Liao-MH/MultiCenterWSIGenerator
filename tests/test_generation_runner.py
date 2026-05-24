import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = str(REPO_ROOT / "src")
if SRC_ROOT not in sys.path:
    # Worker worktrees may not be the active editable install in the shared env.
    sys.path.insert(0, SRC_ROOT)

import numpy as np
import tifffile

from he_wsi_generator.generation.executor import GenerationExecutionError, run_smoke_generation
from he_wsi_generator.generation.tiling import (
    build_resumable_tile_manifest,
    create_tile_traversal_plan,
    update_resumable_tile_manifest,
)
from he_wsi_generator.priors.artifacts import create_prior_artifact_entry, save_prior_manifest
from he_wsi_generator.schemas import validate_metadata, validate_qc_report

class GenerationRunnerTests(unittest.TestCase):
    def create_prior_manifest(self, root: Path) -> Path:
        artifacts = {}
        for name, payload in {
            "layout_mask_prior": {"area_fraction": 0.55},
            "style_prior": {"mean_rgb": [186, 126, 166]},
            "texture_prior": {"cluster_count": 3},
            "qc_reference_distribution": {
                "metrics": {
                    "mask_tissue_fraction": {
                        "warning_min": 0.95,
                        "warning_max": 1.0,
                        "fail_min": 0.9,
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
                "schema_version": "v0.72.0",
                "prior_id": "prior-smoke",
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

    def create_stratified_qc_prior_manifest(self, root: Path) -> Path:
        artifacts = {}
        for name, payload in {
            "layout_mask_prior": {"area_fraction": 0.55},
            "style_prior": {"mean_rgb": [186, 126, 166]},
            "texture_prior": {"cluster_count": 3},
            "qc_reference_distribution": {
                "stratification": {
                    "enabled": True,
                    "fields": ["metadata.cancer_type"],
                    "stratum_count": 1,
                },
                "strata": {
                    "metadata.cancer_type=breast_cancer": {
                        "group_values": {"metadata.cancer_type": "breast_cancer"},
                        "metrics": {
                            "mask_tissue_fraction": {
                                "warning_min": 0.0,
                                "warning_max": 1.0,
                                "fail_min": 0.0,
                                "fail_max": 1.0,
                            }
                        },
                    }
                },
                "metrics": {
                    "mask_tissue_fraction": {
                        "warning_min": 0.95,
                        "warning_max": 1.0,
                        "fail_min": 0.9,
                        "fail_max": 1.0,
                    }
                },
            },
        }.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            artifacts[name] = create_prior_artifact_entry(path, kind="json", metadata={})
        return save_prior_manifest(
            root,
            {
                "schema_version": "v0.72.0",
                "prior_id": "prior-smoke",
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

    def checkpoint_manifest(self, root: Path) -> Path:
        path = root / "trained-checkpoint.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.72.0",
                    "model_family": "latent_diffusion_unet",
                    "status": "trained",
                    "usable_for_inference": True,
                    "model_version": "smoke-trained-v1",
                    "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                    "tile_size_40x": [512, 512],
                }
            ),
            encoding="utf-8",
        )
        return path

    def generation_config(self, canvas_size_40x: list[int] | None = None) -> dict:
        config = {
            "schema_version": "v0.72.0",
            "random_seed": 3,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "canvas_size_40x": canvas_size_40x or [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.0,
            "anchor_preset": "fully_de_novo",
            "style_seed": 9,
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }
        return config

    def write_partial_tile_manifest(
        self,
        output_root: Path,
        config: dict,
        *,
        completed_indexes: tuple[int, ...] = (),
        failed_indexes: tuple[int, ...] = (),
    ) -> Path:
        plan = create_tile_traversal_plan(
            canvas_size_40x=config["canvas_size_40x"],
            tile_size_40x=config["tile_size_40x"],
            overlap_px_40x=config["overlap_px_40x"],
            resume_index=0,
            cascade_level="1/1",
        )
        manifest = build_resumable_tile_manifest(plan)
        tile_dir = output_root / "tiles"
        tile_dir.mkdir(parents=True, exist_ok=True)
        tile_width, tile_height = config["tile_size_40x"]
        for tile_index in completed_indexes:
            tile_path = tile_dir / f"tile-{tile_index:06d}.npy"
            np.save(
                tile_path,
                np.full((tile_height, tile_width, 3), tile_index, dtype=np.uint8),
            )
            manifest = update_resumable_tile_manifest(
                manifest,
                tile_index=tile_index,
                status="completed",
                output_path=(Path("tiles") / tile_path.name).as_posix(),
            )
        for tile_index in failed_indexes:
            manifest = update_resumable_tile_manifest(
                manifest,
                tile_index=tile_index,
                status="failed",
                error_message="unit test failed tile",
            )
        manifest_path = output_root / "tile_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def write_condition_packet(
        self,
        root: Path,
        prior_id: str = "prior-smoke",
        include_tissue_overview: bool = False,
        sampled_layout_mask_path: Path | None = None,
        sampled_policies: bool = False,
        drop_sampled_style_selected_style: bool = False,
        drop_sampled_texture_representative: bool = False,
    ) -> Path:
        path = root / "condition_packet.json"
        layout = {"source": "layout_mask_prior"}
        mask_condition = {"source": "layout_mask_prior"}
        style_condition = {
            "value": 22,
            "source": "generation_config",
        }
        texture_condition = {
            "cluster_id": 2,
            "selection_policy": "unit-test",
            "representative_embedding_index": 5,
        }
        if include_tissue_overview:
            layout["wsi_tissue_overview"] = {
                "source": "wsi_tissue_overview",
                "artifact_path": str(root / "wsi_tissue_overview.json"),
                "record_count": 1,
                "source_backend": "openslide",
                "thumbnail_max_size": [512, 512],
                        "records": [
                            {
                                "wsi_id": "slide-001",
                                "manifest": {
                                    "cancer_type": "breast_cancer",
                                    "tissue_type": "breast",
                                },
                                "tissue_fraction": 0.375,
                                "bounding_box_xywh": [8, 4, 32, 24],
                                "connected_component_count": 3,
                    }
                ],
            }
        if sampled_layout_mask_path is not None:
            sampled_manifest = json.loads(sampled_layout_mask_path.read_text(encoding="utf-8"))
            mask_condition = {
                "source": "sampled_layout_mask",
                "artifact_path": str(sampled_layout_mask_path),
                "mask_path": sampled_manifest["mask_path"],
                "sample_id": sampled_manifest["sample_id"],
                "mask_shape": sampled_manifest["mask_shape"],
                "class_names": sampled_manifest["class_names"],
                "class_pixel_counts_by_id": sampled_manifest["class_pixel_counts_by_id"],
                "class_fractions_by_id": sampled_manifest["class_fractions_by_id"],
                "mask_role": "semantic_spatial_condition",
            }
        if sampled_policies:
            style_condition = {
                "source": "sampled_style_policy",
                "value": 31,
                "artifact_path": str(root / "sampled_style_policy.json"),
                "sample_id": "style-smoke-001",
                "random_seed": 31,
                "selection_policy": "unit-test-style-policy",
                "selected_style": {
                    "tile_index": 3,
                    "sample_id": "tile-style-003",
                    "wsi_id": "slide-style-001",
                    "tile": {"x": 128, "y": 256, "level": "1/1"},
                    "mean_rgb": [121.0, 102.0, 143.0],
                },
                "rgb_statistics_reference": {
                    "global_mean_rgb": [120.5, 101.5, 142.5],
                    "global_std_rgb": [10.0, 9.0, 8.0],
                },
                "limitations": ["statistical_policy_not_trainable_style_encoder"],
            }
            texture_condition = {
                "source": "sampled_texture_policy",
                "artifact_path": str(root / "sampled_texture_policy.json"),
                "sample_id": "texture-smoke-001",
                "random_seed": 37,
                "selection_policy": "unit-test-texture-policy",
                "cluster_count": 4,
                "cluster_id": 2,
                "representative_embedding_index": 9,
                "prototype_index": 1,
                "sample_count": 12,
                "fraction": 0.25,
                "mean_embedding": [0.1, 0.2, 0.3],
                "std_embedding": [0.01, 0.02, 0.03],
                "limitations": ["statistical_policy_not_trainable_texture_codebook"],
            }
            if drop_sampled_style_selected_style:
                del style_condition["selected_style"]
            if drop_sampled_texture_representative:
                del texture_condition["representative_embedding_index"]
        path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.72.0",
                    "condition_packet_type": "generation_condition_packet",
                    "created_at": "2026-05-23T15:00:00Z",
                    "prior_manifest_path": str(root / "prior_manifest.json"),
                    "prior_id": prior_id,
                    "conditions": {
                        "layout": layout,
                        "mask": mask_condition,
                        "style_seed": style_condition,
                        "texture_token": texture_condition,
                        "coord": {
                            "cascade_level": "1/1",
                            "tile_origin_40x": [128, 256],
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

    def write_sampled_layout_mask(self, root: Path) -> Path:
        mask_path = root / "sampled_layout_mask.npy"
        manifest_path = root / "sampled_layout_mask.json"
        mask = np.zeros((512, 512), dtype=np.uint8)
        mask[64:256, 64:256] = 2
        mask[256:448, 64:256] = 3
        np.save(mask_path, mask)
        counts = [int((mask == class_id).sum()) for class_id in range(6)]
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.72.0",
                    "artifact_type": "sampled_layout_mask",
                    "created_at": "2026-05-23T16:00:00Z",
                    "sample_id": "layout-smoke-001",
                    "random_seed": 13,
                    "mask_path": str(mask_path),
                    "mask_shape": [512, 512],
                    "source": {
                        "source_type": "statistical_layout_mask_prior_sampler",
                        "layout_mask_prior_path": str(root / "layout_mask_prior.json"),
                        "wsi_tissue_overview_path": None,
                    },
                    "class_names": [
                        "background",
                        "tissue",
                        "target_pathology",
                        "supporting_tissue",
                        "necrosis_debris",
                        "artifact",
                    ],
                    "class_pixel_counts_by_id": counts,
                    "class_fractions_by_id": [round(count / mask.size, 9) for count in counts],
                    "tissue_overview_reference": None,
                    "limitations": ["statistical_layout_sampler_only"],
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_run_smoke_generation_writes_complete_output_object(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            output_root = root / "generated" / "gen-smoke"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-smoke",
            )

            metadata = validate_metadata(
                json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            )
            qc = validate_qc_report(
                json.loads(Path(result["qc_json_path"]).read_text(encoding="utf-8"))
            )
            batch_line = json.loads(Path(result["batch_index_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))
            mask = np.load(metadata["output"]["mask_path"])
            with tifffile.TiffFile(metadata["output"]["wsi_path"]) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(result["backend"], "smoke-cascade")
        self.assertEqual(metadata["generated_id"], "gen-smoke")
        self.assertEqual(metadata["generation"]["generation_backend"], "smoke-cascade")
        self.assertEqual(metadata["generation"]["tile_traversal_plan"]["tile_count"], 1)
        self.assertEqual(metadata["generation"]["tile_traversal_plan"]["completed_tile_count"], 1)
        self.assertEqual(metadata["generation"]["tile_traversal_plan"]["pending_tile_count"], 0)
        self.assertTrue(
            all(
                tile["status"] == "completed"
                for tile in metadata["generation"]["tile_traversal_plan"]["tiles"]
            )
        )
        self.assertEqual(
            metadata["generation"]["tile_traversal_plan"]["tiles"][0]["tile_origin_40x"],
            [0, 0],
        )
        self.assertEqual(run_summary["plan"]["stages"][0]["status"], "completed")
        self.assertEqual(run_summary["plan"]["tile_traversal_plan"]["completed_tile_count"], 1)
        self.assertEqual(run_summary["plan"]["tile_traversal_plan"]["pending_tile_count"], 0)
        self.assertEqual(run_summary["pyramid_report"]["write_mode"], "chunked_pyramid_write")
        self.assertIn("chunked_write_audit", run_summary["pyramid_report"])
        self.assertFalse(
            run_summary["pyramid_report"]["chunked_write_audit"]["production_streaming"]
        )
        self.assertEqual(
            run_summary["pyramid_report"]["chunked_write_audit"]["levels"][0]["chunk_shape"],
            [512, 512],
        )
        self.assertEqual(qc["overall_status"], "fail")
        self.assertEqual(batch_line["generated_id"], "gen-smoke")
        self.assertEqual(batch_line["status"], "fail")
        self.assertEqual(mask.shape, (512, 512))
        self.assertEqual(shapes, [(512, 512, 3), (128, 128, 3), (32, 32, 3), (16, 16, 3)])
        mask_metrics = {metric["name"]: metric for metric in qc["levels"]["mask_region"]["metrics"]}
        self.assertEqual(mask_metrics["mask_tissue_fraction"]["status"], "fail")
        self.assertEqual(mask_metrics["mask_tissue_fraction"]["reference"]["warning_min"], 0.95)

    def test_run_smoke_generation_writes_tile_manifests_and_disk_tiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            output_root = root / "generated" / "gen-tiles"

            result = run_smoke_generation(
                self.generation_config(canvas_size_40x=[768, 512]),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-tiles",
            )

            metadata = validate_metadata(
                json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            )
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))
            tile_manifest_path = Path(metadata["generation"]["tile_manifest_path"])
            tile_source_manifest_path = Path(metadata["generation"]["tile_source_manifest_path"])
            tile_manifest = json.loads(tile_manifest_path.read_text(encoding="utf-8"))
            tile_source_manifest = json.loads(
                tile_source_manifest_path.read_text(encoding="utf-8")
            )
            tile_file_checks = []
            for tile in tile_manifest["tiles"]:
                tile_path = tile_manifest_path.parent / tile["output_path"]
                tile_file_checks.append((tile_path.exists(), np.load(tile_path).shape))

        self.assertEqual(run_summary["plan"]["tile_manifest_path"], str(tile_manifest_path))
        self.assertEqual(
            run_summary["plan"]["tile_source_manifest_path"],
            str(tile_source_manifest_path),
        )
        self.assertEqual(
            run_summary["pyramid_report"]["streaming_contract"]["tile_source"]["manifest_path"],
            str(tile_source_manifest_path),
        )
        self.assertEqual(tile_manifest["execution_status"], "completed")
        self.assertEqual(tile_manifest["completed_tile_count"], 2)
        self.assertEqual(tile_manifest["pending_tile_count"], 0)
        self.assertEqual([tile["status"] for tile in tile_manifest["tiles"]], ["completed", "completed"])
        for exists, shape in tile_file_checks:
            self.assertTrue(exists)
            self.assertEqual(shape, (512, 512, 3))
        self.assertEqual(tile_source_manifest["expected_tile_count"], 2)
        self.assertEqual(
            tile_source_manifest["levels"],
            [{"level_index": 0, "shape": [512, 768, 3], "expected_tile_count": 2}],
        )
        self.assertEqual(
            [record["status"] for record in tile_source_manifest["tiles"]],
            ["completed", "completed"],
        )

    def test_cli_runs_smoke_generation_with_tile_streaming_writer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            config_path = root / "generation-config.json"
            output_root = root / "generated" / "gen-cli-streaming"
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
                    "smoke-cascade",
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    str(checkpoint_manifest_path),
                    "--wsi-writer",
                    "tile-streaming",
                    "--output-root",
                    str(output_root),
                    "--generated-id",
                    "gen-cli-streaming",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            metadata = json.loads((output_root / "metadata.json").read_text(encoding="utf-8"))
            run_summary = json.loads((output_root / "generation_run.json").read_text(encoding="utf-8"))
            with tifffile.TiffFile(metadata["output"]["wsi_path"]) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(metadata["generation"]["wsi_writer"], "tile-streaming")
        self.assertEqual(
            run_summary["pyramid_report"]["write_mode"],
            "tile_iterator_streaming_write",
        )
        self.assertTrue(run_summary["pyramid_report"]["production_streaming"])
        self.assertFalse(run_summary["pyramid_report"]["resume_capable"])
        self.assertEqual(run_summary["pyramid_report"]["level_count"], 4)
        self.assertEqual(
            shapes,
            [(512, 512, 3), (128, 128, 3), (32, 32, 3), (16, 16, 3)],
        )
        self.assertEqual(
            [level["shape"] for level in run_summary["pyramid_report"]["streaming_write_report"]["levels"]],
            [[512, 512, 3], [128, 128, 3], [32, 32, 3], [16, 16, 3]],
        )
        self.assertEqual(
            run_summary["pyramid_report"]["streaming_write_report"]["levels"][0]["tile_grid"],
            [1, 1],
        )

    def test_run_smoke_generation_resumes_partial_tile_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            output_root = root / "generated" / "gen-resume"
            config = self.generation_config(canvas_size_40x=[1280, 512])
            manifest_path = self.write_partial_tile_manifest(
                output_root,
                config,
                completed_indexes=(0,),
            )
            first_tile_before = np.load(output_root / "tiles" / "tile-000000.npy").copy()

            result = run_smoke_generation(
                config,
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-resume",
                resume_tile_manifest_path=manifest_path,
            )

            metadata = validate_metadata(
                json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            )
            tile_manifest_path = Path(metadata["generation"]["tile_manifest_path"])
            tile_manifest = json.loads(tile_manifest_path.read_text(encoding="utf-8"))
            first_tile_after = np.load(output_root / "tiles" / "tile-000000.npy")

        self.assertEqual(tile_manifest_path, manifest_path)
        self.assertEqual(tile_manifest["execution_status"], "completed")
        self.assertEqual(tile_manifest["completed_tile_count"], 3)
        self.assertEqual(tile_manifest["pending_tile_count"], 0)
        self.assertEqual([tile["status"] for tile in tile_manifest["tiles"]], ["completed", "completed", "completed"])
        self.assertEqual([tile["attempt_count"] for tile in tile_manifest["tiles"]], [1, 1, 1])
        np.testing.assert_array_equal(first_tile_after, first_tile_before)

    def test_run_smoke_generation_rejects_bad_resume_tile_manifests(self):
        cases = [
            ("failed", (), (0,), (), "failed"),
            ("gapped", (1,), (), (), "row-major"),
            ("missing", (0,), (), (0,), "completed tile file"),
        ]
        for name, completed, failed, missing, pattern in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    prior_manifest_path = self.create_prior_manifest(root)
                    checkpoint_manifest_path = self.checkpoint_manifest(root)
                    output_root = root / "generated" / f"gen-{name}"
                    config = self.generation_config(canvas_size_40x=[768, 512])
                    manifest_path = self.write_partial_tile_manifest(
                        output_root,
                        config,
                        completed_indexes=completed,
                        failed_indexes=failed,
                    )
                    for tile_index in missing:
                        (output_root / "tiles" / f"tile-{tile_index:06d}.npy").unlink()

                    with self.assertRaisesRegex(GenerationExecutionError, pattern):
                        run_smoke_generation(
                            config,
                            prior_manifest_path=prior_manifest_path,
                            checkpoint_manifest_path=checkpoint_manifest_path,
                            output_root=output_root,
                            generated_id=f"gen-{name}",
                            resume_tile_manifest_path=manifest_path,
                        )

    def test_run_smoke_generation_respects_canvas_size_40x(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            output_root = root / "generated" / "gen-smoke-large"

            result = run_smoke_generation(
                self.generation_config(canvas_size_40x=[768, 512]),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-smoke-large",
            )
            metadata = validate_metadata(
                json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            )
            with tifffile.TiffFile(metadata["output"]["wsi_path"]) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(metadata["generation"]["tile_traversal_plan"]["tile_count"], 2)
        self.assertEqual(
            metadata["generation"]["tile_traversal_plan"]["tiles"][1]["tile_origin_40x"],
            [448, 0],
        )
        self.assertEqual(shapes, [(512, 768, 3), (128, 192, 3), (32, 48, 3), (16, 24, 3)])

    def test_run_smoke_generation_records_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(root)
            output_root = root / "generated" / "gen-conditioned"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-conditioned",
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))

        self.assertEqual(result["condition_packet_path"], str(condition_packet_path))
        self.assertEqual(metadata["generation"]["condition_packet_path"], str(condition_packet_path))
        self.assertEqual(metadata["generation"]["condition_summary"]["texture_cluster_id"], 2)
        self.assertEqual(metadata["generation"]["condition_summary"]["style_seed_value"], 22)
        self.assertEqual(metadata["generation"]["condition_summary"]["tile_origin_40x"], [128, 256])
        self.assertEqual(run_summary["condition_packet"]["path"], str(condition_packet_path))
        self.assertEqual(run_summary["condition_packet"]["summary"]["cascade_level"], "1/1")

    def test_run_smoke_generation_records_sampled_policy_condition_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(root, sampled_policies=True)
            output_root = root / "generated" / "gen-sampled-policy"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-sampled-policy",
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))

        condition_summary = metadata["generation"]["condition_summary"]
        style_summary = condition_summary["sampled_style_policy"]
        texture_summary = condition_summary["sampled_texture_policy"]
        self.assertEqual(style_summary["source"], "sampled_style_policy")
        self.assertEqual(style_summary["sample_id"], "style-smoke-001")
        self.assertEqual(style_summary["selected_style"]["mean_rgb"], [121.0, 102.0, 143.0])
        self.assertEqual(
            style_summary["limitations"],
            ["statistical_policy_not_trainable_style_encoder"],
        )
        self.assertEqual(texture_summary["source"], "sampled_texture_policy")
        self.assertEqual(texture_summary["sample_id"], "texture-smoke-001")
        self.assertEqual(texture_summary["cluster_id"], 2)
        self.assertEqual(texture_summary["representative_embedding_index"], 9)
        self.assertEqual(texture_summary["mean_embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(
            run_summary["condition_packet"]["summary"]["sampled_style_policy"]["sample_id"],
            "style-smoke-001",
        )
        self.assertEqual(
            run_summary["condition_packet"]["summary"]["sampled_texture_policy"]["sample_id"],
            "texture-smoke-001",
        )

    def test_run_smoke_generation_rejects_invalid_sampled_policy_condition_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(
                root,
                sampled_policies=True,
                drop_sampled_style_selected_style=True,
            )

            with self.assertRaisesRegex(GenerationExecutionError, "selected_style"):
                run_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_manifest_path,
                    output_root=root / "generated" / "bad-style-policy",
                    generated_id="bad-style-policy",
                    condition_packet_path=condition_packet_path,
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(
                root,
                sampled_policies=True,
                drop_sampled_texture_representative=True,
            )

            with self.assertRaisesRegex(GenerationExecutionError, "representative_embedding_index"):
                run_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_manifest_path,
                    output_root=root / "generated" / "bad-texture-policy",
                    generated_id="bad-texture-policy",
                    condition_packet_path=condition_packet_path,
                )

    def test_run_smoke_generation_uses_condition_summary_for_stratified_qc_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_stratified_qc_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(root, include_tissue_overview=True)
            output_root = root / "generated" / "gen-stratified-qc"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-stratified-qc",
                condition_packet_path=condition_packet_path,
            )
            qc = validate_qc_report(
                json.loads(Path(result["qc_json_path"]).read_text(encoding="utf-8"))
            )

        mask_metrics = {metric["name"]: metric for metric in qc["levels"]["mask_region"]["metrics"]}
        reference = mask_metrics["mask_tissue_fraction"]["reference"]
        self.assertEqual(mask_metrics["mask_tissue_fraction"]["status"], "pass")
        self.assertEqual(reference["selection"], "stratified")
        self.assertEqual(reference["stratum_key"], "metadata.cancer_type=breast_cancer")
        self.assertEqual(reference["group_values"], {"metadata.cancer_type": "breast_cancer"})

    def test_run_smoke_generation_uses_sampled_layout_mask_condition(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            sampled_layout_mask_path = self.write_sampled_layout_mask(root)
            condition_packet_path = self.write_condition_packet(
                root,
                sampled_layout_mask_path=sampled_layout_mask_path,
            )
            output_root = root / "generated" / "gen-sampled-layout"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-sampled-layout",
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            generated_mask = np.load(metadata["output"]["mask_path"])
            source_mask = np.load(root / "sampled_layout_mask.npy")
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))

        np.testing.assert_array_equal(generated_mask, source_mask)
        self.assertEqual(
            metadata["generation"]["condition_summary"]["sampled_layout_mask"]["sample_id"],
            "layout-smoke-001",
        )
        self.assertEqual(
            run_summary["condition_packet"]["summary"]["sampled_layout_mask"]["mask_shape"],
            [512, 512],
        )

    def test_run_smoke_generation_records_sampled_layout_mask_qc_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            sampled_layout_mask_path = self.write_sampled_layout_mask(root)
            condition_packet_path = self.write_condition_packet(
                root,
                sampled_layout_mask_path=sampled_layout_mask_path,
            )
            output_root = root / "generated" / "gen-sampled-layout-qc"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-sampled-layout-qc",
                condition_packet_path=condition_packet_path,
            )
            qc = json.loads(Path(result["qc_json_path"]).read_text(encoding="utf-8"))

        metrics = {metric["name"]: metric for metric in qc["non_copy_report"]["metrics"]}
        self.assertEqual(metrics["sampled_layout_mask_match_proxy"]["status"], "pass")
        self.assertEqual(metrics["sampled_layout_mask_match_proxy"]["value"], 1.0)
        self.assertEqual(
            metrics["sampled_layout_mask_match_proxy"]["reference"]["sample_id"],
            "layout-smoke-001",
        )

    def test_run_smoke_generation_records_wsi_tissue_overview_condition_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(
                root,
                include_tissue_overview=True,
            )
            output_root = root / "generated" / "gen-conditioned-tissue"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-conditioned-tissue",
                condition_packet_path=condition_packet_path,
            )
            metadata = json.loads(Path(result["metadata_path"]).read_text(encoding="utf-8"))
            run_summary = json.loads(Path(result["generation_run_path"]).read_text(encoding="utf-8"))

        tissue_summary = metadata["generation"]["condition_summary"]["wsi_tissue_overview"]
        self.assertEqual(tissue_summary["source"], "wsi_tissue_overview")
        self.assertEqual(tissue_summary["record_count"], 1)
        self.assertEqual(tissue_summary["source_backend"], "openslide")
        self.assertEqual(tissue_summary["thumbnail_max_size"], [512, 512])
        self.assertEqual(tissue_summary["records"][0]["wsi_id"], "slide-001")
        self.assertEqual(tissue_summary["records"][0]["tissue_fraction"], 0.375)
        self.assertEqual(tissue_summary["records"][0]["bounding_box_xywh"], [8, 4, 32, 24])
        self.assertEqual(tissue_summary["records"][0]["connected_component_count"], 3)
        self.assertEqual(
            run_summary["condition_packet"]["summary"]["wsi_tissue_overview"],
            tissue_summary,
        )

    def test_run_smoke_generation_records_wsi_tissue_overview_qc_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(
                root,
                include_tissue_overview=True,
            )
            output_root = root / "generated" / "gen-conditioned-tissue-qc"

            result = run_smoke_generation(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
                generated_id="gen-conditioned-tissue-qc",
                condition_packet_path=condition_packet_path,
            )
            qc = json.loads(Path(result["qc_json_path"]).read_text(encoding="utf-8"))

        metrics = {metric["name"]: metric for metric in qc["non_copy_report"]["metrics"]}
        self.assertIn("wsi_tissue_fraction_reference_proxy", metrics)
        self.assertEqual(
            metrics["wsi_tissue_fraction_reference_proxy"]["reference"]["wsi_id"],
            "slide-001",
        )
        self.assertEqual(
            metrics["wsi_tissue_fraction_reference_proxy"]["reference"]["tissue_fraction"],
            0.375,
        )

    def test_run_smoke_generation_rejects_invalid_wsi_tissue_overview_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(
                root,
                include_tissue_overview=True,
            )
            packet = json.loads(condition_packet_path.read_text(encoding="utf-8"))
            del packet["conditions"]["layout"]["wsi_tissue_overview"]["records"][0][
                "tissue_fraction"
            ]
            condition_packet_path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(GenerationExecutionError, "tissue_fraction"):
                run_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_manifest_path,
                    output_root=root / "generated" / "gen-invalid-tissue",
                    generated_id="gen-invalid-tissue",
                    condition_packet_path=condition_packet_path,
                )

    def test_run_smoke_generation_rejects_condition_packet_prior_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(root, prior_id="other-prior")

            with self.assertRaisesRegex(GenerationExecutionError, "condition packet prior_id"):
                run_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_manifest_path,
                    output_root=root / "generated" / "gen-conditioned",
                    generated_id="gen-conditioned",
                    condition_packet_path=condition_packet_path,
                )

    def test_run_smoke_generation_rejects_untrained_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = root / "checkpoint.json"
            checkpoint_manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.72.0",
                        "model_family": "latent_diffusion_unet",
                        "status": "not_trained",
                        "usable_for_inference": False,
                        "model_version": "not-trained",
                        "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                        "tile_size_40x": [512, 512],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(GenerationExecutionError, "checkpoint is not trained"):
                run_smoke_generation(
                    self.generation_config(),
                    prior_manifest_path=prior_manifest_path,
                    checkpoint_manifest_path=checkpoint_manifest_path,
                    output_root=root / "generated",
                    generated_id="gen-smoke",
                )

    def test_cli_runs_smoke_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            config_path = root / "generation-config.json"
            output_root = root / "generated" / "gen-cli"
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
                    "smoke-cascade",
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    str(checkpoint_manifest_path),
                    "--output-root",
                    str(output_root),
                    "--generated-id",
                    "gen-cli",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            metadata_exists = (output_root / "metadata.json").exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generation run completed", result.stdout)
        self.assertTrue(metadata_exists)

    def test_cli_runs_smoke_generation_with_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            condition_packet_path = self.write_condition_packet(root)
            config_path = root / "generation-config.json"
            output_root = root / "generated" / "gen-cli-conditioned"
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
                    "smoke-cascade",
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    str(checkpoint_manifest_path),
                    "--condition-packet",
                    str(condition_packet_path),
                    "--output-root",
                    str(output_root),
                    "--generated-id",
                    "gen-cli-conditioned",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            metadata = json.loads((output_root / "metadata.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            metadata["generation"]["condition_packet_path"],
            str(condition_packet_path),
        )

    def test_cli_runs_smoke_generation_with_resume_tile_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            config = self.generation_config(canvas_size_40x=[768, 512])
            config_path = root / "generation-config.json"
            output_root = root / "generated" / "gen-cli-resume"
            manifest_path = self.write_partial_tile_manifest(
                output_root,
                config,
                completed_indexes=(0,),
            )
            config_path.write_text(json.dumps(config), encoding="utf-8")
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
                    "smoke-cascade",
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--checkpoint-manifest",
                    str(checkpoint_manifest_path),
                    "--resume-tile-manifest",
                    str(manifest_path),
                    "--output-root",
                    str(output_root),
                    "--generated-id",
                    "gen-cli-resume",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            metadata = json.loads((output_root / "metadata.json").read_text(encoding="utf-8"))
            tile_manifest = json.loads(
                Path(metadata["generation"]["tile_manifest_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tile_manifest["execution_status"], "completed")
        self.assertEqual(tile_manifest["completed_tile_count"], 2)

    def test_cli_rejects_resume_tile_manifest_for_torch_diffusion_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            config_path = root / "generation-config.json"
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
                    str(checkpoint_manifest_path),
                    "--resume-tile-manifest",
                    str(root / "tile_manifest.json"),
                    "--output-root",
                    str(root / "generated" / "gen-torch"),
                    "--generated-id",
                    "gen-torch",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--resume-tile-manifest", result.stderr)

    def test_cli_rejects_tile_streaming_writer_for_torch_diffusion_smoke(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            checkpoint_manifest_path = self.checkpoint_manifest(root)
            config_path = root / "generation-config.json"
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
                    str(checkpoint_manifest_path),
                    "--wsi-writer",
                    "tile-streaming",
                    "--output-root",
                    str(root / "generated" / "gen-torch"),
                    "--generated-id",
                    "gen-torch",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--wsi-writer tile-streaming", result.stderr)


if __name__ == "__main__":
    unittest.main()
