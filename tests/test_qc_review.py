import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.qc.review import (
    QCReviewError,
    apply_qc_review_decision,
    build_qc_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class QCReviewTests(unittest.TestCase):
    def run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "he_wsi_generator.cli", *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def metadata(self, generated_id: str = "gen-001") -> dict:
        return {
            "schema_version": "v0.72.0",
            "generated_id": generated_id,
            "version": "v0.72.0",
            "created_at": "2026-05-23T09:00:00+00:00",
            "output": {
                "wsi_path": "generated.ome.tiff",
                "mask_path": "generated_mask/mask.npy",
                "qc_json_path": "qc.json",
            },
            "source": {"source_wsi_id": None},
            "generation": {
                "structure_anchor": 0.0,
                "style_seed": "auto",
                "random_seed": 7,
                "model_checkpoint": "checkpoint.json",
                "model_version": "v0.72.0",
                "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                "max_magnification": "40x",
                "tile_size_40x": [512, 512],
            },
            "mask_schema": {
                "classes": [
                    "background",
                    "tissue",
                    "target_pathology",
                    "supporting_tissue",
                    "necrosis_debris",
                    "artifact",
                ],
                "mapping_source": "manual",
                "input_label_mapping": {},
                "confidence": {},
            },
            "qc": {
                "overall_status": "warning",
                "summary": {},
                "non_copy_report": {"enabled": True},
            },
        }

    def qc_report(self, overall_status: str = "warning") -> dict:
        return {
            "schema_version": "v0.72.0",
            "generated_id": "gen-001",
            "overall_status": overall_status,
            "levels": {
                "wsi": {
                    "status": "pass",
                    "metrics": [
                        {"name": "wsi_file_exists", "status": "pass", "value": True},
                    ],
                },
                "tile": {
                    "status": overall_status,
                    "metrics": [
                        {
                            "name": "sharpness_laplacian_proxy",
                            "status": overall_status,
                            "value": 1.25,
                            "reference": {
                                "warning_min": 2.0,
                                "warning_max": 8.0,
                                "fail_min": 1.0,
                                "fail_max": 10.0,
                                "source": "qc_reference_distribution",
                            },
                            "message": "sharpness below warning range",
                        },
                    ],
                },
                "mask_region": {
                    "status": "pass",
                    "metrics": [
                        {"name": "mask_tissue_fraction", "status": "pass", "value": 0.56},
                    ],
                },
            },
            "non_copy_report": {
                "enabled": True,
                "patch_nearest_neighbor_search": False,
                "items": [],
            },
        }

    def write_inputs(self, root: Path, qc_status: str = "warning") -> tuple[Path, Path]:
        metadata_path = root / "metadata.json"
        qc_path = root / "qc.json"
        metadata_path.write_text(json.dumps(self.metadata()), encoding="utf-8")
        qc_path.write_text(json.dumps(self.qc_report(qc_status)), encoding="utf-8")
        return metadata_path, qc_path

    def test_build_qc_review_extracts_warning_and_fail_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            output_path = root / "qc_review.json"

            review = build_qc_review(metadata_path, qc_path, output_path=output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(review["schema_version"], "v0.72.0")
        self.assertEqual(review["artifact_type"], "qc_review")
        self.assertEqual(review["generated_id"], "gen-001")
        self.assertEqual(review["inputs"]["metadata_path"], str(metadata_path))
        self.assertRegex(review["inputs"]["metadata_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(review["qc_status"]["overall_status"], "warning")
        self.assertEqual(review["qc_status"]["levels"]["tile"], "warning")
        self.assertTrue(review["review_required"])
        self.assertEqual(review["decision"], "pending")
        self.assertIsNone(review["reviewer"])
        self.assertIsNone(review["reviewed_at"])
        self.assertEqual(len(review["review_items"]), 1)
        self.assertEqual(review["review_items"][0]["level"], "tile")
        self.assertEqual(review["review_items"][0]["name"], "sharpness_laplacian_proxy")
        self.assertEqual(review["review_items"][0]["status"], "warning")
        self.assertEqual(review["review_items"][0]["reference"]["source"], "qc_reference_distribution")
        self.assertEqual(review["review_items"][0]["message"], "sharpness below warning range")
        self.assertEqual(written, review)

    def test_build_qc_review_marks_pass_qc_as_not_requiring_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "pass")

            review = build_qc_review(metadata_path, qc_path)

        self.assertFalse(review["review_required"])
        self.assertEqual(review["decision"], "pending")
        self.assertEqual(review["review_items"], [])

    def test_validate_qc_review_rejects_mismatched_review_required(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            review = build_qc_review(metadata_path, qc_path, output_path=review_path)
            review["review_required"] = False
            review_path.write_text(json.dumps(review), encoding="utf-8")

            with self.assertRaisesRegex(QCReviewError, "review_required"):
                apply_qc_review_decision(review_path, decision="accepted", reviewer="Dr. Chen")

    def test_validate_cli_accepts_qc_review_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            build_qc_review(metadata_path, qc_path, output_path=review_path)

            result = self.run_cli("validate", "qc-review", str(review_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("qc-review valid", result.stdout)

    def test_validate_cli_rejects_invalid_qc_review_artifact_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            review = build_qc_review(metadata_path, qc_path, output_path=review_path)
            review["artifact_type"] = "qc_report"
            review_path.write_text(json.dumps(review), encoding="utf-8")

            result = self.run_cli("validate", "qc-review", str(review_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifact_type", result.stderr)

    def test_apply_qc_review_decision_rejects_illegal_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            build_qc_review(metadata_path, qc_path, output_path=review_path)

            with self.assertRaisesRegex(QCReviewError, "decision"):
                apply_qc_review_decision(review_path, decision="approved", reviewer="Dr. Chen")

    def test_apply_qc_review_decision_records_reviewer_and_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            build_qc_review(metadata_path, qc_path, output_path=review_path)

            updated = apply_qc_review_decision(
                review_path,
                decision="needs_rerun",
                reviewer="Dr. Chen",
                note="Regenerate sharper tile preview.",
            )
            persisted = json.loads(review_path.read_text(encoding="utf-8"))

        self.assertEqual(updated["decision"], "needs_rerun")
        self.assertEqual(updated["reviewer"], "Dr. Chen")
        self.assertEqual(updated["note"], "Regenerate sharper tile preview.")
        self.assertIsNotNone(updated["reviewed_at"])
        self.assertEqual(persisted, updated)

    def test_apply_qc_review_decision_rejects_empty_reviewer_and_non_pending_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            build_qc_review(metadata_path, qc_path, output_path=review_path)

            with self.assertRaisesRegex(QCReviewError, "reviewer"):
                apply_qc_review_decision(review_path, decision="accepted", reviewer=" ")

            apply_qc_review_decision(review_path, decision="accepted", reviewer="Dr. Chen")
            with self.assertRaisesRegex(QCReviewError, "pending"):
                apply_qc_review_decision(review_path, decision="rejected", reviewer="Dr. Chen")

    def test_cli_creates_and_updates_qc_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metadata_path, qc_path = self.write_inputs(root, "warning")
            review_path = root / "qc_review.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            create = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "create-qc-review",
                    "--metadata",
                    str(metadata_path),
                    "--qc",
                    str(qc_path),
                    "--output",
                    str(review_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            update = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "apply-qc-review-decision",
                    "--review",
                    str(review_path),
                    "--decision",
                    "accepted",
                    "--reviewer",
                    "Dr. Chen",
                    "--note",
                    "Reviewed warning metric.",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            review = json.loads(review_path.read_text(encoding="utf-8"))

        self.assertEqual(create.returncode, 0, create.stderr)
        self.assertIn("qc review written", create.stdout)
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertIn("qc review decision applied", update.stdout)
        self.assertEqual(review["decision"], "accepted")
        self.assertEqual(review["reviewer"], "Dr. Chen")


if __name__ == "__main__":
    unittest.main()
