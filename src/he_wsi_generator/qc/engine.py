import json
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..schemas import validate_qc_report


class QCReferenceError(ValueError):
    """Raised when QC reference distribution thresholds are invalid."""


def build_qc_report(
    generated_id: str,
    wsi_path: str | Path,
    mask_path: str | Path,
    pyramid_report: dict[str, Any],
    non_copy_items: list[dict[str, Any]],
    qc_reference_distribution: dict[str, Any] | None = None,
    qc_reference_context: dict[str, Any] | None = None,
    wsi_tissue_overview_summary: dict[str, Any] | None = None,
    sampled_layout_mask_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    wsi_path = Path(wsi_path)
    mask_path = Path(mask_path)
    reference = _select_qc_reference_thresholds(
        qc_reference_distribution,
        qc_reference_context,
    )
    file_metrics = [
        {
            "name": "wsi_file_exists",
            "status": "pass" if wsi_path.exists() else "fail",
            "value": bool(wsi_path.exists()),
        },
        {
            "name": "pyramid_level_count",
            "status": "pass" if pyramid_report.get("level_count", 0) >= 1 else "fail",
            "value": int(pyramid_report.get("level_count", 0)),
        },
    ]
    image_metrics, tile_metrics, image_shape, image_tissue_proxy = _image_quality_metrics(
        wsi_path,
        pyramid_report,
    )
    file_metrics.extend(image_metrics)
    _apply_reference_thresholds(file_metrics, reference)
    _apply_reference_thresholds(tile_metrics, reference)
    mask_metrics = [
        {
            "name": "mask_file_exists",
            "status": "pass" if mask_path.exists() else "fail",
            "value": bool(mask_path.exists()),
        }
    ]
    mask_metrics.extend(_mask_quality_metrics(mask_path, image_shape, image_tissue_proxy))
    _apply_reference_thresholds(mask_metrics, reference)
    non_copy_metrics = _non_copy_similarity_metrics(wsi_path, mask_path)
    if wsi_tissue_overview_summary is not None:
        non_copy_metrics.append(
            _wsi_tissue_fraction_reference_metric(
                mask_metrics,
                wsi_tissue_overview_summary,
            )
        )
    if sampled_layout_mask_summary is not None:
        non_copy_metrics.append(
            _sampled_layout_mask_match_metric(
                mask_path,
                sampled_layout_mask_summary,
            )
        )
    overall = _combine_status(file_metrics + tile_metrics + mask_metrics)
    report = {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "overall_status": overall,
        "levels": {
            "wsi": {"status": _combine_status(file_metrics), "metrics": file_metrics},
            "tile": {"status": _combine_status(tile_metrics), "metrics": tile_metrics},
            "mask_region": {"status": _combine_status(mask_metrics), "metrics": mask_metrics},
        },
        "non_copy_report": {
            "enabled": True,
            "patch_nearest_neighbor_search": False,
            "items": non_copy_items,
            "metrics": non_copy_metrics,
        },
    }
    return validate_qc_report(report)


def write_qc_report(report: dict[str, Any], path: str | Path) -> Path:
    validated = validate_qc_report(report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    return target


def _combine_status(metrics: list[dict[str, Any]]) -> str:
    statuses = {metric["status"] for metric in metrics}
    if "fail" in statuses:
        return "fail"
    if "warning" in statuses:
        return "warning"
    return "pass"


def _select_qc_reference_thresholds(
    reference: dict[str, Any] | None,
    context: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if reference is None:
        return {}
    if not isinstance(reference, dict):
        raise QCReferenceError("qc_reference_distribution must be an object")
    global_thresholds = _validate_qc_reference_metrics(reference.get("metrics"), "metrics")
    stratification = reference.get("stratification")
    if not isinstance(stratification, dict) or not stratification.get("enabled"):
        return {
            name: {**threshold, "selection": "global"}
            for name, threshold in global_thresholds.items()
        }

    fields = stratification.get("fields")
    if not isinstance(fields, list) or not all(isinstance(field, str) and field for field in fields):
        raise QCReferenceError("qc_reference_distribution.stratification.fields must be a list")
    strata = reference.get("strata")
    if not isinstance(strata, dict):
        raise QCReferenceError("qc_reference_distribution.strata must be an object")

    key, fallback_reason = _reference_context_key(fields, context)
    if key is not None:
        stratum = strata.get(key)
        if stratum is not None:
            if not isinstance(stratum, dict):
                raise QCReferenceError(f"qc_reference_distribution.strata.{key} must be an object")
            group_values = stratum.get("group_values")
            if not isinstance(group_values, dict):
                raise QCReferenceError(
                    f"qc_reference_distribution.strata.{key}.group_values must be an object"
                )
            stratum_thresholds = _validate_qc_reference_metrics(
                stratum.get("metrics"),
                f"strata.{key}.metrics",
            )
            return {
                name: {
                    **threshold,
                    "selection": "stratified",
                    "stratum_key": key,
                    "stratification_fields": list(fields),
                    "group_values": dict(group_values),
                }
                for name, threshold in stratum_thresholds.items()
            }
        fallback_reason = f"missing_stratum:{key}"

    return {
        name: {
            **threshold,
            "selection": "global_fallback",
            "fallback_reason": fallback_reason,
            "stratification_fields": list(fields),
        }
        for name, threshold in global_thresholds.items()
    }


def _validate_qc_reference_metrics(metrics: Any, path: str) -> dict[str, dict[str, float]]:
    if not isinstance(metrics, dict):
        raise QCReferenceError(f"qc_reference_distribution.{path} must be an object")
    validated: dict[str, dict[str, float]] = {}
    for name, threshold in metrics.items():
        if not isinstance(name, str) or name == "":
            raise QCReferenceError("qc_reference_distribution metric names must be non-empty strings")
        if not isinstance(threshold, dict):
            raise QCReferenceError(f"qc_reference_distribution.{path}.{name} must be an object")
        parsed = {}
        for key in ("warning_min", "warning_max", "fail_min", "fail_max"):
            value = threshold.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise QCReferenceError(f"{name}.{key} must be a number")
            parsed[key] = float(value)
        if not (
            parsed["fail_min"]
            <= parsed["warning_min"]
            <= parsed["warning_max"]
            <= parsed["fail_max"]
        ):
            raise QCReferenceError(
                f"{name} thresholds must satisfy fail_min <= warning_min <= warning_max <= fail_max"
            )
        validated[name] = parsed
    return validated


def _reference_context_key(
    fields: list[str],
    context: dict[str, Any] | None,
) -> tuple[str | None, str]:
    if not isinstance(context, dict):
        return None, f"missing_context_field:{fields[0]}"
    key_parts = []
    for field in fields:
        if field not in context:
            return None, f"missing_context_field:{field}"
        value = context[field]
        if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
            return None, f"invalid_context_field:{field}"
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None, f"invalid_context_field:{field}"
            value = normalized
        elif not isinstance(value, (int, float)):
            return None, f"invalid_context_field:{field}"
        key_parts.append(f"{field}={value}")
    return "|".join(key_parts), ""


def _apply_reference_thresholds(
    metrics: list[dict[str, Any]],
    reference: dict[str, dict[str, Any]],
) -> None:
    for metric in metrics:
        threshold = reference.get(metric["name"])
        if threshold is None:
            continue
        value = metric.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise QCReferenceError(f"reference metric {metric['name']} requires numeric QC value")
        numeric_value = float(value)
        if numeric_value < threshold["fail_min"] or numeric_value > threshold["fail_max"]:
            status = "fail"
        elif numeric_value < threshold["warning_min"] or numeric_value > threshold["warning_max"]:
            status = "warning"
        else:
            status = "pass"
        metric["status"] = status
        metric["reference"] = {
            "warning_min": threshold["warning_min"],
            "warning_max": threshold["warning_max"],
            "fail_min": threshold["fail_min"],
            "fail_max": threshold["fail_max"],
            "source": "qc_reference_distribution",
        }
        for key in ("selection", "stratum_key", "stratification_fields", "group_values", "fallback_reason"):
            if key in threshold:
                metric["reference"][key] = threshold[key]


def _image_quality_metrics(
    wsi_path: Path,
    pyramid_report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[int, int] | None, dict[str, Any] | None]:
    if not wsi_path.exists():
        return [], [], None, None
    try:
        numpy = _import_numpy()
        tifffile = _import_tifffile()
        with tifffile.TiffFile(wsi_path) as tiff:
            if not tiff.series:
                return [_metric("wsi_readable", "fail", False)], [], None, None
            array = tiff.series[0].levels[0].asarray()
            level_count = len(tiff.series[0].levels)
    except Exception as exc:
        return [_metric("wsi_readable", "fail", False, str(exc))], [], None, None

    image = numpy.asarray(array)
    if image.ndim == 2:
        rgb = numpy.stack([image, image, image], axis=2)
    elif image.ndim == 3 and image.shape[2] >= 3:
        rgb = image[..., :3]
    else:
        return [_metric("wsi_readable", "fail", False, "unsupported image shape")], [], None, None

    rgb_float = rgb.astype("float32")
    image_tissue_proxy = _image_tissue_proxy(numpy, rgb_float)
    red_mean = float(rgb_float[..., 0].mean())
    green_mean = float(rgb_float[..., 1].mean())
    blue_mean = float(rgb_float[..., 2].mean())
    dynamic_range = float(rgb_float.max() - rgb_float.min())
    sharpness = _sharpness_proxy(numpy, rgb_float)
    focus_edge_density = _focus_edge_density_proxy(numpy, rgb_float)
    stain_color_separation = _stain_color_separation_proxy(numpy, rgb_float)
    wsi_metrics = [
        _metric("wsi_readable", "pass", True),
        _metric("ome_tiff_level_count_observed", "pass" if level_count >= 1 else "fail", int(level_count)),
        _metric("mean_red", _range_status(red_mean, 1.0, 254.0), round(red_mean, 4)),
        _metric("mean_green", _range_status(green_mean, 1.0, 254.0), round(green_mean, 4)),
        _metric("mean_blue", _range_status(blue_mean, 1.0, 254.0), round(blue_mean, 4)),
        _metric("rgb_dynamic_range", "pass" if dynamic_range >= 5.0 else "warning", round(dynamic_range, 4)),
        _stain_color_separation_metric(stain_color_separation),
        _similarity_metric("style_consistency_proxy", _style_consistency_proxy(numpy, rgb_float)),
    ]
    tile_metrics = [
        _metric(
            "sharpness_laplacian_proxy",
            "pass" if sharpness > 0 else "warning",
            round(sharpness, 4),
        ),
        _focus_edge_density_metric(focus_edge_density),
        _metric("tile_proxy_sample_count", "pass", 1),
        _similarity_metric(
            "seam_score_proxy",
            _seam_score_proxy(numpy, rgb_float, pyramid_report),
        ),
    ]
    return wsi_metrics, tile_metrics, tuple(int(value) for value in rgb.shape[:2]), image_tissue_proxy


def _mask_quality_metrics(
    mask_path: Path,
    image_shape: tuple[int, int] | None,
    image_tissue_proxy: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not mask_path.exists():
        return []
    try:
        numpy = _import_numpy()
        mask = numpy.load(mask_path)
    except Exception as exc:
        return [_metric("mask_readable", "fail", False, str(exc))]

    if mask.ndim != 2:
        return [_metric("mask_readable", "fail", False, "mask must be 2D")]
    unique = [int(value) for value in numpy.unique(mask).tolist()]
    invalid = [value for value in unique if value < 0 or value > 5]
    metrics = [
        _metric("mask_readable", "pass", True),
        _metric("mask_classes_present", "pass" if not invalid else "fail", len(unique)),
        _metric("mask_unique_class_ids", "pass" if not invalid else "fail", unique),
    ]
    if image_shape is None:
        metrics.append(_metric("mask_shape_matches_wsi", "warning", False, "WSI shape unavailable"))
    else:
        expected = tuple(int(value) for value in image_shape)
        actual = tuple(int(value) for value in mask.shape)
        metrics.append(
            _metric(
                "mask_shape_matches_wsi",
                "pass" if actual == expected else "fail",
                actual == expected,
                f"mask_shape={actual}, wsi_shape={expected}",
            )
        )
    tissue_fraction = float((mask > 0).mean())
    metrics.append(
        _metric(
            "mask_tissue_fraction",
            "pass" if 0.0 < tissue_fraction <= 1.0 else "warning",
            round(tissue_fraction, 6),
        )
    )
    metrics.append(_mask_image_tissue_alignment_metric(numpy, mask, image_tissue_proxy))
    return metrics


def _image_tissue_proxy(numpy, rgb_float) -> dict[str, Any]:
    brightness = rgb_float.mean(axis=2)
    min_brightness = float(brightness.min())
    max_brightness = float(brightness.max())
    dynamic_range = max_brightness - min_brightness
    message = None
    # This is a coarse QC proxy, not a pathology segmentation model. Bright
    # high-intensity background is separated when present; otherwise the metric
    # records which global assumption was used so a pass is not over-interpreted.
    if dynamic_range >= 30.0 and max_brightness >= 220.0:
        threshold = min(230.0, min_brightness + dynamic_range * 0.65)
        tissue_mask = brightness < threshold
    elif float(brightness.mean()) < 220.0:
        threshold = None
        tissue_mask = numpy.ones(brightness.shape, dtype=bool)
        message = "image tissue proxy has no bright background candidate; using global tissue assumption"
    else:
        threshold = None
        tissue_mask = numpy.zeros(brightness.shape, dtype=bool)
        message = "image tissue proxy has no foreground candidate; using global background assumption"
    return {
        "mask": tissue_mask,
        "threshold": threshold,
        "message": message,
    }


def _mask_image_tissue_alignment_metric(
    numpy,
    mask,
    image_tissue_proxy: dict[str, Any] | None,
) -> dict[str, Any]:
    if image_tissue_proxy is None:
        return _metric(
            "mask_image_tissue_alignment_proxy",
            "warning",
            None,
            "WSI tissue proxy unavailable; alignment not evaluated",
        )
    image_tissue = image_tissue_proxy["mask"]
    if tuple(mask.shape) != tuple(image_tissue.shape):
        return _metric(
            "mask_image_tissue_alignment_proxy",
            "warning",
            None,
            f"mask_shape={tuple(mask.shape)}, image_tissue_proxy_shape={tuple(image_tissue.shape)}",
        )
    mask_tissue = mask > 0
    union = numpy.logical_or(mask_tissue, image_tissue)
    if union.any():
        score = float(numpy.logical_and(mask_tissue, image_tissue).sum() / union.sum())
    else:
        score = 1.0
    if score >= 0.75:
        status = "pass"
    elif score >= 0.5:
        status = "warning"
    else:
        status = "fail"
    metric = _metric(
        "mask_image_tissue_alignment_proxy",
        status,
        round(score, 6),
        image_tissue_proxy.get("message"),
    )
    metric["mask_tissue_fraction"] = round(float(mask_tissue.mean()), 6)
    metric["image_tissue_fraction"] = round(float(image_tissue.mean()), 6)
    if image_tissue_proxy.get("threshold") is not None:
        metric["image_tissue_brightness_threshold"] = round(float(image_tissue_proxy["threshold"]), 4)
    return metric


def _non_copy_similarity_metrics(wsi_path: Path, mask_path: Path) -> list[dict[str, Any]]:
    if not wsi_path.exists() or not mask_path.exists():
        return []
    try:
        numpy = _import_numpy()
        tifffile = _import_tifffile()
        with tifffile.TiffFile(wsi_path) as tiff:
            if not tiff.series or not tiff.series[0].levels:
                return [_metric("thumbnail_similarity_proxy", "fail", 0.0, "WSI has no levels")]
            first_level = tiff.series[0].levels[0].asarray()
            last_level = tiff.series[0].levels[-1].asarray()
        mask = numpy.load(mask_path)
    except Exception as exc:
        return [
            _metric("thumbnail_similarity_proxy", "fail", 0.0, str(exc)),
            _metric("tissue_contour_similarity_proxy", "fail", 0.0, str(exc)),
            _metric("mask_layout_similarity_proxy", "fail", 0.0, str(exc)),
            _metric("global_embedding_similarity_proxy", "fail", 0.0, str(exc)),
        ]

    first_rgb = _ensure_rgb(numpy, first_level)
    last_rgb = _ensure_rgb(numpy, last_level)
    upsampled_last_rgb = _resize_nearest(
        numpy,
        last_rgb,
        first_rgb.shape[0],
        first_rgb.shape[1],
    )
    thumbnail_similarity = _mean_similarity(numpy, first_rgb, upsampled_last_rgb)

    if mask.ndim != 2:
        mask_layout_similarity = 0.0
        tissue_contour_similarity = 0.0
    else:
        restored_mask = _resize_nearest(
            numpy,
            _resize_nearest(
                numpy,
                mask.astype(numpy.uint8),
                max(1, last_rgb.shape[0]),
                max(1, last_rgb.shape[1]),
            ),
            mask.shape[0],
            mask.shape[1],
        )
        mask_layout_similarity = float((mask == restored_mask).mean())
        tissue = mask > 0
        contour = _binary_contour(numpy, tissue)
        restored_contour = _resize_nearest(
            numpy,
            _resize_nearest(
                numpy,
                contour.astype(numpy.uint8),
                max(1, last_rgb.shape[0]),
                max(1, last_rgb.shape[1]),
            ),
            contour.shape[0],
            contour.shape[1],
        ).astype(bool)
        contour_union = numpy.logical_or(contour, restored_contour)
        if contour_union.any():
            tissue_contour_similarity = float(
                numpy.logical_and(contour, restored_contour).sum() / contour_union.sum()
            )
        else:
            tissue_contour_similarity = 1.0

    first_embedding = numpy.concatenate(
        [
            first_rgb.mean(axis=(0, 1)),
            first_rgb.std(axis=(0, 1)),
        ]
    )
    last_embedding = numpy.concatenate(
        [
            upsampled_last_rgb.mean(axis=(0, 1)),
            upsampled_last_rgb.std(axis=(0, 1)),
        ]
    )
    global_embedding_similarity = _cosine_similarity(numpy, first_embedding, last_embedding)

    return [
        _similarity_metric("thumbnail_similarity_proxy", thumbnail_similarity),
        _similarity_metric("tissue_contour_similarity_proxy", tissue_contour_similarity),
        _similarity_metric("mask_layout_similarity_proxy", mask_layout_similarity),
        _similarity_metric("global_embedding_similarity_proxy", global_embedding_similarity),
    ]


def _wsi_tissue_fraction_reference_metric(
    mask_metrics: list[dict[str, Any]],
    overview: dict[str, Any],
) -> dict[str, Any]:
    reference_record = _first_wsi_tissue_overview_record(overview)
    reference_fraction = _require_number(
        reference_record,
        "tissue_fraction",
        "wsi_tissue_overview_summary.records[0].tissue_fraction",
    )
    generated_fraction = _mask_tissue_fraction_from_metrics(mask_metrics)
    difference = abs(float(generated_fraction) - float(reference_fraction))
    proxy = max(0.0, min(1.0, 1.0 - difference))
    metric = _similarity_metric("wsi_tissue_fraction_reference_proxy", proxy)
    metric["generated_mask_fraction"] = round(float(generated_fraction), 6)
    metric["reference"] = {
        "source": "wsi_tissue_overview",
        "wsi_id": reference_record.get("wsi_id"),
        "tissue_fraction": float(reference_fraction),
        "bounding_box_xywh": list(reference_record.get("bounding_box_xywh", [])),
        "connected_component_count": reference_record.get("connected_component_count"),
    }
    return metric


def _first_wsi_tissue_overview_record(overview: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(overview, dict):
        raise QCReferenceError("wsi_tissue_overview_summary must be an object")
    records = overview.get("records")
    if not isinstance(records, list) or not records:
        raise QCReferenceError("wsi_tissue_overview_summary.records must be a non-empty list")
    record = records[0]
    if not isinstance(record, dict):
        raise QCReferenceError("wsi_tissue_overview_summary.records[0] must be an object")
    return record


def _sampled_layout_mask_match_metric(
    generated_mask_path: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        raise QCReferenceError("sampled_layout_mask_summary must be an object")
    sampled_mask_path = Path(
        _require_string(
            summary,
            "mask_path",
            "sampled_layout_mask_summary.mask_path",
        )
    )
    if not sampled_mask_path.exists():
        raise QCReferenceError(f"sampled layout mask file does not exist: {sampled_mask_path}")
    try:
        numpy = _import_numpy()
        generated_mask = numpy.load(generated_mask_path)
        sampled_mask = numpy.load(sampled_mask_path)
    except Exception as exc:
        raise QCReferenceError("sampled layout mask comparison requires readable .npy masks") from exc
    if generated_mask.ndim != 2 or sampled_mask.ndim != 2:
        raise QCReferenceError("sampled layout mask comparison requires 2D masks")
    if generated_mask.shape != sampled_mask.shape:
        sampled_mask = _resize_nearest(
            numpy,
            sampled_mask.astype(numpy.uint8),
            int(generated_mask.shape[0]),
            int(generated_mask.shape[1]),
        )
    matched_fraction = float((generated_mask == sampled_mask).mean())
    metric = _similarity_metric("sampled_layout_mask_match_proxy", matched_fraction)
    metric["matched_pixel_fraction"] = round(matched_fraction, 6)
    metric["reference"] = {
        "source": "sampled_layout_mask",
        "artifact_path": summary.get("artifact_path"),
        "mask_path": str(sampled_mask_path),
        "sample_id": summary.get("sample_id"),
        "mask_shape": list(summary.get("mask_shape", [])),
        "class_pixel_counts_by_id": list(summary.get("class_pixel_counts_by_id", [])),
        "class_fractions_by_id": list(summary.get("class_fractions_by_id", [])),
    }
    return metric


def _mask_tissue_fraction_from_metrics(mask_metrics: list[dict[str, Any]]) -> float:
    for metric in mask_metrics:
        if metric.get("name") == "mask_tissue_fraction":
            value = metric.get("value")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            raise QCReferenceError("mask_tissue_fraction metric must be numeric")
    raise QCReferenceError("mask_tissue_fraction metric is required for tissue overview QC")


def _require_number(data: dict[str, Any], key: str, path: str) -> int | float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise QCReferenceError(f"{path} must be a number")
    return value


def _require_string(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise QCReferenceError(f"{path} must be a non-empty string")
    return value


def _sharpness_proxy(numpy, rgb_float) -> float:
    gray = rgb_float.mean(axis=2)
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 1.0
    laplacian = (
        -4 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    return float(numpy.abs(laplacian).mean())


def _focus_edge_density_proxy(numpy, rgb_float) -> float:
    gray = rgb_float.mean(axis=2)
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 1.0
    horizontal = numpy.abs(gray[:, 1:] - gray[:, :-1]).mean()
    vertical = numpy.abs(gray[1:, :] - gray[:-1, :]).mean()
    return float(((horizontal + vertical) / 2.0) / 255.0)


def _focus_edge_density_metric(value: float) -> dict[str, Any]:
    if value < 0.0005:
        return _metric(
            "focus_edge_density_proxy",
            "fail",
            round(value, 6),
            "focus proxy found almost no local edge contrast",
        )
    if value < 0.001:
        return _metric(
            "focus_edge_density_proxy",
            "warning",
            round(value, 6),
            "focus proxy found weak local edge contrast",
        )
    return _metric("focus_edge_density_proxy", "pass", round(value, 6))


def _stain_color_separation_proxy(numpy, rgb_float) -> float:
    if rgb_float.size == 0:
        return 1.0
    channel_spread = rgb_float.max(axis=2) - rgb_float.min(axis=2)
    return float(channel_spread.mean() / 255.0)


def _stain_color_separation_metric(value: float) -> dict[str, Any]:
    if value < 0.02:
        return _metric(
            "stain_color_separation_proxy",
            "fail",
            round(value, 6),
            "stain proxy found near-monochrome RGB channels",
        )
    if value < 0.05:
        return _metric(
            "stain_color_separation_proxy",
            "warning",
            round(value, 6),
            "stain proxy found weak RGB channel separation",
        )
    return _metric("stain_color_separation_proxy", "pass", round(value, 6))


def _style_consistency_proxy(numpy, rgb_float) -> float:
    height, width = rgb_float.shape[:2]
    if height < 4 or width < 4:
        return 1.0
    y_mid = height // 2
    x_mid = width // 2
    quadrants = [
        rgb_float[:y_mid, :x_mid],
        rgb_float[:y_mid, x_mid:],
        rgb_float[y_mid:, :x_mid],
        rgb_float[y_mid:, x_mid:],
    ]
    quadrant_means = [quadrant.mean(axis=(0, 1)) for quadrant in quadrants if quadrant.size > 0]
    if len(quadrant_means) < 2:
        return 1.0
    global_mean = rgb_float.mean(axis=(0, 1))
    distances = [numpy.linalg.norm(mean - global_mean) for mean in quadrant_means]
    max_distance = float(numpy.linalg.norm(numpy.array([255.0, 255.0, 255.0])))
    similarity = 1.0 - float(numpy.mean(distances) / max_distance)
    return float(max(0.0, min(1.0, similarity)))


def _seam_score_proxy(numpy, rgb_float, pyramid_report: dict[str, Any]) -> float:
    height, width = rgb_float.shape[:2]
    if height < 4 or width < 4:
        return 1.0
    differences = []
    x_positions, y_positions = _seam_boundary_positions(pyramid_report, width, height)
    for x_position in x_positions:
        vertical = numpy.abs(
            rgb_float[:, x_position - 1] - rgb_float[:, x_position]
        ).mean() / 255.0
        differences.append(float(vertical))
    for y_position in y_positions:
        horizontal = numpy.abs(
            rgb_float[y_position - 1] - rgb_float[y_position]
        ).mean() / 255.0
        differences.append(float(horizontal))
    if not differences:
        return 1.0
    similarity = 1.0 - float(numpy.mean(differences))
    return float(max(0.0, min(1.0, similarity)))


def _seam_boundary_positions(
    pyramid_report: dict[str, Any],
    width: int,
    height: int,
) -> tuple[list[int], list[int]]:
    chunk_shape = _seam_chunk_shape_from_report(pyramid_report)
    if chunk_shape is None:
        return _fallback_midline_positions(width, height)
    chunk_height, chunk_width = chunk_shape
    x_positions = [x for x in range(chunk_width, width, chunk_width) if 0 < x < width]
    y_positions = [y for y in range(chunk_height, height, chunk_height) if 0 < y < height]
    if not x_positions and not y_positions:
        return _fallback_midline_positions(width, height)
    return x_positions, y_positions


def _seam_chunk_shape_from_report(pyramid_report: dict[str, Any]) -> tuple[int, int] | None:
    chunked = pyramid_report.get("chunked_write_audit")
    if isinstance(chunked, dict):
        levels = chunked.get("levels")
        if isinstance(levels, list) and levels and isinstance(levels[0], dict):
            parsed = _parse_positive_pair(levels[0].get("chunk_shape"))
            if parsed is not None:
                return parsed
        parsed = _parse_positive_pair(chunked.get("chunk_shape"))
        if parsed is not None:
            return parsed

    streaming = pyramid_report.get("streaming_write_report")
    if isinstance(streaming, dict):
        parsed = _parse_positive_pair(streaming.get("tile_shape"))
        if parsed is not None:
            return parsed
    return None


def _parse_positive_pair(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    first, second = value
    if not all(
        isinstance(item, int) and not isinstance(item, bool) and item > 0
        for item in (first, second)
    ):
        return None
    return int(first), int(second)


def _fallback_midline_positions(width: int, height: int) -> tuple[list[int], list[int]]:
    x_mid = width // 2
    y_mid = height // 2
    return (
        [x_mid] if 0 < x_mid < width else [],
        [y_mid] if 0 < y_mid < height else [],
    )


def _ensure_rgb(numpy, array):
    image = numpy.asarray(array)
    if image.ndim == 2:
        return numpy.stack([image, image, image], axis=2)
    if image.ndim == 3 and image.shape[2] >= 3:
        return image[..., :3]
    raise ValueError("unsupported RGB image shape")


def _resize_nearest(numpy, array, height: int, width: int):
    if array.ndim not in {2, 3}:
        raise ValueError("resize input must be 2D or 3D")
    y_index = (numpy.arange(height) * array.shape[0] / height).astype(numpy.int64)
    x_index = (numpy.arange(width) * array.shape[1] / width).astype(numpy.int64)
    return array[y_index[:, None], x_index[None, :]]


def _binary_contour(numpy, mask):
    tissue = numpy.asarray(mask, dtype=bool)
    if tissue.shape[0] < 3 or tissue.shape[1] < 3:
        return tissue
    eroded = tissue[1:-1, 1:-1].copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            eroded &= tissue[1 + dy : tissue.shape[0] - 1 + dy, 1 + dx : tissue.shape[1] - 1 + dx]
    contour = numpy.zeros_like(tissue, dtype=bool)
    contour[1:-1, 1:-1] = tissue[1:-1, 1:-1] & ~eroded
    return contour


def _mean_similarity(numpy, left, right) -> float:
    left_float = left.astype("float32")
    right_float = right.astype("float32")
    difference = numpy.abs(left_float - right_float).mean() / 255.0
    return float(max(0.0, min(1.0, 1.0 - difference)))


def _cosine_similarity(numpy, left, right) -> float:
    left_vec = left.astype("float32").ravel()
    right_vec = right.astype("float32").ravel()
    denominator = float(numpy.linalg.norm(left_vec) * numpy.linalg.norm(right_vec))
    if denominator == 0.0:
        return 1.0
    similarity = float(numpy.dot(left_vec, right_vec) / denominator)
    return max(0.0, min(1.0, similarity))


def _similarity_metric(name: str, value: float) -> dict[str, Any]:
    if value >= 0.9:
        status = "pass"
    elif value >= 0.75:
        status = "warning"
    else:
        status = "fail"
    return _metric(name, status, round(value, 6))


def _range_status(value: float, low: float, high: float) -> str:
    return "pass" if low <= value <= high else "warning"


def _metric(name: str, status: str, value: Any, message: str | None = None) -> dict[str, Any]:
    metric = {"name": name, "status": status, "value": value}
    if message:
        metric["message"] = message
    return metric


def _import_numpy():
    import numpy

    return numpy


def _import_tifffile():
    import tifffile

    return tifffile
