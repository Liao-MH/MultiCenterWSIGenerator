import json
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
    tile_source_manifest: dict | str | Path | None = None,
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
    # The disk-tile contract gates publication, but this writer still consumes
    # in-memory arrays until a true tile-by-tile OME-TIFF backend is added.
    if tile_source_manifest is None:
        streaming_contract = _array_writer_streaming_contract_report()
    else:
        streaming_contract = _validate_disk_tile_source_contract(
            tile_source_manifest,
            numpy=numpy,
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
        "production_streaming": False,
        "write_mode": "chunked_pyramid_write",
        "chunked_write_audit": chunked_write_audit,
        "streaming_contract": streaming_contract,
    }


def validate_disk_tile_source_contract(tile_source_manifest: dict | str | Path) -> dict:
    """Validate a disk tile manifest without claiming streaming write support."""
    return _validate_disk_tile_source_contract(tile_source_manifest, numpy=_import_numpy())


def write_pyramid_ome_tiff_from_tile_sources(
    tile_source_manifest: dict | str | Path,
    output_path: str | Path,
    metadata: dict | None = None,
    chunk_shape: tuple[int, int] | list[int] = (512, 512),
    bigtiff_threshold_bytes: int = 4 * 1024 * 1024 * 1024,
) -> dict:
    """Assemble validated .npy disk tiles before delegating to the OME-TIFF writer.

    This is intentionally a contract-gated assembly path, not a production
    gigapixel tile-by-tile writer: tiles are checked on disk, assembled into
    level arrays in memory, then written through the existing tifffile backend.
    """
    numpy = _import_numpy()
    assembly = _assemble_disk_tile_source_arrays(tile_source_manifest, numpy=numpy)
    report = write_pyramid_ome_tiff(
        assembly["levels"],
        output_path,
        metadata=metadata,
        chunk_shape=chunk_shape,
        bigtiff_threshold_bytes=bigtiff_threshold_bytes,
        tile_source_manifest=tile_source_manifest,
    )
    report["write_mode"] = "disk_tile_source_assembly_write"
    report["production_streaming"] = False
    report["assembly_report"] = assembly["assembly_report"]
    report["streaming_contract"]["assembly_mode"] = "in_memory_disk_tile_assembly"
    limitations = report["streaming_contract"].setdefault("streaming_limitations", [])
    if "assembled_in_memory_before_tifffile_write" not in limitations:
        limitations.append("assembled_in_memory_before_tifffile_write")
    return report


