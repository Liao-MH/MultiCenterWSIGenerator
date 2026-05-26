import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import he_wsi_generator.cli as cli_module
import he_wsi_generator.cli_commands as cli_commands
from he_wsi_generator.constants import (
    CASCADE_LEVELS,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    PROJECT_VERSION,
    TILE_SIZE_40X,
)
from he_wsi_generator.schemas import validate_generation_config
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
from he_wsi_generator.ui.pyside_app import (
    UIUnavailableError,
    create_main_window,
    ensure_pyside_available,
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _qc_report(
    generated_id: str = "gen-001",
    overall_status: str = "warning",
    level_statuses: dict[str, str] | None = None,
    metrics_by_level: dict[str, list[dict]] | None = None,
    patch_search: bool = False,
) -> dict:
    statuses = level_statuses or {
        "wsi": "pass",
        "tile": "warning",
        "mask_region": "pass",
    }
    metrics = metrics_by_level or {}
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "overall_status": overall_status,
        "levels": {
            level: {"status": statuses[level], "metrics": metrics.get(level, [])}
            for level in ("wsi", "tile", "mask_region")
        },
        "non_copy_report": {
            "enabled": True,
            "patch_nearest_neighbor_search": patch_search,
            "items": [],
        },
    }


def _metadata(generated_id: str = "gen-001", qc_path: str | Path = "qc.json") -> dict:
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "version": PROJECT_VERSION,
        "created_at": "2026-05-23T09:00:00+00:00",
        "output": {
            "wsi_path": "generated.ome.tiff",
            "mask_path": "generated_mask/mask.npy",
            "qc_json_path": str(qc_path),
            "diagnostics_manifest_path": "generation_output_diagnostics.json",
        },
        "source": {"source_wsi_id": None},
        "generation": {
            "structure_anchor": 0.0,
            "style_seed": "style-001",
            "random_seed": 7,
            "model_checkpoint": "checkpoint.pt",
            "model_version": PROJECT_VERSION,
            "cascade_levels": list(CASCADE_LEVELS),
            "max_magnification": MAX_MAGNIFICATION,
            "tile_size_40x": list(TILE_SIZE_40X),
        },
        "mask_schema": {
            "classes": list(MASK_CLASSES),
            "mapping_source": "manual",
            "input_label_mapping": {},
            "confidence": {},
        },
        "qc": {
            "overall_status": "warning",
            "summary": {},
            "non_copy_report": {
                "enabled": True,
                "patch_nearest_neighbor_search": False,
                "items": [],
            },
        },
    }


def _qc_review(
    metadata_path: str | Path,
    qc_path: str | Path,
    generated_id: str = "gen-001",
    decision: str = "pending",
    reviewer: str | None = None,
    reviewed_at: str | None = None,
    review_items: list[dict] | None = None,
) -> dict:
    items = review_items or [
        {
            "level": "tile",
            "name": "sharpness_laplacian_proxy",
            "status": "warning",
            "value": 1.25,
        }
    ]
    return {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "qc_review",
        "generated_id": generated_id,
        "created_at": "2026-05-23T09:00:00+00:00",
        "inputs": {
            "metadata_path": str(metadata_path),
            "metadata_sha256": "0" * 64,
            "qc_path": str(qc_path),
            "qc_sha256": "1" * 64,
        },
        "qc_status": {
            "overall_status": "warning",
            "levels": {"wsi": "pass", "tile": "warning", "mask_region": "pass"},
        },
        "review_required": True,
        "decision": decision,
        "reviewer": reviewer,
        "note": "Reviewed." if decision != "pending" else "",
        "reviewed_at": reviewed_at,
        "review_items": items,
    }


