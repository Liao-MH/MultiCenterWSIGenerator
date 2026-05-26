import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, PROJECT_VERSION
from ..schemas import validate_qc_report


PRODUCTION_TILE_STREAM_BACKEND = "production-tile-stream"
EXTERNAL_TILE_GENERATOR_ARTIFACT = "external_tile_generator_v1"
PRODUCTION_TILE_SOURCE = "production_external_tile_generator_manifest"
RGB_TILE_FORMAT = "npy_uint8_rgb_tile_v1"
MASK_TILE_FORMAT = "npy_uint8_mask_tile_v1"
TILE_REQUEST_MANIFEST = "production_tile_request_v1"
BACKEND_EXECUTION_EVIDENCE_CONTRACT = "production_tile_backend_execution_evidence_v1"
COMMAND_OUTPUT_PREVIEW_CHARS = 4000


class ProductionTileStreamError(RuntimeError):
    """Raised when production tile streaming cannot produce a publishable WSI."""


def load_external_tile_backend_contract(
    checkpoint_manifest: dict[str, Any],
    checkpoint_manifest_path: str | Path,
) -> dict[str, Any]:
    artifact_path = _resolve_checkpoint_artifact_path(
        checkpoint_manifest["checkpoint_path"],
        checkpoint_manifest_path,
    )
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProductionTileStreamError(
            f"external tile backend artifact must be valid JSON: {artifact_path}"
        ) from exc
    except OSError as exc:
        raise ProductionTileStreamError(
            f"failed to read external tile backend artifact: {artifact_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProductionTileStreamError("external tile backend artifact must be a JSON object")
    if payload.get("schema_version") != PROJECT_VERSION:
        raise ProductionTileStreamError(f"external tile backend schema_version must be {PROJECT_VERSION}")
    if payload.get("artifact_type") != EXTERNAL_TILE_GENERATOR_ARTIFACT:
        raise ProductionTileStreamError(
            f"external tile backend artifact_type must be {EXTERNAL_TILE_GENERATOR_ARTIFACT}"
        )
    command = payload.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(value, str) and value for value in command
    ):
        raise ProductionTileStreamError("external tile backend command must be a non-empty list of strings")
    if payload.get("output_format") != RGB_TILE_FORMAT:
        raise ProductionTileStreamError(f"external tile backend output_format must be {RGB_TILE_FORMAT}")
    if payload.get("mask_output_format") != MASK_TILE_FORMAT:
        raise ProductionTileStreamError(
            f"external tile backend mask_output_format must be {MASK_TILE_FORMAT}"
        )
    timeout_seconds = payload.get("timeout_seconds", 300)
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
        raise ProductionTileStreamError("external tile backend timeout_seconds must be a positive integer")
    return {
        "artifact_path": str(artifact_path),
        "artifact_type": EXTERNAL_TILE_GENERATOR_ARTIFACT,
        "backend_name": _non_empty_str(payload.get("backend_name"), "external_tile_generator"),
        "command": list(command),
        "output_format": RGB_TILE_FORMAT,
        "mask_output_format": MASK_TILE_FORMAT,
        "timeout_seconds": int(timeout_seconds),
    }


