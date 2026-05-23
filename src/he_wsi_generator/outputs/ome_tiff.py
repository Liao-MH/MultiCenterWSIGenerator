from pathlib import Path
from typing import Any


class OutputWriteError(RuntimeError):
    """Raised when output files cannot be written or verified."""


def write_pyramid_ome_tiff(
    levels: list[Any],
    output_path: str | Path,
    metadata: dict | None = None,
) -> dict:
    numpy = _import_numpy()
    tifffile = _import_tifffile()
    if len(levels) < 1:
        raise OutputWriteError("pyramid must contain at least one level")
    arrays = [numpy.asarray(level, dtype=numpy.uint8) for level in levels]
    _validate_pyramid_arrays(arrays)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffWriter(target, bigtiff=False) as writer:
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
        "write_mode": "small_pyramid_smoke_writer",
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
