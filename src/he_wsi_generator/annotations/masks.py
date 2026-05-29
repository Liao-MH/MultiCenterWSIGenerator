import json
from pathlib import Path
from typing import Any

from ..constants import MASK_CLASSES
from ..schemas import validate_label_mapping


class MaskMappingError(ValueError):
    """Raised when a raw annotation mask cannot be mapped to project classes."""


def read_mask_labels(path: str | Path) -> list[int]:
    array = read_mask_array(path)
    numpy = _import_numpy()
    return [int(value) for value in sorted(numpy.unique(array).tolist())]


def read_mask_array(path: str | Path):
    source = Path(path)
    if not source.exists():
        raise MaskMappingError(f"{source} does not exist")
    suffix = source.suffix.lower()
    numpy = _import_numpy()
    if suffix == ".npy":
        return numpy.load(source, mmap_mode="r")
    if suffix == ".npz":
        with numpy.load(source) as data:
            if "mask" not in data:
                raise MaskMappingError(f"{source} must contain an array named 'mask'")
            return data["mask"]
    if suffix in {".png", ".tif", ".tiff"}:
        try:
            from PIL import Image
        except ImportError as exc:
            raise MaskMappingError("PNG/TIFF mask reading requires Pillow") from exc
        try:
            with Image.open(source) as image:
                return numpy.asarray(image)
        except Exception as exc:
            raise MaskMappingError(f"{source} cannot be read as an integer mask: {exc}") from exc
    raise MaskMappingError(f"{source} must be a .png, .tif, .tiff, .npy, or .npz mask")


def apply_label_mapping(mask_array, label_mapping: dict):
    numpy = _import_numpy()
    mapping = validate_label_mapping(label_mapping)
    classes = mapping["classes"]
    mapped = numpy.zeros(mask_array.shape, dtype=numpy.uint8)
    for raw_label in sorted(numpy.unique(mask_array).tolist()):
        raw_key = str(int(raw_label))
        if raw_key not in classes:
            raise MaskMappingError(f"unmapped mask label {raw_key}")
        class_name = classes[raw_key]
        mapped[mask_array == raw_label] = MASK_CLASSES.index(class_name)
    return mapped


