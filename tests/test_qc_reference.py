import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from he_wsi_generator.qc.reference import QCReferenceBuildError, build_qc_reference_distribution


REPO_ROOT = Path(__file__).resolve().parents[1]


class QCReferenceTests(unittest.TestCase):
    def qc_report(self, generated_id: str, red: float, sharpness: float, tissue_fraction: float) -> dict:
        return {
            "schema_version": "v0.41.0",
            "generated_id": generated_id,
            "overall_status": "pass",
            "levels": {
                "wsi": {
                    "status": "pass",
                    "metrics": [
                        {"name": "mean_red", "status": "pass", "value": red},
                        {"name": "rgb_dynamic_range", "status": "pass", "value": 40.0},
                    ],
                },
                "tile": {
                    "status": "pass",
                    "metrics": [
                        {"name": "sharpness_laplacian_proxy", "status": "pass", "value": sharpness},
                    ],
                },
                "mask_region": {
                    "status": "pass",
                    "metrics": [
                        {"name": "mask_tissue_fraction", "status": "pass", "value": tissue_fraction},
                    ],
                },
            },
            "non_copy_report": {
                "enabled": True,
                "patch_nearest_neighbor_search": False,
                "items": [],
            },
        }

    def test_build_qc_reference_distribution_from_qc_reports(self):
        reports = [
            self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=120.0, sharpness=4.0, tissue_fraction=0.60),
            self.qc_report("gen-003", red=140.0, sharpness=6.0, tissue_fraction=0.70),
            self.qc_report("gen-004", red=160.0, sharpness=8.0, tissue_fraction=0.80),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "qc_reference_distribution.json"

            reference = build_qc_reference_distribution(
                reports,
                output_path=output_path,
                metric_names=["mean_red", "sharpness_laplacian_proxy", "mask_tissue_fraction"],
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(reference["schema_version"], "v0.41.0")
        self.assertEqual(reference["sample_count"], 4)
        self.assertEqual(reference["metrics"]["mean_red"]["warning_min"], 100.0)
        self.assertEqual(reference["metrics"]["mean_red"]["warning_max"], 160.0)
        self.assertLess(reference["metrics"]["mean_red"]["fail_min"], 100.0)
        self.assertGreater(reference["metrics"]["mean_red"]["fail_max"], 160.0)
        self.assertEqual(written["metrics"]["mask_tissue_fraction"]["sample_count"], 4)

    def test_build_qc_reference_distribution_rejects_missing_metric(self):
        report = self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50)

        with self.assertRaisesRegex(QCReferenceBuildError, "missing metric"):
            build_qc_reference_distribution(
                [report],
                output_path=None,
                metric_names=["mean_blue"],
                min_samples=1,
            )

    def test_cli_builds_qc_reference_distribution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = []
            for index, value in enumerate((100.0, 120.0, 140.0), start=1):
                path = root / f"qc-{index}.json"
                path.write_text(
                    json.dumps(
                        self.qc_report(
                            f"gen-{index:03d}",
                            red=value,
                            sharpness=float(index),
                            tissue_fraction=0.5 + index * 0.05,
                        )
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
            output_path = root / "qc_reference_distribution.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "build-qc-reference",
                    *[str(path) for path in paths],
                    "--metric",
                    "mean_red",
                    "--metric",
                    "mask_tissue_fraction",
                    "--output",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            reference = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("qc reference distribution written", result.stdout)
        self.assertEqual(reference["metrics"]["mean_red"]["sample_count"], 3)


if __name__ == "__main__":
    unittest.main()
