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
    estimator: str = "observed_min_max_with_range_margin",
    outlier_policy: str = "none",
    stratify_by: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(qc_reports, list) or not qc_reports:
        raise QCReferenceBuildError("qc_reports must contain at least one report")
    if not isinstance(metric_names, list) or not metric_names:
        raise QCReferenceBuildError("metric_names must contain at least one metric")
    if not isinstance(min_samples, int) or isinstance(min_samples, bool) or min_samples <= 0:
        raise QCReferenceBuildError("min_samples must be a positive integer")
    if estimator not in {
        "observed_min_max_with_range_margin",
        "robust_iqr",
        "robust_mad_z_score",
    }:
        raise QCReferenceBuildError(
            "estimator must be observed_min_max_with_range_margin, robust_iqr, "
            "or robust_mad_z_score"
        )
    if outlier_policy not in {"none", "robust_iqr_filter"}:
        raise QCReferenceBuildError("outlier_policy must be none or robust_iqr_filter")
    strata_fields = _validate_stratify_by(stratify_by)

    samples_by_metric = {name: [] for name in metric_names}
    stratum_samples: dict[str, dict[str, Any]] = {}
    for report in qc_reports:
        validated = validate_qc_report(report)
        numeric_metrics = _numeric_metrics(validated)
        for name in metric_names:
            if name not in numeric_metrics:
                raise QCReferenceBuildError(
                    f"missing metric {name} in QC report {validated['generated_id']}"
                )
            samples_by_metric[name].append(
                {
                    "generated_id": validated["generated_id"],
                    "value": numeric_metrics[name],
                }
            )
        if strata_fields:
            key, group_values = _stratum_key(validated, strata_fields)
            bucket = stratum_samples.setdefault(
                key,
                {
                    "group_values": group_values,
                    "samples_by_metric": {name: [] for name in metric_names},
                    "sample_ids": [],
                },
            )
            bucket["sample_ids"].append(validated["generated_id"])
            for name in metric_names:
                bucket["samples_by_metric"][name].append(
                    {
                        "generated_id": validated["generated_id"],
                        "value": numeric_metrics[name],
                    }
                )

    metrics, outlier_audit = _build_metric_thresholds_and_audit(
        samples_by_metric=samples_by_metric,
        min_samples=min_samples,
        estimator=estimator,
        outlier_policy=outlier_policy,
    )
    strata = {}
    if strata_fields:
        for key in sorted(stratum_samples):
            bucket = stratum_samples[key]
            stratum_metrics, stratum_audit = _build_metric_thresholds_and_audit(
                samples_by_metric=bucket["samples_by_metric"],
                min_samples=min_samples,
                estimator=estimator,
                outlier_policy=outlier_policy,
                error_prefix=f"stratum {key} ",
            )
            strata[key] = {
                "group_values": bucket["group_values"],
                "sample_count": len(bucket["sample_ids"]),
                "sample_ids": list(bucket["sample_ids"]),
                "outlier_policy": outlier_policy,
                "outlier_audit": stratum_audit,
                "metrics": stratum_metrics,
            }

    reference = {
        "schema_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "source": "qc_report_metric_distribution",
        "sample_count": len(qc_reports),
        "outlier_policy": outlier_policy,
        "outlier_audit": outlier_audit,
        "stratification": {
            "enabled": bool(strata_fields),
            "fields": strata_fields,
            "stratum_count": len(strata),
            "key_format": "field=value joined by | in requested field order",
        },
        "metrics": metrics,
    }
    if strata_fields:
        reference["strata"] = strata
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


def _thresholds(values: list[float], estimator: str) -> dict[str, Any]:
    if estimator == "robust_iqr":
        return _robust_iqr_thresholds(values)
    if estimator == "robust_mad_z_score":
        return _robust_mad_z_score_thresholds(values)
    return _observed_min_max_thresholds(values)


