import json
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.constants import (
    DEFAULT_GENERATION_CONFIG,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    PROJECT_VERSION,
    TILE_SIZE_40X,
)
from he_wsi_generator.ui.jobs import JobRunner
from he_wsi_generator.ui.workflow import (
    UIWorkflowError,
    build_generation_config_from_form,
    build_run_generation_command,
    collect_generation_job_output_summary,
    create_run_generation_job,
    load_generation_job_status,
    run_queued_generation_job,
)


def _form_state(**overrides: object) -> dict:
    state = {
        "backend": "smoke-cascade",
        "prior_manifest_path": "build/prior_manifest.json",
        "checkpoint_manifest_path": "build/checkpoint_manifest.json",
        "output_root": "build/generated",
        "generated_id": "gen-001",
        "random_seed": "17",
        "anchor_preset": "structure_preserving",
        "structure_anchor": "0.8",
        "source_wsi_id": "slide-001",
        "style_seed": "23",
        "sample_steps": "12",
        "overlap_px_40x": "32",
        "non_copy_patch_nearest_neighbor_search": False,
        "condition_packet_path": "build/condition_packet.json",
        "job_root": "build/generated/ui_jobs",
        "label_mapping_rows": [
            {"raw_label": "1", "class_name": "tissue"},
            {"raw_label": "2", "class_name": "target_pathology"},
        ],
    }
    state.update(overrides)
    return state


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _qc_report(generated_id: str = "gen-001") -> dict:
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
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


