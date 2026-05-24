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
    def qc_report(
        self,
        generated_id: str,
        red: float,
        sharpness: float,
        tissue_fraction: float,
        metadata: dict | None = None,
    ) -> dict:
        return {
            "schema_version": "v0.71.0",
            "generated_id": generated_id,
            "metadata": metadata or {},
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

        self.assertEqual(reference["schema_version"], "v0.71.0")
        self.assertEqual(reference["sample_count"], 4)
        self.assertEqual(reference["metrics"]["mean_red"]["warning_min"], 100.0)
        self.assertEqual(reference["metrics"]["mean_red"]["warning_max"], 160.0)
        self.assertLess(reference["metrics"]["mean_red"]["fail_min"], 100.0)
        self.assertGreater(reference["metrics"]["mean_red"]["fail_max"], 160.0)
        self.assertEqual(written["metrics"]["mask_tissue_fraction"]["sample_count"], 4)

    def test_build_qc_reference_distribution_uses_robust_iqr_estimator(self):
        reports = [
            self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=102.0, sharpness=2.1, tissue_fraction=0.51),
            self.qc_report("gen-003", red=104.0, sharpness=2.2, tissue_fraction=0.52),
            self.qc_report("gen-004", red=106.0, sharpness=2.3, tissue_fraction=0.53),
            self.qc_report("gen-005", red=500.0, sharpness=30.0, tissue_fraction=0.95),
        ]

        reference = build_qc_reference_distribution(
            reports,
            output_path=None,
            metric_names=["mean_red"],
            estimator="robust_iqr",
        )
        metric = reference["metrics"]["mean_red"]

        self.assertEqual(metric["estimator"], "robust_iqr")
        self.assertEqual(metric["observed_max"], 500.0)
        self.assertLess(metric["warning_max"], 500.0)
        self.assertLess(metric["fail_max"], 500.0)
        self.assertEqual(metric["q1"], 102.0)
        self.assertEqual(metric["median"], 104.0)
        self.assertEqual(metric["q3"], 106.0)
        self.assertEqual(metric["iqr"], 4.0)

    def test_build_qc_reference_distribution_uses_robust_mad_z_score_estimator(self):
        reports = [
            self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=102.0, sharpness=2.1, tissue_fraction=0.51),
            self.qc_report("gen-003", red=104.0, sharpness=2.2, tissue_fraction=0.52),
            self.qc_report("gen-004", red=106.0, sharpness=2.3, tissue_fraction=0.53),
            self.qc_report("gen-005", red=500.0, sharpness=30.0, tissue_fraction=0.95),
        ]

        reference = build_qc_reference_distribution(
            reports,
            output_path=None,
            metric_names=["mean_red"],
            estimator="robust_mad_z_score",
        )
        metric = reference["metrics"]["mean_red"]

        self.assertEqual(metric["estimator"], "robust_mad_z_score")
        self.assertEqual(metric["observed_max"], 500.0)
        self.assertEqual(metric["median"], 104.0)
        self.assertEqual(metric["mad"], 2.0)
        self.assertEqual(metric["warning_z_score"], 3.0)
        self.assertEqual(metric["fail_z_score"], 6.0)
        self.assertGreater(metric["scaled_mad"], metric["mad"])
        self.assertLess(metric["warning_max"], 500.0)
        self.assertLess(metric["fail_max"], 500.0)

    def test_build_qc_reference_distribution_uses_nonzero_margin_for_zero_mad(self):
        reports = [
            self.qc_report("gen-001", red=120.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=120.0, sharpness=2.1, tissue_fraction=0.51),
            self.qc_report("gen-003", red=120.0, sharpness=2.2, tissue_fraction=0.52),
        ]

        reference = build_qc_reference_distribution(
            reports,
            output_path=None,
            metric_names=["mean_red"],
            estimator="robust_mad_z_score",
        )
        metric = reference["metrics"]["mean_red"]

        self.assertEqual(metric["mad"], 0.0)
        self.assertGreater(metric["scaled_mad"], 0.0)
        self.assertLess(metric["warning_min"], 120.0)
        self.assertGreater(metric["warning_max"], 120.0)

    def test_build_qc_reference_distribution_filters_robust_iqr_outliers(self):
        reports = [
            self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=102.0, sharpness=2.1, tissue_fraction=0.51),
            self.qc_report("gen-003", red=104.0, sharpness=2.2, tissue_fraction=0.52),
            self.qc_report("gen-004", red=106.0, sharpness=2.3, tissue_fraction=0.53),
            self.qc_report("gen-005", red=500.0, sharpness=30.0, tissue_fraction=0.95),
        ]

        reference = build_qc_reference_distribution(
            reports,
            output_path=None,
            metric_names=["mean_red"],
            estimator="robust_iqr",
            outlier_policy="robust_iqr_filter",
        )
        metric = reference["metrics"]["mean_red"]
        audit = reference["outlier_audit"]["metrics"]["mean_red"]

        self.assertEqual(reference["outlier_policy"], "robust_iqr_filter")
        self.assertEqual(metric["sample_count"], 4)
        self.assertEqual(metric["observed_max"], 106.0)
        self.assertEqual(audit["original_sample_count"], 5)
        self.assertEqual(audit["kept_sample_count"], 4)
        self.assertEqual(audit["excluded_sample_count"], 1)
        self.assertEqual(audit["excluded_samples"][0]["generated_id"], "gen-005")
        self.assertEqual(audit["excluded_samples"][0]["metric"], "mean_red")
        self.assertEqual(audit["excluded_samples"][0]["value"], 500.0)

    def test_build_qc_reference_distribution_writes_stratified_thresholds(self):
        reports = [
            self.qc_report(
                "breast-001",
                red=100.0,
                sharpness=2.0,
                tissue_fraction=0.50,
                metadata={"cancer_type": "breast", "center_id": "A"},
            ),
            self.qc_report(
                "breast-002",
                red=104.0,
                sharpness=2.1,
                tissue_fraction=0.52,
                metadata={"cancer_type": "breast", "center_id": "A"},
            ),
            self.qc_report(
                "lung-001",
                red=180.0,
                sharpness=3.0,
                tissue_fraction=0.70,
                metadata={"cancer_type": "lung", "center_id": "B"},
            ),
            self.qc_report(
                "lung-002",
                red=184.0,
                sharpness=3.1,
                tissue_fraction=0.72,
                metadata={"cancer_type": "lung", "center_id": "B"},
            ),
        ]

        reference = build_qc_reference_distribution(
            reports,
            output_path=None,
            metric_names=["mean_red"],
            min_samples=2,
            estimator="robust_mad_z_score",
            stratify_by=["metadata.cancer_type"],
        )

        self.assertEqual(reference["stratification"]["enabled"], True)
        self.assertEqual(reference["stratification"]["fields"], ["metadata.cancer_type"])
        self.assertEqual(reference["stratification"]["stratum_count"], 2)
        breast = reference["strata"]["metadata.cancer_type=breast"]
        lung = reference["strata"]["metadata.cancer_type=lung"]
        self.assertEqual(breast["sample_count"], 2)
        self.assertEqual(breast["group_values"], {"metadata.cancer_type": "breast"})
        self.assertEqual(breast["metrics"]["mean_red"]["median"], 102.0)
        self.assertEqual(lung["metrics"]["mean_red"]["median"], 182.0)
        self.assertIn("mean_red", breast["outlier_audit"]["metrics"])
        self.assertEqual(reference["metrics"]["mean_red"]["sample_count"], 4)

    def test_build_qc_reference_distribution_rejects_missing_stratification_field(self):
        reports = [
            self.qc_report(
                "gen-001",
                red=100.0,
                sharpness=2.0,
                tissue_fraction=0.50,
                metadata={"cancer_type": "breast"},
            ),
            self.qc_report("gen-002", red=104.0, sharpness=2.1, tissue_fraction=0.52),
        ]

        with self.assertRaisesRegex(QCReferenceBuildError, "metadata.cancer_type"):
            build_qc_reference_distribution(
                reports,
                output_path=None,
                metric_names=["mean_red"],
                min_samples=1,
                stratify_by=["metadata.cancer_type"],
            )

    def test_build_qc_reference_distribution_errors_when_filter_drops_below_min_samples(self):
        reports = [
            self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50),
            self.qc_report("gen-002", red=102.0, sharpness=2.1, tissue_fraction=0.51),
            self.qc_report("gen-003", red=104.0, sharpness=2.2, tissue_fraction=0.52),
            self.qc_report("gen-004", red=106.0, sharpness=2.3, tissue_fraction=0.53),
            self.qc_report("gen-005", red=500.0, sharpness=30.0, tissue_fraction=0.95),
        ]

        with self.assertRaisesRegex(QCReferenceBuildError, "requires at least 5 samples"):
            build_qc_reference_distribution(
                reports,
                output_path=None,
                metric_names=["mean_red"],
                min_samples=5,
                estimator="robust_iqr",
                outlier_policy="robust_iqr_filter",
            )

    def test_build_qc_reference_distribution_rejects_unknown_outlier_policy(self):
        report = self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50)

        with self.assertRaisesRegex(QCReferenceBuildError, "outlier_policy"):
            build_qc_reference_distribution(
                [report],
                output_path=None,
                metric_names=["mean_red"],
                min_samples=1,
                outlier_policy="unknown",
            )

    def test_build_qc_reference_distribution_rejects_unknown_estimator(self):
        report = self.qc_report("gen-001", red=100.0, sharpness=2.0, tissue_fraction=0.50)

        with self.assertRaisesRegex(QCReferenceBuildError, "estimator"):
            build_qc_reference_distribution(
                [report],
                output_path=None,
                metric_names=["mean_red"],
                min_samples=1,
                estimator="unknown",
            )

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
            for index, (value, cancer_type) in enumerate(
                (
                    (100.0, "breast"),
                    (120.0, "breast"),
                    (140.0, "lung"),
                    (160.0, "lung"),
                ),
                start=1,
            ):
                path = root / f"qc-{index}.json"
                path.write_text(
                    json.dumps(
                        self.qc_report(
                            f"gen-{index:03d}",
                            red=value,
                            sharpness=float(index),
                            tissue_fraction=0.5 + index * 0.05,
                            metadata={"cancer_type": cancer_type},
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
                    "--estimator",
                    "robust_mad_z_score",
                    "--outlier-policy",
                    "robust_iqr_filter",
                    "--stratify-by",
                    "metadata.cancer_type",
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
        self.assertEqual(reference["metrics"]["mean_red"]["sample_count"], 4)
        self.assertEqual(reference["metrics"]["mean_red"]["estimator"], "robust_mad_z_score")
        self.assertEqual(reference["outlier_policy"], "robust_iqr_filter")
        self.assertEqual(reference["stratification"]["fields"], ["metadata.cancer_type"])
        self.assertEqual(reference["stratification"]["stratum_count"], 2)
        self.assertIn("metadata.cancer_type=breast", reference["strata"])


if __name__ == "__main__":
    unittest.main()
