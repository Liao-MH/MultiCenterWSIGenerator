import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MAX_MAGNIFICATION, PROJECT_VERSION, TILE_SIZE_40X
from ..schemas import validate_input_manifest, validate_label_mapping


class TrainingIndexError(ValueError):
    """Raised when training samples cannot be indexed safely."""


def build_training_index(
    manifest: dict[str, Any],
    audit: dict[str, Any],
    label_mappings: list[dict[str, Any]],
    output_path: str | Path,
) -> dict[str, Any]:
    validated_manifest = validate_input_manifest(manifest)
    validated_mappings = [validate_label_mapping(mapping) for mapping in label_mappings]
    audit_records = _audit_records_by_wsi(audit)
    mappings = _mappings_by_annotation(validated_mappings)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for manifest_record in validated_manifest["records"]:
        wsi_id = manifest_record["wsi_id"]
        audit_record = _require_audit_record(audit_records, wsi_id)
        annotation = _select_training_annotation(manifest_record)
        mapping_key = (wsi_id, annotation["annotation_id"])
        if mapping_key not in mappings:
            raise TrainingIndexError(
                f"missing label mapping for {wsi_id}/{annotation['annotation_id']}"
            )
        _require_existing_mask(annotation["annotation_path"])
        records.extend(
            _records_for_slide(
                dataset_id=validated_manifest["dataset_id"],
                manifest_record=manifest_record,
                audit_record=audit_record,
                annotation=annotation,
                label_mapping=mappings[mapping_key],
            )
        )

    if not records:
        raise TrainingIndexError("training index would be empty")
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    records_by_level = Counter(record["cascade_level"] for record in records)
    records_by_split = Counter(record["split"] for record in records)
    return {
        "schema_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "dataset_id": validated_manifest["dataset_id"],
        "output_path": str(target),
        "sample_count": len(records),
        "wsi_count": len({record["wsi_id"] for record in records}),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "records_by_level": dict(records_by_level),
        "records_by_split": dict(records_by_split),
    }


