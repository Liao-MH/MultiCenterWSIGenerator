import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.constants import DEFAULT_GENERATION_CONFIG, PROJECT_VERSION
from he_wsi_generator.ui.workflow import (
    UIWorkflowError,
    build_generation_config_from_form,
    build_run_generation_command,
    create_run_generation_job,
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
        "label_mapping_rows": [
            {"raw_label": "1", "class_name": "tissue"},
            {"raw_label": "2", "class_name": "target_pathology"},
        ],
    }
    state.update(overrides)
    return state


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
                _form_state(condition_packet_path=None),
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


if __name__ == "__main__":
    unittest.main()
