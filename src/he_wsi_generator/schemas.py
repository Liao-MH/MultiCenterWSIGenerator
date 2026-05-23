import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import (
    CASCADE_LEVELS,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    MODEL_FAMILY,
    PROJECT_VERSION,
    SOURCE_ANCHORED_PRESETS,
    STATUS_LEVELS,
    TILE_SIZE_40X,
)


class ValidationError(ValueError):
    """Raised when a project schema violates the documented data contract."""


def load_document(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise ValidationError(f"{source} does not exist")
    if not source.is_file():
        raise ValidationError(f"{source} is not a file")

    suffix = source.suffix.lower()
    text = source.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{source} is not valid JSON: {exc.msg}") from exc
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValidationError(
                "YAML files require PyYAML; install the optional yaml dependency or use JSON"
            ) from exc
        data = yaml.safe_load(text)
    else:
        raise ValidationError(f"{source} must be a .json, .yaml, or .yml file")

    return _ensure_mapping(data, "document")


def validate_file(kind: str, path: str | Path) -> dict[str, Any]:
    validators = {
        "manifest": validate_input_manifest,
        "input-manifest": validate_input_manifest,
        "label-mapping": validate_label_mapping,
        "generation-config": validate_generation_config,
        "metadata": validate_metadata,
        "qc": validate_qc_report,
        "qc-report": validate_qc_report,
    }
    validator = validators.get(kind)
    if validator is None:
        valid = ", ".join(sorted(validators))
        raise ValidationError(f"unknown schema kind {kind!r}; expected one of: {valid}")
    return validator(load_document(path))


def validate_input_manifest(data: dict[str, Any]) -> dict[str, Any]:
    manifest = _ensure_mapping(data, "manifest")
    _require_schema_version(manifest)
    _require_non_empty_str(manifest, "dataset_id", "dataset_id")
    _require_non_empty_str(manifest, "created_at", "created_at")

    records = _require_list(manifest, "records", "records")
    if not records:
        raise ValidationError("records must contain at least one WSI record")

    for index, record_value in enumerate(records):
        path = f"records[{index}]"
        record = _ensure_mapping(record_value, path)
        _require_non_empty_str(record, "wsi_id", f"{path}.wsi_id")
        _require_non_empty_str(record, "wsi_path", f"{path}.wsi_path")
        _require_non_empty_str(record, "cancer_type", f"{path}.cancer_type")
        split = _require_non_empty_str(record, "split", f"{path}.split")
        if split not in {"train", "val", "test", "unassigned"}:
            raise ValidationError(
                f"{path}.split must be one of train, val, test, unassigned"
            )
        if "mpp_x" in record and record["mpp_x"] is not None:
            _require_positive_number(record, "mpp_x", f"{path}.mpp_x")
        if "mpp_y" in record and record["mpp_y"] is not None:
            _require_positive_number(record, "mpp_y", f"{path}.mpp_y")
        if "max_magnification" in record and record["max_magnification"] is not None:
            max_mag = _require_non_empty_str(
                record, "max_magnification", f"{path}.max_magnification"
            )
            if max_mag != MAX_MAGNIFICATION:
                raise ValidationError(f"{path}.max_magnification must be {MAX_MAGNIFICATION}")
        annotations = record.get("annotations", [])
        if not isinstance(annotations, list):
            raise ValidationError(f"{path}.annotations must be a list")
        for ann_index, annotation_value in enumerate(annotations):
            _validate_annotation_record(annotation_value, f"{path}.annotations[{ann_index}]")

    return deepcopy(manifest)


def validate_label_mapping(data: dict[str, Any]) -> dict[str, Any]:
    mapping = _ensure_mapping(data, "label_mapping")
    _require_schema_version(mapping)
    _require_non_empty_str(mapping, "wsi_id", "wsi_id")
    _require_non_empty_str(mapping, "source_annotation_id", "source_annotation_id")
    classes = _ensure_mapping(_require(mapping, "classes", "classes"), "classes")
    if not classes:
        raise ValidationError("classes must map at least one source label")

    valid_classes = set(MASK_CLASSES)
    for label, class_name in classes.items():
        if not isinstance(label, str) or label == "":
            raise ValidationError("classes keys must be non-empty strings")
        if class_name not in valid_classes:
            raise ValidationError(f"classes.{label} has invalid mask class {class_name!r}")

    mapping_source = _require_non_empty_str(mapping, "mapping_source", "mapping_source")
    if mapping_source not in {"manual", "roi", "cluster", "mixed"}:
        raise ValidationError("mapping_source must be manual, roi, cluster, or mixed")

    confidence = _ensure_mapping(_require(mapping, "confidence", "confidence"), "confidence")
    for label, value in confidence.items():
        if label not in classes:
            raise ValidationError(f"confidence.{label} does not refer to a mapped class")
        if value not in {"high", "medium", "low"}:
            raise ValidationError(f"confidence.{label} must be high, medium, or low")

    return deepcopy(mapping)


def validate_generation_config(data: dict[str, Any]) -> dict[str, Any]:
    config = _ensure_mapping(data, "generation_config")
    _require_schema_version(config)
    _require_int(config, "random_seed", "random_seed")
    model_family = _require_non_empty_str(config, "model_family", "model_family")
    if model_family != MODEL_FAMILY:
        raise ValidationError(f"model_family must be {MODEL_FAMILY}")
    max_mag = _require_non_empty_str(config, "max_magnification", "max_magnification")
    if max_mag != MAX_MAGNIFICATION:
        raise ValidationError(f"max_magnification must be {MAX_MAGNIFICATION}")
    _validate_tile_size(_require(config, "tile_size_40x", "tile_size_40x"), "tile_size_40x")
    if "canvas_size_40x" in config:
        _validate_canvas_size(config["canvas_size_40x"], "canvas_size_40x")
    _validate_cascade_levels(
        _require(config, "cascade_levels", "cascade_levels"), "cascade_levels"
    )
    anchor = _require_number(config, "structure_anchor", "structure_anchor")
    _validate_anchor(anchor)
    preset = _require_non_empty_str(config, "anchor_preset", "anchor_preset")
    if preset not in {"rescan_simulation", "structure_preserving", "layout_recombination", "fully_de_novo"}:
        raise ValidationError("anchor_preset has unsupported value")
    _require(config, "style_seed", "style_seed")
    source_wsi_id = config.get("source_wsi_id")
    if _requires_source(anchor, preset) and not _is_non_empty_str(source_wsi_id):
        raise ValidationError("source_wsi_id is required for source-anchored generation")
    sample_steps = _require_int(config, "sample_steps", "sample_steps")
    if sample_steps <= 0:
        raise ValidationError("sample_steps must be a positive integer")
    overlap = _require_int(config, "overlap_px_40x", "overlap_px_40x")
    if overlap < 0:
        raise ValidationError("overlap_px_40x must be a non-negative integer")
    non_copy = _require_bool(
        config,
        "non_copy_patch_nearest_neighbor_search",
        "non_copy_patch_nearest_neighbor_search",
    )
    if non_copy:
        raise ValidationError(
            "non_copy_patch_nearest_neighbor_search must be false in v0.60.0"
        )
    return deepcopy(config)


def validate_metadata(data: dict[str, Any]) -> dict[str, Any]:
    metadata = _ensure_mapping(data, "metadata")
    _require_schema_version(metadata)
    _require_non_empty_str(metadata, "generated_id", "generated_id")
    version = _require_non_empty_str(metadata, "version", "version")
    if version != PROJECT_VERSION:
        raise ValidationError(f"version must be {PROJECT_VERSION}")
    _require_non_empty_str(metadata, "created_at", "created_at")

    output = _ensure_mapping(_require(metadata, "output", "output"), "output")
    _require_non_empty_str(output, "wsi_path", "output.wsi_path")
    _require_non_empty_str(output, "mask_path", "output.mask_path")
    _require_non_empty_str(output, "qc_json_path", "output.qc_json_path")

    source = _ensure_mapping(_require(metadata, "source", "source"), "source")
    generation = _ensure_mapping(_require(metadata, "generation", "generation"), "generation")
    anchor = _require_number(generation, "structure_anchor", "generation.structure_anchor")
    _validate_anchor(anchor)
    if anchor > 0.3 and not _is_non_empty_str(source.get("source_wsi_id")):
        raise ValidationError(
            "source.source_wsi_id is required when generation.structure_anchor > 0.3"
        )
    _require(generation, "style_seed", "generation.style_seed")
    _require_int(generation, "random_seed", "generation.random_seed")
    _require_non_empty_str(generation, "model_checkpoint", "generation.model_checkpoint")
    _require_non_empty_str(generation, "model_version", "generation.model_version")
    _validate_cascade_levels(
        _require(generation, "cascade_levels", "generation.cascade_levels"),
        "generation.cascade_levels",
    )
    max_mag = _require_non_empty_str(
        generation, "max_magnification", "generation.max_magnification"
    )
    if max_mag != MAX_MAGNIFICATION:
        raise ValidationError(f"generation.max_magnification must be {MAX_MAGNIFICATION}")
    _validate_tile_size(
        _require(generation, "tile_size_40x", "generation.tile_size_40x"),
        "generation.tile_size_40x",
    )

    mask_schema = _ensure_mapping(_require(metadata, "mask_schema", "mask_schema"), "mask_schema")
    classes = _require_list(mask_schema, "classes", "mask_schema.classes")
    if tuple(classes) != MASK_CLASSES:
        raise ValidationError("mask_schema.classes must list the six project mask classes")
    mapping_source = _require_non_empty_str(
        mask_schema, "mapping_source", "mask_schema.mapping_source"
    )
    if mapping_source not in {"manual", "roi", "cluster", "mixed"}:
        raise ValidationError("mask_schema.mapping_source must be manual, roi, cluster, or mixed")
    _ensure_mapping(
        _require(mask_schema, "input_label_mapping", "mask_schema.input_label_mapping"),
        "mask_schema.input_label_mapping",
    )
    _ensure_mapping(
        _require(mask_schema, "confidence", "mask_schema.confidence"),
        "mask_schema.confidence",
    )

    qc = _ensure_mapping(_require(metadata, "qc", "qc"), "qc")
    _validate_status(_require_non_empty_str(qc, "overall_status", "qc.overall_status"), "qc.overall_status")
    _ensure_mapping(_require(qc, "summary", "qc.summary"), "qc.summary")
    _ensure_mapping(
        _require(qc, "non_copy_report", "qc.non_copy_report"),
        "qc.non_copy_report",
    )
    return deepcopy(metadata)


def validate_qc_report(data: dict[str, Any]) -> dict[str, Any]:
    report = _ensure_mapping(data, "qc_report")
    _require_schema_version(report)
    _require_non_empty_str(report, "generated_id", "generated_id")
    _validate_status(
        _require_non_empty_str(report, "overall_status", "overall_status"),
        "overall_status",
    )
    levels = _ensure_mapping(_require(report, "levels", "levels"), "levels")
    for level in ("wsi", "tile", "mask_region"):
        value = _ensure_mapping(_require(levels, level, f"levels.{level}"), f"levels.{level}")
        _validate_status(
            _require_non_empty_str(value, "status", f"levels.{level}.status"),
            f"levels.{level}.status",
        )
        _require_list(value, "metrics", f"levels.{level}.metrics")

    non_copy_report = _ensure_mapping(
        _require(report, "non_copy_report", "non_copy_report"),
        "non_copy_report",
    )
    _require_bool(non_copy_report, "enabled", "non_copy_report.enabled")
    patch_search = _require_bool(
        non_copy_report,
        "patch_nearest_neighbor_search",
        "non_copy_report.patch_nearest_neighbor_search",
    )
    if patch_search:
        raise ValidationError(
            "non_copy_report.patch_nearest_neighbor_search must be false in v0.60.0"
        )
    _require_list(non_copy_report, "items", "non_copy_report.items")
    return deepcopy(report)


def _validate_annotation_record(value: Any, path: str) -> None:
    annotation = _ensure_mapping(value, path)
    _require_non_empty_str(annotation, "annotation_id", f"{path}.annotation_id")
    _require_non_empty_str(annotation, "annotation_path", f"{path}.annotation_path")
    annotation_type = _require_non_empty_str(
        annotation, "annotation_type", f"{path}.annotation_type"
    )
    if annotation_type not in {
        "png_mask",
        "numpy_mask",
        "roi_json",
        "cluster_pseudo_mask",
    }:
        raise ValidationError(f"{path}.annotation_type has unsupported value")
    _require(annotation, "coordinate_level", f"{path}.coordinate_level")
    label_encoding = _require_non_empty_str(
        annotation, "label_encoding", f"{path}.label_encoding"
    )
    if label_encoding != "integer_index":
        raise ValidationError(f"{path}.label_encoding must be integer_index in v0.60.0")
    _ensure_mapping(
        _require(annotation, "transform_to_level0", f"{path}.transform_to_level0"),
        f"{path}.transform_to_level0",
    )
    status = _require_non_empty_str(annotation, "status", f"{path}.status")
    if status not in {"raw", "mapped", "validated", "rejected"}:
        raise ValidationError(f"{path}.status has unsupported value")


def _require_schema_version(data: dict[str, Any]) -> None:
    version = _require_non_empty_str(data, "schema_version", "schema_version")
    if version != PROJECT_VERSION:
        raise ValidationError(f"schema_version must be {PROJECT_VERSION}")


def _requires_source(anchor: float, preset: str) -> bool:
    # The proposal defines 0.0-0.3 as de novo territory. Source tracking becomes
    # mandatory once the run is source-anchored or uses a source-bound preset.
    return anchor > 0.3 or preset in SOURCE_ANCHORED_PRESETS


def _validate_anchor(value: float) -> None:
    if value < 0 or value > 1:
        raise ValidationError("structure_anchor must be between 0 and 1")


def _validate_cascade_levels(value: Any, path: str) -> None:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list")
    if tuple(value) != CASCADE_LEVELS:
        raise ValidationError(f"{path} must be {list(CASCADE_LEVELS)}")


def _validate_tile_size(value: Any, path: str) -> None:
    if not isinstance(value, list) or tuple(value) != TILE_SIZE_40X:
        raise ValidationError(f"{path} must be {list(TILE_SIZE_40X)}")


def _validate_canvas_size(value: Any, path: str) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise ValidationError(f"{path} must contain [width, height]")
    width, height = value
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width <= 0
        or height <= 0
    ):
        raise ValidationError(f"{path} values must be positive integers")


