import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.ui.config import (
    create_default_ui_config,
    load_ui_config,
    save_ui_config,
)
from he_wsi_generator.ui.controller import (
    JobStateError,
    JobStateStore,
    collect_output_summary,
)
from he_wsi_generator.ui.pyside_app import UIUnavailableError, ensure_pyside_available


REPO_ROOT = Path(__file__).resolve().parents[1]


class UITests(unittest.TestCase):
    def test_default_ui_config_contains_single_page_sections(self):
        config = create_default_ui_config()

        self.assertEqual(config["schema_version"], "v0.46.0")
        self.assertEqual(
            list(config["sections"]),
            [
                "data_input",
                "label_mapping",
                "prior_model",
                "generation_parameters",
                "task_status",
                "qc_output",
            ],
        )
        self.assertIn("structure_anchor", config["sections"]["generation_parameters"]["fields"])

    def test_ui_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.json"
            config = create_default_ui_config()

            save_ui_config(config, path)
            loaded = load_ui_config(path)

        self.assertEqual(loaded["sections"]["task_status"]["statuses"], [
            "queued",
            "running",
            "completed",
            "failed",
            "cancelled",
        ])

    def test_job_state_store_tracks_valid_transitions(self):
        store = JobStateStore()

        store.set_status("job-001", "queued")
        store.set_status("job-001", "running")
        store.set_status("job-001", "completed", message="metadata.json")

        self.assertEqual(store.get_status("job-001")["status"], "completed")
        self.assertEqual(store.get_status("job-001")["message"], "metadata.json")

    def test_job_state_store_rejects_invalid_status(self):
        store = JobStateStore()

        with self.assertRaisesRegex(JobStateError, "invalid job status"):
            store.set_status("job-001", "paused")

    def test_collect_output_summary_reads_metadata_and_qc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            qc_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.46.0",
                        "generated_id": "gen-001",
                        "overall_status": "warning",
                        "levels": {
                            "wsi": {"status": "pass", "metrics": []},
                            "tile": {"status": "warning", "metrics": []},
                            "mask_region": {"status": "pass", "metrics": []},
                        },
                        "non_copy_report": {
                            "enabled": True,
                            "patch_nearest_neighbor_search": False,
                            "items": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            metadata_path.write_text(
                json.dumps(
                    {
                        "generated_id": "gen-001",
                        "output": {
                            "wsi_path": "generated.ome.tiff",
                            "mask_path": "generated_mask/mask.npy",
                            "qc_json_path": str(qc_path),
                        },
                    }
                ),
                encoding="utf-8",
            )

            summary = collect_output_summary(metadata_path, qc_path)

        self.assertEqual(summary["generated_id"], "gen-001")
        self.assertEqual(summary["qc_status"], "warning")
        self.assertEqual(summary["outputs"]["wsi_path"], "generated.ome.tiff")

    def test_ensure_pyside_available_reports_missing_dependency(self):
        try:
            import PySide6  # noqa: F401
        except ImportError:
            with self.assertRaisesRegex(UIUnavailableError, "PySide6 is required"):
                ensure_pyside_available()
        else:
            self.assertIsNotNone(ensure_pyside_available())

    def test_cli_writes_ui_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "write-ui-config",
                    str(path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            config = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ui config written", result.stdout)
        self.assertEqual(config["schema_version"], "v0.46.0")

    def test_cli_inspects_output_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            qc_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.46.0",
                        "generated_id": "gen-001",
                        "overall_status": "warning",
                        "levels": {
                            "wsi": {"status": "pass", "metrics": []},
                            "tile": {"status": "warning", "metrics": []},
                            "mask_region": {"status": "pass", "metrics": []},
                        },
                        "non_copy_report": {
                            "enabled": True,
                            "patch_nearest_neighbor_search": False,
                            "items": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            metadata_path.write_text(
                json.dumps(
                    {
                        "generated_id": "gen-001",
                        "output": {
                            "wsi_path": "generated.ome.tiff",
                            "mask_path": "generated_mask/mask.npy",
                            "qc_json_path": str(qc_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-output-summary",
                    "--metadata",
                    str(metadata_path),
                    "--qc",
                    str(qc_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            summary = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary["generated_id"], "gen-001")
        self.assertEqual(summary["qc_status"], "warning")
        self.assertEqual(summary["outputs"]["wsi_path"], "generated.ome.tiff")

    def test_cli_rejects_invalid_output_summary_qc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            qc_path.write_text(
                json.dumps(
                    {
                        "schema_version": "v0.46.0",
                        "generated_id": "gen-001",
                        "overall_status": "warning",
                        "levels": {
                            "wsi": {"status": "pass", "metrics": []},
                            "tile": {"status": "warning", "metrics": []},
                            "mask_region": {"status": "pass", "metrics": []},
                        },
                        "non_copy_report": {
                            "enabled": True,
                            "patch_nearest_neighbor_search": True,
                            "items": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            metadata_path.write_text(
                json.dumps(
                    {
                        "generated_id": "gen-001",
                        "output": {
                            "wsi_path": "generated.ome.tiff",
                            "mask_path": "generated_mask/mask.npy",
                            "qc_json_path": str(qc_path),
                        },
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "inspect-output-summary",
                    "--metadata",
                    str(metadata_path),
                    "--qc",
                    str(qc_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non_copy_report.patch_nearest_neighbor_search must be false", result.stderr)


if __name__ == "__main__":
    unittest.main()
