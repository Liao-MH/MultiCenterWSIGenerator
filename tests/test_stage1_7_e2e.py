import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = str(REPO_ROOT / "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from he_wsi_generator.annotations.pipeline import build_six_class_mask_artifact
from he_wsi_generator.embeddings.embedder import FixturePatchEmbedder
from he_wsi_generator.io.audit import audit_manifest
from he_wsi_generator.io.readers import FixtureImageSlideReader
from he_wsi_generator.metadata.archive import append_batch_index
from he_wsi_generator.models.training_index import build_training_index
from he_wsi_generator.priors.artifacts import build_prior_manifest_from_artifacts
from he_wsi_generator.priors.layout import build_layout_mask_prior_from_training_index
from he_wsi_generator.priors.pseudo_mask import build_pseudo_mask_from_manifest
from he_wsi_generator.priors.style import build_style_prior_from_training_index
from he_wsi_generator.priors.texture import build_texture_prior_from_embedding_cache
from he_wsi_generator.priors.tissue import build_wsi_tissue_overview_from_manifest
from he_wsi_generator.qc.reference import build_qc_reference_distribution
from he_wsi_generator.ui.workflow import (
    build_generation_config_from_form,
    collect_generation_job_output_summary,
    create_run_generation_job,
    load_generation_job_status,
    run_queued_generation_job,
)


class Stage1To7E2ETests(unittest.TestCase):
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
            "dataset_id": "stage1-7-e2e",
            "created_at": "2026-05-26T23:30:00Z",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": str(slide_path),
                    "center_id": "center-a",
                    "cancer_type": "breast",
                    "tissue_type": "breast",
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

    def qc_reports(self) -> list[dict]:
        reports = []
        for idx, red, sharp, fraction in ((1, 100.0, 2.0, 0.50), (2, 120.0, 3.0, 0.60)):
            reports.append(
                {
                    "schema_version": "v0.80.0",
                    "generated_id": f"qc-{idx:03d}",
                    "overall_status": "pass",
                    "levels": {
                        "wsi": {
                            "status": "pass",
                            "metrics": [{"name": "mean_red", "status": "pass", "value": red}],
                        },
                        "tile": {
                            "status": "pass",
                            "metrics": [
                                {
                                    "name": "sharpness_laplacian_proxy",
                                    "status": "pass",
                                    "value": sharp,
                                }
                            ],
                        },
                        "mask_region": {
                            "status": "pass",
                            "metrics": [
                                {
                                    "name": "mask_tissue_fraction",
                                    "status": "pass",
                                    "value": fraction,
                                }
                            ],
                        },
                    },
                    "non_copy_report": {
                        "enabled": True,
                        "patch_nearest_neighbor_search": False,
                        "items": [],
                    },
                }
            )
        return reports

    def checkpoint_manifest(self, root: Path) -> Path:
        checkpoint_file = root / "trained-checkpoint.bin"
        checkpoint_file.write_bytes(b"stage1-7 e2e checkpoint artifact\n")
        checkpoint_hash = hashlib.sha256(checkpoint_file.read_bytes()).hexdigest()
        checkpoint_path = root / "trained-checkpoint.json"
        checkpoint_path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.80.0",
                    "model_family": "latent_diffusion_unet",
                    "status": "trained",
                    "usable_for_inference": True,
                    "model_version": "stage1-7-e2e-v1",
                    "training_backend": "smoke-generation-contract-fixture",
                    "target_type": "smoke_cascade_generation",
                    "checkpoint_path": str(checkpoint_file.resolve()),
                    "checkpoint_sha256": checkpoint_hash,
                    "inference_contract": {
                        "backend_type": "smoke_contract_fixture",
                        "artifact_role": "generation_runner_fixture",
                        "production_ready": False,
                        "limitations": ["smoke_fixture_not_production_backend"],
                        "compatible_generation_backends": ["smoke-cascade"],
                        "model_architecture_contract": {
                            "model_family": "latent_diffusion_unet",
                            "architecture_name": "smoke_cascade_contract_fixture",
                            "input_space": "rgb_tile_proxy",
                            "output_space": "rgb_pyramid_tile",
                        },
                        "condition_input_contract": {
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
                        },
                    },
                    "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                    "tile_size_40x": [512, 512],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return checkpoint_path

    def form_state(self, prior_manifest_path: Path, checkpoint_manifest_path: Path, output_root: Path) -> dict:
        return {
            "backend": "smoke-cascade",
            "prior_manifest_path": str(prior_manifest_path),
            "checkpoint_manifest_path": str(checkpoint_manifest_path),
            "output_root": str(output_root),
            "generated_id": "gen-stage1-7-e2e",
            "random_seed": "17",
            "anchor_preset": "fully_de_novo",
            "structure_anchor": "0.0",
            "source_wsi_id": "",
            "style_seed": "23",
            "sample_steps": "12",
            "overlap_px_40x": "32",
            "non_copy_patch_nearest_neighbor_search": False,
            "condition_packet_path": None,
            "label_mapping_rows": [
                {"raw_label": "1", "class_name": "tissue"},
                {"raw_label": "2", "class_name": "target_pathology"},
            ],
        }

    def test_stage1_to_7_fixed_e2e_entry_runs_generation_job_and_collects_summary(self):
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

            training_index_path = root / "training-index.jsonl"
            build_training_index(manifest, audit, [mapping], training_index_path)

            build_wsi_tissue_overview_from_manifest(
                manifest_path,
                output_path=root / "wsi_tissue_overview.json",
                backend="fixture-image",
            )

            pseudo_output = build_pseudo_mask_from_manifest(
                manifest_path=manifest_path,
                output_dir=root / "pseudo-mask",
                backend="fixture-image",
                embedder=FixturePatchEmbedder(),
                patch_size=(256, 256),
                n_clusters=2,
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
            build_qc_reference_distribution(
                self.qc_reports(),
                output_path=qc_reference_path,
                metric_names=[
                    "mean_red",
                    "sharpness_laplacian_proxy",
                    "mask_tissue_fraction",
                ],
            )

            prior_manifest = build_prior_manifest_from_artifacts(
                output_dir=root / "prior",
                prior_id="prior-stage1-7-e2e",
                dataset_id="stage1-7-e2e",
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

            checkpoint_manifest_path = self.checkpoint_manifest(root)
            workflow_root = root / "generated" / "workflow"
            output_root = workflow_root / "run-artifacts"
            job_root = workflow_root / "ui_jobs"
            generation_config_path = root / "generation.json"
            form_state = self.form_state(
                prior_manifest_path=Path(root / "prior" / "prior_manifest.json"),
                checkpoint_manifest_path=checkpoint_manifest_path,
                output_root=output_root,
            )
            form_state["job_root"] = str(job_root)
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

        self.assertEqual(record["status"], "queued")
        self.assertEqual(summary["generated_id"], "gen-stage1-7-e2e")
        self.assertIn("metadata.json", summary["outputs"]["metadata_path"])
        self.assertIn("generated.ome.tiff", summary["outputs"]["wsi_path"])
        self.assertIn("mask.npy", summary["outputs"]["mask_path"])
        self.assertIn("qc.json", summary["outputs"]["qc_json_path"])


if __name__ == "__main__":
    unittest.main()
