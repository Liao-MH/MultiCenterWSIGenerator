import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..schemas import validate_qc_report


class QCReferenceBuildError(ValueError):
    """Raised when QC reports cannot define a usable reference distribution."""


def build_qc_reference_distribution(
    qc_reports: list[dict[str, Any]],
    output_path: str | Path | None,
    metric_names: list[str],
    min_samples: int = 2,
) -> dict[str, Any]:
    if not isinstance(qc_reports, list) or not qc_reports:
        raise QCReferenceBuildError("qc_reports must contain at least one report")
    if not isinstance(metric_names, list) or not metric_names:
        raise QCReferenceBuildError("metric_names must contain at least one metric")
    if not isinstance(min_samples, int) or isinstance(min_samples, bool) or min_samples <= 0:
        raise QCReferenceBuildError("min_samples must be a positive integer")

    values_by_metric = {name: [] for name in metric_names}
    for report in qc_reports:
        validated = validate_qc_report(report)
        numeric_metrics = _numeric_metrics(validated)
        for name in metric_names:
            if name not in numeric_metrics:
                raise QCReferenceBuildError(
                    f"missing metric {name} in QC report {validated['generated_id']}"
                )
            values_by_metric[name].append(numeric_metrics[name])

    metrics = {}
    for name, values in values_by_metric.items():
        if len(values) < min_samples:
            raise QCReferenceBuildError(f"metric {name} requires at least {min_samples} samples")
        metrics[name] = _thresholds(values)

    reference = {
        "schema_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "source": "qc_report_metric_distribution",
        "sample_count": len(qc_reports),
        "metrics": metrics,
    }
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(reference, indent=2) + "\n", encoding="utf-8")
    return reference


def _numeric_metrics(qc_report: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for level in qc_report["levels"].values():
        for metric in level["metrics"]:
            value = metric.get("value")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[metric["name"]] = float(value)
    return metrics


def _thresholds(values: list[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    observed_min = ordered[0]
    observed_max = ordered[-1]
    span = observed_max - observed_min
    margin = span if span > 0 else max(abs(observed_min) * 0.1, 1.0)
    return {
        "warning_min": round(observed_min, 6),
        "warning_max": round(observed_max, 6),
        "fail_min": round(observed_min - margin, 6),
        "fail_max": round(observed_max + margin, 6),
        "sample_count": len(values),
        "observed_min": round(observed_min, 6),
        "observed_max": round(observed_max, 6),
        "estimator": "observed_min_max_with_range_margin",
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
