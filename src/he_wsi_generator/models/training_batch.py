import json
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, PROJECT_VERSION


class TrainingBatchError(ValueError):
    """Raised when a training-index batch cannot be loaded safely."""


VALID_SPLITS = ("train", "val", "test", "unassigned")
MASK_CLASS_TO_ID = {name: index for index, name in enumerate(MASK_CLASSES)}


def load_training_batch(
    training_index_path: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str | None = None,
    include_image: bool = False,
) -> dict[str, Any]:
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise TrainingBatchError("batch_size must be a positive integer")
    if not isinstance(include_image, bool):
        raise TrainingBatchError("include_image must be a boolean")
    if split is not None and split not in VALID_SPLITS:
        raise TrainingBatchError(f"unknown split: {split}")
    if cascade_level is not None and cascade_level not in CASCADE_LEVELS:
        raise TrainingBatchError(f"unknown cascade level: {cascade_level}")

    numpy = _import_numpy()
    records = _load_training_index_records(training_index_path)
    filtered = [
        record
        for record in records
        if (split is None or record["split"] == split)
        and (cascade_level is None or record["cascade_level"] == cascade_level)
    ]
    if not filtered:
        raise TrainingBatchError("no training samples matched filters")
    if len(filtered) < batch_size:
        raise TrainingBatchError(
            f"batch_size {batch_size} exceeds matched sample count {len(filtered)}"
        )

    selected = filtered[:batch_size]
    mask_tiles = [_load_project_mask_tile(numpy, record) for record in selected]
    mask_batch = numpy.stack(mask_tiles, axis=0)
    class_ids = [int(value) for value in sorted(numpy.unique(mask_batch).tolist())]
    batch = {
        "schema_version": PROJECT_VERSION,
        "batch_size": int(mask_batch.shape[0]),
        "sample_ids": [record["sample_id"] for record in selected],
        "cascade_levels": sorted({record["cascade_level"] for record in selected}),
        "wsi_ids": sorted({record["wsi_id"] for record in selected}),
        "tile_records": [record["tile"] for record in selected],
        "mask_batch": mask_batch,
        "mask_batch_shape": [int(value) for value in mask_batch.shape],
        "mask_class_ids": class_ids,
        "conditioning": [record["conditioning"] for record in selected],
        "source_records": [record["source"] for record in selected],
    }
    if include_image:
        image_tiles = [_load_rgb_image_tile(numpy, record) for record in selected]
        image_batch = numpy.stack(image_tiles, axis=0)
        batch.update(
            {
                "image_batch": image_batch,
                "image_batch_shape": [int(value) for value in image_batch.shape],
                "image_dtype": str(image_batch.dtype),
            }
        )
    return batch


def training_batch_summary(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in batch.items()
        if key not in {"mask_batch", "image_batch"}
    }