def _build_metric_thresholds_and_audit(
    samples_by_metric: dict[str, list[dict[str, Any]]],
    min_samples: int,
    estimator: str,
    outlier_policy: str,
    error_prefix: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics = {}
    outlier_audit = {"policy": outlier_policy, "metrics": {}}
    filtered_by_metric = _apply_outlier_policy(samples_by_metric, outlier_policy)
    for name, result in filtered_by_metric.items():
        values = [sample["value"] for sample in result["kept_samples"]]
        if len(values) < min_samples:
            raise QCReferenceBuildError(
                f"{error_prefix}metric {name} requires at least {min_samples} samples"
            )
        metrics[name] = _thresholds(values, estimator)
        outlier_audit["metrics"][name] = {
            "original_sample_count": result["original_sample_count"],
            "kept_sample_count": len(result["kept_samples"]),
            "excluded_sample_count": len(result["excluded_samples"]),
            "filter": result["filter"],
            "excluded_samples": result["excluded_samples"],
        }
    return metrics, outlier_audit


def _apply_outlier_policy(
    samples_by_metric: dict[str, list[dict[str, Any]]],
    outlier_policy: str,
) -> dict[str, dict[str, Any]]:
    if outlier_policy == "none":
        return {
            name: {
                "original_sample_count": len(samples),
                "kept_samples": list(samples),
                "excluded_samples": [],
                "filter": None,
            }
            for name, samples in samples_by_metric.items()
        }
    return {
        name: _robust_iqr_filter_samples(name, samples)
        for name, samples in samples_by_metric.items()
    }


def _robust_iqr_filter_samples(
    metric_name: str,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    values = [float(sample["value"]) for sample in samples]
    ordered = sorted(values)
    q1 = _percentile(ordered, 0.25)
    q3 = _percentile(ordered, 0.75)
    iqr = q3 - q1
    margin_source = iqr if iqr > 0 else max(abs(_percentile(ordered, 0.5)) * 0.1, 1.0)
    lower = q1 - 1.5 * margin_source
    upper = q3 + 1.5 * margin_source
    kept_samples = []
    excluded_samples = []
    for sample in samples:
        value = float(sample["value"])
        if lower <= value <= upper:
            kept_samples.append(sample)
        else:
            excluded_samples.append(
                {
                    "generated_id": sample["generated_id"],
                    "metric": metric_name,
                    "value": round(value, 6),
                    "lower_fence": round(lower, 6),
                    "upper_fence": round(upper, 6),
                }
            )
    return {
        "original_sample_count": len(samples),
        "kept_samples": kept_samples,
        "excluded_samples": excluded_samples,
        "filter": {
            "method": "robust_iqr_filter",
            "q1": round(q1, 6),
            "q3": round(q3, 6),
            "iqr": round(iqr, 6),
            "lower_fence": round(lower, 6),
            "upper_fence": round(upper, 6),
        },
    }


def _observed_min_max_thresholds(values: list[float]) -> dict[str, Any]:
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


def _robust_iqr_thresholds(values: list[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    observed_min = ordered[0]
    observed_max = ordered[-1]
    q1 = _percentile(ordered, 0.25)
    median = _percentile(ordered, 0.5)
    q3 = _percentile(ordered, 0.75)
    iqr = q3 - q1
    margin_source = iqr if iqr > 0 else max(abs(median) * 0.1, 1.0)
    warning_min = q1 - 1.5 * margin_source
    warning_max = q3 + 1.5 * margin_source
    fail_min = q1 - 3.0 * margin_source
    fail_max = q3 + 3.0 * margin_source
    return {
        "warning_min": round(warning_min, 6),
        "warning_max": round(warning_max, 6),
        "fail_min": round(fail_min, 6),
        "fail_max": round(fail_max, 6),
        "sample_count": len(values),
        "observed_min": round(observed_min, 6),
        "observed_max": round(observed_max, 6),
        "q1": round(q1, 6),
        "median": round(median, 6),
        "q3": round(q3, 6),
        "iqr": round(iqr, 6),
        "estimator": "robust_iqr",
    }


def _robust_mad_z_score_thresholds(values: list[float]) -> dict[str, Any]:
    ordered = sorted(float(value) for value in values)
    observed_min = ordered[0]
    observed_max = ordered[-1]
    median = _percentile(ordered, 0.5)
    deviations = sorted(abs(value - median) for value in ordered)
    mad = _percentile(deviations, 0.5)
    # 1.4826 scales MAD to match a normal-distribution standard deviation.
    # If all reference values are identical, keep a finite margin so warning/fail
    # intervals still expose future drift instead of collapsing to one point.
    scaled_mad = 1.4826 * mad if mad > 0 else max(abs(median) * 0.1, 1.0)
    warning_z_score = 3.0
    fail_z_score = 6.0
    warning_min = median - warning_z_score * scaled_mad
    warning_max = median + warning_z_score * scaled_mad
    fail_min = median - fail_z_score * scaled_mad
    fail_max = median + fail_z_score * scaled_mad
    return {
        "warning_min": round(warning_min, 6),
        "warning_max": round(warning_max, 6),
        "fail_min": round(fail_min, 6),
        "fail_max": round(fail_max, 6),
        "sample_count": len(values),
        "observed_min": round(observed_min, 6),
        "observed_max": round(observed_max, 6),
        "median": round(median, 6),
        "mad": round(mad, 6),
        "scaled_mad": round(scaled_mad, 6),
        "warning_z_score": warning_z_score,
        "fail_z_score": fail_z_score,
        "estimator": "robust_mad_z_score",
    }


def _percentile(ordered_values: list[float], fraction: float) -> float:
    if not ordered_values:
        raise QCReferenceBuildError("percentile requires at least one value")
    if len(ordered_values) == 1:
        return float(ordered_values[0])
    position = (len(ordered_values) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    weight = position - lower_index
    lower = ordered_values[lower_index]
    upper = ordered_values[upper_index]
    return float(lower + (upper - lower) * weight)


def _validate_stratify_by(stratify_by: list[str] | None) -> list[str]:
    if stratify_by is None:
        return []
    if not isinstance(stratify_by, list):
        raise QCReferenceBuildError("stratify_by must be a list of dot-path strings")
    fields = []
    seen = set()
    for field in stratify_by:
        if not isinstance(field, str) or not field.strip():
            raise QCReferenceBuildError("stratify_by fields must be non-empty strings")
        normalized = field.strip()
        parts = normalized.split(".")
        if any(part == "" for part in parts):
            raise QCReferenceBuildError(f"stratify_by field {normalized!r} is not a valid dot path")
        if normalized in seen:
            raise QCReferenceBuildError(f"duplicate stratify_by field {normalized}")
        seen.add(normalized)
        fields.append(normalized)
    return fields


def _stratum_key(report: dict[str, Any], fields: list[str]) -> tuple[str, dict[str, Any]]:
    group_values = {}
    key_parts = []
    generated_id = report["generated_id"]
    for field in fields:
        value = _read_dot_path(report, field, generated_id)
        normalized = _normalize_group_value(value, field, generated_id)
        group_values[field] = normalized
        key_parts.append(f"{field}={normalized}")
    return "|".join(key_parts), group_values


def _read_dot_path(report: dict[str, Any], field: str, generated_id: str) -> Any:
    current: Any = report
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            raise QCReferenceBuildError(
                f"stratification field {field} is missing in QC report {generated_id}"
            )
        current = current[part]
    return current


def _normalize_group_value(value: Any, field: str, generated_id: str) -> str | int | float:
    # Stratification values become audit keys, so only scalar, explicit values
    # are accepted. Missing/null/empty/group-object values are rejected instead
    # of being silently collapsed into an unknown bucket.
    if value is None:
        raise QCReferenceBuildError(
            f"stratification field {field} is null in QC report {generated_id}"
        )
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        raise QCReferenceBuildError(
            f"stratification field {field} in QC report {generated_id} must be a string or number"
        )
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise QCReferenceBuildError(
                f"stratification field {field} is empty in QC report {generated_id}"
            )
        return normalized
    if isinstance(value, (int, float)):
        return value
    raise QCReferenceBuildError(
        f"stratification field {field} in QC report {generated_id} must be a string or number"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