def _metadata(qc_path: str | Path, generated_id: str = "gen-001") -> dict:
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "version": PROJECT_VERSION,
        "created_at": "2026-05-24T08:00:00+00:00",
        "output": {
            "wsi_path": "generated.ome.tiff",
            "mask_path": "generated_mask/mask.npy",
            "qc_json_path": str(qc_path),
            "diagnostics_manifest_path": "generation_output_diagnostics.json",
        },
        "source": {"source_wsi_id": None},
        "generation": {
            "structure_anchor": 0.0,
            "style_seed": "auto",
            "random_seed": 17,
            "model_checkpoint": "checkpoint.pt",
            "model_version": PROJECT_VERSION,
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
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


def _qc_review(metadata_path: str | Path, qc_path: str | Path) -> dict:
    return {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "qc_review",
        "generated_id": "gen-001",
        "created_at": "2026-05-24T08:00:00+00:00",
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
        "decision": "accepted",
        "reviewer": "Dr. Chen",
        "note": "Reviewed.",
        "reviewed_at": "2026-05-24T08:05:00+00:00",
        "review_items": [
            {"level": "tile", "name": "sharpness_laplacian_proxy", "status": "warning"}
        ],
    }


class UIWorkflowTests(unittest.TestCase):
    def test_build_generation_config_from_form_overrides_p2_fields(self):
        config = build_generation_config_from_form(_form_state())

        self.assertEqual(config["schema_version"], PROJECT_VERSION)
        self.assertEqual(config["model_family"], DEFAULT_GENERATION_CONFIG["model_family"])
        self.assertEqual(config["random_seed"], 17)
        self.assertEqual(config["anchor_preset"], "structure_preserving")
        self.assertEqual(config["structure_anchor"], 0.8)
        self.assertEqual(config["source_wsi_id"], "slide-001")
        self.assertEqual(config["style_seed"], 23)
        self.assertEqual(config["sample_steps"], 12)
        self.assertEqual(config["overlap_px_40x"], 32)
        self.assertFalse(config["non_copy_patch_nearest_neighbor_search"])

    def test_build_generation_config_rejects_invalid_range(self):
        with self.assertRaisesRegex(UIWorkflowError, "sample_steps must be a positive integer"):
            build_generation_config_from_form(_form_state(sample_steps="0"))

    def test_build_generation_config_rejects_duplicate_raw_label(self):
        with self.assertRaisesRegex(UIWorkflowError, "duplicate raw label"):
            build_generation_config_from_form(
                _form_state(
                    label_mapping_rows=[
                        {"raw_label": "1", "class_name": "tissue"},
                        {"raw_label": "1", "class_name": "artifact"},
                    ]
                )
            )

    def test_build_run_generation_command_matches_existing_cli(self):
        command = build_run_generation_command(_form_state(), "build/generation.json")

        self.assertEqual(
            command,
            [
                sys.executable,
                "-m",
                "he_wsi_generator.cli",
                "run-generation",
                "build/generation.json",
                "--backend",
                "smoke-cascade",
                "--prior-manifest",
                "build/prior_manifest.json",
                "--checkpoint-manifest",
                "build/checkpoint_manifest.json",
                "--output-root",
                "build/generated",
                "--generated-id",
                "gen-001",
                "--condition-packet",
                "build/condition_packet.json",
            ],
        )

    def test_build_run_generation_command_requires_training_index_for_torch_backend(self):
        with self.assertRaisesRegex(UIWorkflowError, "training index is required"):
            build_run_generation_command(
                _form_state(backend="torch-diffusion-smoke", training_index_path=""),
                "build/generation.json",
            )

    def test_build_run_generation_command_includes_training_index_for_torch_backend(self):
        command = build_run_generation_command(
            _form_state(
                backend="torch-diffusion-smoke",
                training_index_path="build/training-index.jsonl",
                condition_packet_path=None,
            ),
            "build/generation.json",
        )

        self.assertIn("--training-index", command)
        self.assertIn("build/training-index.jsonl", command)
        self.assertNotIn("--condition-packet", command)

    def test_build_run_generation_command_accepts_production_tile_stream_backend(self):
        command = build_run_generation_command(
            _form_state(
                backend="production-tile-stream",
                condition_packet_path="build/condition_packet.json",
            ),
            "build/generation.json",
        )

        self.assertIn("--backend", command)
        self.assertIn("production-tile-stream", command)
        self.assertNotIn("--training-index", command)
        self.assertIn("--wsi-writer", command)
        self.assertIn("tile-streaming", command)

    def test_build_run_generation_command_rejects_missing_required_field(self):
        with self.assertRaisesRegex(UIWorkflowError, "prior manifest is required"):
            build_run_generation_command(
                _form_state(prior_manifest_path=""),
                "build/generation.json",
            )

    def test_build_generation_config_normalizes_duplicate_raw_labels(self):
        with self.assertRaisesRegex(UIWorkflowError, "duplicate raw label: 1"):
            build_generation_config_from_form(
                _form_state(
                    label_mapping_rows=[
                        {"raw_label": "01", "class_name": "tissue"},
                        {"raw_label": "1", "class_name": "artifact"},
                    ]
                )
            )

    def test_create_run_generation_job_creates_queued_record_without_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            record = create_run_generation_job(
                _form_state(
                    condition_packet_path=None,
                    job_root=str(root / "jobs"),
                ),
                root / "jobs",
                root / "generation.json",
                cwd=root / "work",
            )

            persisted = Path(record["record_path"]).read_text(encoding="utf-8")

        self.assertEqual(record["job_id"], "gen-001")
        self.assertEqual(record["status"], "queued")
        self.assertIsNone(record["return_code"])
        self.assertEqual(record["cwd"], str(root / "work"))
        self.assertIn("run-generation", record["command"])
        self.assertIn("gen-001", persisted)

    def test_run_generation_job_helpers_honor_explicit_job_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "outputs" / "run-artifacts"
            job_root = root / "outputs" / "ui-jobs"
            create_run_generation_job(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(job_root),
                ),
                job_root,
                root / "generation.json",
            )
            record = JobRunner(job_root).load_job("gen-001")
            record["command"] = [sys.executable, "-c", "print('job root ok')"]
            Path(record["record_path"]).write_text(
                json.dumps(record, indent=2) + "\n",
                encoding="utf-8",
            )

            completed = run_queued_generation_job(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(job_root),
                )
            )
            refreshed = load_generation_job_status(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(job_root),
                )
            )

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(refreshed["status"], "completed")

    def test_create_run_generation_job_rejects_invalid_generation_fields_before_queueing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            with self.assertRaisesRegex(UIWorkflowError, "sample_steps must be a positive integer"):
                create_run_generation_job(
                    _form_state(sample_steps="0"),
                    root / "jobs",
                    root / "generation.json",
                )

            self.assertFalse((root / "jobs" / "gen-001" / "job.json").exists())

    def test_run_queued_generation_job_executes_existing_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "outputs"
            create_run_generation_job(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(output_root / "ui_jobs"),
                ),
                output_root / "ui_jobs",
                root / "generation.json",
            )
            record = JobRunner(output_root / "ui_jobs").load_job("gen-001")
            record["command"] = [sys.executable, "-c", "print('gui job done')"]
            Path(record["record_path"]).write_text(
                json.dumps(record, indent=2) + "\n",
                encoding="utf-8",
            )

            completed = run_queued_generation_job(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(output_root / "ui_jobs"),
                )
            )
            refreshed = load_generation_job_status(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(output_root / "ui_jobs"),
                )
            )
            stdout = Path(completed["stdout_path"]).read_text(encoding="utf-8")

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(refreshed["status"], "completed")
        self.assertIn("gui job done", stdout)

    def test_collect_generation_job_output_summary_reads_completed_job_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "outputs"
            output_root.mkdir()
            metadata_path = output_root / "metadata.json"
            qc_path = output_root / "qc.json"
            review_path = output_root / "qc_review.json"
            _write_json(qc_path, _qc_report())
            _write_json(metadata_path, _metadata(qc_path=qc_path))
            _write_json(review_path, _qc_review(metadata_path, qc_path))
            runner = JobRunner(output_root / "ui_jobs")
            runner.create_job("gen-001", [sys.executable, "-c", "print('done')"])
            runner.run_job("gen-001")

            summary = collect_generation_job_output_summary(
                _form_state(
                    output_root=str(output_root),
                    condition_packet_path=None,
                    job_root=str(output_root / "ui_jobs"),
                )
            )

        self.assertEqual(summary["generated_id"], "gen-001")
        self.assertEqual(summary["qc_status"], "warning")
        self.assertEqual(summary["outputs"]["metadata_path"], str(metadata_path))
        self.assertEqual(summary["review"]["decision"], "accepted")

    def test_collect_generation_job_output_summary_rejects_unfinished_or_missing_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "outputs"
            runner = JobRunner(output_root / "ui_jobs")
            runner.create_job("gen-001", [sys.executable, "-c", "print('not run')"])

            with self.assertRaisesRegex(UIWorkflowError, "must be completed"):
                collect_generation_job_output_summary(
                    _form_state(
                        output_root=str(output_root),
                        condition_packet_path=None,
                        job_root=str(output_root / "ui_jobs"),
                    )
                )

            runner.run_job("gen-001")
            with self.assertRaisesRegex(UIWorkflowError, "metadata.json"):
                collect_generation_job_output_summary(
                    _form_state(
                        output_root=str(output_root),
                        condition_packet_path=None,
                        job_root=str(output_root / "ui_jobs"),
                    )
                )


if __name__ == "__main__":
    unittest.main()