def write_training_batch_summary(batch: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    summary = training_batch_summary(batch)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _load_training_index_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise TrainingBatchError(f"training index does not exist: {source}")
    records: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped == "":
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TrainingBatchError(
                    f"{source}:{line_number} is not valid JSON: {exc.msg}"
                ) from exc
            records.append(_validate_index_record(record, line_number))
    if not records:
        raise TrainingBatchError("training index is empty")
    return records


def _validate_index_record(record: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TrainingBatchError(f"training index line {line_number} must be an object")
    if record.get("schema_version") != PROJECT_VERSION:
        raise TrainingBatchError(
            f"training index line {line_number} schema_version must be {PROJECT_VERSION}"
        )
    for key in ("sample_id", "wsi_id", "split", "cascade_level"):
        if not isinstance(record.get(key), str) or record[key] == "":
            raise TrainingBatchError(f"training index line {line_number} missing {key}")
    if not isinstance(record.get("wsi_path"), str) or record["wsi_path"] == "":
        raise TrainingBatchError(f"training index line {line_number} missing wsi_path")
    if record["split"] not in VALID_SPLITS:
        raise TrainingBatchError(f"training index line {line_number} has unknown split")
    if record["cascade_level"] not in CASCADE_LEVELS:
        raise TrainingBatchError(f"training index line {line_number} has unknown cascade level")
    for key in ("tile", "mask", "conditioning", "source"):
        if not isinstance(record.get(key), dict):
            raise TrainingBatchError(f"training index line {line_number} missing {key}")
    _validate_tile(record["tile"], line_number)
    if not isinstance(record["mask"].get("annotation_path"), str):
        raise TrainingBatchError(f"training index line {line_number} missing mask annotation_path")
    if not isinstance(record["mask"].get("class_mapping"), dict):
        raise TrainingBatchError(f"training index line {line_number} missing mask class_mapping")
    return record


def _validate_tile(tile: dict[str, Any], line_number: int) -> None:
    for key in ("x", "y", "width", "height"):
        value = tile.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TrainingBatchError(f"training index line {line_number} tile.{key} must be int")
    if tile["x"] < 0 or tile["y"] < 0 or tile["width"] <= 0 or tile["height"] <= 0:
        raise TrainingBatchError(f"training index line {line_number} has invalid tile bounds")


def _load_project_mask_tile(numpy, record: dict[str, Any]):
    mask_info = record["mask"]
    path = Path(mask_info["annotation_path"])
    if not path.exists():
        raise TrainingBatchError(f"mask file does not exist: {path}")
    try:
        mask = numpy.load(path, mmap_mode="r") if path.suffix.lower() == ".npy" else numpy.load(path)
    except Exception as exc:
        raise TrainingBatchError(f"mask file cannot be loaded: {path}") from exc
    if mask.ndim != 2:
        raise TrainingBatchError("mask array must be 2D")
    if mask.dtype == numpy.bool_ or not numpy.issubdtype(mask.dtype, numpy.integer):
        raise TrainingBatchError("mask array must contain integer class ids")

    x, y, width, height = _mask_tile_bounds(record)
    if x < 0 or y < 0 or x + width > mask.shape[1] or y + height > mask.shape[0]:
        raise TrainingBatchError(f"tile exceeds mask bounds for {record['sample_id']}")
    raw_tile = mask[y : y + height, x : x + width]
    mapped = _map_raw_mask_to_project_ids(numpy, raw_tile, mask_info["class_mapping"])
    target_mask_shape = _target_spatial_shape(record, "target_mask_shape")
    return _resize_nearest_mask(numpy, mapped, target_mask_shape)


def _load_rgb_image_tile(numpy, record: dict[str, Any]):
    backend = record["source"].get("backend")
    path = Path(record["wsi_path"])
    if not path.exists():
        raise TrainingBatchError(f"WSI image file does not exist: {path}")
    if backend == "fixture-image":
        return _load_fixture_image_tile(numpy, path, record)
    if backend == "openslide":
        return _load_openslide_image_tile(numpy, path, record)
    raise TrainingBatchError(f"unsupported image tile backend: {backend}")


def _load_fixture_image_tile(numpy, path: Path, record: dict[str, Any]):
    try:
        from PIL import Image
    except ImportError as exc:
        raise TrainingBatchError("fixture image tile loading requires Pillow") from exc
    x, y, width, height = _level0_tile_bounds(record)
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            if x < 0 or y < 0 or x + width > rgb.size[0] or y + height > rgb.size[1]:
                raise TrainingBatchError(f"tile exceeds WSI image bounds for {record['sample_id']}")
            tile = rgb.crop((x, y, x + width, y + height))
            array = numpy.asarray(tile, dtype=numpy.uint8)
            return _resize_rgb_tile(numpy, array, _target_spatial_shape(record, "target_image_shape"))
    except TrainingBatchError:
        raise
    except Exception as exc:
        raise TrainingBatchError(f"fixture image tile cannot be loaded: {path}") from exc


def _load_openslide_image_tile(numpy, path: Path, record: dict[str, Any]):
    try:
        import openslide
    except ImportError as exc:
        raise TrainingBatchError("OpenSlide image tile loading requires openslide-python") from exc
    x, y, width, height = _level0_tile_bounds(record)
    try:
        slide = openslide.OpenSlide(str(path))
    except Exception as exc:
        raise TrainingBatchError(f"OpenSlide cannot read image tile source: {path}") from exc
    try:
        slide_width, slide_height = slide.dimensions
        if x < 0 or y < 0 or x + width > slide_width or y + height > slide_height:
            raise TrainingBatchError(f"tile exceeds WSI image bounds for {record['sample_id']}")
        tile = slide.read_region((x, y), 0, (width, height)).convert("RGB")
        array = numpy.asarray(tile, dtype=numpy.uint8)
        return _resize_rgb_tile(numpy, array, _target_spatial_shape(record, "target_image_shape"))
    finally:
        slide.close()


def _level0_tile_bounds(record: dict[str, Any]) -> tuple[int, int, int, int]:
    tile = record["tile"]
    return int(tile["x"]), int(tile["y"]), int(tile["width"]), int(tile["height"])


def _mask_tile_bounds(record: dict[str, Any]) -> tuple[int, int, int, int]:
    tile = record["tile"]
    transform = record["mask"].get("transform_to_level0", {})
    # The index stores level-0 tile bounds. For common aligned masks, invert the
    # documented scale/offset transform so lower-resolution masks are still auditable.
    scale_x = _positive_number(transform.get("scale_x", 1.0), "scale_x")
    scale_y = _positive_number(transform.get("scale_y", 1.0), "scale_y")
    offset_x = _number(transform.get("offset_x", 0), "offset_x")
    offset_y = _number(transform.get("offset_y", 0), "offset_y")
    values = (
        (tile["x"] - offset_x) / scale_x,
        (tile["y"] - offset_y) / scale_y,
        tile["width"] / scale_x,
        tile["height"] / scale_y,
    )
    rounded = tuple(round(value) for value in values)
    if any(abs(value - rounded[index]) > 1e-6 for index, value in enumerate(values)):
        raise TrainingBatchError("tile bounds are not integer-aligned in mask coordinates")
    x, y, width, height = (int(value) for value in rounded)
    return x, y, width, height


def _map_raw_mask_to_project_ids(numpy, raw_tile, class_mapping: dict[str, Any]):
    mapped = numpy.empty(raw_tile.shape, dtype=numpy.uint8)
    for raw_value in numpy.unique(raw_tile).tolist():
        raw_id = int(raw_value)
        class_name = class_mapping.get(str(raw_id))
        if class_name not in MASK_CLASS_TO_ID:
            raise TrainingBatchError(f"mask class id {raw_id} is not mapped to a project class")
        mapped[raw_tile == raw_id] = MASK_CLASS_TO_ID[class_name]
    return mapped


def _target_spatial_shape(record: dict[str, Any], key: str) -> tuple[int, int]:
    coord = record.get("conditioning", {}).get("coord")
    if not isinstance(coord, dict):
        raise TrainingBatchError("training index record missing conditioning.coord")
    shape = coord.get(key)
    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in shape)
    ):
        raise TrainingBatchError(f"conditioning.coord.{key} must contain two positive integers")
    return int(shape[0]), int(shape[1])