def load_annotation_source(annotation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(annotation, dict):
        raise MaskMappingError("annotation must be an object")
    for key in (
        "annotation_id",
        "annotation_path",
        "annotation_type",
        "transform_to_level0",
    ):
        if key not in annotation:
            raise MaskMappingError(f"annotation.{key} is required")

    loaded = {
        "annotation_id": annotation["annotation_id"],
        "annotation_path": annotation["annotation_path"],
        "annotation_type": annotation["annotation_type"],
        "transform_to_level0": dict(annotation["transform_to_level0"]),
    }
    annotation_type = annotation["annotation_type"]
    if annotation_type in {"png_mask", "numpy_mask", "cluster_pseudo_mask"}:
        loaded["data"] = read_mask_array(annotation["annotation_path"])
        return loaded
    if annotation_type == "roi_json":
        loaded["roi_records"] = _load_roi_json(annotation["annotation_path"])
        return loaded
    raise MaskMappingError(f"unsupported annotation_type: {annotation_type}")


def build_six_class_mask(
    *,
    wsi_id: str,
    wsi_level0_size: tuple[int, int],
    annotation_sources: list[dict[str, Any]],
    output_path: str | Path | None = None,
    block_size: int = 4096,
) -> dict[str, Any]:
    if not isinstance(wsi_id, str) or wsi_id == "":
        raise MaskMappingError("wsi_id must be a non-empty string")
    if (
        not isinstance(wsi_level0_size, tuple)
        or len(wsi_level0_size) != 2
        or not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in wsi_level0_size)
    ):
        raise MaskMappingError("wsi_level0_size must be a tuple of two positive integers")
    if not isinstance(annotation_sources, list) or not annotation_sources:
        raise MaskMappingError("annotation_sources must contain at least one annotation")
    if not isinstance(block_size, int) or isinstance(block_size, bool) or block_size <= 0:
        raise MaskMappingError("block_size must be a positive integer")

    numpy = _import_numpy()
    width, height = wsi_level0_size
    priority_rank = {"cluster_pseudo_mask": 0, "roi_json": 1, "manual_mask": 2}
    output = _create_output_mask(
        numpy=numpy,
        output_path=output_path,
        height=int(height),
        width=int(width),
    )
    ordered_sources = _prepare_annotation_sources(
        annotation_sources=annotation_sources,
        wsi_level0_size=wsi_level0_size,
        priority_rank=priority_rank,
    )

    priority_order = []
    global_class_counts: dict[str, int] = {}
    annotation_counts: dict[str, dict[str, int]] = {
        source["annotation_id"]: {} for source in ordered_sources
    }
    block_summaries = []
    conflict_state = {"count": 0, "examples": []}
    block_index = 0

    for block_y in range(0, height, block_size):
        for block_x in range(0, width, block_size):
            block_height = int(min(block_size, height - block_y))
            block_width = int(min(block_size, width - block_x))
            block_mask = numpy.zeros((block_height, block_width), dtype=numpy.uint8)
            block_owner_rank = numpy.full((block_height, block_width), -1, dtype=numpy.int16)
            block_owner_source = numpy.full((block_height, block_width), -1, dtype=numpy.int32)
            for source in ordered_sources:
                if source["priority"] not in priority_order:
                    priority_order.append(source["priority"])
                _merge_source_into_block(
                    numpy=numpy,
                    block_mask=block_mask,
                    block_owner_rank=block_owner_rank,
                    block_owner_source=block_owner_source,
                    block_x=block_x,
                    block_y=block_y,
                    source=source,
                    ordered_sources=ordered_sources,
                    priority_rank=priority_rank,
                    conflict_state=conflict_state,
                )
            output[block_y : block_y + block_height, block_x : block_x + block_width] = block_mask
            block_class_counts = _class_counts_by_id(numpy, block_mask)
            block_annotation_counts = _annotation_counts_by_id(
                numpy=numpy,
                block_mask=block_mask,
                block_owner_source=block_owner_source,
                ordered_sources=ordered_sources,
            )
            _accumulate_counts(global_class_counts, block_class_counts)
            _accumulate_nested_counts(annotation_counts, block_annotation_counts)
            block_summaries.append(
                {
                    "block_index": int(block_index),
                    "x": int(block_x),
                    "y": int(block_y),
                    "width": int(block_width),
                    "height": int(block_height),
                    "class_pixel_counts_by_id": block_class_counts,
                    "annotation_pixel_counts_by_id": block_annotation_counts,
                }
            )
            block_index += 1

    if hasattr(output, "flush"):
        output.flush()
    compact_provenance_summary = {
        "class_pixel_counts_by_id": _sorted_count_dict(global_class_counts),
        "annotation_pixel_counts_by_id": _sorted_nested_count_dict(annotation_counts),
        "block_summaries": block_summaries,
        "source_priority_order": priority_order[::-1],
        "same_priority_conflict_count": int(conflict_state["count"]),
        "same_priority_conflict_examples": list(conflict_state["examples"]),
    }
    result = {
        "wsi_id": wsi_id,
        "mask": output,
        "mask_shape": [int(height), int(width)],
        "source_priority_order": priority_order[::-1],
        "compact_provenance_summary": compact_provenance_summary,
    }
    if output_path is not None:
        result["mask_path"] = str(output_path)
    return result


def _create_output_mask(*, numpy, output_path: str | Path | None, height: int, width: int):
    if output_path is None:
        return numpy.zeros((height, width), dtype=numpy.uint8)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return numpy.lib.format.open_memmap(
        str(target),
        mode="w+",
        dtype=numpy.uint8,
        shape=(height, width),
    )


def _prepare_annotation_sources(
    *,
    annotation_sources: list[dict[str, Any]],
    wsi_level0_size: tuple[int, int],
    priority_rank: dict[str, int],
) -> list[dict[str, Any]]:
    normalized_sources = []
    for source in annotation_sources:
        normalized = _normalize_annotation_source(source)
        priority = normalized["priority"]
        if priority not in priority_rank:
            raise MaskMappingError(f"unsupported annotation priority: {priority}")
        if normalized["annotation_type"] == "roi_json":
            roi_records = normalized.get("roi_records")
            if not isinstance(roi_records, list) or not roi_records:
                raise MaskMappingError(f"{normalized['annotation_id']} roi_records must be a non-empty list")
            report = _roi_alignment_report(
                roi_records,
                normalized["transform_to_level0"],
                wsi_level0_size=wsi_level0_size,
            )
            normalized["_roi_transform"] = report["transform_to_level0"]
        else:
            data = normalized.get("data")
            if data is None:
                raise MaskMappingError(f"{normalized['annotation_id']} is missing mask data")
            if getattr(data, "ndim", None) != 2:
                raise MaskMappingError("mask array must be 2D")
            normalized["_alignment_report"] = _mask_alignment_report(
                data,
                normalized["transform_to_level0"],
                wsi_level0_size=wsi_level0_size,
            )
        normalized_sources.append(normalized)
    ordered = sorted(normalized_sources, key=lambda source: priority_rank[source["priority"]])
    for source_index, source in enumerate(ordered):
        source["_source_index"] = int(source_index)
    return ordered