def write_pyramid_ome_tiff_streaming_from_tile_sources(
    tile_source_manifest: dict | str | Path,
    output_path: str | Path,
    metadata: dict | None = None,
    chunk_shape: tuple[int, int] | list[int] = (512, 512),
    bigtiff_threshold_bytes: int = 4 * 1024 * 1024 * 1024,
) -> dict:
    """Write a tiled OME-TIFF pyramid from disk tiles without level assembly.

    This path streams one TIFF tile at a time from validated `.npy` sources.
    It is intentionally stricter than the in-memory assembly path: every
    manifest record must map to exactly one TIFF tile grid cell. The output file
    itself is not resume-capable after interruption, so the report keeps that
    limitation explicit.
    """
    numpy = _import_numpy()
    tifffile = _import_tifffile()
    chunk_height, chunk_width = _validate_chunk_shape(chunk_shape)
    _validate_tiff_tile_shape(chunk_height, chunk_width)
    bigtiff_threshold = _validate_bigtiff_threshold(bigtiff_threshold_bytes)
    manifest, manifest_path = _load_tile_source_manifest(tile_source_manifest)
    streaming_contract = _validate_disk_tile_source_contract(tile_source_manifest, numpy=numpy)
    plan = _build_tile_iterator_streaming_plan(
        manifest,
        manifest_path=manifest_path,
        numpy=numpy,
        chunk_height=chunk_height,
        chunk_width=chunk_width,
    )
    estimated_total_bytes = _estimated_total_bytes_from_shapes(plan["level_shapes"], numpy.uint8)
    use_bigtiff = estimated_total_bytes >= bigtiff_threshold

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffWriter(target, bigtiff=use_bigtiff) as writer:
        for offset, level in enumerate(plan["levels"]):
            level_shape = tuple(level["shape"])
            axes = "YXS" if len(level_shape) == 3 else "YX"
            writer.write(
                _iter_streaming_level_tiles(numpy, level, chunk_height, chunk_width),
                shape=level_shape,
                dtype=numpy.uint8,
                tile=(chunk_height, chunk_width),
                photometric="rgb" if len(level_shape) == 3 else "minisblack",
                subifds=(len(plan["levels"]) - 1 if offset == 0 else None),
                subfiletype=(1 if offset > 0 else None),
                metadata=({"axes": axes, **(metadata or {})} if offset == 0 else {"axes": axes}),
            )

    with tifffile.TiffFile(target) as tiff:
        if not tiff.is_ome:
            raise OutputWriteError("written TIFF is not recognized as OME-TIFF")
        level_shapes = [list(level.shape) for level in tiff.series[0].levels]

    streaming_write_report = _tile_iterator_streaming_report(
        plan,
        chunk_height=chunk_height,
        chunk_width=chunk_width,
        estimated_total_bytes=estimated_total_bytes,
        bigtiff=use_bigtiff,
        bigtiff_threshold_bytes=bigtiff_threshold,
    )
    streaming_contract["contract_status"] = "streaming_write_validated"
    streaming_contract["production_streaming"] = True
    streaming_contract["partial_contract_only"] = False
    streaming_contract["resume_capable"] = False
    streaming_contract["pyramid_order"] = plan["pyramid_order"]
    streaming_contract["level_order"] = plan["level_order"]
    streaming_contract["streaming_limitations"] = streaming_write_report["streaming_limitations"]
    return {
        "status": "written",
        "path": str(target),
        "level_count": len(level_shapes),
        "level_shapes": level_shapes,
        "is_ome": True,
        "production_streaming": True,
        "resume_capable": False,
        "write_mode": "tile_iterator_streaming_write",
        "streaming_contract": streaming_contract,
        "streaming_write_report": streaming_write_report,
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


def _validate_tiff_tile_shape(height: int, width: int) -> None:
    if height % 16 != 0 or width % 16 != 0:
        raise OutputWriteError("chunk_shape values must be multiples of 16 for tiled TIFF writing")


def _validate_bigtiff_threshold(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise OutputWriteError("bigtiff_threshold_bytes must be a positive integer")
    return int(value)


def _estimated_total_bytes(arrays: list[Any]) -> int:
    return int(sum(int(array.size) * int(array.dtype.itemsize) for array in arrays))


def _estimated_total_bytes_from_shapes(shapes: list[list[int]], dtype) -> int:
    itemsize = int(dtype().itemsize)
    total = 0
    for shape in shapes:
        size = 1
        for value in shape:
            size *= int(value)
        total += size * itemsize
    return int(total)


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


def _array_writer_streaming_contract_report() -> dict:
    return {
        "contract_status": "array_input_only",
        "production_streaming": False,
        "partial_contract_only": True,
        "tile_source": None,
        "coverage": {
            "expected_tile_count": 0,
            "completed_tile_count": 0,
            "pending_tile_count": 0,
            "failed_tile_count": 0,
            "missing_tile_count": 0,
            "levels": [],
        },
        "streaming_limitations": [
            "in_memory_array_writer",
            "no_disk_tile_source_manifest",
            "not_a_resume_capable_gigapixel_streaming_writer",
        ],
    }


def _validate_disk_tile_source_contract(tile_source_manifest: dict | str | Path, *, numpy) -> dict:
    manifest, manifest_path = _load_tile_source_manifest(tile_source_manifest)
    expected_tile_count = _validate_positive_int(
        _first_present(manifest, ("expected_tile_count", "tile_count")),
        "tile_source.expected_tile_count",
    )
    records = _validate_tile_records(manifest.get("tiles", manifest.get("records")))
    level_contracts = _validate_level_contracts(manifest.get("levels", []))
    level_indexes = {level["level_index"] for level in level_contracts}
    level_expected_counts = {
        level["level_index"]: level["expected_tile_count"]
        for level in level_contracts
        if level.get("expected_tile_count") is not None
    }
    if level_expected_counts:
        level_expected_total = sum(level_expected_counts.values())
        if level_expected_total != expected_tile_count:
            raise OutputWriteError(
                "tile source level expected counts must sum to expected_tile_count"
            )

    seen_keys: set[tuple[int, int]] = set()
    per_level_indexes: dict[int, list[int]] = {}
    for record_offset, record in enumerate(records):
        record_path = f"tile_source.tiles[{record_offset}]"
        level_index = _validate_non_negative_int(record.get("level_index"), f"{record_path}.level_index")
        tile_index = _validate_non_negative_int(record.get("tile_index"), f"{record_path}.tile_index")
        if level_indexes and level_index not in level_indexes:
            raise OutputWriteError(f"{record_path}.level_index is not declared in tile_source.levels")
        key = (level_index, tile_index)
        if key in seen_keys:
            raise OutputWriteError(
                f"duplicate tile source record for level_index={level_index} tile_index={tile_index}"
            )
        seen_keys.add(key)

        status = record.get("status")
        if status != "completed":
            if status == "pending":
                raise OutputWriteError(f"{record_path} is pending and cannot be published")
            if status == "failed":
                raise OutputWriteError(f"{record_path} is failed and cannot be published")
            raise OutputWriteError(f"{record_path}.status must be completed")

        tile_path = _resolve_tile_path(record.get("path", record.get("tile_path")), manifest_path, record_path)
        shape = _validate_shape(record.get("shape"), f"{record_path}.shape")
        dtype = _validate_dtype(record.get("dtype"), f"{record_path}.dtype")
        actual_shape, actual_dtype = _inspect_npy_tile(numpy, tile_path, record_path)
        if actual_shape != shape:
            raise OutputWriteError(
                f"{record_path}.shape mismatch: manifest {shape}, file {actual_shape}"
            )
        if actual_dtype != dtype:
            raise OutputWriteError(
                f"{record_path}.dtype mismatch: manifest {dtype}, file {actual_dtype}"
            )

        per_level_indexes.setdefault(level_index, []).append(tile_index)

    completed_tile_count = len(seen_keys)
    if completed_tile_count < expected_tile_count:
        raise OutputWriteError(
            f"missing tile source records: expected {expected_tile_count}, found {completed_tile_count}"
        )
    if completed_tile_count > expected_tile_count:
        raise OutputWriteError(
            f"tile source expected_tile_count is {expected_tile_count}, found {completed_tile_count}"
        )

    level_coverage = _build_level_coverage(per_level_indexes, level_expected_counts)
    return {
        "contract_status": "partial_contract_only",
        "production_streaming": False,
        "partial_contract_only": True,
        "tile_source": {
            "source_type": "disk_npy_tile_manifest",
            "manifest_path": str(manifest_path) if manifest_path is not None else None,
        },
        "coverage": {
            "expected_tile_count": expected_tile_count,
            "completed_tile_count": completed_tile_count,
            "pending_tile_count": 0,
            "failed_tile_count": 0,
            "missing_tile_count": 0,
            "levels": level_coverage,
        },
        "validated_fields": [
            "tile_index",
            "level_index",
            "path_exists",
            "shape",
            "dtype",
            "completed_status",
            "expected_tile_count",
        ],
        "streaming_limitations": [
            "tile_source_validated_but_writer_still_in_memory",
            "npy_tile_arrays_only",
            "not_a_resume_capable_gigapixel_streaming_writer",
        ],
    }


def _assemble_disk_tile_source_arrays(tile_source_manifest: dict | str | Path, *, numpy) -> dict:
    manifest, manifest_path = _load_tile_source_manifest(tile_source_manifest)
    # Reuse the existing publication gate first so pending/failed records,
    # missing files, duplicate indexes, shape, dtype, and count mismatches fail
    # before any canvas allocation or partial write can happen.
    _validate_disk_tile_source_contract(tile_source_manifest, numpy=numpy)
    records = _validate_tile_records(manifest.get("tiles", manifest.get("records")))
    level_shapes = _level_shapes_by_index(manifest.get("levels", []))
    if not level_shapes:
        raise OutputWriteError("tile source levels must declare shape for assembly")

    level_arrays: dict[int, Any] = {
        level_index: numpy.zeros(shape, dtype=numpy.uint8)
        for level_index, shape in level_shapes.items()
    }
    coverage_masks = {
        level_index: numpy.zeros(shape[:2], dtype=numpy.uint8)
        for level_index, shape in level_shapes.items()
    }
    per_level_records: dict[int, int] = {level_index: 0 for level_index in level_shapes}

    for record_offset, record in enumerate(records):
        record_path = f"tile_source.tiles[{record_offset}]"
        level_index = _validate_non_negative_int(record.get("level_index"), f"{record_path}.level_index")
        if level_index not in level_arrays:
            raise OutputWriteError(f"{record_path}.level_index is not declared in tile_source.levels")
        tile_path = _resolve_tile_path(record.get("path", record.get("tile_path")), manifest_path, record_path)
        tile = _load_npy_tile(numpy, tile_path, record_path)
        declared_shape = _validate_shape(record.get("shape"), f"{record_path}.shape")
        if [int(value) for value in tile.shape] != declared_shape:
            raise OutputWriteError(
                f"{record_path}.shape mismatch: manifest {declared_shape}, file {[int(value) for value in tile.shape]}"
            )
        if str(tile.dtype) != _validate_dtype(record.get("dtype"), f"{record_path}.dtype"):
            raise OutputWriteError(f"{record_path}.dtype mismatch")
        region = _validate_write_region(
            _first_present(record, ("write_region_40x", "write_region")),
            record_path,
        )
        origin = _validate_tile_origin(
            _first_present(record, ("tile_origin_40x", "tile_origin")),
            record_path,
        )
        if origin != region[:2]:
            raise OutputWriteError(f"{record_path}.tile_origin must match write_region origin")
        canvas = level_arrays[level_index]
        coverage = coverage_masks[level_index]
        _write_tile_to_level(canvas, coverage, tile, region, record_path)
        per_level_records[level_index] += 1

    assembly_levels = []
    assembly_report_levels = []
    for level_index in sorted(level_arrays):
        coverage = coverage_masks[level_index]
        if numpy.any(coverage == 0):
            raise OutputWriteError(f"tile source records must cover level_index={level_index}")
        level_array = level_arrays[level_index]
        assembly_levels.append(level_array)
        assembly_report_levels.append(
            {
                "level_index": level_index,
                "shape": [int(value) for value in level_array.shape],
                "dtype": str(level_array.dtype),
                "tile_count": per_level_records[level_index],
                "covered_pixel_count": int(coverage.sum()),
            }
        )

    return {
        "levels": assembly_levels,
        "assembly_report": {
            "assembly_mode": "in_memory_disk_tile_assembly",
            "production_streaming": False,
            "assembled_level_count": len(assembly_levels),
            "levels": assembly_report_levels,
            "limitations": [
                "assembled_in_memory_before_tifffile_write",
                "not_a_resume_capable_gigapixel_streaming_writer",
            ],
        },
    }


def _build_tile_iterator_streaming_plan(
    manifest: dict,
    *,
    manifest_path: Path | None,
    numpy,
    chunk_height: int,
    chunk_width: int,
) -> dict:
    records = _validate_tile_records(manifest.get("tiles", manifest.get("records")))
    ordered_levels = _streaming_levels_from_manifest(manifest.get("levels", []))
    level_shapes = {level["level_index"]: level["shape"] for level in ordered_levels}

    level_records: dict[int, dict[tuple[int, int], dict]] = {
        level_index: {} for level_index in level_shapes
    }
    level_counts: dict[int, int] = {level_index: 0 for level_index in level_shapes}

    for record_offset, record in enumerate(records):
        record_path = f"tile_source.tiles[{record_offset}]"
        level_index = _validate_non_negative_int(record.get("level_index"), f"{record_path}.level_index")
        if level_index not in level_shapes:
            raise OutputWriteError(f"{record_path}.level_index is not declared in tile_source.levels")
        tile_path = _resolve_tile_path(record.get("path", record.get("tile_path")), manifest_path, record_path)
        tile = _load_npy_tile(numpy, tile_path, record_path)
        shape = _validate_shape(record.get("shape"), f"{record_path}.shape")
        if [int(value) for value in tile.shape] != shape:
            raise OutputWriteError(
                f"{record_path}.shape mismatch: manifest {shape}, file {[int(value) for value in tile.shape]}"
            )
        if str(tile.dtype) != _validate_dtype(record.get("dtype"), f"{record_path}.dtype"):
            raise OutputWriteError(f"{record_path}.dtype mismatch")
        region = _validate_write_region(
            _first_present(record, ("write_region_40x", "write_region")),
            record_path,
        )
        origin = _validate_tile_origin(
            _first_present(record, ("tile_origin_40x", "tile_origin")),
            record_path,
        )
        if origin != region[:2]:
            raise OutputWriteError(f"{record_path}.tile_origin must match write_region origin")

        level_shape = level_shapes[level_index]
        cell_key = _validate_streaming_tile_grid_cell(
            tile,
            region,
            level_shape,
            record_path,
            chunk_height=chunk_height,
            chunk_width=chunk_width,
        )
        if cell_key in level_records[level_index]:
            raise OutputWriteError(f"{record_path}.write_region overlaps another tile")
        level_records[level_index][cell_key] = {
            "record_path": record_path,
            "path": tile_path,
            "region": region,
            "shape": shape,
        }
        level_counts[level_index] += 1

    levels = []
    for pyramid_position, level in enumerate(ordered_levels):
        level_index = level["level_index"]
        level_shape = level["shape"]
        height, width = level_shape[:2]
        grid_y = _ceil_div(height, chunk_height)
        grid_x = _ceil_div(width, chunk_width)
        expected_cells = {(row, col) for row in range(grid_y) for col in range(grid_x)}
        missing_cells = sorted(expected_cells - set(level_records[level_index]))
        if missing_cells:
            raise OutputWriteError(f"tile source records must cover level_index={level_index}")
        levels.append(
            {
                "level_index": level_index,
                "pyramid_position": pyramid_position,
                "shape": level_shape,
                "tile_grid": [grid_y, grid_x],
                "tile_count": level_counts[level_index],
                "records": level_records[level_index],
            }
        )

    return {
        "pyramid_order": "high_to_low_resolution",
        "level_order": [level["level_index"] for level in levels],
        "level_shapes": [level["shape"] for level in levels],
        "levels": levels,
    }


def _streaming_levels_from_manifest(value: Any) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise OutputWriteError("tile source levels must declare shape for streaming write")
    levels = []
    seen_indexes: set[int] = set()
    previous_height = None
    previous_width = None
    for index, level in enumerate(value):
        if not isinstance(level, dict):
            raise OutputWriteError(f"tile_source.levels[{index}] must be an object")
        level_index = _validate_non_negative_int(
            level.get("level_index"),
            f"tile_source.levels[{index}].level_index",
        )
        if level_index in seen_indexes:
            raise OutputWriteError(f"duplicate tile source level_index={level_index}")
        if "shape" not in level:
            raise OutputWriteError(
                f"tile_source.levels[{index}].shape is required for streaming write"
            )
        shape = _validate_shape(level.get("shape"), f"tile_source.levels[{index}].shape")
        height, width = shape[:2]
        # Streaming writes the OME-TIFF in this manifest order; accepting a
        # later level that is larger would silently invert the pyramid.
        if previous_height is not None and (height > previous_height or width > previous_width):
            raise OutputWriteError(
                "streaming pyramid level order must be high-to-low resolution; "
                f"tile_source.levels[{index}].shape is larger than the previous level"
            )
        levels.append({"level_index": level_index, "shape": shape})
        seen_indexes.add(level_index)
        previous_height = height
        previous_width = width
    return levels


def _validate_streaming_tile_grid_cell(
    tile,
    region: list[int],
    level_shape: list[int],
    record_path: str,
    *,
    chunk_height: int,
    chunk_width: int,
) -> tuple[int, int]:
    x_origin, y_origin, width, height = region
    level_height, level_width = level_shape[:2]
    if y_origin + height > level_height or x_origin + width > level_width:
        raise OutputWriteError(f"{record_path}.write_region exceeds level bounds")
    if x_origin % chunk_width != 0 or y_origin % chunk_height != 0:
        raise OutputWriteError(f"{record_path}.write_region origin must be aligned to chunk_shape")
    expected_width = min(chunk_width, level_width - x_origin)
    expected_height = min(chunk_height, level_height - y_origin)
    if width != expected_width or height != expected_height:
        raise OutputWriteError(f"{record_path}.write_region must match the TIFF tile grid")
    if tile.shape[0] < height or tile.shape[1] < width:
        raise OutputWriteError(f"{record_path}.shape is smaller than write_region")
    if len(level_shape) != tile.ndim:
        raise OutputWriteError(f"{record_path}.shape dimensionality does not match level")
    if tile.ndim == 3 and tile.shape[2] != level_shape[2]:
        raise OutputWriteError(f"{record_path}.shape channel count does not match level")
    return y_origin // chunk_height, x_origin // chunk_width


def _iter_streaming_level_tiles(numpy, level: dict, chunk_height: int, chunk_width: int):
    shape = level["shape"]
    channels = shape[2] if len(shape) == 3 else None
    for row in range(level["tile_grid"][0]):
        for col in range(level["tile_grid"][1]):
            record = level["records"][(row, col)]
            tile = _load_npy_tile(numpy, record["path"], record["record_path"])
            _, _, width, height = record["region"]
            if channels is None:
                output_tile = numpy.zeros((chunk_height, chunk_width), dtype=numpy.uint8)
                output_tile[:height, :width] = tile[:height, :width]
            else:
                output_tile = numpy.zeros((chunk_height, chunk_width, channels), dtype=numpy.uint8)
                output_tile[:height, :width, :] = tile[:height, :width, :]
            yield output_tile


def _tile_iterator_streaming_report(
    plan: dict,
    *,
    chunk_height: int,
    chunk_width: int,
    estimated_total_bytes: int,
    bigtiff: bool,
    bigtiff_threshold_bytes: int,
) -> dict:
    return {
        "writer_backend": "tifffile",
        "write_mode": "tile_iterator_streaming_write",
        "production_streaming": True,
        "resume_capable": False,
        "pyramid_order": plan["pyramid_order"],
        "level_order": plan["level_order"],
        "bigtiff": bool(bigtiff),
        "bigtiff_threshold_bytes": int(bigtiff_threshold_bytes),
        "estimated_total_bytes": int(estimated_total_bytes),
        "tile_shape": [chunk_height, chunk_width],
        "levels": [
            {
                "level_index": level["level_index"],
                "pyramid_position": level["pyramid_position"],
                "shape": level["shape"],
                "tile_grid": level["tile_grid"],
                "tile_count": level["tile_count"],
            }
            for level in plan["levels"]
        ],
        "streaming_limitations": [
            "ome_tiff_file_resume_not_supported",
            "requires_complete_tile_source_manifest_before_write",
            "npy_tile_arrays_only",
        ],
    }


def _load_tile_source_manifest(tile_source_manifest: dict | str | Path) -> tuple[dict, Path | None]:
    if isinstance(tile_source_manifest, dict):
        return tile_source_manifest, None
    if isinstance(tile_source_manifest, (str, Path)):
        manifest_path = Path(tile_source_manifest)
        if not manifest_path.exists():
            raise OutputWriteError("tile source manifest does not exist")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise OutputWriteError("tile source manifest must be valid JSON") from exc
        except OSError as exc:
            raise OutputWriteError(f"failed to read tile source manifest: {exc}") from exc
        if not isinstance(manifest, dict):
            raise OutputWriteError("tile source manifest JSON must contain an object")
        return manifest, manifest_path
    raise OutputWriteError("tile_source_manifest must be a dict or JSON path")


def _validate_tile_records(value: Any) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise OutputWriteError("tile_source.tiles must contain at least one tile record")
    records = []
    for index, record in enumerate(value):
        if not isinstance(record, dict):
            raise OutputWriteError(f"tile_source.tiles[{index}] must be an object")
        records.append(record)
    return records


def _validate_level_contracts(value: Any) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OutputWriteError("tile_source.levels must be a list")
    levels = []
    seen_indexes: set[int] = set()
    for index, level in enumerate(value):
        if not isinstance(level, dict):
            raise OutputWriteError(f"tile_source.levels[{index}] must be an object")
        level_index = _validate_non_negative_int(
            level.get("level_index"),
            f"tile_source.levels[{index}].level_index",
        )
        if level_index in seen_indexes:
            raise OutputWriteError(f"duplicate tile source level_index={level_index}")
        seen_indexes.add(level_index)
        level_contract = {"level_index": level_index, "expected_tile_count": None}
        expected_tile_count = _first_present(level, ("expected_tile_count", "tile_count"))
        if expected_tile_count is not None:
            level_contract["expected_tile_count"] = _validate_positive_int(
                expected_tile_count,
                f"tile_source.levels[{index}].expected_tile_count",
            )
        levels.append(level_contract)
    return levels


def _level_shapes_by_index(value: Any) -> dict[int, list[int]]:
    if not isinstance(value, list):
        raise OutputWriteError("tile_source.levels must be a list")
    shapes: dict[int, list[int]] = {}
    for index, level in enumerate(value):
        if not isinstance(level, dict):
            raise OutputWriteError(f"tile_source.levels[{index}] must be an object")
        level_index = _validate_non_negative_int(
            level.get("level_index"),
            f"tile_source.levels[{index}].level_index",
        )
        if "shape" in level:
            shapes[level_index] = _validate_shape(
                level.get("shape"),
                f"tile_source.levels[{index}].shape",
            )
    return shapes


def _build_level_coverage(
    per_level_indexes: dict[int, list[int]],
    level_expected_counts: dict[int, int],
) -> list[dict]:
    coverage = []
    for level_index in sorted(per_level_indexes):
        indexes = sorted(per_level_indexes[level_index])
        if level_index in level_expected_counts:
            expected_count = level_expected_counts[level_index]
            expected_indexes = set(range(expected_count))
            actual_indexes = set(indexes)
            missing_indexes = sorted(expected_indexes - actual_indexes)
            extra_indexes = sorted(actual_indexes - expected_indexes)
            if missing_indexes:
                raise OutputWriteError(
                    f"missing tile source records for level_index={level_index}: {missing_indexes}"
                )
            if extra_indexes:
                raise OutputWriteError(
                    f"tile source tile_index out of range for level_index={level_index}: {extra_indexes}"
                )
        else:
            expected_count = len(indexes)
            missing_indexes = sorted(set(range(indexes[-1] + 1)) - set(indexes))
            if missing_indexes:
                raise OutputWriteError(
                    f"missing tile source records for level_index={level_index}: {missing_indexes}"
                )

        coverage.append(
            {
                "level_index": level_index,
                "expected_tile_count": expected_count,
                "completed_tile_count": len(indexes),
                "missing_tile_count": 0,
                "tile_indexes": indexes,
            }
        )
    return coverage


def _resolve_tile_path(value: Any, manifest_path: Path | None, record_path: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise OutputWriteError(f"{record_path}.path must be a non-empty path")
    path = Path(value)
    if not path.is_absolute() and manifest_path is not None:
        path = manifest_path.parent / path
    if not path.exists():
        raise OutputWriteError(f"{record_path}.path does not exist: {path}")
    # This partial contract intentionally accepts only .npy arrays so shape and
    # dtype can be verified from disk without pretending to stream OME-TIFF.
    if path.suffix.lower() != ".npy":
        raise OutputWriteError(f"{record_path}.path must point to a .npy tile array")
    return path


def _inspect_npy_tile(numpy, path: Path, record_path: str) -> tuple[list[int], str]:
    try:
        tile_array = numpy.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise OutputWriteError(f"{record_path}.path must be a readable .npy tile array") from exc
    return [int(value) for value in tile_array.shape], str(tile_array.dtype)


def _load_npy_tile(numpy, path: Path, record_path: str):
    try:
        tile_array = numpy.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise OutputWriteError(f"{record_path}.path must be a readable .npy tile array") from exc
    if tile_array.dtype != numpy.uint8:
        raise OutputWriteError(f"{record_path}.dtype must be uint8 for assembly")
    if tile_array.ndim not in {2, 3}:
        raise OutputWriteError(f"{record_path}.path must contain a 2D or RGB tile array")
    return tile_array


def _validate_tile_origin(value: Any, record_path: str) -> list[int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise OutputWriteError(f"{record_path}.tile_origin must contain [x, y]")
    origin = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise OutputWriteError(f"{record_path}.tile_origin values must be non-negative integers")
        origin.append(int(item))
    return origin


def _validate_write_region(value: Any, record_path: str) -> list[int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise OutputWriteError(f"{record_path}.write_region must contain [x, y, width, height]")
    x_origin, y_origin, width, height = value
    for item in (x_origin, y_origin):
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise OutputWriteError(f"{record_path}.write_region origin values must be non-negative integers")
    for item in (width, height):
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise OutputWriteError(f"{record_path}.write_region size values must be positive integers")
    return [int(x_origin), int(y_origin), int(width), int(height)]


def _write_tile_to_level(canvas, coverage, tile, region: list[int], record_path: str) -> None:
    x_origin, y_origin, width, height = region
    if y_origin + height > canvas.shape[0] or x_origin + width > canvas.shape[1]:
        raise OutputWriteError(f"{record_path}.write_region exceeds level bounds")
    if tile.shape[0] < height or tile.shape[1] < width:
        raise OutputWriteError(f"{record_path}.shape is smaller than write_region")
    if canvas.ndim != tile.ndim:
        raise OutputWriteError(f"{record_path}.shape dimensionality does not match level")
    if canvas.ndim == 3 and tile.shape[2] != canvas.shape[2]:
        raise OutputWriteError(f"{record_path}.shape channel count does not match level")

    y_slice = slice(y_origin, y_origin + height)
    x_slice = slice(x_origin, x_origin + width)
    if coverage[y_slice, x_slice].any():
        raise OutputWriteError(f"{record_path}.write_region overlaps another tile")
    canvas[y_slice, x_slice] = tile[:height, :width]
    coverage[y_slice, x_slice] = 1


def _validate_shape(value: Any, path: str) -> list[int]:
    if not isinstance(value, (list, tuple)) or len(value) not in {2, 3}:
        raise OutputWriteError(f"{path} must contain a 2D or RGB tile shape")
    shape = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise OutputWriteError(f"{path} values must be positive integers")
        shape.append(int(item))
    if len(shape) == 3 and shape[2] not in {3, 4}:
        raise OutputWriteError(f"{path} channel count must be 3 or 4")
    return shape


def _validate_dtype(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise OutputWriteError(f"{path} must be a non-empty dtype string")
    return value


def _validate_non_negative_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise OutputWriteError(f"{path} must be a non-negative integer")
    return int(value)


def _validate_positive_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise OutputWriteError(f"{path} must be a positive integer")
    return int(value)


def _first_present(mapping: dict, names: tuple[str, ...]) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


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
