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
) -> dict[str, Any]:
    wsi_path = Path(wsi_path)
    mask_path = Path(mask_path)
    reference = _validate_qc_reference_distribution(qc_reference_distribution)
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
    image_metrics, tile_metrics, image_shape = _image_quality_metrics(wsi_path)
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
    mask_metrics.extend(_mask_quality_metrics(mask_path, image_shape))
    _apply_reference_thresholds(mask_metrics, reference)
    non_copy_metrics = _non_copy_similarity_metrics(wsi_path, mask_path)
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


def _validate_qc_reference_distribution(reference: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    if reference is None:
        return {}
    if not isinstance(reference, dict):
        raise QCReferenceError("qc_reference_distribution must be an object")
    metrics = reference.get("metrics")
    if not isinstance(metrics, dict):
        raise QCReferenceError("qc_reference_distribution.metrics must be an object")
    validated: dict[str, dict[str, float]] = {}
    for name, threshold in metrics.items():
        if not isinstance(name, str) or name == "":
            raise QCReferenceError("qc_reference_distribution metric names must be non-empty strings")
        if not isinstance(threshold, dict):
            raise QCReferenceError(f"qc_reference_distribution.metrics.{name} must be an object")
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


def _apply_reference_thresholds(
    metrics: list[dict[str, Any]],
    reference: dict[str, dict[str, float]],
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


def _image_quality_metrics(wsi_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[int, int] | None]:
    if not wsi_path.exists():
        return [], [], None
    try:
        numpy = _import_numpy()
        tifffile = _import_tifffile()
        with tifffile.TiffFile(wsi_path) as tiff:
            if not tiff.series:
                return [_metric("wsi_readable", "fail", False)], [], None
            array = tiff.series[0].levels[0].asarray()
            level_count = len(tiff.series[0].levels)
    except Exception as exc:
        return [_metric("wsi_readable", "fail", False, str(exc))], [], None

    image = numpy.asarray(array)
    if image.ndim == 2:
        rgb = numpy.stack([image, image, image], axis=2)
    elif image.ndim == 3 and image.shape[2] >= 3:
        rgb = image[..., :3]
    else:
        return [_metric("wsi_readable", "fail", False, "unsupported image shape")], [], None

    rgb_float = rgb.astype("float32")
    red_mean = float(rgb_float[..., 0].mean())
    green_mean = float(rgb_float[..., 1].mean())
    blue_mean = float(rgb_float[..., 2].mean())
    dynamic_range = float(rgb_float.max() - rgb_float.min())
    wsi_metrics = [
        _metric("wsi_readable", "pass", True),
        _metric("ome_tiff_level_count_observed", "pass" if level_count >= 1 else "fail", int(level_count)),
        _metric("mean_red", _range_status(red_mean, 1.0, 254.0), round(red_mean, 4)),
        _metric("mean_green", _range_status(green_mean, 1.0, 254.0), round(green_mean, 4)),
        _metric("mean_blue", _range_status(blue_mean, 1.0, 254.0), round(blue_mean, 4)),
        _metric("rgb_dynamic_range", "pass" if dynamic_range >= 5.0 else "warning", round(dynamic_range, 4)),
        _similarity_metric("style_consistency_proxy", _style_consistency_proxy(numpy, rgb_float)),
    ]
    tile_metrics = [
        _metric(
            "sharpness_laplacian_proxy",
            "pass" if _sharpness_proxy(numpy, rgb_float) > 0 else "warning",
            round(_sharpness_proxy(numpy, rgb_float), 4),
        ),
        _metric("tile_proxy_sample_count", "pass", 1),
        _similarity_metric("seam_score_proxy", _seam_score_proxy(numpy, rgb_float)),
    ]
    return wsi_metrics, tile_metrics, tuple(int(value) for value in rgb.shape[:2])


def _mask_quality_metrics(mask_path: Path, image_shape: tuple[int, int] | None) -> list[dict[str, Any]]:
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
    return metrics


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


def _seam_score_proxy(numpy, rgb_float) -> float:
    height, width = rgb_float.shape[:2]
    if height < 4 or width < 4:
        return 1.0
    differences = []
    x_mid = width // 2
    y_mid = height // 2
    if 0 < x_mid < width:
        vertical = numpy.abs(rgb_float[:, x_mid - 1] - rgb_float[:, x_mid]).mean() / 255.0
        differences.append(float(vertical))
    if 0 < y_mid < height:
        horizontal = numpy.abs(rgb_float[y_mid - 1] - rgb_float[y_mid]).mean() / 255.0
        differences.append(float(horizontal))
    if not differences:
        return 1.0
    similarity = 1.0 - float(numpy.mean(differences))
    return float(max(0.0, min(1.0, similarity)))


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