def _normalize_annotation_source(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise MaskMappingError("annotation_sources entries must be objects")
    required = {
        "annotation_id",
        "annotation_type",
        "annotation_path",
        "priority",
        "transform_to_level0",
        "label_mapping",
    }
    missing = sorted(required.difference(source))
    if missing:
        raise MaskMappingError(f"annotation source missing required fields: {', '.join(missing)}")
    mapping = validate_label_mapping(source["label_mapping"])
    normalized = dict(source)
    normalized["label_mapping"] = mapping
    return normalized


def _merge_source_into_block(
    *,
    numpy,
    block_mask,
    block_owner_rank,
    block_owner_source,
    block_x: int,
    block_y: int,
    source: dict[str, Any],
    ordered_sources: list[dict[str, Any]],
    priority_rank: dict[str, int],
    conflict_state: dict[str, Any],
) -> None:
    if source["annotation_type"] == "roi_json":
        _merge_roi_source_into_block(
            numpy=numpy,
            block_mask=block_mask,
            block_owner_rank=block_owner_rank,
            block_owner_source=block_owner_source,
            block_x=block_x,
            block_y=block_y,
            source=source,
            ordered_sources=ordered_sources,
            priority_rank=priority_rank,
            conflict_state=conflict_state,
        )
        return
    _merge_mask_source_into_block(
        numpy=numpy,
        block_mask=block_mask,
        block_owner_rank=block_owner_rank,
        block_owner_source=block_owner_source,
        block_x=block_x,
        block_y=block_y,
        source=source,
        ordered_sources=ordered_sources,
        priority_rank=priority_rank,
        conflict_state=conflict_state,
    )


def _merge_mask_source_into_block(
    *,
    numpy,
    block_mask,
    block_owner_rank,
    block_owner_source,
    block_x: int,
    block_y: int,
    source: dict[str, Any],
    ordered_sources: list[dict[str, Any]],
    priority_rank: dict[str, int],
    conflict_state: dict[str, Any],
) -> None:
    data = source.get("data")
    if data is None:
        raise MaskMappingError(f"{source['annotation_id']} is missing mask data")
    report = source["_alignment_report"]
    x0, y0, x1, y1 = report["level0_extent_int"]
    scale_x = int(round(report["transform_to_level0"]["scale_x"]))
    scale_y = int(round(report["transform_to_level0"]["scale_y"]))
    block_height, block_width = block_mask.shape[:2]
    intersection = _intersect_rect(
        block_x,
        block_y,
        block_x + block_width,
        block_y + block_height,
        x0,
        y0,
        x1,
        y1,
    )
    if intersection is None:
        return
    ix0, iy0, ix1, iy1 = intersection
    src_x0 = max(0, (ix0 - x0) // scale_x)
    src_y0 = max(0, (iy0 - y0) // scale_y)
    src_x1 = min(int(data.shape[1]), _ceil_div(ix1 - x0, scale_x))
    src_y1 = min(int(data.shape[0]), _ceil_div(iy1 - y0, scale_y))
    raw = data[src_y0:src_y1, src_x0:src_x1]
    mapped = _map_mask_labels_to_project_classes(numpy, raw, source["label_mapping"])
    expanded = mapped
    if scale_x != 1:
        expanded = numpy.repeat(expanded, scale_x, axis=1)
    if scale_y != 1:
        expanded = numpy.repeat(expanded, scale_y, axis=0)
    expanded_x0 = x0 + src_x0 * scale_x
    expanded_y0 = y0 + src_y0 * scale_y
    crop_x0 = ix0 - expanded_x0
    crop_y0 = iy0 - expanded_y0
    crop_x1 = crop_x0 + (ix1 - ix0)
    crop_y1 = crop_y0 + (iy1 - iy0)
    region = expanded[crop_y0:crop_y1, crop_x0:crop_x1]
    _merge_region_into_block(
        numpy=numpy,
        block_mask=block_mask,
        block_owner_rank=block_owner_rank,
        block_owner_source=block_owner_source,
        region=region,
        block_x=block_x,
        block_y=block_y,
        local_x0=ix0 - block_x,
        local_y0=iy0 - block_y,
        source=source,
        ordered_sources=ordered_sources,
        priority_rank=priority_rank,
        conflict_state=conflict_state,
    )


def _merge_roi_source_into_block(
    *,
    numpy,
    block_mask,
    block_owner_rank,
    block_owner_source,
    block_x: int,
    block_y: int,
    source: dict[str, Any],
    ordered_sources: list[dict[str, Any]],
    priority_rank: dict[str, int],
    conflict_state: dict[str, Any],
) -> None:
    roi_records = source.get("roi_records")
    if not isinstance(roi_records, list) or not roi_records:
        raise MaskMappingError(f"{source['annotation_id']} roi_records must be a non-empty list")
    mapping = source["label_mapping"]["classes"]
    block_height, block_width = block_mask.shape[:2]
    for roi in roi_records:
        raw_label = int(roi["label"])
        class_name = mapping.get(str(raw_label))
        if class_name is None:
            raise MaskMappingError(f"unmapped ROI label {raw_label}")
        class_id = MASK_CLASSES.index(class_name)
        x, y, width, height = _map_roi_bbox_to_level0(roi["bounding_box_xywh"], source["_roi_transform"])
        intersection = _intersect_rect(
            block_x,
            block_y,
            block_x + block_width,
            block_y + block_height,
            x,
            y,
            x + width,
            y + height,
        )
        if intersection is None:
            continue
        ix0, iy0, ix1, iy1 = intersection
        region = numpy.full((iy1 - iy0, ix1 - ix0), class_id, dtype=numpy.uint8)
        _merge_region_into_block(
            numpy=numpy,
            block_mask=block_mask,
            block_owner_rank=block_owner_rank,
            block_owner_source=block_owner_source,
            region=region,
            block_x=block_x,
            block_y=block_y,
            local_x0=ix0 - block_x,
            local_y0=iy0 - block_y,
            source=source,
            ordered_sources=ordered_sources,
            priority_rank=priority_rank,
            conflict_state=conflict_state,
        )


def _merge_region_into_block(
    *,
    numpy,
    block_mask,
    block_owner_rank,
    block_owner_source,
    region,
    block_x: int,
    block_y: int,
    local_x0: int,
    local_y0: int,
    source: dict[str, Any],
    ordered_sources: list[dict[str, Any]],
    priority_rank: dict[str, int],
    conflict_state: dict[str, Any],
) -> None:
    if region.size == 0:
        return
    region = numpy.asarray(region, dtype=numpy.uint8)
    region_height, region_width = region.shape[:2]
    target = block_mask[local_y0 : local_y0 + region_height, local_x0 : local_x0 + region_width]
    owner_rank = block_owner_rank[local_y0 : local_y0 + region_height, local_x0 : local_x0 + region_width]
    owner_source = block_owner_source[local_y0 : local_y0 + region_height, local_x0 : local_x0 + region_width]
    current_rank = priority_rank[source["priority"]]
    nonzero = region != 0
    if not bool(nonzero.any()):
        return
    conflict = nonzero & (owner_rank == current_rank) & (target != region)
    if bool(conflict.any()):
        _record_conflicts(
            numpy=numpy,
            conflict=conflict,
            target=target,
            region=region,
            owner_source=owner_source,
            global_x0=block_x + local_x0,
            global_y0=block_y + local_y0,
            source=source,
            ordered_sources=ordered_sources,
            conflict_state=conflict_state,
        )
        first = conflict_state["examples"][0]
        raise MaskMappingError(
            "same-priority conflict at "
            f"({first['x']}, {first['y']}) between annotation sources"
        )
    overwrite = nonzero & (owner_rank <= current_rank)
    target[overwrite] = region[overwrite]
    owner_rank[overwrite] = current_rank
    owner_source[overwrite] = int(source["_source_index"])


def _map_mask_labels_to_project_classes(numpy, mask_array, label_mapping: dict):
    classes = label_mapping["classes"]
    mapped = numpy.zeros(mask_array.shape, dtype=numpy.uint8)
    for raw_label in sorted(numpy.unique(mask_array).tolist()):
        raw_key = str(int(raw_label))
        if raw_key not in classes:
            raise MaskMappingError(f"unmapped mask label {raw_key}")
        mapped[mask_array == raw_label] = MASK_CLASSES.index(classes[raw_key])
    return mapped


def _record_conflicts(
    *,
    numpy,
    conflict,
    target,
    region,
    owner_source,
    global_x0: int,
    global_y0: int,
    source: dict[str, Any],
    ordered_sources: list[dict[str, Any]],
    conflict_state: dict[str, Any],
) -> None:
    conflict_state["count"] = int(conflict_state["count"]) + int(conflict.sum())
    slots = max(0, 5 - len(conflict_state["examples"]))
    for y, x in numpy.argwhere(conflict)[:slots]:
        existing_source_index = int(owner_source[int(y), int(x)])
        existing_annotation_id = None
        if 0 <= existing_source_index < len(ordered_sources):
            existing_annotation_id = ordered_sources[existing_source_index]["annotation_id"]
        conflict_state["examples"].append(
            {
                "x": int(global_x0 + int(x)),
                "y": int(global_y0 + int(y)),
                "existing_annotation_id": existing_annotation_id,
                "incoming_annotation_id": source["annotation_id"],
                "priority": source["priority"],
                "existing_class_id": int(target[int(y), int(x)]),
                "incoming_class_id": int(region[int(y), int(x)]),
            }
        )


def _intersect_rect(
    ax0: int,
    ay0: int,
    ax1: int,
    ay1: int,
    bx0: int,
    by0: int,
    bx1: int,
    by1: int,
) -> tuple[int, int, int, int] | None:
    ix0 = max(int(ax0), int(bx0))
    iy0 = max(int(ay0), int(by0))
    ix1 = min(int(ax1), int(bx1))
    iy1 = min(int(ay1), int(by1))
    if ix0 >= ix1 or iy0 >= iy1:
        return None
    return ix0, iy0, ix1, iy1


def _ceil_div(value: int, divisor: int) -> int:
    return (int(value) + int(divisor) - 1) // int(divisor)


def _class_counts_by_id(numpy, mask_array) -> dict[str, int]:
    values, counts = numpy.unique(mask_array, return_counts=True)
    return {
        str(int(value)): int(count)
        for value, count in sorted(zip(values.tolist(), counts.tolist()), key=lambda item: int(item[0]))
    }


def _annotation_counts_by_id(
    *,
    numpy,
    block_mask,
    block_owner_source,
    ordered_sources: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    counts = {source["annotation_id"]: {} for source in ordered_sources}
    for source_index in sorted(int(value) for value in numpy.unique(block_owner_source).tolist() if int(value) >= 0):
        annotation_id = ordered_sources[source_index]["annotation_id"]
        owned = block_owner_source == source_index
        values, value_counts = numpy.unique(block_mask[owned], return_counts=True)
        for value, count in zip(values.tolist(), value_counts.tolist()):
            class_id = int(value)
            if class_id == 0:
                continue
            counts[annotation_id][str(class_id)] = counts[annotation_id].get(str(class_id), 0) + int(count)
    return {key: _sorted_count_dict(value) for key, value in counts.items()}


def _accumulate_counts(total: dict[str, int], increment: dict[str, int]) -> None:
    for key, value in increment.items():
        total[key] = total.get(key, 0) + int(value)


def _accumulate_nested_counts(total: dict[str, dict[str, int]], increment: dict[str, dict[str, int]]) -> None:
    for key, counts in increment.items():
        if key not in total:
            total[key] = {}
        _accumulate_counts(total[key], counts)


def _sorted_count_dict(counts: dict[str, int]) -> dict[str, int]:
    return {key: int(counts[key]) for key in sorted(counts, key=lambda value: int(value))}


def _sorted_nested_count_dict(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    return {
        key: _sorted_count_dict(value)
        for key, value in sorted(counts.items(), key=lambda item: item[0])
    }


def _mask_alignment_report(mask_array, transform_to_level0: dict[str, Any], wsi_level0_size: tuple[int, int]) -> dict[str, Any]:
    from .alignment import validate_mask_alignment

    report = validate_mask_alignment(
        mask_size=(int(mask_array.shape[1]), int(mask_array.shape[0])),
        wsi_level0_size=wsi_level0_size,
        transform_to_level0=transform_to_level0,
    )
    extent = report["level0_extent"]
    rounded = [round(value) for value in extent]
    if any(abs(value - rounded[index]) > 1e-6 for index, value in enumerate(extent)):
        raise MaskMappingError("mask transform must map to integer-aligned level0 extent")
    scale_x = report["transform_to_level0"]["scale_x"]
    scale_y = report["transform_to_level0"]["scale_y"]
    if abs(scale_x - round(scale_x)) > 1e-6 or abs(scale_y - round(scale_y)) > 1e-6:
        raise MaskMappingError("mask transform scale must be an integer for Stage 2 alignment")
    report["level0_extent_int"] = [int(value) for value in rounded]
    return report


def _roi_alignment_report(roi_records: list[dict[str, Any]], transform_to_level0: dict[str, Any], wsi_level0_size: tuple[int, int]) -> dict[str, Any]:
    scale_x = _require_positive_integer_scale(transform_to_level0, "scale_x")
    scale_y = _require_positive_integer_scale(transform_to_level0, "scale_y")
    offset_x = _require_integer_offset(transform_to_level0, "offset_x")
    offset_y = _require_integer_offset(transform_to_level0, "offset_y")
    max_width, max_height = wsi_level0_size
    for roi in roi_records:
        x, y, width, height = _validate_roi_bbox(roi.get("bounding_box_xywh"))
        x0 = offset_x + x * scale_x
        y0 = offset_y + y * scale_y
        x1 = x0 + width * scale_x
        y1 = y0 + height * scale_y
        if x0 < 0 or y0 < 0 or x1 > max_width or y1 > max_height:
            raise MaskMappingError("ROI level0 extent exceeds WSI level0 bounds")
    return {
        "transform_to_level0": {
            "scale_x": scale_x,
            "scale_y": scale_y,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }
    }


def _map_roi_bbox_to_level0(bounding_box_xywh: Any, transform_to_level0: dict[str, Any]) -> tuple[int, int, int, int]:
    x, y, width, height = _validate_roi_bbox(bounding_box_xywh)
    return (
        transform_to_level0["offset_x"] + x * transform_to_level0["scale_x"],
        transform_to_level0["offset_y"] + y * transform_to_level0["scale_y"],
        width * transform_to_level0["scale_x"],
        height * transform_to_level0["scale_y"],
    )


def _validate_roi_bbox(value: Any) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        raise MaskMappingError("ROI bounding_box_xywh must contain four integers")
    x, y, width, height = value
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise MaskMappingError("ROI bounding_box_xywh must contain non-negative origin and positive size")
    return x, y, width, height


def _load_roi_json(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise MaskMappingError(f"{source} does not exist")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaskMappingError(f"{source} is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise MaskMappingError(f"{source} must contain a JSON object")
    rois = payload.get("rois")
    if not isinstance(rois, list) or not rois:
        raise MaskMappingError(f"{source} must contain a non-empty rois list")
    records = []
    for index, roi in enumerate(rois):
        if not isinstance(roi, dict):
            raise MaskMappingError(f"{source}.rois[{index}] must be an object")
        label = roi.get("label")
        if not isinstance(label, int) or isinstance(label, bool) or label < 0:
            raise MaskMappingError(f"{source}.rois[{index}].label must be a non-negative integer")
        bbox = _validate_roi_bbox(roi.get("bounding_box_xywh"))
        records.append(
            {
                "label": int(label),
                "bounding_box_xywh": [int(value) for value in bbox],
            }
        )
    return records


def _require_positive_integer_scale(transform_to_level0: dict[str, Any], key: str) -> int:
    value = transform_to_level0.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise MaskMappingError(f"transform_to_level0.{key} must be a positive number")
    rounded = round(float(value))
    if abs(float(value) - rounded) > 1e-6:
        raise MaskMappingError(f"transform_to_level0.{key} must be integer-aligned")
    return int(rounded)


def _require_integer_offset(transform_to_level0: dict[str, Any], key: str) -> int:
    value = transform_to_level0.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise MaskMappingError(f"transform_to_level0.{key} must be a number")
    rounded = round(float(value))
    if abs(float(value) - rounded) > 1e-6:
        raise MaskMappingError(f"transform_to_level0.{key} must be integer-aligned")
    return int(rounded)


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise MaskMappingError("Mask operations require numpy") from exc
    return numpy