def _records_for_slide(
    dataset_id: str,
    manifest_record: dict[str, Any],
    audit_record: dict[str, Any],
    annotation: dict[str, Any],
    label_mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    width, height = _dimensions(audit_record)
    tile_width, tile_height = TILE_SIZE_40X
    x_starts = list(range(0, width - tile_width + 1, tile_width))
    y_starts = list(range(0, height - tile_height + 1, tile_height))
    if not x_starts or not y_starts:
        raise TrainingIndexError(
            f"{manifest_record['wsi_id']} has no full {tile_width}x{tile_height} 40x tiles"
        )

    records: list[dict[str, Any]] = []
    for y in y_starts:
        for x in x_starts:
            tile_id = f"x{x}_y{y}_w{tile_width}_h{tile_height}"
            for level in CASCADE_LEVELS:
                records.append(
                    {
                        "schema_version": PROJECT_VERSION,
                        "sample_id": f"{manifest_record['wsi_id']}:{level}:{tile_id}",
                        "dataset_id": dataset_id,
                        "wsi_id": manifest_record["wsi_id"],
                        "wsi_path": audit_record["wsi_path"],
                        "split": manifest_record["split"],
                        "cancer_type": manifest_record["cancer_type"],
                        "cascade_level": level,
                        "max_magnification": MAX_MAGNIFICATION,
                        "tile_size_40x": list(TILE_SIZE_40X),
                        "tile": {
                            "x": x,
                            "y": y,
                            "width": tile_width,
                            "height": tile_height,
                            "coordinate_level": 0,
                        },
                        "source": {
                            "backend": audit_record["backend"],
                            "dimensions": audit_record["dimensions"],
                            "mpp_x": audit_record["mpp_x"],
                            "mpp_y": audit_record["mpp_y"],
                        },
                        "mask": {
                            "source_annotation_id": annotation["annotation_id"],
                            "annotation_path": annotation["annotation_path"],
                            "annotation_type": annotation["annotation_type"],
                            "coordinate_level": annotation["coordinate_level"],
                            "transform_to_level0": annotation["transform_to_level0"],
                            "class_mapping": label_mapping["classes"],
                            "mapping_source": label_mapping["mapping_source"],
                            "confidence": label_mapping["confidence"],
                        },
                        "conditioning": {
                            "style": {
                                "source": "training_or_generation_config",
                                "style_seed_source": "training_or_generation_config",
                            },
                            "texture": {
                                "source": "training_or_generation_config",
                                "texture_token_source": "training_or_generation_config",
                            },
                            "coord": _coord_condition(
                                cascade_level=level,
                                tile_x=x,
                                tile_y=y,
                                tile_width=tile_width,
                                tile_height=tile_height,
                            ),
                            "source": {
                                "required_when_anchor_gt_0": True,
                                "source_condition_policy": "required_when_anchor_gt_0",
                            },
                            "structure_anchor": {
                                "policy": "source_condition_required_when_anchor_gt_0",
                                "supported_range": [0.0, 1.0],
                            },
                            "structure_anchor_policy": "source_condition_required_when_anchor_gt_0",
                            "style_seed_source": "training_or_generation_config",
                            "texture_token_source": "training_or_generation_config",
                            "label_semantics": "six_class_project_mask",
                        },
                    }
                )
    return records


def _audit_records_by_wsi(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(audit, dict):
        raise TrainingIndexError("audit must be a JSON object")
    if audit.get("schema_version") != PROJECT_VERSION:
        raise TrainingIndexError(f"audit schema_version must be {PROJECT_VERSION}")
    records = audit.get("records")
    if not isinstance(records, list):
        raise TrainingIndexError("audit.records must be a list")
    by_wsi: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TrainingIndexError(f"audit.records[{index}] must be an object")
        wsi_id = record.get("wsi_id")
        if not isinstance(wsi_id, str) or wsi_id == "":
            raise TrainingIndexError(f"audit.records[{index}].wsi_id must be a non-empty string")
        if wsi_id in by_wsi:
            raise TrainingIndexError(f"duplicate audit record for {wsi_id}")
        by_wsi[wsi_id] = record
    return by_wsi


def _require_audit_record(records: dict[str, dict[str, Any]], wsi_id: str) -> dict[str, Any]:
    record = records.get(wsi_id)
    if record is None:
        raise TrainingIndexError(f"missing audit record for {wsi_id}")
    if record.get("status") != "ok":
        raise TrainingIndexError(f"audit record for {wsi_id} is not ok")
    if record.get("max_magnification") != MAX_MAGNIFICATION:
        raise TrainingIndexError(f"audit record for {wsi_id} must be {MAX_MAGNIFICATION}")
    _dimensions(record)
    for key in ("wsi_path", "backend", "mpp_x", "mpp_y"):
        if key not in record:
            raise TrainingIndexError(f"audit record for {wsi_id} missing {key}")
    return record


def _select_training_annotation(record: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        annotation
        for annotation in record.get("annotations", [])
        if annotation["status"] in {"mapped", "validated"}
    ]
    if not candidates:
        raise TrainingIndexError(f"{record['wsi_id']} has no mapped or validated mask annotation")
    return candidates[0]


def _mappings_by_annotation(
    mappings: list[dict[str, Any]]
) -> dict[tuple[str, str], dict[str, Any]]:
    by_annotation: dict[tuple[str, str], dict[str, Any]] = {}
    for mapping in mappings:
        key = (mapping["wsi_id"], mapping["source_annotation_id"])
        if key in by_annotation:
            raise TrainingIndexError(
                f"duplicate label mapping for {mapping['wsi_id']}/{mapping['source_annotation_id']}"
            )
        by_annotation[key] = mapping
    return by_annotation


def _dimensions(record: dict[str, Any]) -> tuple[int, int]:
    dimensions = record.get("dimensions")
    if (
        not isinstance(dimensions, list)
        or len(dimensions) != 2
        or not all(isinstance(value, int) and value > 0 for value in dimensions)
    ):
        raise TrainingIndexError("audit record dimensions must be [positive_width, positive_height]")
    return int(dimensions[0]), int(dimensions[1])


def _require_existing_mask(path: str) -> None:
    source = Path(path)
    if not source.exists():
        raise TrainingIndexError(f"mask annotation does not exist: {source}")
    if not source.is_file():
        raise TrainingIndexError(f"mask annotation is not a file: {source}")


def _coord_condition(
    *,
    cascade_level: str,
    tile_x: int,
    tile_y: int,
    tile_width: int,
    tile_height: int,
) -> dict[str, Any]:
    divisor = _cascade_divisor(cascade_level)
    return {
        "cascade_level": cascade_level,
        "tile_origin_40x": [int(tile_x), int(tile_y)],
        "target_image_shape": [int(tile_height // divisor), int(tile_width // divisor)],
        "target_mask_shape": [int(tile_height // divisor), int(tile_width // divisor)],
        "max_magnification": MAX_MAGNIFICATION,
    }


def _cascade_divisor(cascade_level: str) -> int:
    mapping = {
        "1/32": 32,
        "1/16": 16,
        "1/4": 4,
        "1/1": 1,
    }
    return mapping[cascade_level]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
