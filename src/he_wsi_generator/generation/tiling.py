from typing import Any

from ..constants import PROJECT_VERSION, TILE_SIZE_40X


class GenerationTilingError(ValueError):
    """Raised when tile traversal or blending inputs violate generation contracts."""


def create_tile_traversal_plan(
    canvas_size_40x: list[int] | tuple[int, int],
    tile_size_40x: list[int] | tuple[int, int] = TILE_SIZE_40X,
    overlap_px_40x: int = 64,
    resume_index: int = 0,
    cascade_level: str = "1/1",
) -> dict[str, Any]:
    canvas_width, canvas_height = _validate_size_pair(canvas_size_40x, "canvas_size_40x")
    tile_width, tile_height = _validate_size_pair(tile_size_40x, "tile_size_40x")
    overlap = _validate_overlap(overlap_px_40x, tile_width, tile_height)
    if not isinstance(resume_index, int) or isinstance(resume_index, bool):
        raise GenerationTilingError("resume_index must be an integer")

    stride_x = tile_width - overlap
    stride_y = tile_height - overlap
    x_origins = _axis_origins(canvas_width, tile_width, stride_x)
    y_origins = _axis_origins(canvas_height, tile_height, stride_y)
    tile_count = len(x_origins) * len(y_origins)
    if resume_index < 0 or resume_index > tile_count:
        raise GenerationTilingError("resume_index must be between 0 and tile_count")

    tiles: list[dict[str, Any]] = []
    for y_origin in y_origins:
        for x_origin in x_origins:
            tile_index = len(tiles)
            write_width = min(tile_width, canvas_width - x_origin)
            write_height = min(tile_height, canvas_height - y_origin)
            tiles.append(
                {
                    "tile_index": tile_index,
                    "cascade_level": cascade_level,
                    "status": "completed" if tile_index < resume_index else "pending",
                    "tile_origin_40x": [x_origin, y_origin],
                    "model_tile_size_40x": [tile_width, tile_height],
                    "write_region_40x": [x_origin, y_origin, write_width, write_height],
                    "canvas_size_40x": [canvas_width, canvas_height],
                    "overlap_px_40x": overlap,
                    "stride_40x": [stride_x, stride_y],
                }
            )

    return {
        "schema_version": PROJECT_VERSION,
        "tile_traversal": "row_major_with_resume_index",
        "cascade_level": cascade_level,
        "canvas_size_40x": [canvas_width, canvas_height],
        "model_tile_size_40x": [tile_width, tile_height],
        "overlap_px_40x": overlap,
        "stride_40x": [stride_x, stride_y],
        "edge_policy": "crop_tile_to_canvas",
        "resume_index": resume_index,
        "tile_count": tile_count,
        "completed_tile_count": resume_index,
        "pending_tile_count": tile_count - resume_index,
        "next_tile_index": None if resume_index == tile_count else resume_index,
        "tiles": tiles,
    }


def blend_rgb_tiles(
    tile_records: list[dict[str, Any]],
    canvas_size_40x: list[int] | tuple[int, int],
    overlap_px_40x: int,
):
    numpy = _import_numpy()
    canvas_width, canvas_height = _validate_size_pair(canvas_size_40x, "canvas_size_40x")
    if (
        not isinstance(overlap_px_40x, int)
        or isinstance(overlap_px_40x, bool)
        or overlap_px_40x < 0
    ):
        raise GenerationTilingError("overlap_px_40x must be a non-negative integer")
    if not isinstance(tile_records, list) or not tile_records:
        raise GenerationTilingError("tile_records must contain at least one tile")

    accum = numpy.zeros((canvas_height, canvas_width, 3), dtype=numpy.float64)
    weight_sum = numpy.zeros((canvas_height, canvas_width), dtype=numpy.float64)

    for index, record in enumerate(tile_records):
        if not isinstance(record, dict):
            raise GenerationTilingError(f"tile_records[{index}] must be an object")
        image = record.get("image")
        if not isinstance(image, numpy.ndarray):
            raise GenerationTilingError(f"tile_records[{index}].image must be a numpy array")
        if image.ndim != 3 or image.shape[2] != 3 or image.shape[0] <= 0 or image.shape[1] <= 0:
            raise GenerationTilingError(f"tile_records[{index}].image must be a non-empty RGB tile")
        if image.dtype != numpy.uint8:
            raise GenerationTilingError(f"tile_records[{index}].image must have dtype uint8")
        x_origin, y_origin = _validate_origin(
            record.get("tile_origin_40x"),
            f"tile_records[{index}].tile_origin_40x",
        )
        if x_origin >= canvas_width or y_origin >= canvas_height:
            raise GenerationTilingError(f"tile_records[{index}].tile_origin_40x must overlap canvas")

        crop_width = min(image.shape[1], canvas_width - x_origin)
        crop_height = min(image.shape[0], canvas_height - y_origin)
        if crop_width <= 0 or crop_height <= 0:
            raise GenerationTilingError(f"tile_records[{index}].image has no writable region")

        # Each tile carries a soft edge ramp. Single-tile regions divide by their
        # own positive weight, while overlaps become weighted averages.
        weight = _tile_weight_mask(numpy, image.shape[0], image.shape[1], overlap_px_40x)
        image_crop = image[:crop_height, :crop_width].astype(numpy.float64)
        weight_crop = weight[:crop_height, :crop_width]
        y_slice = slice(y_origin, y_origin + crop_height)
        x_slice = slice(x_origin, x_origin + crop_width)
        accum[y_slice, x_slice] += image_crop * weight_crop[..., None]
        weight_sum[y_slice, x_slice] += weight_crop

    if numpy.any(weight_sum <= 0):
        raise GenerationTilingError("tile inputs must cover canvas")

    blended = accum / weight_sum[..., None]
    return numpy.clip(numpy.rint(blended), 0, 255).astype(numpy.uint8)