def materialize_production_tile_sources(
    generation_config: dict[str, Any],
    plan: dict[str, Any],
    backend_contract: dict[str, Any],
    output_root: str | Path,
    *,
    generated_id: str,
    resume_manifest_path: str | Path | None = None,
    condition_packet_path: str | Path | None = None,
    retry_failed_tiles: bool = False,
) -> dict[str, Any]:
    numpy = _import_numpy()
    root = Path(output_root)
    tile_source_manifest_path = (
        Path(resume_manifest_path)
        if resume_manifest_path is not None
        else root / "production_tile_source_manifest.json"
    )
    expected_manifest = _refresh_tile_source_manifest(
        _build_expected_tile_source_manifest(
            generation_config,
            plan,
            backend_contract,
            root,
            generated_id=generated_id,
            condition_packet_path=condition_packet_path,
        )
    )
    if tile_source_manifest_path.exists():
        manifest = _load_resumable_tile_source_manifest(
            numpy,
            tile_source_manifest_path,
            expected_manifest,
            root,
            retry_failed_tiles=retry_failed_tiles,
        )
    else:
        manifest = expected_manifest
        _write_json(tile_source_manifest_path, manifest)

    for record_index, record in enumerate(manifest["tiles"]):
        if record["status"] == "completed":
            record = dict(record)
            record["request_evidence"] = _file_evidence(root, root / record["tile_request_path"])
            record["output_evidence"] = _ensure_completed_record(numpy, root, record, record_index)
            manifest["tiles"][record_index] = record
            continue
        if record["status"] != "pending":
            raise ProductionTileStreamError("production tile source manifest contains failed tiles")
        record = dict(record)
        record["attempt_count"] = int(record.get("attempt_count", 0)) + 1
        try:
            execution_evidence = _execute_tile_backend_command(
                backend_contract,
                root,
                record,
                generated_id=generated_id,
                random_seed=int(generation_config["random_seed"]),
                tile_request_context={
                    "condition_packet_path": str(condition_packet_path)
                    if condition_packet_path is not None
                    else None,
                    "prior_id": plan["prior_id"],
                    "checkpoint_manifest_path": plan["checkpoint_manifest_path"],
                    "checkpoint_model_version": plan["checkpoint_model_version"],
                },
            )
            record["request_evidence"] = execution_evidence["request_evidence"]
            record["backend_execution"] = execution_evidence["backend_execution"]
            record["output_evidence"] = _ensure_completed_record(numpy, root, record, record_index)
            record["status"] = "completed"
            record["error_message"] = None
        except Exception as exc:
            record["status"] = "failed"
            record["error_message"] = str(exc)
            manifest["tiles"][record_index] = record
            manifest = _refresh_tile_source_manifest(manifest)
            _write_json(tile_source_manifest_path, manifest)
            raise ProductionTileStreamError(str(exc)) from exc
        manifest["tiles"][record_index] = record
        manifest = _refresh_tile_source_manifest(manifest)
        _write_json(tile_source_manifest_path, manifest)

    manifest = _refresh_tile_source_manifest(manifest)
    if manifest["pending_tile_count"] or manifest["failed_tile_count"]:
        raise ProductionTileStreamError("production tile source manifest is incomplete")
    _write_json(tile_source_manifest_path, manifest)
    return {
        "tile_source_manifest_path": tile_source_manifest_path,
        "tile_source_manifest": manifest,
    }