def _validate_status(value: str, path: str) -> None:
    if value not in STATUS_LEVELS:
        raise ValidationError(f"{path} must be pass, warning, or fail")


def _require(data: dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise ValidationError(f"{path} is required")
    return data[key]


def _require_non_empty_str(data: dict[str, Any], key: str, path: str) -> str:
    value = _require(data, key, path)
    if not _is_non_empty_str(value):
        raise ValidationError(f"{path} must be a non-empty string")
    return value


def _require_number(data: dict[str, Any], key: str, path: str) -> float:
    value = _require(data, key, path)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValidationError(f"{path} must be a number")
    return float(value)


def _require_positive_number(data: dict[str, Any], key: str, path: str) -> float:
    value = _require_number(data, key, path)
    if value <= 0:
        raise ValidationError(f"{path} must be positive")
    return value


def _require_int(data: dict[str, Any], key: str, path: str) -> int:
    value = _require(data, key, path)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{path} must be an integer")
    return value


def _require_bool(data: dict[str, Any], key: str, path: str) -> bool:
    value = _require(data, key, path)
    if not isinstance(value, bool):
        raise ValidationError(f"{path} must be a boolean")
    return value


def _require_list(data: dict[str, Any], key: str, path: str) -> list[Any]:
    value = _require(data, key, path)
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list")
    return value


def _ensure_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return value


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value != ""
