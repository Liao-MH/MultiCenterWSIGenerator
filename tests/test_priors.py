import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.priors.artifacts import (
    PriorArtifactError,
    build_prior_manifest_from_artifacts,
    create_prior_artifact_entry,
    load_prior_manifest,
    save_prior_manifest,
    validate_prior_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class PriorArtifactTests(unittest.TestCase):
    def write_artifacts(self, root: Path) -> dict:
        root.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, payload in {
            "layout_mask_prior": {
                "schema_version": "v0.62.0",
                "prior_type": "layout_mask_prior",
                "sample_count": 2,
                "non_background_fraction": 0.75,
            },
            "style_prior": {
                "schema_version": "v0.62.0",
                "prior_type": "style_prior",
                "sample_count": 2,
                "rgb_statistics": {"mean_rgb": [180.0, 120.0, 160.0]},
            },
            "texture_prior": {
                "schema_version": "v0.62.0",
                "prior_type": "texture_prior",
                "embedding_count": 4,
                "cluster_count": 2,
            },
            "qc_reference_distribution": {
                "schema_version": "v0.62.0",
                "source": "qc_report_metric_distribution",
                "sample_count": 3,
                "stratification": {
                    "enabled": True,
                    "fields": ["metadata.cancer_type"],
                    "stratum_count": 2,
                },
                "metrics": {
                    "blur": {
                        "warning_min": 0.1,
                        "warning_max": 0.9,
                        "sample_count": 3,
                    }
                },
            },
            "wsi_tissue_overview": {
                "schema_version": "v0.62.0",
                "artifact_type": "wsi_tissue_overview",
                "record_count": 2,
                "source": {
                    "backend": "openslide",
                    "thumbnail_max_size": [512, 512],
                },
                "records": [],
            },
        }.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[name] = path
        return paths

    def build_manifest(self, root: Path) -> dict:
        artifact_paths = self.write_artifacts(root)
        return {
            "schema_version": "v0.62.0",
            "prior_id": "prior-demo",
            "created_at": "2026-05-23T10:00:00Z",
            "random_seed": 7,
            "input_data": {
                "dataset_id": "demo",
                "manifest_path": "inputs/manifest.json",
                "training_data_version": "train-v1",
                "wsi_ids": ["slide-001", "slide-002"],
            },
            "artifacts": {
                name: create_prior_artifact_entry(path, kind="json", metadata={"stage": name})
                for name, path in artifact_paths.items()
                if name != "wsi_tissue_overview"
            },
        }

    def test_prior_manifest_roundtrip_records_required_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.build_manifest(root)
            manifest_path = save_prior_manifest(root, manifest)

            loaded = load_prior_manifest(manifest_path, verify_files=True)

        self.assertEqual(loaded["schema_version"], "v0.62.0")
        self.assertEqual(loaded["prior_id"], "prior-demo")
        self.assertEqual(loaded["random_seed"], 7)
        self.assertEqual(
            sorted(loaded["artifacts"]),
            [
                "layout_mask_prior",
                "qc_reference_distribution",
                "style_prior",
                "texture_prior",
            ],
        )
        self.assertEqual(loaded["input_data"]["wsi_ids"], ["slide-001", "slide-002"])

    def test_prior_manifest_rejects_missing_required_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self.build_manifest(Path(tmpdir))
            del manifest["artifacts"]["texture_prior"]

            with self.assertRaisesRegex(PriorArtifactError, "missing required artifact"):
                validate_prior_manifest(manifest, verify_files=True)

    def test_prior_manifest_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.build_manifest(root)
            texture_path = Path(manifest["artifacts"]["texture_prior"]["path"])
            texture_path.write_text(json.dumps({"cluster_count": 99}), encoding="utf-8")

            with self.assertRaisesRegex(PriorArtifactError, "sha256 mismatch"):
                validate_prior_manifest(manifest, verify_files=True)

    def test_prior_manifest_rejects_duplicate_artifact_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self.build_manifest(Path(tmpdir))
            manifest["artifacts"]["style_prior"]["path"] = manifest["artifacts"][
                "layout_mask_prior"
            ]["path"]

            with self.assertRaisesRegex(PriorArtifactError, "duplicate artifact path"):
                validate_prior_manifest(manifest, verify_files=True)

    def test_cli_validates_prior_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = self.build_manifest(root)
            manifest_path = save_prior_manifest(root, manifest)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "validate-prior-manifest",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prior manifest valid", result.stdout)

    def test_build_prior_manifest_from_artifacts_writes_valid_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_paths = self.write_artifacts(root / "artifacts")
            output_dir = root / "prior"

            manifest = build_prior_manifest_from_artifacts(
                output_dir=output_dir,
                prior_id="prior-demo",
                dataset_id="demo",
                input_manifest_path="inputs/manifest.json",
                training_data_version="train-v1",
                wsi_ids=["slide-001", "slide-002"],
                random_seed=7,
                layout_mask_prior_path=artifact_paths["layout_mask_prior"],
                style_prior_path=artifact_paths["style_prior"],
                texture_prior_path=artifact_paths["texture_prior"],
                qc_reference_distribution_path=artifact_paths["qc_reference_distribution"],
                created_at="2026-05-23T12:00:00Z",
            )
            manifest_path = output_dir / "prior_manifest.json"
            loaded = load_prior_manifest(manifest_path, verify_files=True)

        self.assertEqual(manifest["schema_version"], "v0.62.0")
        self.assertEqual(loaded["created_at"], "2026-05-23T12:00:00Z")
        self.assertEqual(loaded["input_data"]["dataset_id"], "demo")
        self.assertEqual(loaded["input_data"]["manifest_path"], "inputs/manifest.json")
        self.assertEqual(loaded["artifacts"]["layout_mask_prior"]["kind"], "json")
        self.assertEqual(
            loaded["artifacts"]["style_prior"]["metadata"]["artifact_type"],
            "style_prior",
        )
        self.assertEqual(
            loaded["artifacts"]["style_prior"]["metadata"]["artifact_schema_version"],
            "v0.62.0",
        )
        self.assertEqual(
            loaded["artifacts"]["texture_prior"]["metadata"]["cluster_count"],
            2,
        )
        self.assertEqual(
            loaded["artifacts"]["qc_reference_distribution"]["metadata"]["metric_count"],
            1,
        )
        self.assertEqual(
            loaded["artifacts"]["qc_reference_distribution"]["metadata"]["stratification_fields"],
            ["metadata.cancer_type"],
        )
        self.assertEqual(
            loaded["artifacts"]["qc_reference_distribution"]["metadata"]["stratum_count"],
            2,
        )

    def test_build_prior_manifest_from_artifacts_records_optional_wsi_tissue_overview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_paths = self.write_artifacts(root / "artifacts")
            output_dir = root / "prior"

            manifest = build_prior_manifest_from_artifacts(
                output_dir=output_dir,
                prior_id="prior-demo",
                dataset_id="demo",
                input_manifest_path="inputs/manifest.json",
                training_data_version="train-v1",
                wsi_ids=["slide-001", "slide-002"],
                random_seed=7,
                layout_mask_prior_path=artifact_paths["layout_mask_prior"],
                style_prior_path=artifact_paths["style_prior"],
                texture_prior_path=artifact_paths["texture_prior"],
                qc_reference_distribution_path=artifact_paths["qc_reference_distribution"],
                wsi_tissue_overview_path=artifact_paths["wsi_tissue_overview"],
                created_at="2026-05-23T12:00:00Z",
            )

        artifact = manifest["artifacts"]["wsi_tissue_overview"]
        self.assertEqual(artifact["kind"], "json")
        self.assertEqual(artifact["metadata"]["artifact_type"], "wsi_tissue_overview")
        self.assertEqual(artifact["metadata"]["artifact_schema_version"], "v0.62.0")
        self.assertEqual(artifact["metadata"]["record_count"], 2)
        self.assertEqual(artifact["metadata"]["source_backend"], "openslide")
        self.assertEqual(artifact["metadata"]["thumbnail_max_size"], [512, 512])

    def test_build_prior_manifest_from_artifacts_rejects_artifact_type_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_paths = self.write_artifacts(root / "artifacts")
            artifact_paths["style_prior"].write_text(
                json.dumps(
                    {
                        "schema_version": "v0.62.0",
                        "prior_type": "layout_mask_prior",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PriorArtifactError, "style_prior artifact prior_type"):
                build_prior_manifest_from_artifacts(
                    output_dir=root / "prior",
                    prior_id="prior-demo",
                    dataset_id="demo",
                    input_manifest_path="inputs/manifest.json",
                    training_data_version="train-v1",
                    wsi_ids=["slide-001"],
                    random_seed=7,
                    layout_mask_prior_path=artifact_paths["layout_mask_prior"],
                    style_prior_path=artifact_paths["style_prior"],
                    texture_prior_path=artifact_paths["texture_prior"],
                    qc_reference_distribution_path=artifact_paths["qc_reference_distribution"],
                    created_at="2026-05-23T12:00:00Z",
                )

    def test_cli_builds_prior_manifest_from_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_paths = self.write_artifacts(root / "artifacts")
            output_dir = root / "prior"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-prior-manifest",
                    "--output-dir",
                    str(output_dir),
                    "--prior-id",
                    "prior-demo",
                    "--dataset-id",
                    "demo",
                    "--input-manifest",
                    "inputs/manifest.json",
                    "--training-data-version",
                    "train-v1",
                    "--wsi-id",
                    "slide-001",
                    "--wsi-id",
                    "slide-002",
                    "--random-seed",
                    "7",
                    "--layout-mask-prior",
                    str(artifact_paths["layout_mask_prior"]),
                    "--style-prior",
                    str(artifact_paths["style_prior"]),
                    "--texture-prior",
                    str(artifact_paths["texture_prior"]),
                    "--qc-reference-distribution",
                    str(artifact_paths["qc_reference_distribution"]),
                    "--wsi-tissue-overview",
                    str(artifact_paths["wsi_tissue_overview"]),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            manifest = load_prior_manifest(output_dir / "prior_manifest.json", verify_files=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prior manifest written", result.stdout)
        self.assertEqual(manifest["prior_id"], "prior-demo")
        self.assertEqual(manifest["input_data"]["wsi_ids"], ["slide-001", "slide-002"])
        self.assertIn("wsi_tissue_overview", manifest["artifacts"])


if __name__ == "__main__":
    unittest.main()