def complete_tile_traversal_plan(
    tile_traversal_plan: dict[str, Any],
    completed_tile_count: int | None = None,
) -> dict[str, Any]:
    if not isinstance(tile_traversal_plan, dict):
        raise GenerationTilingError("tile_traversal_plan must be an object")
    tiles = tile_traversal_plan.get("tiles")
    if not isinstance(tiles, list):
        raise GenerationTilingError("tile_traversal_plan.tiles must be a list")
    tile_count = tile_traversal_plan.get("tile_count")
    if not isinstance(tile_count, int) or isinstance(tile_count, bool) or tile_count < 0:
        raise GenerationTilingError("tile_traversal_plan.tile_count must be a non-negative integer")

    if completed_tile_count is None:
        completed_tile_count = tile_count
    if (
        not isinstance(completed_tile_count, int)
        or isinstance(completed_tile_count, bool)
        or completed_tile_count < 0
        or completed_tile_count > tile_count
    ):
        raise GenerationTilingError(
            "completed_tile_count must be between 0 and tile_traversal_plan.tile_count"
        )

    updated_tiles: list[dict[str, Any]] = []
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise GenerationTilingError(f"tile_traversal_plan.tiles[{index}] must be an object")
        updated_tile = dict(tile)
        updated_tile["status"] = "completed" if index < completed_tile_count else "pending"
        updated_tiles.append(updated_tile)

    updated_plan = dict(tile_traversal_plan)
    updated_plan["resume_index"] = completed_tile_count
    updated_plan["completed_tile_count"] = completed_tile_count
    updated_plan["pending_tile_count"] = tile_count - completed_tile_count
    updated_plan["next_tile_index"] = None if completed_tile_count == tile_count else completed_tile_count
    updated_plan["tiles"] = updated_tiles
    updated_plan["execution_status"] = (
        "completed" if completed_tile_count == tile_count else "in_progress"
    )
    return updated_plan


def _axis_origins(length: int, tile_size: int, stride: int) -> list[int]:
    origins = [0]
    while origins[-1] + tile_size < length:
        origins.append(origins[-1] + stride)
    return origins


def _tile_weight_mask(numpy, height: int, width: int, overlap: int):
    if overlap == 0:
        return numpy.ones((height, width), dtype=numpy.float64)
    y_weight = _axis_weight(numpy, height, overlap)
    x_weight = _axis_weight(numpy, width, overlap)
    return y_weight[:, None] * x_weight[None, :]


def _axis_weight(numpy, length: int, overlap: int):
    positions = numpy.arange(length, dtype=numpy.float64)
    denominator = float(overlap + 1)
    left = numpy.minimum(1.0, (positions + 1.0) / denominator)
    right = numpy.minimum(1.0, (length - positions) / denominator)
    return numpy.minimum(left, right)


def _validate_size_pair(value: Any, path: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise GenerationTilingError(f"{path} must contain [width, height]")
    width, height = value
    if (
        not isinstance(width, int)
        or isinstance(width, bool)
        or not isinstance(height, int)
        or isinstance(height, bool)
        or width <= 0
        or height <= 0
    ):
        raise GenerationTilingError(f"{path} values must be positive integers")
    return width, height


def _validate_origin(value: Any, path: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise GenerationTilingError(f"{path} must contain [x, y]")
    x_origin, y_origin = value
    if (
        not isinstance(x_origin, int)
        or isinstance(x_origin, bool)
        or not isinstance(y_origin, int)
        or isinstance(y_origin, bool)
        or x_origin < 0
        or y_origin < 0
    ):
        raise GenerationTilingError(f"{path} values must be non-negative integers")
    return x_origin, y_origin


def _validate_overlap(overlap: Any, tile_width: int, tile_height: int) -> int:
    if not isinstance(overlap, int) or isinstance(overlap, bool) or overlap < 0:
        raise GenerationTilingError("overlap_px_40x must be a non-negative integer")
    if overlap >= min(tile_width, tile_height):
        raise GenerationTilingError("overlap_px_40x must be smaller than both tile dimensions")
    return overlap


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise GenerationTilingError("tile blending requires numpy") from exc
    return numpy
