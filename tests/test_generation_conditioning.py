import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from he_wsi_generator.generation.conditioning import (
    GenerationConditionError,
    build_generation_condition_packet,
)
from he_wsi_generator.priors.artifacts import (
    build_prior_manifest_from_artifacts,
    create_prior_artifact_entry,
    save_prior_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class GenerationConditioningTests(unittest.TestCase):
    def generation_config(self, style_seed="auto", structure_anchor=0.0, source_wsi_id=None) -> dict:
        return {
            "schema_version": "v0.68.0",
            "random_seed": 7,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": structure_anchor,
            "anchor_preset": "fully_de_novo"
            if structure_anchor <= 0.3
            else "structure_preserving",
            "style_seed": style_seed,
            "source_wsi_id": source_wsi_id,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

    def write_prior_artifacts(self, root: Path) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "layout_mask_prior": {
                "schema_version": "v0.68.0",
                "prior_type": "layout_mask_prior",
                "sample_count": 2,
                "class_names": [
                    "background",
                    "tissue",
                    "target_pathology",
                    "supporting_tissue",
                    "necrosis_debris",
                    "artifact",
                ],
                "class_fractions_by_id": [0.1, 0.4, 0.2, 0.2, 0.05, 0.05],
                "non_background_fraction": 0.9,
                "adjacency_counts": {"horizontal": {"1:2": 3}, "vertical": {"2:3": 2}},
            },
            "style_prior": {
                "schema_version": "v0.68.0",
                "prior_type": "style_prior",
                "sample_count": 2,
                "rgb_statistics": {
                    "mean_rgb": [180.0, 120.0, 160.0],
                    "std_rgb": [10.0, 8.0, 9.0],
                    "mean_rgb_normalized": [0.705882353, 0.470588235, 0.62745098],
                },
            },
            "texture_prior": {
                "schema_version": "v0.68.0",
                "prior_type": "texture_prior",
                "embedding_count": 4,
                "embedding_dim": 2,
                "cluster_count": 2,
                "texture_prototypes": [
                    {
                        "cluster_id": 0,
                        "sample_count": 2,
                        "fraction": 0.5,
                        "mean_embedding": [0.1, 0.1],
                        "representative_embedding_index": 0,
                    },
                    {
                        "cluster_id": 1,
                        "sample_count": 2,
                        "fraction": 0.5,
                        "mean_embedding": [10.1, 10.1],
                        "representative_embedding_index": 2,
                    },
                ],
            },
            "qc_reference_distribution": {
                "schema_version": "v0.68.0",
                "source": "qc_report_metric_distribution",
                "sample_count": 3,
                "metrics": {
                    "mean_red": {
                        "warning_min": 100.0,
                        "warning_max": 180.0,
                        "fail_min": 20.0,
                        "fail_max": 260.0,
                        "sample_count": 3,
                    }
                },
            },
            "wsi_tissue_overview": {
                "schema_version": "v0.68.0",
                "artifact_type": "wsi_tissue_overview",
                "record_count": 2,
                "source": {
                    "backend": "openslide",
                    "thumbnail_max_size": [512, 512],
                },
                "records": [
                    {
                        "wsi_id": "slide-001",
                        "manifest": {
                            "cancer_type": "breast_cancer",
                            "tissue_type": "breast",
                            "center_id": "center-a",
                            "split": "train",
                        },
                        "tissue_mask_proxy": {
                            "tissue_fraction": 0.25,
                            "bounding_box_xywh": [4, 3, 8, 6],
                            "connected_component_count": 1,
                        },
                    },
                    {
                        "wsi_id": "slide-002",
                        "tissue_mask_proxy": {
                            "tissue_fraction": 0.5,
                            "bounding_box_xywh": [0, 0, 16, 12],
                            "connected_component_count": 2,
                        },
                    },
                ],
            },
        }
        paths = {}
        for artifact_type, payload in artifacts.items():
            path = root / f"{artifact_type}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[artifact_type] = path
        return paths

    def write_sampled_layout_mask(self, root: Path) -> Path:
        mask_path = root / "sampled_layout_mask.npy"
        manifest_path = root / "sampled_layout_mask.json"
        mask = np.zeros((8, 8), dtype=np.uint8)
        mask[2:6, 2:6] = 2
        np.save(mask_path, mask)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "v0.68.0",
                    "artifact_type": "sampled_layout_mask",
                    "created_at": "2026-05-23T16:00:00Z",
                    "sample_id": "layout-sampled-001",
                    "random_seed": 13,
                    "mask_path": str(mask_path),
                    "mask_shape": [8, 8],
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
                    "class_pixel_counts_by_id": [48, 0, 16, 0, 0, 0],
                    "class_fractions_by_id": [0.75, 0.0, 0.25, 0.0, 0.0, 0.0],
                    "tissue_overview_reference": None,
                    "limitations": ["statistical_layout_sampler_only"],
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def create_prior_manifest(self, root: Path) -> Path:
        paths = self.write_prior_artifacts(root / "artifacts")
        build_prior_manifest_from_artifacts(
            output_dir=root / "prior",
            prior_id="prior-demo",
            dataset_id="demo",
            input_manifest_path="inputs/manifest.json",
            training_data_version="train-v1",
            wsi_ids=["slide-001", "slide-002"],
            random_seed=7,
            layout_mask_prior_path=paths["layout_mask_prior"],
            style_prior_path=paths["style_prior"],
            texture_prior_path=paths["texture_prior"],
            qc_reference_distribution_path=paths["qc_reference_distribution"],
            created_at="2026-05-23T12:00:00Z",
        )
        return root / "prior" / "prior_manifest.json"

    def create_prior_manifest_with_tissue_overview(self, root: Path) -> Path:
        paths = self.write_prior_artifacts(root / "artifacts")
        build_prior_manifest_from_artifacts(
            output_dir=root / "prior",
            prior_id="prior-demo",
            dataset_id="demo",
            input_manifest_path="inputs/manifest.json",
            training_data_version="train-v1",
            wsi_ids=["slide-001", "slide-002"],
            random_seed=7,
            layout_mask_prior_path=paths["layout_mask_prior"],
            style_prior_path=paths["style_prior"],
            texture_prior_path=paths["texture_prior"],
            qc_reference_distribution_path=paths["qc_reference_distribution"],
            wsi_tissue_overview_path=paths["wsi_tissue_overview"],
            created_at="2026-05-23T12:00:00Z",
        )
        return root / "prior" / "prior_manifest.json"

    def test_build_generation_condition_packet_records_all_condition_inputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            output_path = root / "condition_packet.json"

            packet = build_generation_condition_packet(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                output_path=output_path,
                cascade_level="1/1",
                tile_origin_40x=(128, 256),
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(packet["schema_version"], "v0.68.0")
        self.assertEqual(packet["condition_packet_type"], "generation_condition_packet")
        self.assertEqual(packet["prior_id"], "prior-demo")
        self.assertEqual(written["conditions"]["coord"]["tile_origin_40x"], [128, 256])
        self.assertEqual(written["conditions"]["layout"]["non_background_fraction"], 0.9)
        self.assertEqual(written["conditions"]["mask"]["class_fractions_by_id"][2], 0.2)
        self.assertEqual(written["conditions"]["style_seed"]["value"], 7)
        self.assertEqual(
            written["conditions"]["style_seed"]["source"],
            "generation_config_auto_random_seed",
        )
        self.assertEqual(written["conditions"]["texture_token"]["cluster_id"], 1)
        self.assertEqual(
            written["conditions"]["texture_token"]["selection_policy"],
            "deterministic_random_seed_mod_cluster_count",
        )
        self.assertEqual(
            written["conditions"]["texture_token"]["representative_embedding_index"],
            2,
        )
        self.assertFalse(written["conditions"]["source_condition"]["enabled"])
        self.assertEqual(written["conditions"]["structure_anchor"]["value"], 0.0)

    def test_build_generation_condition_packet_records_wsi_tissue_overview_layout_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest_with_tissue_overview(root)
            output_path = root / "condition_packet.json"

            packet = build_generation_condition_packet(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                output_path=output_path,
                cascade_level="1/1",
                tile_origin_40x=(128, 256),
            )

        self.assertIn("wsi_tissue_overview", packet["artifact_inputs"])
        overview = packet["conditions"]["layout"]["wsi_tissue_overview"]
        self.assertEqual(overview["source"], "wsi_tissue_overview")
        self.assertEqual(overview["record_count"], 2)
        self.assertEqual(overview["source_backend"], "openslide")
        self.assertEqual(overview["thumbnail_max_size"], [512, 512])
        self.assertEqual(
            overview["records"],
            [
                {
                    "wsi_id": "slide-001",
                    "manifest": {
                        "cancer_type": "breast_cancer",
                        "tissue_type": "breast",
                        "center_id": "center-a",
                        "split": "train",
                    },
                    "tissue_fraction": 0.25,
                    "bounding_box_xywh": [4, 3, 8, 6],
                    "connected_component_count": 1,
                },
                {
                    "wsi_id": "slide-002",
                    "tissue_fraction": 0.5,
                    "bounding_box_xywh": [0, 0, 16, 12],
                    "connected_component_count": 2,
                },
            ],
        )

    def test_build_generation_condition_packet_records_sampled_layout_mask_condition(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            sampled_layout_mask_path = self.write_sampled_layout_mask(root)
            output_path = root / "condition_packet.json"

            packet = build_generation_condition_packet(
                self.generation_config(),
                prior_manifest_path=prior_manifest_path,
                output_path=output_path,
                cascade_level="1/1",
                tile_origin_40x=(0, 0),
                sampled_layout_mask_path=sampled_layout_mask_path,
            )

        mask_condition = packet["conditions"]["mask"]
        self.assertEqual(mask_condition["source"], "sampled_layout_mask")
        self.assertEqual(mask_condition["artifact_path"], str(sampled_layout_mask_path))
        self.assertEqual(mask_condition["mask_path"], str(root / "sampled_layout_mask.npy"))
        self.assertEqual(mask_condition["sample_id"], "layout-sampled-001")
        self.assertEqual(mask_condition["mask_shape"], [8, 8])
        self.assertEqual(mask_condition["class_pixel_counts_by_id"], [48, 0, 16, 0, 0, 0])
        self.assertEqual(packet["artifact_inputs"]["sampled_layout_mask"]["path"], str(sampled_layout_mask_path))

    def test_build_generation_condition_packet_preserves_integer_style_seed_and_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)

            packet = build_generation_condition_packet(
                self.generation_config(
                    style_seed=99,
                    structure_anchor=0.8,
                    source_wsi_id="slide-001",
                ),
                prior_manifest_path=prior_manifest_path,
                output_path=root / "condition_packet.json",
                cascade_level="1/4",
                tile_origin_40x=(0, 0),
            )

        self.assertEqual(packet["conditions"]["style_seed"]["value"], 99)
        self.assertEqual(packet["conditions"]["style_seed"]["source"], "generation_config")
        self.assertTrue(packet["conditions"]["source_condition"]["enabled"])
        self.assertEqual(packet["conditions"]["source_condition"]["source_wsi_id"], "slide-001")
        self.assertTrue(packet["conditions"]["structure_anchor"]["source_condition_required"])

    def test_build_generation_condition_packet_rejects_missing_texture_prototypes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = self.write_prior_artifacts(root / "artifacts")
            paths["texture_prior"].write_text(
                json.dumps(
                    {
                        "schema_version": "v0.68.0",
                        "prior_type": "texture_prior",
                        "cluster_count": 2,
                    }
                ),
                encoding="utf-8",
            )
            build_prior_manifest_from_artifacts(
                output_dir=root / "prior",
                prior_id="prior-demo",
                dataset_id="demo",
                input_manifest_path="inputs/manifest.json",
                training_data_version="train-v1",
                wsi_ids=["slide-001"],
                random_seed=7,
                layout_mask_prior_path=paths["layout_mask_prior"],
                style_prior_path=paths["style_prior"],
                texture_prior_path=paths["texture_prior"],
                qc_reference_distribution_path=paths["qc_reference_distribution"],
                created_at="2026-05-23T12:00:00Z",
            )

            with self.assertRaisesRegex(GenerationConditionError, "texture_prior.texture_prototypes"):
                build_generation_condition_packet(
                    self.generation_config(),
                    prior_manifest_path=root / "prior" / "prior_manifest.json",
                    output_path=root / "condition_packet.json",
                    cascade_level="1/1",
                    tile_origin_40x=(0, 0),
                )

    def test_build_generation_condition_packet_rejects_invalid_wsi_tissue_overview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = self.write_prior_artifacts(root / "artifacts")
            paths["wsi_tissue_overview"].write_text(
                json.dumps(
                    {
                        "schema_version": "v0.68.0",
                        "artifact_type": "not_wsi_tissue_overview",
                        "record_count": 0,
                        "source": {"backend": "openslide", "thumbnail_max_size": [512, 512]},
                        "records": [],
                    }
                ),
                encoding="utf-8",
            )
            save_prior_manifest(
                root / "prior",
                {
                    "schema_version": "v0.68.0",
                    "prior_id": "prior-demo",
                    "created_at": "2026-05-23T12:00:00Z",
                    "random_seed": 7,
                    "input_data": {
                        "dataset_id": "demo",
                        "manifest_path": "inputs/manifest.json",
                        "training_data_version": "train-v1",
                        "wsi_ids": ["slide-001"],
                    },
                    "artifacts": {
                        artifact_type: create_prior_artifact_entry(path, kind="json")
                        for artifact_type, path in paths.items()
                    },
                },
            )

            with self.assertRaisesRegex(GenerationConditionError, "wsi_tissue_overview.artifact_type"):
                build_generation_condition_packet(
                    self.generation_config(),
                    prior_manifest_path=root / "prior" / "prior_manifest.json",
                    output_path=root / "condition_packet.json",
                    cascade_level="1/1",
                    tile_origin_40x=(0, 0),
                )

    def test_cli_builds_generation_condition_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prior_manifest_path = self.create_prior_manifest(root)
            config_path = root / "generation-config.json"
            output_path = root / "condition_packet.json"
            config_path.write_text(json.dumps(self.generation_config()), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-condition-packet",
                    str(config_path),
                    "--prior-manifest",
                    str(prior_manifest_path),
                    "--output",
                    str(output_path),
                    "--cascade-level",
                    "1/1",
                    "--tile-origin-x",
                    "128",
                    "--tile-origin-y",
                    "256",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            packet = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("condition packet written", result.stdout)
        self.assertEqual(packet["conditions"]["coord"]["tile_origin_40x"], [128, 256])


if __name__ == "__main__":
    unittest.main()
