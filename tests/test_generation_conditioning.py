import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.generation.conditioning import (
    GenerationConditionError,
    build_generation_condition_packet,
)
from he_wsi_generator.priors.artifacts import build_prior_manifest_from_artifacts


REPO_ROOT = Path(__file__).resolve().parents[1]


class GenerationConditioningTests(unittest.TestCase):
    def generation_config(self, style_seed="auto", structure_anchor=0.0, source_wsi_id=None) -> dict:
        return {
            "schema_version": "v0.44.0",
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
                "schema_version": "v0.44.0",
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
                "schema_version": "v0.44.0",
                "prior_type": "style_prior",
                "sample_count": 2,
                "rgb_statistics": {
                    "mean_rgb": [180.0, 120.0, 160.0],
                    "std_rgb": [10.0, 8.0, 9.0],
                    "mean_rgb_normalized": [0.705882353, 0.470588235, 0.62745098],
                },
            },
            "texture_prior": {
                "schema_version": "v0.44.0",
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
                "schema_version": "v0.44.0",
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
        }
        paths = {}
        for artifact_type, payload in artifacts.items():
            path = root / f"{artifact_type}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[artifact_type] = path
        return paths

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

        self.assertEqual(packet["schema_version"], "v0.44.0")
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
                        "schema_version": "v0.44.0",
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
