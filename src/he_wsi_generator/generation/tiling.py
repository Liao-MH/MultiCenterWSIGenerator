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


def build_resumable_tile_manifest(tile_traversal_plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(tile_traversal_plan, dict):
        raise GenerationTilingError("tile_traversal_plan must be an object")
    base_plan = complete_tile_traversal_plan(
        tile_traversal_plan,
        completed_tile_count=_validate_resume_count(tile_traversal_plan),
    )
    tiles = []
    for index, tile in enumerate(base_plan["tiles"]):
        tile_copy = dict(tile)
        tile_copy.setdefault("tile_index", index)
        tile_copy["attempt_count"] = 0
        tile_copy["output_path"] = None
        tile_copy["error_message"] = None
        tiles.append(tile_copy)

    manifest = {
        "schema_version": PROJECT_VERSION,
        "manifest_type": "resumable_tile_manifest",
        "tile_traversal": base_plan["tile_traversal"],
        "cascade_level": base_plan["cascade_level"],
        "canvas_size_40x": list(base_plan["canvas_size_40x"]),
        "model_tile_size_40x": list(base_plan["model_tile_size_40x"]),
        "overlap_px_40x": base_plan["overlap_px_40x"],
        "stride_40x": list(base_plan["stride_40x"]),
        "edge_policy": base_plan["edge_policy"],
        "tile_count": base_plan["tile_count"],
        "tiles": tiles,
    }
    return _refresh_resumable_tile_manifest(manifest)


def update_resumable_tile_manifest(
    tile_manifest: dict[str, Any],
    *,
    tile_index: int,
    status: str,
    output_path: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    manifest = validate_resumable_tile_manifest(tile_manifest)
    index = _validate_tile_index_value(tile_index, "tile_index")
    if index >= manifest["tile_count"]:
        raise GenerationTilingError("tile_index must be smaller than tile_count")
    if status not in {"pending", "completed", "failed"}:
        raise GenerationTilingError("status must be pending, completed, or failed")
    if output_path is not None and (not isinstance(output_path, str) or output_path == ""):
        raise GenerationTilingError("output_path must be a non-empty string")
    if error_message is not None and (
        not isinstance(error_message, str) or error_message == ""
    ):
        raise GenerationTilingError("error_message must be a non-empty string")

    tiles = [dict(tile) for tile in manifest["tiles"]]
    tile = dict(tiles[index])
    tile["status"] = status
    tile["attempt_count"] = int(tile.get("attempt_count", 0)) + 1
    if status == "completed":
        tile["output_path"] = output_path
        tile["error_message"] = None
    elif status == "failed":
        tile["output_path"] = output_path
        tile["error_message"] = error_message
    else:
        tile["output_path"] = None
        tile["error_message"] = None
    tiles[index] = tile

    updated = dict(manifest)
    updated["tiles"] = tiles
    return _refresh_resumable_tile_manifest(updated)


def validate_resumable_tile_manifest(tile_manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(tile_manifest, dict):
        raise GenerationTilingError("tile_manifest must be an object")
    if tile_manifest.get("schema_version") != PROJECT_VERSION:
        raise GenerationTilingError(f"tile_manifest.schema_version must be {PROJECT_VERSION}")
    if tile_manifest.get("manifest_type") != "resumable_tile_manifest":
        raise GenerationTilingError("tile_manifest.manifest_type must be resumable_tile_manifest")
    tile_count = _validate_tile_count_value(tile_manifest.get("tile_count"), "tile_count")
    tiles = tile_manifest.get("tiles")
    if not isinstance(tiles, list):
        raise GenerationTilingError("tile_manifest.tiles must be a list")
    if len(tiles) != tile_count:
        raise GenerationTilingError("tile_manifest.tiles length must match tile_count")

    validated_tiles = []
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise GenerationTilingError(f"tile_manifest.tiles[{index}] must be an object")
        tile_index = _validate_tile_index_value(
            tile.get("tile_index"),
            f"tile_manifest.tiles[{index}].tile_index",
        )
        if tile_index != index:
            raise GenerationTilingError("tile_manifest tile_index values must be sequential")
        status = tile.get("status")
        if status not in {"pending", "completed", "failed"}:
            raise GenerationTilingError(f"tile_manifest.tiles[{index}].status is invalid")
        attempt_count = tile.get("attempt_count", 0)
        if not isinstance(attempt_count, int) or isinstance(attempt_count, bool) or attempt_count < 0:
            raise GenerationTilingError(
                f"tile_manifest.tiles[{index}].attempt_count must be non-negative"
            )
        output_path = tile.get("output_path")
        if output_path is not None and (not isinstance(output_path, str) or output_path == ""):
            raise GenerationTilingError(
                f"tile_manifest.tiles[{index}].output_path must be a non-empty string"
            )
        error_message = tile.get("error_message")
        if error_message is not None and (
            not isinstance(error_message, str) or error_message == ""
        ):
            raise GenerationTilingError(
                f"tile_manifest.tiles[{index}].error_message must be a non-empty string"
            )
        validated_tile = dict(tile)
        validated_tile["attempt_count"] = attempt_count
        validated_tile.setdefault("output_path", None)
        validated_tile.setdefault("error_message", None)
        validated_tiles.append(validated_tile)

    refreshed = dict(tile_manifest)
    refreshed["tile_count"] = tile_count
    refreshed["tiles"] = validated_tiles
    expected = _summarize_tile_statuses(validated_tiles, tile_count)
    for key, value in expected.items():
        if refreshed.get(key) != value:
            raise GenerationTilingError(f"tile_manifest.{key} does not match tile statuses")
    return refreshed


def require_complete_tile_manifest(tile_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = validate_resumable_tile_manifest(tile_manifest)
    if manifest["failed_tile_count"] > 0:
        raise GenerationTilingError("tile manifest contains failed tiles")
    if _has_row_major_gap(manifest["tiles"]):
        raise GenerationTilingError("tile manifest must complete tiles in row-major resume order")
    if manifest["pending_tile_count"] > 0:
        raise GenerationTilingError("tile manifest contains pending tiles")
    if manifest["completed_tile_count"] != manifest["tile_count"]:
        raise GenerationTilingError("tile manifest is incomplete")
    return manifest


def _refresh_resumable_tile_manifest(tile_manifest: dict[str, Any]) -> dict[str, Any]:
    tile_count = _validate_tile_count_value(tile_manifest.get("tile_count"), "tile_count")
    tiles = tile_manifest.get("tiles")
    if not isinstance(tiles, list):
        raise GenerationTilingError("tile_manifest.tiles must be a list")
    if len(tiles) != tile_count:
        raise GenerationTilingError("tile_manifest.tiles length must match tile_count")

    normalized_tiles = []
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise GenerationTilingError(f"tile_manifest.tiles[{index}] must be an object")
        normalized = dict(tile)
        normalized["tile_index"] = _validate_tile_index_value(
            normalized.get("tile_index"),
            f"tile_manifest.tiles[{index}].tile_index",
        )
        if normalized["tile_index"] != index:
            raise GenerationTilingError("tile_manifest tile_index values must be sequential")
        normalized.setdefault("attempt_count", 0)
        normalized.setdefault("output_path", None)
        normalized.setdefault("error_message", None)
        normalized_tiles.append(normalized)

    refreshed = dict(tile_manifest)
    refreshed["schema_version"] = PROJECT_VERSION
    refreshed["manifest_type"] = "resumable_tile_manifest"
    refreshed["tile_count"] = tile_count
    refreshed["tiles"] = normalized_tiles
    refreshed.update(_summarize_tile_statuses(normalized_tiles, tile_count))
    return refreshed


def _summarize_tile_statuses(tiles: list[dict[str, Any]], tile_count: int) -> dict[str, Any]:
    completed = sum(1 for tile in tiles if tile.get("status") == "completed")
    failed = sum(1 for tile in tiles if tile.get("status") == "failed")
    pending = sum(1 for tile in tiles if tile.get("status") == "pending")
    resume_index = 0
    for tile in tiles:
        if tile.get("status") != "completed":
            break
        resume_index += 1
    next_tile_index = None if resume_index == tile_count else resume_index
    if failed > 0:
        execution_status = "failed"
    elif completed == tile_count:
        execution_status = "completed"
    else:
        execution_status = "in_progress"
    return {
        "completed_tile_count": completed,
        "pending_tile_count": pending,
        "failed_tile_count": failed,
        "resume_index": resume_index,
        "next_tile_index": next_tile_index,
        "execution_status": execution_status,
    }


def _has_row_major_gap(tiles: list[dict[str, Any]]) -> bool:
    seen_open_tile = False
    for tile in tiles:
        if tile.get("status") == "completed":
            if seen_open_tile:
                return True
        else:
            seen_open_tile = True
    return False


def _validate_resume_count(tile_traversal_plan: dict[str, Any]) -> int:
    resume_index = tile_traversal_plan.get("resume_index", 0)
    if not isinstance(resume_index, int) or isinstance(resume_index, bool) or resume_index < 0:
        raise GenerationTilingError("tile_traversal_plan.resume_index must be non-negative")
    return resume_index


def _validate_tile_count_value(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GenerationTilingError(f"{path} must be a non-negative integer")
    return int(value)


def _validate_tile_index_value(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GenerationTilingError(f"{path} must be a non-negative integer")
    return int(value)


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