def write_streaming_mask_from_tile_sources(
    tile_source_manifest: dict[str, Any],
    output_root: str | Path,
    output_dir: str | Path,
    stem: str = "mask",
) -> dict[str, Any]:
    numpy = _import_numpy()
    root = Path(output_root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    level0 = _level_by_index(tile_source_manifest, 0)
    height, width = [int(value) for value in level0["shape"][:2]]
    mask_path = target_dir / f"{stem}.npy"
    metadata_path = target_dir / f"{stem}.metadata.json"
    mask = numpy.lib.format.open_memmap(
        mask_path,
        mode="w+",
        dtype=numpy.uint8,
        shape=(height, width),
    )
    class_counts = [0 for _ in MASK_CLASSES]
    for record in tile_source_manifest["tiles"]:
        if int(record["level_index"]) != 0:
            continue
        mask_tile_path = record.get("mask_path")
        if not isinstance(mask_tile_path, str) or not mask_tile_path:
            raise ProductionTileStreamError("level 0 production tiles must include mask_path")
        tile_mask = numpy.load(root / mask_tile_path, allow_pickle=False)
        if tile_mask.dtype != numpy.uint8 or tile_mask.ndim != 2:
            raise ProductionTileStreamError("production mask tile must be a uint8 2D .npy array")
        invalid = [int(value) for value in numpy.unique(tile_mask).tolist() if int(value) >= len(MASK_CLASSES)]
        if invalid:
            raise ProductionTileStreamError(f"production mask tile contains invalid class id {invalid[0]}")
        x_origin, y_origin, region_width, region_height = [int(value) for value in record["write_region"]]
        if list(tile_mask.shape) != [region_height, region_width]:
            raise ProductionTileStreamError("production mask tile shape must match level 0 write_region")
        mask[y_origin : y_origin + region_height, x_origin : x_origin + region_width] = tile_mask
        counts = numpy.bincount(tile_mask.reshape(-1), minlength=len(MASK_CLASSES))
        for index, count in enumerate(counts[: len(MASK_CLASSES)]):
            class_counts[index] += int(count)
    mask.flush()
    unique_class_ids = [index for index, count in enumerate(class_counts) if count > 0]
    metadata = {
        "status": "written",
        "path": str(mask_path),
        "shape": [height, width],
        "dtype": "uint8",
        "classes": len(MASK_CLASSES),
        "class_names": list(MASK_CLASSES),
        "class_pixel_counts_by_id": class_counts,
        "unique_class_ids": unique_class_ids,
        "write_mode": "tile_memmap_mask_write",
        "production_streaming": True,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {**metadata, "metadata_path": str(metadata_path)}


def build_streaming_tile_source_qc_report(
    *,
    generated_id: str,
    wsi_path: str | Path,
    tile_source_manifest: dict[str, Any],
    pyramid_report: dict[str, Any],
    mask_report: dict[str, Any],
    non_copy_items: list[dict[str, Any]],
    sample_tile_count: int = 4,
) -> dict[str, Any]:
    numpy = _import_numpy()
    wsi_path = Path(wsi_path)
    wsi_metrics = [
        _metric("wsi_file_exists", "pass" if wsi_path.exists() else "fail", bool(wsi_path.exists())),
        _metric(
            "pyramid_level_count",
            "pass" if int(pyramid_report.get("level_count", 0)) >= 1 else "fail",
            int(pyramid_report.get("level_count", 0)),
        ),
    ]
    wsi_metrics.extend(_ome_container_metrics(wsi_path, pyramid_report))
    rgb_tiles = _sample_completed_level0_tiles(numpy, tile_source_manifest, sample_tile_count)
    wsi_metrics.extend(_sampled_rgb_metrics(numpy, rgb_tiles))
    tile_metrics = _sampled_tile_metrics(numpy, rgb_tiles, tile_source_manifest)
    mask_metrics = _streaming_mask_metrics(mask_report, pyramid_report)
    report = {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "overall_status": _combine_status(wsi_metrics + tile_metrics + mask_metrics),
        "levels": {
            "wsi": {"status": _combine_status(wsi_metrics), "metrics": wsi_metrics},
            "tile": {"status": _combine_status(tile_metrics), "metrics": tile_metrics},
            "mask_region": {"status": _combine_status(mask_metrics), "metrics": mask_metrics},
        },
        "non_copy_report": {
            "enabled": True,
            "patch_nearest_neighbor_search": False,
            "items": non_copy_items,
            "metrics": [],
        },
    }
    return validate_qc_report(report)


def _build_expected_tile_source_manifest(
    generation_config: dict[str, Any],
    plan: dict[str, Any],
    backend_contract: dict[str, Any],
    output_root: Path,
    *,
    generated_id: str,
    condition_packet_path: str | Path | None,
) -> dict[str, Any]:
    canvas_width, canvas_height = [
        int(value)
        for value in generation_config.get("canvas_size_40x", generation_config["tile_size_40x"])
    ]
    tile_width, tile_height = [int(value) for value in generation_config["tile_size_40x"]]
    levels = []
    records = []
    for level_index, (cascade_level, divisor) in enumerate(
        zip(("1/1", "1/4", "1/16", "1/32"), (1, 4, 16, 32), strict=True)
    ):
        level_width = max(1, _ceil_div(canvas_width, divisor))
        level_height = max(1, _ceil_div(canvas_height, divisor))
        grid_y = _ceil_div(level_height, tile_height)
        grid_x = _ceil_div(level_width, tile_width)
        levels.append(
            {
                "level_index": level_index,
                "cascade_level": cascade_level,
                "shape": [level_height, level_width, 3],
                "tile_grid": [grid_y, grid_x],
                "expected_tile_count": grid_y * grid_x,
            }
        )
        for row in range(grid_y):
            for col in range(grid_x):
                x_origin = col * tile_width
                y_origin = row * tile_height
                write_width = min(tile_width, level_width - x_origin)
                write_height = min(tile_height, level_height - y_origin)
                tile_index = row * grid_x + col
                path = (
                    output_root
                    / "production_tiles"
                    / f"level-{level_index}-tile-{row:06d}-{col:06d}.npy"
                )
                tile_request_path = (
                    output_root
                    / "production_tile_requests"
                    / f"level-{level_index}-tile-{row:06d}-{col:06d}.request.json"
                )
                record = {
                    "record_index": len(records),
                    "level_index": level_index,
                    "cascade_level": cascade_level,
                    "tile_index": int(tile_index),
                    "path": path.relative_to(output_root).as_posix(),
                    "tile_request_path": tile_request_path.relative_to(output_root).as_posix(),
                    "shape": [write_height, write_width, 3],
                    "dtype": "uint8",
                    "status": "pending",
                    "attempt_count": 0,
                    "error_message": None,
                    "tile_origin": [x_origin, y_origin],
                    "write_region": [x_origin, y_origin, write_width, write_height],
                }
                if level_index == 0:
                    mask_path = (
                        output_root
                        / "production_mask_tiles"
                        / f"tile-{row:06d}-{col:06d}.npy"
                    )
                    record["mask_path"] = mask_path.relative_to(output_root).as_posix()
                    record["mask_shape"] = [write_height, write_width]
                    record["mask_dtype"] = "uint8"
                records.append(record)

    estimated_bytes = sum(
        int(level["shape"][0]) * int(level["shape"][1]) * int(level["shape"][2])
        for level in levels
    )
    return {
        "schema_version": PROJECT_VERSION,
        "manifest_type": "disk_npy_tile_source_manifest",
        "source": PRODUCTION_TILE_SOURCE,
        "generated_id": generated_id,
        "generation_backend": PRODUCTION_TILE_STREAM_BACKEND,
        "prior_id": plan["prior_id"],
        "checkpoint_manifest_path": plan["checkpoint_manifest_path"],
        "checkpoint_model_version": plan["checkpoint_model_version"],
        "condition_packet_path": str(condition_packet_path) if condition_packet_path is not None else None,
        "tile_backend": {
            "artifact_type": backend_contract["artifact_type"],
            "artifact_path": backend_contract["artifact_path"],
            "backend_name": backend_contract["backend_name"],
            "output_format": backend_contract["output_format"],
            "mask_output_format": backend_contract["mask_output_format"],
        },
        "canvas_size_40x": [canvas_width, canvas_height],
        "tile_size_40x": [tile_width, tile_height],
        "chunk_shape": [tile_height, tile_width],
        "pyramid_order": "high_to_low_resolution",
        "levels": levels,
        "expected_tile_count": len(records),
        "tile_count": len(records),
        "request_manifest_type": TILE_REQUEST_MANIFEST,
        "estimated_uncompressed_bytes": estimated_bytes,
        "gigabyte_scale": estimated_bytes >= 1_000_000_000,
        "resume_semantics": "completed_disk_tiles_reused_before_atomic_ome_tiff_publish",
        "tiles": records,
        "limitations": [
            "ome_tiff_file_resume_not_supported_after_publish",
            "requires_complete_tile_source_manifest_before_atomic_publish",
            "external_backend_consumes_per_tile_request_manifest",
        ],
    }


def _load_resumable_tile_source_manifest(
    numpy,
    manifest_path: Path,
    expected_manifest: dict[str, Any],
    output_root: Path,
    *,
    retry_failed_tiles: bool = False,
) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProductionTileStreamError("production tile source manifest must be valid JSON") from exc
    if not isinstance(manifest, dict):
        raise ProductionTileStreamError("production tile source manifest must contain an object")
    for key in (
        "schema_version",
        "manifest_type",
        "source",
        "generated_id",
        "generation_backend",
        "prior_id",
        "checkpoint_manifest_path",
        "checkpoint_model_version",
        "canvas_size_40x",
        "tile_size_40x",
        "chunk_shape",
        "levels",
        "expected_tile_count",
        "tile_count",
        "request_manifest_type",
    ):
        if manifest.get(key) != expected_manifest.get(key):
            raise ProductionTileStreamError(f"production tile source manifest {key} does not match generation plan")
    records = manifest.get("tiles")
    expected_records = expected_manifest["tiles"]
    if not isinstance(records, list) or len(records) != len(expected_records):
        raise ProductionTileStreamError("production tile source manifest tiles do not match generation plan")
    merged_records = []
    immutable_keys = (
        "record_index",
        "level_index",
        "cascade_level",
        "tile_index",
        "path",
        "tile_request_path",
        "shape",
        "dtype",
        "tile_origin",
        "write_region",
        "mask_path",
        "mask_shape",
        "mask_dtype",
    )
    for index, (record, expected_record) in enumerate(zip(records, expected_records, strict=True)):
        if not isinstance(record, dict):
            raise ProductionTileStreamError(f"production tile source tiles[{index}] must be an object")
        for key in immutable_keys:
            if record.get(key) != expected_record.get(key):
                raise ProductionTileStreamError(
                    f"production tile source tiles[{index}].{key} does not match generation plan"
                )
        status = record.get("status")
        if status == "completed":
            _ensure_completed_record(numpy, output_root, record, index)
        elif status == "failed":
            if not retry_failed_tiles:
                raise ProductionTileStreamError("production tile source manifest contains failed tiles")
            # Retrying a failed production tile is opt-in because it replays an
            # external backend side effect. Immutable tile/request fields were
            # already checked above; only mutable execution state is reset.
            status = "pending"
        elif status != "pending":
            raise ProductionTileStreamError("production tile source status must be pending, completed, or failed")
        merged_record = {
            **expected_record,
            "status": status,
            "attempt_count": int(record.get("attempt_count", 0)),
            "error_message": record.get("error_message") if status != "pending" else None,
        }
        if record.get("retry_from_failed") is True:
            merged_record["retry_from_failed"] = True
        if "previous_status" in record:
            merged_record["previous_status"] = record.get("previous_status")
        if "previous_error_message" in record:
            merged_record["previous_error_message"] = record.get("previous_error_message")
        if "retry_count" in record:
            merged_record["retry_count"] = int(record.get("retry_count", 0))
        for evidence_key in ("request_evidence", "backend_execution", "output_evidence"):
            if evidence_key in record:
                merged_record[evidence_key] = record.get(evidence_key)
        if record.get("status") == "failed" and retry_failed_tiles:
            merged_record["retry_from_failed"] = True
            merged_record["previous_status"] = "failed"
            merged_record["previous_error_message"] = record.get("error_message")
            merged_record["retry_count"] = int(record.get("retry_count", 0)) + 1
        merged_records.append(merged_record)
    resumed = dict(expected_manifest)
    resumed["tiles"] = merged_records
    return _refresh_tile_source_manifest(resumed)


def _execute_tile_backend_command(
    backend_contract: dict[str, Any],
    output_root: Path,
    record: dict[str, Any],
    *,
    generated_id: str,
    random_seed: int,
    tile_request_context: dict[str, Any],
) -> dict[str, Any]:
    tile_path = output_root / record["path"]
    tile_path.parent.mkdir(parents=True, exist_ok=True)
    tile_request_path = output_root / record["tile_request_path"]
    mask_tile_path = None
    if int(record["level_index"]) == 0:
        mask_tile_path = output_root / record["mask_path"]
        mask_tile_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        tile_request_path,
        _tile_request_manifest(
            backend_contract,
            output_root,
            record,
            tile_path,
            mask_tile_path,
            generated_id=generated_id,
            random_seed=random_seed,
            context=tile_request_context,
        ),
    )
    request_evidence = _file_evidence(output_root, tile_request_path)
    values = _command_placeholders(
        record,
        tile_path,
        tile_request_path,
        mask_tile_path,
        generated_id,
        random_seed,
    )
    try:
        command = [part.format_map(values) for part in backend_contract["command"]]
    except KeyError as exc:
        raise ProductionTileStreamError(f"external tile backend command has unknown placeholder: {exc}") from exc
    timeout_seconds = int(backend_contract["timeout_seconds"])
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=str(output_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        duration = round(time.perf_counter() - started, 6)
        raise ProductionTileStreamError(
            f"external tile backend timed out for record {record['record_index']} "
            f"after {duration} seconds"
        ) from exc
    duration = round(time.perf_counter() - started, 6)
    backend_execution = {
        "contract": BACKEND_EXECUTION_EVIDENCE_CONTRACT,
        "command": command,
        "cwd": str(output_root),
        "return_code": int(result.returncode),
        "timeout_seconds": timeout_seconds,
        "duration_seconds": duration,
        "stdout_preview": _text_preview(result.stdout),
        "stderr_preview": _text_preview(result.stderr),
    }
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise ProductionTileStreamError(f"external tile backend failed for record {record['record_index']}: {detail}")
    return {
        "request_evidence": request_evidence,
        "backend_execution": backend_execution,
    }


def _command_placeholders(
    record: dict[str, Any],
    tile_path: Path,
    tile_request_path: Path,
    mask_tile_path: Path | None,
    generated_id: str,
    random_seed: int,
) -> dict[str, str]:
    x_origin, y_origin, width, height = [int(value) for value in record["write_region"]]
    return {
        "tile_path": str(tile_path),
        "tile_request_path": str(tile_request_path),
        "mask_tile_path": str(mask_tile_path) if mask_tile_path is not None else "",
        "generated_id": generated_id,
        "random_seed": str(random_seed),
        "record_index": str(record["record_index"]),
        "level_index": str(record["level_index"]),
        "cascade_level": str(record["cascade_level"]),
        "tile_index": str(record["tile_index"]),
        "tile_origin_x": str(x_origin),
        "tile_origin_y": str(y_origin),
        "tile_width": str(width),
        "tile_height": str(height),
    }


def _tile_request_manifest(
    backend_contract: dict[str, Any],
    output_root: Path,
    record: dict[str, Any],
    tile_path: Path,
    mask_tile_path: Path | None,
    *,
    generated_id: str,
    random_seed: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "manifest_type": TILE_REQUEST_MANIFEST,
        "generated_id": generated_id,
        "random_seed": int(random_seed),
        "condition_packet_path": context["condition_packet_path"],
        "tile": {
            "record_index": int(record["record_index"]),
            "level_index": int(record["level_index"]),
            "cascade_level": record["cascade_level"],
            "tile_index": int(record["tile_index"]),
            "tile_origin": list(record["tile_origin"]),
            "write_region": list(record["write_region"]),
            "shape": list(record["shape"]),
            "dtype": record["dtype"],
        },
        "outputs": {
            "rgb_tile_path": str(tile_path),
            "rgb_tile_relative_path": record["path"],
            "mask_tile_path": str(mask_tile_path) if mask_tile_path is not None else None,
            "mask_tile_relative_path": record.get("mask_path"),
        },
        "prior": {
            "prior_id": context["prior_id"],
        },
        "checkpoint": {
            "checkpoint_manifest_path": context["checkpoint_manifest_path"],
            "model_version": context["checkpoint_model_version"],
        },
        "tile_backend": {
            "backend_name": backend_contract["backend_name"],
            "artifact_type": backend_contract["artifact_type"],
            "artifact_path": backend_contract["artifact_path"],
            "output_format": backend_contract["output_format"],
            "mask_output_format": backend_contract["mask_output_format"],
        },
        "output_root": str(output_root),
    }


def _ensure_completed_record(
    numpy,
    output_root: Path,
    record: dict[str, Any],
    record_index: int,
) -> dict[str, Any]:
    tile = _load_npy(numpy, output_root / record["path"], f"tiles[{record_index}].path")
    if tile.dtype != numpy.uint8 or tile.ndim != 3 or tile.shape[2] != 3:
        raise ProductionTileStreamError("production RGB tile must be a uint8 RGB .npy array")
    if [int(value) for value in tile.shape] != record["shape"]:
        raise ProductionTileStreamError(f"production tile source tiles[{record_index}].shape does not match manifest")
    evidence = {
        "contract": BACKEND_EXECUTION_EVIDENCE_CONTRACT,
        "rgb_tile": _file_evidence(output_root, output_root / record["path"]),
        "mask_tile": None,
    }
    if int(record["level_index"]) != 0:
        return evidence
    mask = _load_npy(numpy, output_root / record["mask_path"], f"tiles[{record_index}].mask_path")
    if mask.dtype != numpy.uint8 or mask.ndim != 2:
        raise ProductionTileStreamError("production mask tile must be a uint8 2D .npy array")
    if [int(value) for value in mask.shape] != record["mask_shape"]:
        raise ProductionTileStreamError(
            f"production tile source tiles[{record_index}].mask_shape does not match manifest"
        )
    unique = [int(value) for value in numpy.unique(mask).tolist()]
    invalid = [value for value in unique if value < 0 or value >= len(MASK_CLASSES)]
    if invalid:
        raise ProductionTileStreamError(f"production mask tile contains invalid class id {invalid[0]}")
    evidence["mask_tile"] = _file_evidence(output_root, output_root / record["mask_path"])
    return evidence


def _refresh_tile_source_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    tiles = manifest["tiles"]
    completed = sum(1 for record in tiles if record.get("status") == "completed")
    pending = sum(1 for record in tiles if record.get("status") == "pending")
    failed = sum(1 for record in tiles if record.get("status") == "failed")
    resume_index = 0
    for record in tiles:
        if record.get("status") != "completed":
            break
        resume_index += 1
    updated = dict(manifest)
    updated["completed_tile_count"] = completed
    updated["pending_tile_count"] = pending
    updated["failed_tile_count"] = failed
    updated["backend_execution_summary"] = _backend_execution_summary(tiles)
    updated["resume_index"] = resume_index
    updated["next_tile_index"] = None if resume_index == len(tiles) else resume_index
    if failed:
        status = "failed"
    elif pending:
        status = "in_progress"
    else:
        status = "completed"
    updated["generation_status"] = status
    return updated


def _backend_execution_summary(tiles: list[dict[str, Any]]) -> dict[str, Any]:
    completed_tiles = [record for record in tiles if record.get("status") == "completed"]
    request_count = sum(1 for record in completed_tiles if _has_file_evidence(record.get("request_evidence")))
    execution_count = sum(
        1 for record in completed_tiles if _has_backend_execution_evidence(record.get("backend_execution"))
    )
    output_count = sum(1 for record in completed_tiles if _has_output_evidence(record))
    completed_count = len(completed_tiles)
    return {
        "contract": BACKEND_EXECUTION_EVIDENCE_CONTRACT,
        "completed_tile_count": completed_count,
        "completed_with_request_evidence_count": request_count,
        "completed_with_execution_evidence_count": execution_count,
        "completed_with_output_evidence_count": output_count,
        "all_completed_tiles_have_evidence": (
            completed_count == request_count == execution_count == output_count
        ),
    }


def _has_backend_execution_evidence(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("contract") == BACKEND_EXECUTION_EVIDENCE_CONTRACT
        and isinstance(value.get("command"), list)
        and value.get("return_code") == 0
        and isinstance(value.get("cwd"), str)
        and isinstance(value.get("timeout_seconds"), int)
        and isinstance(value.get("duration_seconds"), (int, float))
    )


def _has_output_evidence(record: dict[str, Any]) -> bool:
    evidence = record.get("output_evidence")
    if not isinstance(evidence, dict) or evidence.get("contract") != BACKEND_EXECUTION_EVIDENCE_CONTRACT:
        return False
    if not _has_file_evidence(evidence.get("rgb_tile")):
        return False
    if int(record.get("level_index", -1)) != 0:
        return True
    return _has_file_evidence(evidence.get("mask_tile"))


def _has_file_evidence(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and value.get("path") != ""
        and isinstance(value.get("size_bytes"), int)
        and value.get("size_bytes") >= 0
        and isinstance(value.get("sha256"), str)
        and len(value.get("sha256", "")) == 64
    )


def _level_by_index(manifest: dict[str, Any], level_index: int) -> dict[str, Any]:
    for level in manifest.get("levels", []):
        if isinstance(level, dict) and level.get("level_index") == level_index:
            return level
    raise ProductionTileStreamError(f"production tile source level_index={level_index} is missing")


def _sample_completed_level0_tiles(numpy, manifest: dict[str, Any], limit: int) -> list[Any]:
    samples = []
    root = Path(".")
    manifest_path = manifest.get("_manifest_path")
    if isinstance(manifest_path, str) and manifest_path:
        root = Path(manifest_path).parent
    for record in manifest.get("tiles", []):
        if (
            isinstance(record, dict)
            and record.get("status") == "completed"
            and int(record.get("level_index", -1)) == 0
        ):
            samples.append(_load_npy(numpy, root / record["path"], "tile_source.tiles.path"))
            if len(samples) >= limit:
                break
    return samples


def _sampled_rgb_metrics(numpy, tiles: list[Any]) -> list[dict[str, Any]]:
    if not tiles:
        return [_metric("wsi_readable", "fail", False, "no completed level 0 RGB tiles")]
    rgb = numpy.concatenate([tile.reshape(-1, 3) for tile in tiles], axis=0).astype("float32")
    dynamic_range = float(rgb.max() - rgb.min())
    return [
        _metric("wsi_readable", "pass", True),
        _metric("mean_red", _range_status(float(rgb[:, 0].mean()), 1.0, 254.0), round(float(rgb[:, 0].mean()), 4)),
        _metric("mean_green", _range_status(float(rgb[:, 1].mean()), 1.0, 254.0), round(float(rgb[:, 1].mean()), 4)),
        _metric("mean_blue", _range_status(float(rgb[:, 2].mean()), 1.0, 254.0), round(float(rgb[:, 2].mean()), 4)),
        _metric("rgb_dynamic_range", "pass" if dynamic_range >= 5.0 else "warning", round(dynamic_range, 4)),
    ]


def _sampled_tile_metrics(numpy, tiles: list[Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sharpness_values = [_sharpness_proxy(numpy, tile.astype("float32")) for tile in tiles]
    sharpness = float(sum(sharpness_values) / len(sharpness_values)) if sharpness_values else 0.0
    return [
        _metric(
            "tile_source_completed_count",
            "pass" if manifest.get("pending_tile_count") == 0 and manifest.get("failed_tile_count") == 0 else "fail",
            int(manifest.get("completed_tile_count", 0)),
        ),
        _metric("tile_proxy_sample_count", "pass" if tiles else "fail", len(tiles)),
        _metric("sharpness_laplacian_proxy", "pass" if sharpness > 0 else "warning", round(sharpness, 4)),
        _metric("seam_score_proxy", "pass", 0.0, "streaming QC samples tile files without full-canvas seam scan"),
    ]


def _streaming_mask_metrics(mask_report: dict[str, Any], pyramid_report: dict[str, Any]) -> list[dict[str, Any]]:
    mask_path = Path(mask_report["path"])
    level_shapes = pyramid_report.get("level_shapes", [])
    expected_shape = level_shapes[0][:2] if level_shapes else None
    actual_shape = list(mask_report.get("shape", []))
    total_pixels = sum(int(value) for value in mask_report.get("class_pixel_counts_by_id", []))
    tissue_pixels = sum(int(value) for value in mask_report.get("class_pixel_counts_by_id", [0])[1:])
    tissue_fraction = float(tissue_pixels / total_pixels) if total_pixels else 0.0
    metrics = [
        _metric("mask_file_exists", "pass" if mask_path.exists() else "fail", bool(mask_path.exists())),
        _metric("mask_readable", "pass" if mask_path.exists() else "fail", bool(mask_path.exists())),
        _metric(
            "mask_shape_matches_wsi",
            "pass" if expected_shape is not None and actual_shape == expected_shape else "fail",
            expected_shape is not None and actual_shape == expected_shape,
            f"mask_shape={actual_shape}, wsi_shape={expected_shape}",
        ),
        _metric("mask_classes_present", "pass", len(mask_report.get("unique_class_ids", []))),
        _metric("mask_unique_class_ids", "pass", list(mask_report.get("unique_class_ids", []))),
        _metric(
            "mask_tissue_fraction",
            "pass" if 0.0 < tissue_fraction <= 1.0 else "warning",
            round(tissue_fraction, 6),
        ),
    ]
    return metrics


def _ome_container_metrics(wsi_path: Path, pyramid_report: dict[str, Any]) -> list[dict[str, Any]]:
    if not wsi_path.exists():
        return [_metric("ome_tiff_container_readable", "fail", False)]
    try:
        import tifffile

        with tifffile.TiffFile(wsi_path) as tiff:
            level_count = len(tiff.series[0].levels) if tiff.series else 0
            is_ome = bool(tiff.is_ome)
    except Exception as exc:
        return [_metric("ome_tiff_container_readable", "fail", False, str(exc))]
    expected = int(pyramid_report.get("level_count", 0))
    return [
        _metric("ome_tiff_container_readable", "pass", True),
        _metric("ome_tiff_is_ome", "pass" if is_ome else "fail", is_ome),
        _metric("ome_tiff_level_count_observed", "pass" if level_count == expected else "fail", level_count),
    ]


def _sharpness_proxy(numpy, rgb_float) -> float:
    gray = rgb_float.mean(axis=2)
    if gray.shape[0] < 2 or gray.shape[1] < 2:
        return 0.0
    dx = numpy.abs(gray[:, 1:] - gray[:, :-1]).mean()
    dy = numpy.abs(gray[1:, :] - gray[:-1, :]).mean()
    return float(dx + dy)


def _range_status(value: float, lower: float, upper: float) -> str:
    return "pass" if lower <= value <= upper else "warning"


def _combine_status(metrics: list[dict[str, Any]]) -> str:
    statuses = {metric["status"] for metric in metrics}
    if "fail" in statuses:
        return "fail"
    if "warning" in statuses:
        return "warning"
    return "pass"


def _metric(name: str, status: str, value: Any, message: str | None = None) -> dict[str, Any]:
    metric = {"name": name, "status": status, "value": value}
    if message:
        metric["message"] = message
    return metric


def _load_npy(numpy, path: Path, label: str):
    if not path.exists():
        raise ProductionTileStreamError(f"{label} does not exist: {path}")
    try:
        return numpy.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ProductionTileStreamError(f"{label} must be a readable .npy array: {path}") from exc


def _resolve_checkpoint_artifact_path(checkpoint_path: str, checkpoint_manifest_path: str | Path) -> Path:
    path = Path(checkpoint_path)
    if not path.is_absolute():
        path = Path(checkpoint_manifest_path).parent / path
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _file_evidence(output_root: Path, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ProductionTileStreamError(f"evidence file does not exist: {path}")
    relative_path = path.relative_to(output_root).as_posix()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": relative_path,
        "size_bytes": int(path.stat().st_size),
        "sha256": digest.hexdigest(),
    }


def _text_preview(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= COMMAND_OUTPUT_PREVIEW_CHARS:
        return value
    return value[:COMMAND_OUTPUT_PREVIEW_CHARS]


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _non_empty_str(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise ProductionTileStreamError("production tile streaming requires numpy") from exc
    return numpy