class UITests(unittest.TestCase):
    def test_default_ui_config_contains_single_page_sections(self):
        config = create_default_ui_config()

        self.assertEqual(config["schema_version"], PROJECT_VERSION)
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

    def test_ui_config_yaml_roundtrip_uses_optional_yaml_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.yaml"
            config = create_default_ui_config()
            yaml_module = types.ModuleType("yaml")
            yaml_module.safe_dump = lambda data, sort_keys=False: json.dumps(data, indent=2)  # type: ignore[assignment]
            yaml_module.safe_load = lambda text: json.loads(text)  # type: ignore[assignment]

            with patch.dict(sys.modules, {"yaml": yaml_module}):
                save_ui_config(config, path)
                loaded = load_ui_config(path)

        self.assertEqual(loaded["schema_version"], PROJECT_VERSION)
        self.assertEqual(loaded["sections"]["qc_output"]["status_levels"], ["pass", "warning", "fail"])

    def test_ui_config_yaml_requires_optional_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.yaml"
            config = create_default_ui_config()

            try:
                import yaml  # noqa: F401
            except ImportError:
                with self.assertRaisesRegex(ValueError, "PyYAML"):
                    save_ui_config(config, path)
            else:
                self.assertIsNotNone(yaml)

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
            _write_json(qc_path, _qc_report())
            _write_json(metadata_path, _metadata(qc_path=qc_path))

            summary = collect_output_summary(metadata_path, qc_path)

        self.assertEqual(summary["generated_id"], "gen-001")
        self.assertEqual(summary["qc_status"], "warning")
        self.assertEqual(summary["outputs"]["wsi_path"], "generated.ome.tiff")

    def test_collect_output_summary_rejects_invalid_metadata_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            _write_json(qc_path, _qc_report())
            _write_json(
                metadata_path,
                {
                    "generated_id": "gen-001",
                    "output": {
                        "wsi_path": "generated.ome.tiff",
                        "mask_path": "generated_mask/mask.npy",
                        "qc_json_path": str(qc_path),
                    },
                },
            )

            with self.assertRaisesRegex(ValueError, "schema_version"):
                collect_output_summary(metadata_path, qc_path)

    def test_collect_output_summary_rejects_metadata_qc_generated_id_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            _write_json(qc_path, _qc_report(generated_id="gen-002"))
            _write_json(metadata_path, _metadata(generated_id="gen-001", qc_path=qc_path))

            with self.assertRaisesRegex(ValueError, "metadata.generated_id must match qc.generated_id"):
                collect_output_summary(metadata_path, qc_path)

    def test_collect_output_summary_includes_qc_review_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            review_path = root / "qc_review.json"
            review_items = [
                {
                    "level": "tile",
                    "name": "sharpness_laplacian_proxy",
                    "status": "warning",
                    "value": 1.25,
                }
            ]
            _write_json(
                qc_path,
                _qc_report(
                    metrics_by_level={
                        "tile": [
                            {
                                "name": "sharpness_laplacian_proxy",
                                "status": "warning",
                                "value": 1.25,
                            }
                        ]
                    }
                ),
            )
            _write_json(metadata_path, _metadata(qc_path=qc_path))
            _write_json(review_path, _qc_review(metadata_path, qc_path, review_items=review_items))

            summary = collect_output_summary(metadata_path, qc_path, qc_review_path=review_path)

        self.assertEqual(summary["review"]["review_required"], True)
        self.assertEqual(summary["review"]["decision"], "pending")
        self.assertIsNone(summary["review"]["reviewer"])
        self.assertEqual(summary["review"]["review_item_count"], 1)

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
        self.assertEqual(config["schema_version"], PROJECT_VERSION)

    def test_cli_writes_yaml_ui_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.yaml"
            yaml_module = types.ModuleType("yaml")
            yaml_module.safe_dump = lambda data, sort_keys=False: json.dumps(data, indent=2)  # type: ignore[assignment]
            yaml_module.safe_load = lambda text: json.loads(text)  # type: ignore[assignment]

            with patch.dict(sys.modules, {"yaml": yaml_module}):
                result = cli_module.main(["write-ui-config", str(path)])
                config = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(config["schema_version"], PROJECT_VERSION)

    def test_cli_launches_ui_with_yaml_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ui-config.yaml"
            yaml_module = types.ModuleType("yaml")
            yaml_module.safe_dump = lambda data, sort_keys=False: json.dumps(data, indent=2)  # type: ignore[assignment]
            yaml_module.safe_load = lambda text: json.loads(text)  # type: ignore[assignment]

            with patch.dict(sys.modules, {"yaml": yaml_module}):
                save_ui_config(create_default_ui_config(), path)
                with patch.object(cli_commands, "launch_ui", return_value=0) as launch_mock:
                    result = cli_module.main(["launch-ui", "--config", str(path)])

        self.assertEqual(result, 0)
        self.assertTrue(launch_mock.called)
        self.assertEqual(launch_mock.call_args.args[0]["schema_version"], PROJECT_VERSION)

    def test_cli_inspects_output_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            _write_json(qc_path, _qc_report())
            _write_json(metadata_path, _metadata(qc_path=qc_path))
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

    def test_cli_inspects_output_summary_with_qc_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            review_path = root / "qc_review.json"
            _write_json(qc_path, _qc_report())
            _write_json(metadata_path, _metadata(qc_path=qc_path))
            _write_json(
                review_path,
                _qc_review(
                    metadata_path,
                    qc_path,
                    decision="accepted",
                    reviewer="Dr. Chen",
                    reviewed_at="2026-05-23T09:05:00+00:00",
                    review_items=[{"level": "tile", "name": "sharpness", "status": "warning"}],
                ),
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
                    "--qc-review",
                    str(review_path),
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
        self.assertEqual(summary["review"]["review_required"], True)
        self.assertEqual(summary["review"]["decision"], "accepted")
        self.assertEqual(summary["review"]["reviewer"], "Dr. Chen")
        self.assertEqual(summary["review"]["review_item_count"], 1)

    def test_cli_rejects_invalid_output_summary_qc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "metadata.json"
            qc_path = root / "qc.json"
            _write_json(qc_path, _qc_report(patch_search=True))
            _write_json(metadata_path, _metadata(qc_path=qc_path))
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


class PySideFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError as exc:
            raise unittest.SkipTest("PySide6 is not installed") from exc
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        self.app.processEvents()

    def test_main_window_exposes_enabled_form_controls(self):
        from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton

        window = create_main_window()

        self.assertIsNotNone(window.findChild(QLineEdit, "generation_config_path_input"))
        self.assertIsNotNone(window.findChild(QLineEdit, "prior_manifest_input"))
        self.assertIsNotNone(window.findChild(QLineEdit, "checkpoint_manifest_input"))
        self.assertIsNotNone(window.findChild(QLineEdit, "output_root_input"))
        self.assertIsNotNone(window.findChild(QLineEdit, "generated_id_input"))
        self.assertIsNotNone(window.findChild(QComboBox, "backend_select"))
        self.assertIsNotNone(window.findChild(QComboBox, "anchor_preset_select"))
        for class_name in MASK_CLASSES:
            self.assertIsNotNone(window.findChild(QLineEdit, f"label_mapping_{class_name}_input"))
        self.assertTrue(window.findChild(QPushButton, "save_config_button").isEnabled())
        self.assertTrue(window.findChild(QPushButton, "create_job_button").isEnabled())
        self.assertTrue(window.findChild(QPushButton, "run_job_button").isEnabled())
        self.assertTrue(window.findChild(QPushButton, "refresh_job_button").isEnabled())
        self.assertTrue(window.findChild(QPushButton, "load_output_summary_button").isEnabled())
        self.assertIsNotNone(window.findChild(QLabel, "job_status_label"))
        self.assertIsNotNone(window.findChild(QLabel, "output_summary_label"))

    def test_save_config_writes_valid_generation_json(self):
        from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            window = create_main_window()
            self._populate_valid_form(window, root)

            window.findChild(QPushButton, "save_config_button").click()
            self.app.processEvents()

            config_path = root / "generation-config.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))

        validated = validate_generation_config(payload)
        self.assertEqual(validated["schema_version"], PROJECT_VERSION)
        self.assertEqual(validated["anchor_preset"], "fully_de_novo")
        self.assertIn("Saved generation config", window.findChild(QLabel, "ui_status_label").text())

    def test_invalid_label_mapping_blocks_save(self):
        from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            window = create_main_window()
            self._populate_valid_form(window, root)
            window.findChild(QLineEdit, "label_mapping_tissue_input").setText("1, not-an-int")

            window.findChild(QPushButton, "save_config_button").click()
            self.app.processEvents()

            status = window.findChild(QLabel, "ui_status_label").text()

        self.assertFalse((root / "generation-config.json").exists())
        self.assertIn("label mapping", status)

    def test_missing_run_parameters_and_torch_training_index_block_job_creation(self):
        from PySide6.QtWidgets import QLabel, QComboBox, QLineEdit, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            window = create_main_window()
            self._populate_valid_form(window, root)
            window.findChild(QLineEdit, "prior_manifest_input").clear()

            window.findChild(QPushButton, "create_job_button").click()
            self.app.processEvents()
            missing_prior_status = window.findChild(QLabel, "ui_status_label").text()

            self._populate_valid_form(window, root)
            window.findChild(QLineEdit, "generated_id_input").clear()
            window.findChild(QPushButton, "create_job_button").click()
            self.app.processEvents()
            missing_generated_id_status = window.findChild(QLabel, "ui_status_label").text()

            self._populate_valid_form(window, root)
            window.findChild(QComboBox, "backend_select").setCurrentText("torch-diffusion-smoke")
            window.findChild(QLineEdit, "training_index_input").clear()
            window.findChild(QPushButton, "create_job_button").click()
            self.app.processEvents()
            missing_training_status = window.findChild(QLabel, "ui_status_label").text()

        self.assertIn("prior manifest", missing_prior_status)
        self.assertIn("generated id", missing_generated_id_status)
        self.assertIn("training index", missing_training_status)
        self.assertFalse((root / "generation-config.json").exists())
        self.assertFalse((root / "outputs" / "ui_jobs" / "gen-001" / "job.json").exists())

    def test_create_job_writes_queued_local_job_record(self):
        from PySide6.QtWidgets import QLineEdit, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            window = create_main_window()
            self._populate_valid_form(window, root)

            window.findChild(QPushButton, "create_job_button").click()
            self.app.processEvents()
            record_path = root / "outputs" / "ui_jobs" / "gen-001" / "job.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))

        self.assertEqual(record["status"], "queued")
        self.assertEqual(record["command"][2:4], ["he_wsi_generator.cli", "run-generation"])
        self.assertIn(str(root / "generation-config.json"), record["command"])

    def test_run_job_button_uses_workflow_helper_and_displays_status(self):
        from PySide6.QtWidgets import QLabel, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            record_path = root / "outputs" / "ui_jobs" / "gen-001" / "job.json"
            window = create_main_window()
            self._populate_valid_form(window, root)

            with patch(
                "he_wsi_generator.ui.pyside_app.run_queued_generation_job",
                return_value={
                    "job_id": "gen-001",
                    "status": "completed",
                    "message": "command completed",
                    "record_path": str(record_path),
                },
            ) as run_helper:
                window.findChild(QPushButton, "run_job_button").click()
                self.app.processEvents()

        run_helper.assert_called_once()
        form_state = run_helper.call_args.args[0]
        self.assertEqual(form_state["generated_id"], "gen-001")
        status_text = window.findChild(QLabel, "job_status_label").text()
        self.assertIn("completed", status_text)
        self.assertIn(str(record_path), status_text)

    def test_refresh_job_button_uses_workflow_helper_and_displays_status(self):
        from PySide6.QtWidgets import QLabel, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            record_path = root / "outputs" / "ui_jobs" / "gen-001" / "job.json"
            window = create_main_window()
            self._populate_valid_form(window, root)

            with patch(
                "he_wsi_generator.ui.pyside_app.load_generation_job_status",
                return_value={
                    "job_id": "gen-001",
                    "status": "running",
                    "message": "still running",
                    "record_path": str(record_path),
                },
            ) as refresh_helper:
                window.findChild(QPushButton, "refresh_job_button").click()
                self.app.processEvents()

        refresh_helper.assert_called_once()
        status_text = window.findChild(QLabel, "job_status_label").text()
        self.assertIn("running", status_text)
        self.assertIn("still running", status_text)
        self.assertIn(str(record_path), status_text)

    def test_output_summary_button_uses_workflow_helper_and_displays_review(self):
        from PySide6.QtWidgets import QLabel, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path = root / "outputs" / "metadata.json"
            qc_path = root / "outputs" / "qc.json"
            window = create_main_window()
            self._populate_valid_form(window, root)

            with patch(
                "he_wsi_generator.ui.pyside_app.collect_generation_job_output_summary",
                return_value={
                    "generated_id": "gen-001",
                    "qc_status": "warning",
                    "outputs": {
                        "wsi_path": "generated.ome.tiff",
                        "mask_path": "generated_mask/mask.npy",
                        "metadata_path": str(metadata_path),
                        "qc_json_path": str(qc_path),
                    },
                    "review": {"decision": "accepted"},
                },
            ) as summary_helper:
                window.findChild(QPushButton, "load_output_summary_button").click()
                self.app.processEvents()

        summary_helper.assert_called_once()
        summary_text = window.findChild(QLabel, "output_summary_label").text()
        self.assertIn("gen-001", summary_text)
        self.assertIn("warning", summary_text)
        self.assertIn("generated.ome.tiff", summary_text)
        self.assertIn("generated_mask/mask.npy", summary_text)
        self.assertIn(str(metadata_path), summary_text)
        self.assertIn(str(qc_path), summary_text)
        self.assertIn("accepted", summary_text)

    def test_job_flow_helper_error_is_shown_with_error_prefix(self):
        from PySide6.QtWidgets import QLabel, QPushButton

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            window = create_main_window()
            self._populate_valid_form(window, root)

            with patch(
                "he_wsi_generator.ui.pyside_app.run_queued_generation_job",
                side_effect=ValueError("job helper failed"),
            ):
                window.findChild(QPushButton, "run_job_button").click()
                self.app.processEvents()

        self.assertTrue(
            window.findChild(QLabel, "job_status_label").text().startswith("Error: job helper failed")
        )

    def _populate_valid_form(self, window, root: Path) -> None:
        from PySide6.QtWidgets import QLineEdit

        values = {
            "generation_config_path_input": root / "generation-config.json",
            "prior_manifest_input": root / "prior_manifest.json",
            "checkpoint_manifest_input": root / "checkpoint_manifest.json",
            "output_root_input": root / "outputs",
            "generated_id_input": "gen-001",
            "condition_packet_input": "",
            "training_index_input": root / "training-index.jsonl",
        }
        for object_name, value in values.items():
            window.findChild(QLineEdit, object_name).setText(str(value))
        for raw_label, class_name in enumerate(MASK_CLASSES):
            window.findChild(QLineEdit, f"label_mapping_{class_name}_input").setText(str(raw_label))


if __name__ == "__main__":
    unittest.main()
