from pathlib import Path
from typing import Any


class OutputWriteError(RuntimeError):
    """Raised when output files cannot be written or verified."""


def write_pyramid_ome_tiff(
    levels: list[Any],
    output_path: str | Path,
    metadata: dict | None = None,
    chunk_shape: tuple[int, int] | list[int] = (512, 512),
    bigtiff_threshold_bytes: int = 4 * 1024 * 1024 * 1024,
) -> dict:
    numpy = _import_numpy()
    tifffile = _import_tifffile()
    if len(levels) < 1:
        raise OutputWriteError("pyramid must contain at least one level")
    arrays = [numpy.asarray(level, dtype=numpy.uint8) for level in levels]
    _validate_pyramid_arrays(arrays)
    chunk_height, chunk_width = _validate_chunk_shape(chunk_shape)
    bigtiff_threshold = _validate_bigtiff_threshold(bigtiff_threshold_bytes)
    estimated_total_bytes = _estimated_total_bytes(arrays)
    use_bigtiff = estimated_total_bytes >= bigtiff_threshold
    chunked_write_audit = _chunked_write_audit(
        arrays,
        chunk_height=chunk_height,
        chunk_width=chunk_width,
        estimated_total_bytes=estimated_total_bytes,
        bigtiff=use_bigtiff,
        bigtiff_threshold_bytes=bigtiff_threshold,
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffWriter(target, bigtiff=use_bigtiff) as writer:
        writer.write(
            arrays[0],
            subifds=len(arrays) - 1,
            photometric="rgb" if arrays[0].ndim == 3 else "minisblack",
            metadata={"axes": "YXS" if arrays[0].ndim == 3 else "YX", **(metadata or {})},
        )
        for array in arrays[1:]:
            writer.write(
                array,
                subfiletype=1,
                photometric="rgb" if array.ndim == 3 else "minisblack",
                metadata={"axes": "YXS" if array.ndim == 3 else "YX"},
            )

    with tifffile.TiffFile(target) as tiff:
        if not tiff.is_ome:
            raise OutputWriteError("written TIFF is not recognized as OME-TIFF")
        level_shapes = [list(level.shape) for level in tiff.series[0].levels]

    return {
        "status": "written",
        "path": str(target),
        "level_count": len(level_shapes),
        "level_shapes": level_shapes,
        "is_ome": True,
        "write_mode": "chunked_pyramid_write",
        "chunked_write_audit": chunked_write_audit,
    }


def _validate_pyramid_arrays(arrays: list[Any]) -> None:
    previous_height = None
    previous_width = None
    for index, array in enumerate(arrays):
        if array.ndim not in {2, 3}:
            raise OutputWriteError(f"level {index} must be a 2D or RGB image array")
        height, width = array.shape[:2]
        if height <= 0 or width <= 0:
            raise OutputWriteError(f"level {index} has invalid dimensions")
        if array.ndim == 3 and array.shape[2] not in {3, 4}:
            raise OutputWriteError(f"level {index} must have 3 or 4 channels")
        if previous_height is not None and (height > previous_height or width > previous_width):
            raise OutputWriteError("pyramid levels must be ordered from high to low resolution")
        previous_height = height
        previous_width = width


def _validate_chunk_shape(value: tuple[int, int] | list[int]) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise OutputWriteError("chunk_shape must contain [height, width]")
    height, width = value
    if (
        not isinstance(height, int)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or isinstance(width, bool)
        or height <= 0
        or width <= 0
    ):
        raise OutputWriteError("chunk_shape values must be positive integers")
    return int(height), int(width)


def _validate_bigtiff_threshold(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise OutputWriteError("bigtiff_threshold_bytes must be a positive integer")
    return int(value)


def _estimated_total_bytes(arrays: list[Any]) -> int:
    return int(sum(int(array.size) * int(array.dtype.itemsize) for array in arrays))


def _chunked_write_audit(
    arrays: list[Any],
    *,
    chunk_height: int,
    chunk_width: int,
    estimated_total_bytes: int,
    bigtiff: bool,
    bigtiff_threshold_bytes: int,
) -> dict:
    return {
        "writer_backend": "tifffile",
        "write_mode": "chunked_pyramid_write",
        "production_streaming": False,
        "bigtiff": bool(bigtiff),
        "bigtiff_threshold_bytes": int(bigtiff_threshold_bytes),
        "estimated_total_bytes": int(estimated_total_bytes),
        "chunk_shape": [chunk_height, chunk_width],
        "levels": [
            _level_chunk_plan(
                index,
                array,
                chunk_height=chunk_height,
                chunk_width=chunk_width,
            )
            for index, array in enumerate(arrays)
        ],
        "streaming_limitations": [
            "in_memory_array_writer",
            "chunk_plan_is_audit_metadata_only",
            "not_a_resume_capable_gigapixel_streaming_writer",
        ],
    }


def _level_chunk_plan(
    level_index: int,
    array: Any,
    *,
    chunk_height: int,
    chunk_width: int,
) -> dict:
    height, width = [int(value) for value in array.shape[:2]]
    grid_y = _ceil_div(height, chunk_height)
    grid_x = _ceil_div(width, chunk_width)
    edge_height = height - (grid_y - 1) * chunk_height
    edge_width = width - (grid_x - 1) * chunk_width
    return {
        "level_index": int(level_index),
        "shape": [int(value) for value in array.shape],
        "dtype": str(array.dtype),
        "chunk_shape": [chunk_height, chunk_width],
        "chunk_grid": [grid_y, grid_x],
        "chunk_count": int(grid_y * grid_x),
        "edge_chunk_shape": [edge_height, edge_width],
    }


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise OutputWriteError("OME-TIFF writing requires numpy") from exc
    return numpy


def _import_tifffile():
    try:
        import tifffile
    except ImportError as exc:
        raise OutputWriteError("OME-TIFF writing requires tifffile") from exc
    return tifffile