def _resize_nearest_mask(numpy, array, target_shape: tuple[int, int]):
    target_height, target_width = target_shape
    if array.shape == (target_height, target_width):
        return array.astype(numpy.uint8)
    y_index = _nearest_indices(array.shape[0], target_height)
    x_index = _nearest_indices(array.shape[1], target_width)
    return array[y_index][:, x_index].astype(numpy.uint8)


def _resize_rgb_tile(numpy, array, target_shape: tuple[int, int]):
    target_height, target_width = target_shape
    if array.shape[:2] == (target_height, target_width):
        return array.astype(numpy.uint8)
    y_index = _nearest_indices(array.shape[0], target_height)
    x_index = _nearest_indices(array.shape[1], target_width)
    return array[y_index][:, x_index, :].astype(numpy.uint8)


def _nearest_indices(source_size: int, target_size: int):
    if source_size <= 0 or target_size <= 0:
        raise TrainingBatchError("resize dimensions must be positive")
    if source_size == target_size:
        return slice(None)
    ratio = source_size / target_size
    indexes = [min(source_size - 1, int(index * ratio)) for index in range(target_size)]
    return indexes


def _number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TrainingBatchError(f"mask transform {name} must be a number")
    return float(value)


def _positive_number(value: Any, name: str) -> float:
    number = _number(value, name)
    if number <= 0:
        raise TrainingBatchError(f"mask transform {name} must be positive")
    return number


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise TrainingBatchError("training batch loading requires numpy") from exc
    return numpy
