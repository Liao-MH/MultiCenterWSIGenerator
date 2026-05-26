import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, MAX_MAGNIFICATION, PROJECT_VERSION, TILE_SIZE_40X
from ..metadata.archive import archive_sample
from ..models.torch_training import TorchTrainingError, sample_torch_diffusion_smoke_model
from ..models.training import ModelRunError, load_checkpoint_manifest
from ..models.training_batch import TrainingBatchError, load_training_batch
from ..outputs.masks import write_mask_array
from ..outputs.ome_tiff import (
    OutputWriteError,
    write_pyramid_ome_tiff,
    write_pyramid_ome_tiff_streaming_from_tile_sources,
)
from ..priors.artifacts import PriorArtifactError, load_prior_manifest
from ..qc.engine import QCReferenceError, build_qc_report
from ..schemas import (
    ValidationError,
    validate_generation_config,
    validate_generation_output_diagnostics,
)
from .tiling import (
    GenerationTilingError,
    blend_rgb_tiles,
    build_resumable_tile_manifest,
    complete_tile_traversal_plan,
    require_complete_tile_manifest,
    update_resumable_tile_manifest,
    validate_resumable_tile_manifest,
)
from .planner import create_generation_plan
from .production_streaming import (
    PRODUCTION_TILE_STREAM_BACKEND,
    ProductionTileStreamError,
    build_streaming_tile_source_qc_report,
    load_external_tile_backend_contract,
    materialize_production_tile_sources,
    write_streaming_mask_from_tile_sources,
)


class GenerationExecutionError(RuntimeError):
    """Raised when a generation run cannot produce an auditable output object."""


SMOKE_BACKEND = "smoke-cascade"
TORCH_DIFFUSION_SMOKE_BACKEND = "torch-diffusion-smoke"
ARRAY_WSI_WRITER = "array"
TILE_STREAMING_WSI_WRITER = "tile-streaming"


def run_smoke_generation(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    checkpoint_manifest_path: str | Path,
    output_root: str | Path,
    generated_id: str,
    condition_packet_path: str | Path | None = None,
    resume_tile_manifest_path: str | Path | None = None,
    wsi_writer: str = ARRAY_WSI_WRITER,
) -> dict[str, Any]:
    if not isinstance(generated_id, str) or generated_id == "":
        raise GenerationExecutionError("generated_id must be a non-empty string")
    if wsi_writer not in {ARRAY_WSI_WRITER, TILE_STREAMING_WSI_WRITER}:
        raise GenerationExecutionError("wsi_writer must be 'array' or 'tile-streaming'")

    root = Path(output_root)
    resume_manifest_path = Path(resume_tile_manifest_path) if resume_tile_manifest_path else None
    if root.exists() and any(root.iterdir()) and resume_manifest_path is None:
        raise GenerationExecutionError(f"output_root already exists and is not empty: {root}")
    if resume_manifest_path is not None and resume_manifest_path.resolve().parent != root.resolve():
        raise GenerationExecutionError("resume_tile_manifest_path must be inside output_root")
    root.mkdir(parents=True, exist_ok=True)

    try:
        plan = create_generation_plan(
            generation_config,
            prior_manifest_path=prior_manifest_path,
            checkpoint_manifest_path=checkpoint_manifest_path,
        )
    except ModelRunError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    condition_packet = _load_generation_condition_packet(condition_packet_path, plan)

    numpy = _import_numpy()
    tile_output = _prepare_smoke_tile_outputs(
        numpy,
        generation_config,
        plan["tile_traversal_plan"],
        root,
        resume_manifest_path=resume_manifest_path,
        keep_tile_images=wsi_writer == ARRAY_WSI_WRITER,
    )
    plan = dict(plan)
    plan["stages"] = _complete_generation_stages(plan["stages"])
    plan["tile_traversal_plan"] = complete_tile_traversal_plan(plan["tile_traversal_plan"])
    plan["tile_manifest_path"] = str(tile_output["tile_manifest_path"])
    tile_source_manifest_path = tile_output["tile_source_manifest_path"]
    if wsi_writer == TILE_STREAMING_WSI_WRITER:
        tile_source_manifest_path = _write_smoke_direct_multilevel_tile_source_manifest(
            numpy,
            generation_config,
            plan["tile_traversal_plan"],
            output_root=root,
            chunk_shape=tuple(generation_config["tile_size_40x"][::-1]),
        )
        pyramid_levels = None
        mask_shape = tuple(plan["tile_traversal_plan"]["canvas_size_40x"][::-1])
    else:
        smoke_canvas = _build_smoke_canvas_from_tile_records(
            numpy,
            tile_output["tile_records"],
            plan["tile_traversal_plan"],
        )
        pyramid_levels = list(_iter_smoke_pyramid_levels_high_to_low(numpy, smoke_canvas))
        mask_shape = smoke_canvas.shape[:2]
    plan["tile_source_manifest_path"] = str(tile_source_manifest_path)
    plan["wsi_writer"] = wsi_writer

    wsi_path = root / "generated.ome.tiff"
    mask_dir = root / "generated_mask"
    try:
        metadata_tags = {
            "GeneratedID": generated_id,
            "GeneratorBackend": SMOKE_BACKEND,
            "ProjectVersion": PROJECT_VERSION,
        }
        if wsi_writer == TILE_STREAMING_WSI_WRITER:
            pyramid_report = write_pyramid_ome_tiff_streaming_from_tile_sources(
                tile_source_manifest_path,
                wsi_path,
                metadata=metadata_tags,
                chunk_shape=tuple(generation_config["tile_size_40x"][::-1]),
            )
        else:
            pyramid_report = write_pyramid_ome_tiff(
                pyramid_levels,
                wsi_path,
                metadata=metadata_tags,
                tile_source_manifest=tile_source_manifest_path,
            )
        mask_report = write_mask_array(
            _conditioned_or_smoke_mask(
                numpy,
                condition_packet,
                mask_shape,
            ),
            mask_dir,
            "mask",
        )
    except (OutputWriteError, RuntimeError, ValueError) as exc:
        raise GenerationExecutionError(str(exc)) from exc

    try:
        qc = build_qc_report(
            generated_id=generated_id,
            wsi_path=wsi_path,
            mask_path=mask_report["path"],
            pyramid_report=pyramid_report,
            non_copy_items=[
                {
                    "name": "generation_backend",
                    "status": "warning",
                    "value": SMOKE_BACKEND,
                    "message": "Smoke backend validates the pipeline but is not a real diffusion generator.",
                }
            ],
            qc_reference_distribution=_load_qc_reference_distribution(prior_manifest_path),
            qc_reference_context=_condition_qc_reference_context(condition_packet),
            wsi_tissue_overview_summary=_condition_wsi_tissue_overview(condition_packet),
            sampled_layout_mask_summary=_condition_sampled_layout_mask(condition_packet),
        )
    except QCReferenceError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    diagnostics_path = root / "generation_output_diagnostics.json"
    metadata = _metadata_payload(
        generated_id=generated_id,
        generation_config=generation_config,
        plan=plan,
        wsi_path=wsi_path,
        mask_path=mask_report["path"],
        qc_path=root / "qc.json",
        diagnostics_manifest_path=diagnostics_path,
        condition_packet=condition_packet,
    )
    try:
        archive = archive_sample(root, metadata, qc)
    except (ValueError, RuntimeError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    diagnostics = _generation_output_diagnostics(
        generated_id=generated_id,
        backend=SMOKE_BACKEND,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        qc_report=qc,
        diagnostics_manifest_path=diagnostics_path,
    )
    _write_validated_generation_output_diagnostics(diagnostics_path, diagnostics)
    run_summary = _run_summary(
        generated_id=generated_id,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        diagnostics_manifest_path=diagnostics_path,
        condition_packet=condition_packet,
    )
    run_path = root / "generation_run.json"
    run_path.write_text(json.dumps(run_summary, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "backend": SMOKE_BACKEND,
        "status": "completed",
        "generation_run_path": str(run_path),
        "diagnostics_manifest_path": str(diagnostics_path),
        **_condition_packet_return(condition_packet),
        **archive,
    }


def run_torch_diffusion_smoke_generation(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    checkpoint_manifest_path: str | Path,
    training_index_path: str | Path,
    output_root: str | Path,
    generated_id: str,
    batch_size: int = 1,
    condition_packet_path: str | Path | None = None,
    wsi_writer: str = ARRAY_WSI_WRITER,
) -> dict[str, Any]:
    if not isinstance(generated_id, str) or generated_id == "":
        raise GenerationExecutionError("generated_id must be a non-empty string")
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise GenerationExecutionError("batch_size must be a positive integer")
    if wsi_writer not in {ARRAY_WSI_WRITER, TILE_STREAMING_WSI_WRITER}:
        raise GenerationExecutionError("wsi_writer must be 'array' or 'tile-streaming'")

    root = Path(output_root)
    if root.exists() and any(root.iterdir()):
        raise GenerationExecutionError(f"output_root already exists and is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)

    try:
        config = validate_generation_config(generation_config)
        prior = load_prior_manifest(prior_manifest_path, verify_files=True)
        checkpoint = load_checkpoint_manifest(checkpoint_manifest_path)
        condition_packet = _load_generation_condition_packet(
            condition_packet_path,
            {"prior_id": prior["prior_id"]},
        )
        cascade_sample_manifests = _run_torch_diffusion_smoke_cascade_samples(
            checkpoint_manifest_path=checkpoint_manifest_path,
            training_index_path=training_index_path,
            output_root=root,
            batch_size=batch_size,
            sample_steps=config["sample_steps"],
            random_seed=config["random_seed"],
            condition_packet_path=condition_packet_path,
            expected_prior_id=prior["prior_id"],
        )
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            cascade_level="1/1",
            include_image=False,
        )
    except (ValidationError, PriorArtifactError, ModelRunError, TorchTrainingError, TrainingBatchError) as exc:
        raise GenerationExecutionError(str(exc)) from exc

    numpy = _import_numpy()
    levels_by_cascade = _build_torch_diffusion_smoke_cascade_from_samples(
        numpy,
        cascade_sample_manifests,
    )
    tile_source_manifest_path = None
    if wsi_writer == TILE_STREAMING_WSI_WRITER:
        tile_source_manifest_path = _write_torch_diffusion_smoke_tile_source_manifest(
            numpy,
            levels_by_cascade,
            output_root=root,
            chunk_shape=tuple(config["tile_size_40x"][::-1]),
        )
        pyramid_levels = None
    else:
        pyramid_levels = [
            levels_by_cascade["1/1"],
            levels_by_cascade["1/4"],
            levels_by_cascade["1/16"],
            levels_by_cascade["1/32"],
        ]
    first_mask = batch["mask_batch"][0]
    wsi_path = root / "generated.ome.tiff"
    mask_dir = root / "generated_mask"
    try:
        metadata_tags = {
            "GeneratedID": generated_id,
            "GeneratorBackend": TORCH_DIFFUSION_SMOKE_BACKEND,
            "ProjectVersion": PROJECT_VERSION,
        }
        if wsi_writer == TILE_STREAMING_WSI_WRITER:
            pyramid_report = write_pyramid_ome_tiff_streaming_from_tile_sources(
                tile_source_manifest_path,
                wsi_path,
                metadata=metadata_tags,
                chunk_shape=tuple(config["tile_size_40x"][::-1]),
            )
        else:
            pyramid_report = write_pyramid_ome_tiff(
                pyramid_levels,
                wsi_path,
                metadata=metadata_tags,
            )
        mask_report = write_mask_array(
            _resize_nearest(numpy, first_mask, TILE_SIZE_40X[1], TILE_SIZE_40X[0]),
            mask_dir,
            "mask",
        )
    except (OutputWriteError, RuntimeError, ValueError) as exc:
        raise GenerationExecutionError(str(exc)) from exc

    try:
        qc = build_qc_report(
            generated_id=generated_id,
            wsi_path=wsi_path,
            mask_path=mask_report["path"],
            pyramid_report=pyramid_report,
            non_copy_items=[
                {
                    "name": "generation_backend",
                    "status": "warning",
                    "value": TORCH_DIFFUSION_SMOKE_BACKEND,
                    "message": (
                        "PyTorch diffusion smoke backend validates sampling/output plumbing "
                        "but is not a production WSI diffusion generator."
                    ),
                }
            ],
            qc_reference_distribution=_load_qc_reference_distribution(prior_manifest_path),
            qc_reference_context=_condition_qc_reference_context(condition_packet),
            wsi_tissue_overview_summary=_condition_wsi_tissue_overview(condition_packet),
            sampled_layout_mask_summary=_condition_sampled_layout_mask(condition_packet),
        )
    except QCReferenceError as exc:
        raise GenerationExecutionError(str(exc)) from exc

    plan = _torch_diffusion_smoke_plan(
        config=config,
        prior_manifest_path=prior_manifest_path,
        prior_id=prior["prior_id"],
        checkpoint_manifest_path=checkpoint_manifest_path,
        checkpoint_model_version=checkpoint["model_version"],
        checkpoint_inference_contract=checkpoint["inference_contract"],
    )
    plan["wsi_writer"] = wsi_writer
    if tile_source_manifest_path is not None:
        plan["tile_source_manifest_path"] = str(tile_source_manifest_path)
    diagnostics_path = root / "generation_output_diagnostics.json"
    metadata = _metadata_payload(
        generated_id=generated_id,
        generation_config=config,
        plan=plan,
        wsi_path=wsi_path,
        mask_path=mask_report["path"],
        qc_path=root / "qc.json",
        diagnostics_manifest_path=diagnostics_path,
        generation_backend=TORCH_DIFFUSION_SMOKE_BACKEND,
        condition_packet=condition_packet,
        cascade_sample_manifests=cascade_sample_manifests,
    )
    try:
        archive = archive_sample(root, metadata, qc)
    except (ValueError, RuntimeError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    diagnostics = _generation_output_diagnostics(
        generated_id=generated_id,
        backend=TORCH_DIFFUSION_SMOKE_BACKEND,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        qc_report=qc,
        diagnostics_manifest_path=diagnostics_path,
    )
    _write_validated_generation_output_diagnostics(diagnostics_path, diagnostics)
    run_summary = _run_summary(
        generated_id=generated_id,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        backend=TORCH_DIFFUSION_SMOKE_BACKEND,
        diagnostics_manifest_path=diagnostics_path,
        cascade_sample_manifests=cascade_sample_manifests,
        condition_packet=condition_packet,
    )
    run_path = root / "generation_run.json"
    run_path.write_text(json.dumps(run_summary, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "backend": TORCH_DIFFUSION_SMOKE_BACKEND,
        "status": "completed",
        "output_root": str(root),
        "generation_run_path": str(run_path),
        "diagnostics_manifest_path": str(diagnostics_path),
        **_condition_packet_return(condition_packet),
        **archive,
    }


def run_production_tile_stream_generation(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    checkpoint_manifest_path: str | Path,
    output_root: str | Path,
    generated_id: str,
    condition_packet_path: str | Path | None = None,
    resume_tile_manifest_path: str | Path | None = None,
    retry_failed_tiles: bool = False,
) -> dict[str, Any]:
    if not isinstance(generated_id, str) or generated_id == "":
        raise GenerationExecutionError("generated_id must be a non-empty string")

    root = Path(output_root)
    resume_manifest_path = Path(resume_tile_manifest_path) if resume_tile_manifest_path else None
    if root.exists() and any(root.iterdir()) and resume_manifest_path is None:
        raise GenerationExecutionError(f"output_root already exists and is not empty: {root}")
    if resume_manifest_path is not None and resume_manifest_path.resolve().parent != root.resolve():
        raise GenerationExecutionError("resume_tile_manifest_path must be inside output_root")
    root.mkdir(parents=True, exist_ok=True)

    try:
        config = validate_generation_config(generation_config)
        plan = create_generation_plan(
            config,
            prior_manifest_path=prior_manifest_path,
            checkpoint_manifest_path=checkpoint_manifest_path,
            generation_backend=PRODUCTION_TILE_STREAM_BACKEND,
        )
        checkpoint = load_checkpoint_manifest(checkpoint_manifest_path)
        if checkpoint["inference_contract"]["production_ready"] is not True:
            raise GenerationExecutionError("production-tile-stream requires a production_ready checkpoint")
        backend_contract = load_external_tile_backend_contract(
            checkpoint,
            checkpoint_manifest_path,
        )
    except (ValidationError, ModelRunError, ProductionTileStreamError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    condition_packet = _load_generation_condition_packet(condition_packet_path, plan)

    try:
        tile_output = materialize_production_tile_sources(
            config,
            plan,
            backend_contract,
            root,
            generated_id=generated_id,
            resume_manifest_path=resume_manifest_path,
            condition_packet_path=condition_packet_path,
            retry_failed_tiles=retry_failed_tiles,
        )
    except ProductionTileStreamError as exc:
        raise GenerationExecutionError(str(exc)) from exc

    tile_source_manifest_path = tile_output["tile_source_manifest_path"]
    tile_source_manifest = tile_output["tile_source_manifest"]
    plan = dict(plan)
    plan["stages"] = _complete_generation_stages(plan["stages"])
    plan["tile_manifest_path"] = str(tile_source_manifest_path)
    plan["tile_source_manifest_path"] = str(tile_source_manifest_path)
    plan["wsi_writer"] = TILE_STREAMING_WSI_WRITER
    plan["tile_traversal"] = "pyramid_tile_grid_external_backend"
    plan["tile_traversal_plan"] = {
        "schema_version": PROJECT_VERSION,
        "tile_traversal": "pyramid_tile_grid_external_backend",
        "canvas_size_40x": list(tile_source_manifest["canvas_size_40x"]),
        "model_tile_size_40x": list(tile_source_manifest["tile_size_40x"]),
        "tile_count": int(tile_source_manifest["tile_count"]),
        "completed_tile_count": int(tile_source_manifest["completed_tile_count"]),
        "pending_tile_count": int(tile_source_manifest["pending_tile_count"]),
        "failed_tile_count": int(tile_source_manifest["failed_tile_count"]),
        "resume_index": int(tile_source_manifest["resume_index"]),
        "next_tile_index": tile_source_manifest["next_tile_index"],
        "retry_failed_tiles": bool(retry_failed_tiles),
        "levels": list(tile_source_manifest["levels"]),
    }
    plan["blending"] = "not_applicable_external_backend_tiff_grid_tiles"
    plan["write_mode"] = "tile_iterator_streaming_write"
    plan["production_tile_backend"] = {
        "backend_name": backend_contract["backend_name"],
        "artifact_path": backend_contract["artifact_path"],
        "artifact_type": backend_contract["artifact_type"],
        "output_format": backend_contract["output_format"],
        "mask_output_format": backend_contract["mask_output_format"],
    }

    wsi_path = root / "generated.ome.tiff"
    mask_dir = root / "generated_mask"
    try:
        pyramid_report = write_pyramid_ome_tiff_streaming_from_tile_sources(
            tile_source_manifest_path,
            wsi_path,
            metadata={
                "GeneratedID": generated_id,
                "GeneratorBackend": PRODUCTION_TILE_STREAM_BACKEND,
                "ProjectVersion": PROJECT_VERSION,
            },
            chunk_shape=tuple(config["tile_size_40x"][::-1]),
        )
        mask_report = write_streaming_mask_from_tile_sources(
            tile_source_manifest,
            root,
            mask_dir,
            "mask",
        )
        qc_manifest = dict(tile_source_manifest)
        qc_manifest["_manifest_path"] = str(tile_source_manifest_path)
        qc = build_streaming_tile_source_qc_report(
            generated_id=generated_id,
            wsi_path=wsi_path,
            tile_source_manifest=qc_manifest,
            pyramid_report=pyramid_report,
            mask_report=mask_report,
            non_copy_items=[
                {
                    "name": "generation_backend",
                    "status": "pass",
                    "value": PRODUCTION_TILE_STREAM_BACKEND,
                    "message": "External production tile backend generated disk tiles before OME-TIFF publish.",
                }
            ],
        )
    except (OutputWriteError, ProductionTileStreamError, RuntimeError, ValueError) as exc:
        raise GenerationExecutionError(str(exc)) from exc

    diagnostics_path = root / "generation_output_diagnostics.json"
    metadata = _metadata_payload(
        generated_id=generated_id,
        generation_config=config,
        plan=plan,
        wsi_path=wsi_path,
        mask_path=mask_report["path"],
        qc_path=root / "qc.json",
        diagnostics_manifest_path=diagnostics_path,
        generation_backend=PRODUCTION_TILE_STREAM_BACKEND,
        condition_packet=condition_packet,
    )
    try:
        archive = archive_sample(root, metadata, qc)
    except (ValueError, RuntimeError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    diagnostics = _generation_output_diagnostics(
        generated_id=generated_id,
        backend=PRODUCTION_TILE_STREAM_BACKEND,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        qc_report=qc,
        diagnostics_manifest_path=diagnostics_path,
    )
    _write_validated_generation_output_diagnostics(diagnostics_path, diagnostics)
    run_summary = _run_summary(
        generated_id=generated_id,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        backend=PRODUCTION_TILE_STREAM_BACKEND,
        diagnostics_manifest_path=diagnostics_path,
        condition_packet=condition_packet,
    )
    run_path = root / "generation_run.json"
    run_path.write_text(json.dumps(run_summary, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "backend": PRODUCTION_TILE_STREAM_BACKEND,
        "status": "completed",
        "output_root": str(root),
        "generation_run_path": str(run_path),
        "diagnostics_manifest_path": str(diagnostics_path),
        **_condition_packet_return(condition_packet),
        **archive,
    }


def _metadata_payload(
    generated_id: str,
    generation_config: dict[str, Any],
    plan: dict[str, Any],
    wsi_path: Path,
    mask_path: str | Path,
    qc_path: Path,
    diagnostics_manifest_path: Path,
    generation_backend: str = SMOKE_BACKEND,
    condition_packet: dict[str, Any] | None = None,
    cascade_sample_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    generation_payload = {
        "generation_backend": generation_backend,
        "structure_anchor": generation_config["structure_anchor"],
        "style_seed": generation_config["style_seed"],
        "random_seed": generation_config["random_seed"],
        "model_checkpoint": plan["checkpoint_manifest_path"],
        "model_version": plan["checkpoint_model_version"],
        "prior_manifest_path": plan["prior_manifest_path"],
        "prior_id": plan["prior_id"],
        "cascade_levels": list(CASCADE_LEVELS),
        "max_magnification": MAX_MAGNIFICATION,
        "tile_size_40x": list(TILE_SIZE_40X),
        "sample_steps": generation_config["sample_steps"],
        "overlap_px_40x": generation_config["overlap_px_40x"],
    }
    if condition_packet is not None:
        generation_payload["condition_packet_path"] = condition_packet["path"]
        generation_payload["condition_summary"] = condition_packet["summary"]
    if cascade_sample_manifests is not None:
        generation_payload["cascade_sample_manifests"] = cascade_sample_manifests
    if "tile_traversal_plan" in plan:
        generation_payload["tile_traversal_plan"] = plan["tile_traversal_plan"]
    if "tile_manifest_path" in plan:
        generation_payload["tile_manifest_path"] = plan["tile_manifest_path"]
    if "tile_source_manifest_path" in plan:
        generation_payload["tile_source_manifest_path"] = plan["tile_source_manifest_path"]
    if "wsi_writer" in plan:
        generation_payload["wsi_writer"] = plan["wsi_writer"]

    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "output": {
            "wsi_path": str(wsi_path),
            "mask_path": str(mask_path),
            "qc_json_path": str(qc_path),
            "diagnostics_manifest_path": str(diagnostics_manifest_path),
        },
        "source": {
            "source_wsi_id": generation_config.get("source_wsi_id"),
            "source_wsi_path": None,
            "source_region": None,
            "source_scale": None,
        },
        "generation": generation_payload,
        "mask_schema": {
            "classes": list(MASK_CLASSES),
            "input_label_mapping": {},
            "mapping_source": "cluster",
            "confidence": {},
        },
        "qc": {
            "overall_status": "pass",
            "summary": {},
            "non_copy_report": {},
        },
    }


def _run_summary(
    generated_id: str,
    plan: dict[str, Any],
    archive: dict[str, Any],
    pyramid_report: dict[str, Any],
    mask_report: dict[str, Any],
    backend: str = SMOKE_BACKEND,
    sample_manifest_path: str | None = None,
    diagnostics_manifest_path: str | Path | None = None,
    cascade_sample_manifests: list[dict[str, Any]] | None = None,
    condition_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    outputs = {
        **archive,
        "wsi_path": pyramid_report["path"],
        "mask_path": mask_report["path"],
    }
    if diagnostics_manifest_path is not None:
        outputs["diagnostics_manifest_path"] = str(diagnostics_manifest_path)
    summary = {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "backend": backend,
        "status": "completed",
        "created_at": _now_iso(),
        "plan": plan,
        "outputs": outputs,
        "pyramid_report": pyramid_report,
        "mask_report": mask_report,
    }
    if sample_manifest_path is not None:
        summary["sample_manifest_path"] = sample_manifest_path
    if cascade_sample_manifests is not None:
        summary["cascade_sample_manifests"] = cascade_sample_manifests
    if condition_packet is not None:
        summary["condition_packet"] = {
            "path": condition_packet["path"],
            "summary": condition_packet["summary"],
        }
    return summary


def _generation_output_diagnostics(
    *,
    generated_id: str,
    backend: str,
    plan: dict[str, Any],
    archive: dict[str, Any],
    pyramid_report: dict[str, Any],
    mask_report: dict[str, Any],
    qc_report: dict[str, Any],
    diagnostics_manifest_path: str | Path,
) -> dict[str, Any]:
    """Build the run-level output diagnostics manifest.

    The manifest intentionally summarizes already-published contracts instead
    of introducing another source of truth. Missing optional manifests are
    represented as `applicable=false`; malformed manifests fail the run because
    the generated output would otherwise be hard to audit.
    """
    artifacts = {
        **archive,
        "wsi_path": pyramid_report["path"],
        "mask_path": mask_report["path"],
        "diagnostics_manifest_path": str(diagnostics_manifest_path),
    }
    return {
        "schema_version": PROJECT_VERSION,
        "manifest_type": "generation_output_diagnostics",
        "generated_id": generated_id,
        "backend": backend,
        "status": "completed",
        "created_at": _now_iso(),
        "artifacts": artifacts,
        "pyramid_summary": _pyramid_summary(pyramid_report),
        "writer_summary": _writer_summary(pyramid_report),
        "tile_execution": _tile_execution_summary(plan),
        "tile_source": _tile_source_summary(plan),
        "qc_summary": _qc_summary(qc_report),
    }


def _write_validated_generation_output_diagnostics(path: Path, payload: dict[str, Any]) -> None:
    try:
        validated = validate_generation_output_diagnostics(payload)
    except ValidationError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    _write_json(path, validated)


def _pyramid_summary(pyramid_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": pyramid_report.get("status"),
        "path": pyramid_report.get("path"),
        "is_ome": bool(pyramid_report.get("is_ome")),
        "level_count": pyramid_report.get("level_count"),
        "level_shapes": list(pyramid_report.get("level_shapes", [])),
        "write_mode": pyramid_report.get("write_mode"),
    }


def _writer_summary(pyramid_report: dict[str, Any]) -> dict[str, Any]:
    streaming_contract = pyramid_report.get("streaming_contract")
    if not isinstance(streaming_contract, dict):
        streaming_contract = {}
    streaming_write_report = pyramid_report.get("streaming_write_report")
    if not isinstance(streaming_write_report, dict):
        streaming_write_report = {}

    limitations = _first_list(
        streaming_write_report.get("streaming_limitations"),
        streaming_contract.get("streaming_limitations"),
        pyramid_report.get("streaming_limitations"),
    )
    transaction_manifest_path = _first_non_empty_str(
        pyramid_report.get("transaction_manifest_path"),
        streaming_write_report.get("transaction_manifest_path"),
        streaming_contract.get("transaction_manifest_path"),
    )
    return {
        "write_mode": pyramid_report.get("write_mode"),
        "production_streaming": bool(pyramid_report.get("production_streaming", False)),
        "resume_capable": bool(
            pyramid_report.get("resume_capable", streaming_contract.get("resume_capable", False))
        ),
        "atomic_publish": bool(
            pyramid_report.get("atomic_publish", streaming_contract.get("atomic_publish", False))
        ),
        "transaction_manifest_path": transaction_manifest_path,
        "recovered_from_temporary": bool(streaming_write_report.get("recovered_from_temporary", False)),
        "reused_existing_target": bool(streaming_write_report.get("reused_existing_target", False)),
        "disk_space_preflight": streaming_write_report.get(
            "disk_space_preflight",
            streaming_contract.get("disk_space_preflight"),
        ),
        "progress_manifest_path": streaming_write_report.get("progress_manifest_path"),
        "progress_summary": streaming_write_report.get("progress_summary"),
        "streaming_limitations": limitations,
    }


def _tile_execution_summary(plan: dict[str, Any]) -> dict[str, Any]:
    manifest_path = plan.get("tile_manifest_path")
    if manifest_path is None:
        return {
            "applicable": False,
            "reason": "torch_diffusion_smoke_uses_training_batch_sampling",
        }
    manifest = _load_json_object(manifest_path, "tile execution manifest")
    tiles = manifest.get("tiles")
    if not isinstance(tiles, list):
        raise GenerationExecutionError("tile execution manifest tiles must be a list")
    counts = _status_counts(tiles)
    return {
        "applicable": True,
        "manifest_path": str(manifest_path),
        "manifest_type": manifest.get("manifest_type"),
        "execution_status": manifest.get("execution_status", _execution_status_from_counts(counts)),
        "tile_count": int(manifest.get("tile_count", len(tiles))),
        **counts,
        "resume_index": manifest.get("resume_index"),
        "next_tile_index": manifest.get("next_tile_index"),
    }


def _tile_source_summary(plan: dict[str, Any]) -> dict[str, Any]:
    manifest_path = plan.get("tile_source_manifest_path")
    if manifest_path is None:
        return {
            "applicable": False,
            "reason": "torch_diffusion_smoke_writes_from_sampled_pyramid_arrays",
        }
    manifest = _load_json_object(manifest_path, "tile source manifest")
    records = manifest.get("tiles", manifest.get("records"))
    if not isinstance(records, list):
        raise GenerationExecutionError("tile source manifest tiles must be a list")
    levels = manifest.get("levels", [])
    if levels is not None and not isinstance(levels, list):
        raise GenerationExecutionError("tile source manifest levels must be a list")
    counts = _status_counts(records)
    return {
        "applicable": True,
        "manifest_path": str(manifest_path),
        "manifest_type": manifest.get("manifest_type"),
        "expected_tile_count": int(manifest.get("expected_tile_count", manifest.get("tile_count", len(records)))),
        **counts,
        "backend_execution_summary": manifest.get("backend_execution_summary"),
        "level_count": len(levels or []),
        "levels": [
            {
                "level_index": level.get("level_index"),
                "shape": level.get("shape"),
                "expected_tile_count": level.get("expected_tile_count"),
            }
            for level in levels or []
            if isinstance(level, dict)
        ],
    }


def _qc_summary(qc_report: dict[str, Any]) -> dict[str, Any]:
    levels = qc_report.get("levels", {})
    if not isinstance(levels, dict):
        levels = {}
    return {
        "overall_status": qc_report.get("overall_status"),
        "levels": {
            level: value.get("status")
            for level, value in levels.items()
            if isinstance(value, dict)
        },
        "non_copy_report": qc_report.get("non_copy_report", {}),
    }


def _load_json_object(path: str | Path, label: str) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise GenerationExecutionError(f"{label} does not exist: {source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationExecutionError(f"{label} must be valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise GenerationExecutionError(f"{label} must contain an object")
    return data


def _status_counts(records: list[Any]) -> dict[str, int]:
    completed = 0
    pending = 0
    failed = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("status") == "completed":
            completed += 1
        elif record.get("status") == "pending":
            pending += 1
        elif record.get("status") == "failed":
            failed += 1
    return {
        "completed_tile_count": completed,
        "pending_tile_count": pending,
        "failed_tile_count": failed,
    }


def _execution_status_from_counts(counts: dict[str, int]) -> str:
    if counts["failed_tile_count"] > 0:
        return "failed"
    if counts["pending_tile_count"] > 0:
        return "in_progress"
    return "completed"


def _first_non_empty_str(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return list(value)
    return []


def _load_generation_condition_packet(
    condition_packet_path: str | Path | None,
    plan: dict[str, Any],
) -> dict[str, Any] | None:
    if condition_packet_path is None:
        return None
    path = Path(condition_packet_path)
    if not path.exists():
        raise GenerationExecutionError(f"condition packet does not exist: {path}")
    if not path.is_file():
        raise GenerationExecutionError(f"condition packet path is not a file: {path}")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationExecutionError(f"condition packet is not valid JSON: {exc.msg}") from exc
    if not isinstance(packet, dict):
        raise GenerationExecutionError("condition packet must be a JSON object")
    if packet.get("schema_version") != PROJECT_VERSION:
        raise GenerationExecutionError(f"condition packet schema_version must be {PROJECT_VERSION}")
    if packet.get("condition_packet_type") != "generation_condition_packet":
        raise GenerationExecutionError("condition packet type must be generation_condition_packet")
    if packet.get("prior_id") != plan["prior_id"]:
        raise GenerationExecutionError("condition packet prior_id must match prior manifest")
    conditions = packet.get("conditions")
    if not isinstance(conditions, dict):
        raise GenerationExecutionError("condition packet conditions must be an object")
    for key in (
        "layout",
        "mask",
        "style_seed",
        "texture_token",
        "coord",
        "source_condition",
        "structure_anchor",
    ):
        if not isinstance(conditions.get(key), dict):
            raise GenerationExecutionError(f"condition packet conditions.{key} must be an object")
    return {
        "path": str(path),
        "summary": _condition_packet_summary(conditions),
    }


def _condition_packet_summary(conditions: dict[str, Any]) -> dict[str, Any]:
    coord = conditions["coord"]
    layout = conditions["layout"]
    mask = conditions["mask"]
    style_seed = conditions["style_seed"]
    texture = conditions["texture_token"]
    source = conditions["source_condition"]
    anchor = conditions["structure_anchor"]
    summary = {
        "cascade_level": coord.get("cascade_level"),
        "tile_origin_40x": list(coord.get("tile_origin_40x", [])),
        "style_seed_value": style_seed.get("value"),
        "style_seed_source": style_seed.get("source"),
        "texture_cluster_id": texture.get("cluster_id"),
        "source_condition_enabled": bool(source.get("enabled")),
        "structure_anchor": anchor.get("value"),
    }
    if mask.get("source") == "sampled_layout_mask":
        summary["sampled_layout_mask"] = _sampled_layout_mask_summary(mask)
    if style_seed.get("source") == "sampled_style_policy":
        summary["sampled_style_policy"] = _sampled_style_policy_summary(style_seed)
    if texture.get("source") == "sampled_texture_policy":
        summary["sampled_texture_policy"] = _sampled_texture_policy_summary(texture)
    if "wsi_tissue_overview" in layout:
        summary["wsi_tissue_overview"] = _wsi_tissue_overview_summary(
            layout["wsi_tissue_overview"]
        )
    return summary


def _sampled_layout_mask_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationExecutionError("condition packet conditions.mask must be an object")
    return {
        "source": "sampled_layout_mask",
        "artifact_path": _require_non_empty_condition_str(
            value,
            "artifact_path",
            "condition packet conditions.mask.artifact_path",
        ),
        "mask_path": _require_non_empty_condition_str(
            value,
            "mask_path",
            "condition packet conditions.mask.mask_path",
        ),
        "sample_id": _require_non_empty_condition_str(
            value,
            "sample_id",
            "condition packet conditions.mask.sample_id",
        ),
        "mask_shape": list(
            _require_condition_list(
                value,
                "mask_shape",
                "condition packet conditions.mask.mask_shape",
            )
        ),
        "class_pixel_counts_by_id": list(
            _require_condition_list(
                value,
                "class_pixel_counts_by_id",
                "condition packet conditions.mask.class_pixel_counts_by_id",
            )
        ),
        "class_fractions_by_id": list(
            _require_condition_list(
                value,
                "class_fractions_by_id",
                "condition packet conditions.mask.class_fractions_by_id",
            )
        ),
    }


def _sampled_style_policy_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationExecutionError(
            "condition packet conditions.style_seed must be an object"
        )
    selected_style = value.get("selected_style")
    if not isinstance(selected_style, dict):
        raise GenerationExecutionError(
            "condition packet conditions.style_seed.selected_style must be an object"
        )
    return {
        "source": "sampled_style_policy",
        "artifact_path": _require_non_empty_condition_str(
            value,
            "artifact_path",
            "condition packet conditions.style_seed.artifact_path",
        ),
        "sample_id": _require_non_empty_condition_str(
            value,
            "sample_id",
            "condition packet conditions.style_seed.sample_id",
        ),
        "random_seed": _require_condition_int(
            value,
            "random_seed",
            "condition packet conditions.style_seed.random_seed",
        ),
        "selection_policy": _require_non_empty_condition_str(
            value,
            "selection_policy",
            "condition packet conditions.style_seed.selection_policy",
        ),
        "selected_style": _sampled_selected_style_summary(selected_style),
        "rgb_statistics_reference": _copy_optional_condition_dict(
            value,
            "rgb_statistics_reference",
            "condition packet conditions.style_seed.rgb_statistics_reference",
        ),
        "limitations": list(
            _require_condition_list(
                value,
                "limitations",
                "condition packet conditions.style_seed.limitations",
            )
        ),
    }


def _sampled_selected_style_summary(value: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "tile_index": _require_condition_int(
            value,
            "tile_index",
            "condition packet conditions.style_seed.selected_style.tile_index",
        ),
        "mean_rgb": list(
            _require_condition_list(
                value,
                "mean_rgb",
                "condition packet conditions.style_seed.selected_style.mean_rgb",
            )
        ),
    }
    for key in ("sample_id", "wsi_id"):
        field_value = value.get(key)
        if field_value is not None:
            if not isinstance(field_value, str):
                raise GenerationExecutionError(
                    f"condition packet conditions.style_seed.selected_style.{key} must be a string"
                )
            summary[key] = field_value
    tile = value.get("tile")
    if tile is not None:
        if not isinstance(tile, dict):
            raise GenerationExecutionError(
                "condition packet conditions.style_seed.selected_style.tile must be an object"
            )
        summary["tile"] = dict(tile)
    return summary


def _sampled_texture_policy_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationExecutionError(
            "condition packet conditions.texture_token must be an object"
        )
    return {
        "source": "sampled_texture_policy",
        "artifact_path": _require_non_empty_condition_str(
            value,
            "artifact_path",
            "condition packet conditions.texture_token.artifact_path",
        ),
        "sample_id": _require_non_empty_condition_str(
            value,
            "sample_id",
            "condition packet conditions.texture_token.sample_id",
        ),
        "random_seed": _require_condition_int(
            value,
            "random_seed",
            "condition packet conditions.texture_token.random_seed",
        ),
        "selection_policy": _require_non_empty_condition_str(
            value,
            "selection_policy",
            "condition packet conditions.texture_token.selection_policy",
        ),
        "cluster_id": _require_condition_int(
            value,
            "cluster_id",
            "condition packet conditions.texture_token.cluster_id",
        ),
        "representative_embedding_index": _require_condition_int(
            value,
            "representative_embedding_index",
            "condition packet conditions.texture_token.representative_embedding_index",
        ),
        "prototype_index": _require_condition_int(
            value,
            "prototype_index",
            "condition packet conditions.texture_token.prototype_index",
        ),
        "sample_count": _optional_condition_int(
            value,
            "sample_count",
            "condition packet conditions.texture_token.sample_count",
        ),
        "fraction": _optional_condition_number(
            value,
            "fraction",
            "condition packet conditions.texture_token.fraction",
        ),
        "mean_embedding": list(
            _require_condition_list(
                value,
                "mean_embedding",
                "condition packet conditions.texture_token.mean_embedding",
            )
        ),
        "std_embedding": list(
            _require_condition_list(
                value,
                "std_embedding",
                "condition packet conditions.texture_token.std_embedding",
            )
        ),
        "texture_token": dict(
            _require_condition_dict(
                value,
                "texture_token",
                "condition packet conditions.texture_token.texture_token",
            )
        ),
        "morphology_latent": list(
            _require_condition_list(
                value,
                "morphology_latent",
                "condition packet conditions.texture_token.morphology_latent",
            )
        ),
        "texture_codebook_reference": dict(
            _require_condition_dict(
                value,
                "texture_codebook_reference",
                "condition packet conditions.texture_token.texture_codebook_reference",
            )
        ),
        "limitations": list(
            _require_condition_list(
                value,
                "limitations",
                "condition packet conditions.texture_token.limitations",
            )
        ),
    }


def _wsi_tissue_overview_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationExecutionError(
            "condition packet conditions.layout.wsi_tissue_overview must be an object"
        )
    source_value = _require_non_empty_condition_str(
        value,
        "source",
        "condition packet conditions.layout.wsi_tissue_overview.source",
    )
    artifact_path = _require_non_empty_condition_str(
        value,
        "artifact_path",
        "condition packet conditions.layout.wsi_tissue_overview.artifact_path",
    )
    record_count = _require_condition_int(
        value,
        "record_count",
        "condition packet conditions.layout.wsi_tissue_overview.record_count",
    )
    source_backend = _require_non_empty_condition_str(
        value,
        "source_backend",
        "condition packet conditions.layout.wsi_tissue_overview.source_backend",
    )
    thumbnail_max_size = _require_condition_list(
        value,
        "thumbnail_max_size",
        "condition packet conditions.layout.wsi_tissue_overview.thumbnail_max_size",
    )
    records = value.get("records")
    if not isinstance(records, list):
        raise GenerationExecutionError(
            "condition packet conditions.layout.wsi_tissue_overview.records must be a list"
        )
    summarized_records = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise GenerationExecutionError(
                "condition packet conditions.layout.wsi_tissue_overview.records"
                f"[{index}] must be an object"
            )
        summarized_records.append(
            {
                "wsi_id": _require_non_empty_condition_str(
                    record,
                    "wsi_id",
                    "condition packet conditions.layout.wsi_tissue_overview.records"
                    f"[{index}].wsi_id",
                ),
                "tissue_fraction": _require_condition_number(
                    record,
                    "tissue_fraction",
                    "condition packet conditions.layout.wsi_tissue_overview.records"
                    f"[{index}].tissue_fraction",
                ),
                "bounding_box_xywh": list(
                    _require_condition_list(
                        record,
                        "bounding_box_xywh",
                        "condition packet conditions.layout.wsi_tissue_overview.records"
                        f"[{index}].bounding_box_xywh",
                    )
                ),
                "connected_component_count": _require_condition_int(
                    record,
                    "connected_component_count",
                    "condition packet conditions.layout.wsi_tissue_overview.records"
                    f"[{index}].connected_component_count",
                ),
            }
        )
        manifest = record.get("manifest")
        if isinstance(manifest, dict):
            manifest_summary = {}
            for key in ("cancer_type", "tissue_type", "center_id", "split"):
                value = manifest.get(key)
                if isinstance(value, str) and value:
                    manifest_summary[key] = value
            if manifest_summary:
                summarized_records[-1]["manifest"] = manifest_summary
    return {
        "source": source_value,
        "artifact_path": artifact_path,
        "record_count": record_count,
        "source_backend": source_backend,
        "thumbnail_max_size": list(thumbnail_max_size),
        "records": summarized_records,
    }


def _require_non_empty_condition_str(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise GenerationExecutionError(f"{path} must be a non-empty string")
    return value


def _require_condition_list(data: dict[str, Any], key: str, path: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise GenerationExecutionError(f"{path} must be a list")
    return value


def _require_condition_dict(data: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise GenerationExecutionError(f"{path} must be an object")
    return value


def _require_condition_number(data: dict[str, Any], key: str, path: str) -> int | float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GenerationExecutionError(f"{path} must be a number")
    return value


def _require_condition_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise GenerationExecutionError(f"{path} must be an integer")
    return value


def _optional_condition_int(data: dict[str, Any], key: str, path: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise GenerationExecutionError(f"{path} must be an integer")
    return value


def _optional_condition_number(data: dict[str, Any], key: str, path: str) -> int | float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GenerationExecutionError(f"{path} must be a number")
    return value


def _copy_optional_condition_dict(data: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise GenerationExecutionError(f"{path} must be an object")
    return dict(value)


def _condition_packet_return(condition_packet: dict[str, Any] | None) -> dict[str, Any]:
    if condition_packet is None:
        return {}
    return {"condition_packet_path": condition_packet["path"]}


def _condition_wsi_tissue_overview(condition_packet: dict[str, Any] | None) -> dict[str, Any] | None:
    if condition_packet is None:
        return None
    return condition_packet["summary"].get("wsi_tissue_overview")


def _condition_sampled_layout_mask(condition_packet: dict[str, Any] | None) -> dict[str, Any] | None:
    if condition_packet is None:
        return None
    return condition_packet["summary"].get("sampled_layout_mask")


def _condition_qc_reference_context(condition_packet: dict[str, Any] | None) -> dict[str, Any]:
    if condition_packet is None:
        return {}
    overview = condition_packet["summary"].get("wsi_tissue_overview")
    if not isinstance(overview, dict):
        return {}
    records = overview.get("records")
    if not isinstance(records, list) or not records:
        return {}
    first_record = records[0]
    if not isinstance(first_record, dict):
        return {}
    manifest = first_record.get("manifest")
    if not isinstance(manifest, dict):
        return {}
    context = {}
    for field in ("cancer_type", "tissue_type", "center_id", "split"):
        value = manifest.get(field)
        if isinstance(value, str) and value:
            context[f"metadata.{field}"] = value
    return context


def _conditioned_or_smoke_mask(
    numpy,
    condition_packet: dict[str, Any] | None,
    shape: tuple[int, int],
):
    if condition_packet is None:
        return _build_smoke_mask(numpy, shape)
    sampled_layout_mask = condition_packet["summary"].get("sampled_layout_mask")
    if sampled_layout_mask is None:
        return _build_smoke_mask(numpy, shape)
    return _load_condition_sampled_layout_mask(
        numpy,
        sampled_layout_mask,
        shape,
    )


def _load_condition_sampled_layout_mask(
    numpy,
    sampled_layout_mask: dict[str, Any],
    shape: tuple[int, int],
):
    mask_path = Path(sampled_layout_mask["mask_path"])
    if not mask_path.exists():
        raise GenerationExecutionError(f"sampled layout mask file does not exist: {mask_path}")
    try:
        mask = numpy.load(mask_path)
    except Exception as exc:
        raise GenerationExecutionError(f"sampled layout mask cannot be loaded: {mask_path}") from exc
    if mask.ndim != 2:
        raise GenerationExecutionError("sampled layout mask must be 2D")
    unique_values = [int(value) for value in numpy.unique(mask).tolist()]
    invalid_values = [value for value in unique_values if value < 0 or value >= len(MASK_CLASSES)]
    if invalid_values:
        raise GenerationExecutionError("sampled layout mask contains invalid class ids")
    if tuple(int(value) for value in mask.shape) != tuple(int(value) for value in shape):
        mask = _resize_nearest(numpy, mask.astype(numpy.uint8), int(shape[0]), int(shape[1]))
    return mask.astype(numpy.uint8)


def _torch_diffusion_smoke_plan(
    config: dict[str, Any],
    prior_manifest_path: str | Path,
    prior_id: str,
    checkpoint_manifest_path: str | Path,
    checkpoint_model_version: str,
    checkpoint_inference_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "model_family": config["model_family"],
        "prior_manifest_path": str(prior_manifest_path),
        "prior_id": prior_id,
        "checkpoint_manifest_path": str(checkpoint_manifest_path),
        "checkpoint_model_version": checkpoint_model_version,
        "checkpoint_inference_contract": {
            "backend_type": checkpoint_inference_contract["backend_type"],
            "artifact_role": checkpoint_inference_contract["artifact_role"],
            "production_ready": checkpoint_inference_contract["production_ready"],
            "limitations": list(checkpoint_inference_contract["limitations"]),
            "compatible_generation_backends": list(
                checkpoint_inference_contract["compatible_generation_backends"]
            ),
            "model_architecture_contract": dict(
                checkpoint_inference_contract["model_architecture_contract"]
            ),
            "condition_input_contract": {
                "required_condition_inputs": list(
                    checkpoint_inference_contract["condition_input_contract"][
                        "required_condition_inputs"
                    ]
                ),
                "cascade_levels": list(
                    checkpoint_inference_contract["condition_input_contract"][
                        "cascade_levels"
                    ]
                ),
                "condition_feature_policy": checkpoint_inference_contract[
                    "condition_input_contract"
                ]["condition_feature_policy"],
            },
        },
        "random_seed": config["random_seed"],
        "structure_anchor": config["structure_anchor"],
        "style_seed": config["style_seed"],
        "source_wsi_id": config["source_wsi_id"],
        "sample_steps": config["sample_steps"],
        "overlap_px_40x": config["overlap_px_40x"],
        "tile_traversal": "training_index_first_batch_smoke",
        "blending": "nearest_proxy_preview_resize",
        "write_mode": "small_pyramid_write",
        "stages": [
            {
                "order": index,
                "level": level,
                "status": "completed",
                "condition_inputs": [
                    "previous_scale_rgb_proxy",
                    "mask",
                    "timestep",
                    "condition_feature_channels",
                    "diffusion_smoke_checkpoint",
                ],
                "resume_index": 0,
            }
            for index, level in enumerate(CASCADE_LEVELS)
        ],
    }


def _run_torch_diffusion_smoke_cascade_samples(
    checkpoint_manifest_path: str | Path,
    training_index_path: str | Path,
    output_root: Path,
    batch_size: int,
    sample_steps: int,
    random_seed: int,
    condition_packet_path: str | Path | None,
    expected_prior_id: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    previous_scale_condition_path: str | None = None
    for order, cascade_level in enumerate(CASCADE_LEVELS):
        sample = sample_torch_diffusion_smoke_model(
            checkpoint_manifest_path=checkpoint_manifest_path,
            training_index_path=training_index_path,
            output_dir=output_root
            / "torch_diffusion_cascade_samples"
            / cascade_level.replace("/", "_"),
            batch_size=batch_size,
            split=None,
            cascade_level=cascade_level,
            sample_steps=sample_steps,
            random_seed=random_seed + order,
            condition_packet_path=condition_packet_path,
            expected_prior_id=expected_prior_id,
            previous_scale_condition_path=previous_scale_condition_path,
        )
        record = {
            "order": order,
            "cascade_level": cascade_level,
            "sample_manifest_path": sample["sample_manifest_path"],
            "sample_preview_path": sample["sample_preview_path"],
            "cross_scale_condition_source": sample["cross_scale_condition_source"],
        }
        if previous_scale_condition_path is not None:
            record["previous_scale_condition_path"] = previous_scale_condition_path
        records.append(record)
        previous_scale_condition_path = sample["sample_preview_path"]
    return records


def _prepare_smoke_tile_outputs(
    numpy,
    generation_config: dict[str, Any],
    tile_traversal_plan: dict[str, Any],
    output_root: Path,
    *,
    resume_manifest_path: Path | None = None,
    keep_tile_images: bool = True,
) -> dict[str, Any]:
    try:
        manifest = (
            _load_resume_tile_manifest(resume_manifest_path, output_root)
            if resume_manifest_path is not None
            else build_resumable_tile_manifest(tile_traversal_plan)
        )
    except GenerationTilingError as exc:
        raise GenerationExecutionError(str(exc)) from exc

    _ensure_resume_manifest_matches_plan(manifest, tile_traversal_plan)
    _ensure_existing_completed_tile_files(manifest, output_root)
    seed = int(generation_config["random_seed"])
    style_seed = generation_config.get("style_seed")
    if isinstance(style_seed, int) and not isinstance(style_seed, bool):
        seed += style_seed
    anchor_offset = int(float(generation_config["structure_anchor"]) * 50)
    base_rgb = numpy.array([184, 122, 168], dtype=numpy.uint16)
    tile_width, tile_height = [int(value) for value in tile_traversal_plan["model_tile_size_40x"]]
    tiles_dir = output_root / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    tile_records = []

    for tile in manifest["tiles"]:
        tile_index = int(tile["tile_index"])
        source_tile = tile_traversal_plan["tiles"][tile_index]
        tile_origin = source_tile["tile_origin_40x"]
        x_origin = int(tile_origin[0])
        y_origin = int(tile_origin[1])
        output_path = tile.get("output_path")
        if tile.get("status") == "completed":
            tile_path = _resolve_output_relative_path(output_path, output_root, "completed tile file")
            image = _load_completed_tile(numpy, tile_path) if keep_tile_images else None
        else:
            image = _smoke_rgb_image(
                numpy,
                tile_height,
                tile_width,
                base_rgb,
                seed + tile_index * 17 + anchor_offset + x_origin + y_origin,
            )
            tile_path = tiles_dir / f"tile-{tile_index:06d}.npy"
            numpy.save(tile_path, image)
            try:
                manifest = update_resumable_tile_manifest(
                    manifest,
                    tile_index=tile_index,
                    status="completed",
                    output_path=tile_path.relative_to(output_root).as_posix(),
                )
            except GenerationTilingError as exc:
                raise GenerationExecutionError(str(exc)) from exc

        record = {
            "tile_index": tile_index,
            "tile_origin_40x": [x_origin, y_origin],
            "write_region_40x": list(source_tile["write_region_40x"]),
            "path": str(tile_path),
            "relative_path": tile_path.relative_to(output_root).as_posix(),
        }
        if keep_tile_images:
            record["image"] = image
        tile_records.append(record)

    try:
        manifest = require_complete_tile_manifest(manifest)
    except GenerationTilingError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    manifest_path = resume_manifest_path or (output_root / "tile_manifest.json")
    _write_json(manifest_path, manifest)
    tile_source_manifest_path = output_root / "tile_source_manifest.json"
    tile_source_manifest = _build_tile_source_manifest(manifest, tile_traversal_plan, output_root)
    _write_json(tile_source_manifest_path, tile_source_manifest)
    return {
        "tile_records": tile_records,
        "tile_manifest_path": manifest_path,
        "tile_source_manifest_path": tile_source_manifest_path,
    }


def _build_smoke_canvas_from_tile_records(
    numpy,
    tile_records: list[dict[str, Any]],
    tile_traversal_plan: dict[str, Any],
):
    canvas_width, canvas_height = [int(value) for value in tile_traversal_plan["canvas_size_40x"]]
    overlap_px = int(tile_traversal_plan["overlap_px_40x"])
    return blend_rgb_tiles(
        tile_records,
        canvas_size_40x=[canvas_width, canvas_height],
        overlap_px_40x=overlap_px,
    )


def _iter_smoke_pyramid_levels_high_to_low(numpy, canvas) -> Iterable[Any]:
    # OME-TIFF pyramid writers expect high-to-low resolution. The streaming
    # path yields derived levels one at a time to avoid an extra four-level
    # pyramid container before disk tile materialization.
    canvas_height, canvas_width = [int(value) for value in canvas.shape[:2]]
    yield canvas
    for divisor in (4, 16, 32):
        height = max(1, canvas_height // divisor)
        width = max(1, canvas_width // divisor)
        yield _resize_nearest(numpy, canvas, height, width)


def _build_smoke_cascade_from_tile_records(
    numpy,
    tile_records: list[dict[str, Any]],
    tile_traversal_plan: dict[str, Any],
) -> dict[str, Any]:
    canvas = _build_smoke_canvas_from_tile_records(numpy, tile_records, tile_traversal_plan)
    levels = list(_iter_smoke_pyramid_levels_high_to_low(numpy, canvas))
    return {
        "1/1": levels[0],
        "1/4": levels[1],
        "1/16": levels[2],
        "1/32": levels[3],
    }


def _load_resume_tile_manifest(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        raise GenerationExecutionError(f"resume tile manifest does not exist: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationExecutionError("resume tile manifest must be valid JSON") from exc
    if not isinstance(data, dict):
        raise GenerationExecutionError("resume tile manifest must contain an object")
    try:
        manifest = validate_resumable_tile_manifest(data)
        if manifest["failed_tile_count"] > 0:
            require_complete_tile_manifest(manifest)
        if manifest["completed_tile_count"] != manifest["resume_index"]:
            require_complete_tile_manifest(manifest)
    except GenerationTilingError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    if manifest_path.resolve().parent != output_root.resolve():
        raise GenerationExecutionError("resume tile manifest must be in output_root")
    return manifest


def _ensure_resume_manifest_matches_plan(
    manifest: dict[str, Any],
    tile_traversal_plan: dict[str, Any],
) -> None:
    expected = {
        "tile_count": tile_traversal_plan["tile_count"],
        "canvas_size_40x": tile_traversal_plan["canvas_size_40x"],
        "model_tile_size_40x": tile_traversal_plan["model_tile_size_40x"],
        "overlap_px_40x": tile_traversal_plan["overlap_px_40x"],
        "stride_40x": tile_traversal_plan["stride_40x"],
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise GenerationExecutionError(f"resume tile manifest {key} does not match generation plan")


def _ensure_existing_completed_tile_files(manifest: dict[str, Any], output_root: Path) -> None:
    for tile in manifest["tiles"]:
        if tile["status"] != "completed":
            continue
        tile_path = _resolve_output_relative_path(
            tile.get("output_path"),
            output_root,
            "completed tile file",
        )
        if not tile_path.exists():
            raise GenerationExecutionError(f"completed tile file does not exist: {tile_path}")


def _resolve_output_relative_path(value: Any, output_root: Path, label: str) -> Path:
    if not isinstance(value, str) or value == "":
        raise GenerationExecutionError(f"{label} path must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        try:
            path.relative_to(output_root)
        except ValueError as exc:
            raise GenerationExecutionError(f"{label} path must be inside output_root") from exc
        return path
    return output_root / path


def _load_completed_tile(numpy, tile_path: Path):
    try:
        image = numpy.load(tile_path, allow_pickle=False)
    except Exception as exc:
        raise GenerationExecutionError(f"completed tile file cannot be loaded: {tile_path}") from exc
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != numpy.uint8:
        raise GenerationExecutionError("completed tile file must be a uint8 RGB .npy array")
    return image


def _build_tile_source_manifest(
    tile_manifest: dict[str, Any],
    tile_traversal_plan: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    records = []
    for tile in tile_manifest["tiles"]:
        tile_index = int(tile["tile_index"])
        plan_tile = tile_traversal_plan["tiles"][tile_index]
        path = _resolve_output_relative_path(tile["output_path"], output_root, "completed tile file")
        records.append(
            {
                "level_index": 0,
                "tile_index": tile_index,
                "path": path.relative_to(output_root).as_posix(),
                "shape": list(plan_tile["model_tile_size_40x"][::-1]) + [3],
                "dtype": "uint8",
                "status": tile["status"],
                "tile_origin_40x": list(plan_tile["tile_origin_40x"]),
                "write_region_40x": list(plan_tile["write_region_40x"]),
            }
        )
    return {
        "schema_version": PROJECT_VERSION,
        "manifest_type": "disk_npy_tile_source_manifest",
        "expected_tile_count": tile_manifest["tile_count"],
        "levels": [
            {
                "level_index": 0,
                "shape": list(tile_traversal_plan["canvas_size_40x"][::-1]) + [3],
                "expected_tile_count": tile_manifest["tile_count"],
            }
        ],
        "tiles": records,
    }


def _write_smoke_multilevel_tile_source_manifest(
    numpy,
    pyramid_levels: Iterable[Any],
    *,
    output_root: Path,
    chunk_shape: tuple[int, int],
) -> Path:
    """Materialize smoke pyramid levels as complete disk tile sources.

    This helper is only used by the explicit `tile-streaming` smoke writer. It
    keeps the default array writer and level0 execution/resume manifest intact,
    while giving the OME-TIFF tiled iterator writer a full high-to-low pyramid
    manifest. The smoke cascade arrays are still produced in memory before this
    point, so this is not a production backend streaming implementation.
    """
    chunk_height, chunk_width = [int(value) for value in chunk_shape]
    if chunk_height <= 0 or chunk_width <= 0:
        raise GenerationExecutionError("tile-streaming chunk shape must contain positive values")

    tile_root = output_root / "streaming_tiles"
    tile_root.mkdir(parents=True, exist_ok=True)
    levels = []
    records = []
    for level_index, level in enumerate(pyramid_levels):
        array = numpy.asarray(level)
        if array.ndim != 3 or array.shape[2] != 3 or array.dtype != numpy.uint8:
            raise GenerationExecutionError("smoke streaming pyramid levels must be uint8 RGB arrays")
        height, width = [int(value) for value in array.shape[:2]]
        grid_y = (height + chunk_height - 1) // chunk_height
        grid_x = (width + chunk_width - 1) // chunk_width
        expected_count = int(grid_y * grid_x)
        levels.append(
            {
                "level_index": level_index,
                "shape": [height, width, 3],
                "expected_tile_count": expected_count,
            }
        )
        for row in range(grid_y):
            for col in range(grid_x):
                x_origin = col * chunk_width
                y_origin = row * chunk_height
                tile_width = min(chunk_width, width - x_origin)
                tile_height = min(chunk_height, height - y_origin)
                tile = array[y_origin : y_origin + tile_height, x_origin : x_origin + tile_width, :]
                tile_path = tile_root / f"level-{level_index}-tile-{row:04d}-{col:04d}.npy"
                numpy.save(tile_path, tile)
                records.append(
                    {
                        "level_index": level_index,
                        "tile_index": int(row * grid_x + col),
                        "path": tile_path.relative_to(output_root).as_posix(),
                        "shape": [tile_height, tile_width, 3],
                        "dtype": "uint8",
                        "status": "completed",
                        "tile_origin": [x_origin, y_origin],
                        "write_region": [x_origin, y_origin, tile_width, tile_height],
                    }
                )

    manifest_path = output_root / "tile_source_manifest.streaming.json"
    _write_json(
        manifest_path,
        {
            "schema_version": PROJECT_VERSION,
            "manifest_type": "disk_npy_tile_source_manifest",
            "source": "smoke_multilevel_pyramid_tile_streaming_manifest",
            "expected_tile_count": len(records),
            "levels": levels,
            "tiles": records,
            "limitations": [
                "smoke_cascade_arrays_materialized_before_tile_source_write",
                "ome_tiff_file_resume_not_supported",
            ],
        },
    )
    return manifest_path


def _write_torch_diffusion_smoke_tile_source_manifest(
    numpy,
    levels_by_cascade: dict[str, Any],
    *,
    output_root: Path,
    chunk_shape: tuple[int, int],
) -> Path:
    """Materialize learned smoke cascade previews for the tiled writer.

    This closes the writer handoff for the PyTorch smoke backend without
    claiming production inference: sample previews are already complete small
    arrays, and the OME-TIFF writer still requires a complete tile source
    manifest before publishing.
    """
    chunk_height, chunk_width = [int(value) for value in chunk_shape]
    if chunk_height <= 0 or chunk_width <= 0:
        raise GenerationExecutionError("tile-streaming chunk shape must contain positive values")

    tile_root = output_root / "streaming_tiles"
    tile_root.mkdir(parents=True, exist_ok=True)
    levels = []
    records = []
    for level_index, cascade_level in enumerate(("1/1", "1/4", "1/16", "1/32")):
        array = numpy.asarray(levels_by_cascade[cascade_level])
        if array.ndim != 3 or array.shape[2] != 3 or array.dtype != numpy.uint8:
            raise GenerationExecutionError("torch diffusion smoke streaming levels must be uint8 RGB arrays")
        height, width = [int(value) for value in array.shape[:2]]
        grid_y = (height + chunk_height - 1) // chunk_height
        grid_x = (width + chunk_width - 1) // chunk_width
        expected_count = int(grid_y * grid_x)
        levels.append(
            {
                "level_index": level_index,
                "cascade_level": cascade_level,
                "shape": [height, width, 3],
                "expected_tile_count": expected_count,
            }
        )
        for row in range(grid_y):
            for col in range(grid_x):
                x_origin = col * chunk_width
                y_origin = row * chunk_height
                tile_width = min(chunk_width, width - x_origin)
                tile_height = min(chunk_height, height - y_origin)
                tile = array[y_origin : y_origin + tile_height, x_origin : x_origin + tile_width, :]
                tile_path = tile_root / f"level-{level_index}-tile-{row:04d}-{col:04d}.npy"
                numpy.save(tile_path, tile)
                records.append(
                    {
                        "level_index": level_index,
                        "cascade_level": cascade_level,
                        "tile_index": int(row * grid_x + col),
                        "path": tile_path.relative_to(output_root).as_posix(),
                        "shape": [tile_height, tile_width, 3],
                        "dtype": "uint8",
                        "status": "completed",
                        "tile_origin": [x_origin, y_origin],
                        "write_region": [x_origin, y_origin, tile_width, tile_height],
                    }
                )

    manifest_path = output_root / "tile_source_manifest.streaming.json"
    _write_json(
        manifest_path,
        {
            "schema_version": PROJECT_VERSION,
            "manifest_type": "disk_npy_tile_source_manifest",
            "source": "torch_diffusion_smoke_cascade_tile_streaming_manifest",
            "expected_tile_count": len(records),
            "levels": levels,
            "tiles": records,
            "generation_status": "completed",
            "completed_tile_count": len(records),
            "pending_tile_count": 0,
            "failed_tile_count": 0,
            "limitations": [
                "torch_diffusion_smoke_not_production_model",
                "sample_previews_materialized_before_tile_source_write",
                "requires_complete_tile_source_manifest_before_write",
                "ome_tiff_file_resume_not_supported",
            ],
        },
    )
    return manifest_path


def _write_smoke_direct_multilevel_tile_source_manifest(
    numpy,
    generation_config: dict[str, Any],
    tile_traversal_plan: dict[str, Any],
    *,
    output_root: Path,
    chunk_shape: tuple[int, int],
) -> Path:
    """Write pyramid tile source files directly on the TIFF tile grid.

    The explicit `tile-streaming` path uses this helper so it no longer needs a
    full blended level-0 canvas before the OME-TIFF tiled iterator writer can
    run. It remains a deterministic smoke renderer, not a production diffusion
    model, and still requires a complete tile source manifest before publishing.
    """
    chunk_height, chunk_width = [int(value) for value in chunk_shape]
    if chunk_height <= 0 or chunk_width <= 0:
        raise GenerationExecutionError("tile-streaming chunk shape must contain positive values")

    canvas_width, canvas_height = [
        int(value) for value in tile_traversal_plan["canvas_size_40x"]
    ]
    seed = int(generation_config["random_seed"])
    style_seed = generation_config.get("style_seed")
    if isinstance(style_seed, int) and not isinstance(style_seed, bool):
        seed += style_seed
    seed += int(float(generation_config["structure_anchor"]) * 50)
    base_rgb = numpy.array([184, 122, 168], dtype=numpy.uint16)

    tile_root = output_root / "streaming_tiles"
    tile_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "tile_source_manifest.streaming.json"
    levels = []
    records = []
    for level_index, divisor in enumerate((1, 4, 16, 32)):
        height = max(1, canvas_height // divisor)
        width = max(1, canvas_width // divisor)
        grid_y = (height + chunk_height - 1) // chunk_height
        grid_x = (width + chunk_width - 1) // chunk_width
        expected_count = int(grid_y * grid_x)
        levels.append(
            {
                "level_index": level_index,
                "shape": [height, width, 3],
                "expected_tile_count": expected_count,
            }
        )
        for row in range(grid_y):
            for col in range(grid_x):
                x_origin = col * chunk_width
                y_origin = row * chunk_height
                tile_width = min(chunk_width, width - x_origin)
                tile_height = min(chunk_height, height - y_origin)
                tile_index = int(row * grid_x + col)
                tile_path = tile_root / f"level-{level_index}-tile-{row:04d}-{col:04d}.npy"
                records.append(
                    {
                        "level_index": level_index,
                        "tile_index": tile_index,
                        "path": tile_path.relative_to(output_root).as_posix(),
                        "shape": [tile_height, tile_width, 3],
                        "dtype": "uint8",
                        "status": "pending",
                        "tile_origin": [x_origin, y_origin],
                        "write_region": [x_origin, y_origin, tile_width, tile_height],
                    }
                )

    expected_manifest = _refresh_smoke_direct_tile_source_manifest(
        {
            "schema_version": PROJECT_VERSION,
            "manifest_type": "disk_npy_tile_source_manifest",
            "source": "smoke_direct_pyramid_tile_streaming_manifest",
            "expected_tile_count": len(records),
            "levels": levels,
            "tiles": records,
            "limitations": [
                "smoke_generator_not_production_model",
                "requires_complete_tile_source_manifest_before_write",
                "ome_tiff_file_resume_not_supported",
            ],
        }
    )
    if manifest_path.exists():
        manifest = _load_resumable_smoke_direct_tile_source_manifest(
            numpy,
            manifest_path,
            expected_manifest,
            output_root,
        )
    else:
        manifest = expected_manifest
        _write_json(manifest_path, manifest)

    for record_index, record in enumerate(manifest["tiles"]):
        if record["status"] == "completed":
            _ensure_smoke_direct_tile_source_file(numpy, output_root, record, record_index)
            continue
        if record["status"] != "pending":
            raise GenerationExecutionError("smoke direct tile source status must be pending or completed")
        _, _, tile_width, tile_height = record["write_region"]
        level_index = int(record["level_index"])
        tile_index = int(record["tile_index"])
        x_origin, y_origin = [int(value) for value in record["tile_origin"]]
        tile = _smoke_rgb_image(
            numpy,
            tile_height,
            tile_width,
            base_rgb,
            seed + level_index * 97 + tile_index * 17 + x_origin + y_origin,
        )
        tile_path = output_root / record["path"]
        numpy.save(tile_path, tile)
        record["status"] = "completed"
        manifest["tiles"][record_index] = record
        manifest = _refresh_smoke_direct_tile_source_manifest(manifest)
        _write_json(manifest_path, manifest)
    return manifest_path


def _load_resumable_smoke_direct_tile_source_manifest(
    numpy,
    manifest_path: Path,
    expected_manifest: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    manifest = _load_json_object(manifest_path, "smoke direct tile source manifest")
    for key in ("schema_version", "manifest_type", "source", "expected_tile_count", "levels"):
        if manifest.get(key) != expected_manifest.get(key):
            raise GenerationExecutionError(f"smoke direct tile source manifest {key} does not match generation plan")
    tiles = manifest.get("tiles")
    expected_tiles = expected_manifest["tiles"]
    if not isinstance(tiles, list) or len(tiles) != len(expected_tiles):
        raise GenerationExecutionError("smoke direct tile source manifest tiles do not match generation plan")
    merged_tiles = []
    for index, (record, expected_record) in enumerate(zip(tiles, expected_tiles, strict=True)):
        if not isinstance(record, dict):
            raise GenerationExecutionError(f"smoke direct tile source tiles[{index}] must be an object")
        for key in (
            "level_index",
            "tile_index",
            "path",
            "shape",
            "dtype",
            "tile_origin",
            "write_region",
        ):
            if record.get(key) != expected_record.get(key):
                raise GenerationExecutionError(
                    f"smoke direct tile source tiles[{index}].{key} does not match generation plan"
                )
        status = record.get("status")
        if status == "completed":
            _ensure_smoke_direct_tile_source_file(numpy, output_root, record, index)
        elif status != "pending":
            raise GenerationExecutionError("smoke direct tile source status must be pending or completed")
        merged_tiles.append({**expected_record, "status": status})
    resumed = dict(expected_manifest)
    resumed["tiles"] = merged_tiles
    return _refresh_smoke_direct_tile_source_manifest(resumed)


def _ensure_smoke_direct_tile_source_file(
    numpy,
    output_root: Path,
    record: dict[str, Any],
    record_index: int,
) -> None:
    tile_path = output_root / record["path"]
    if not tile_path.exists():
        raise GenerationExecutionError(f"completed smoke direct tile source file does not exist: {tile_path}")
    try:
        tile = numpy.load(tile_path, allow_pickle=False)
    except Exception as exc:
        raise GenerationExecutionError(f"completed smoke direct tile source file cannot be loaded: {tile_path}") from exc
    expected_shape = record["shape"]
    if [int(value) for value in tile.shape] != expected_shape:
        raise GenerationExecutionError(
            f"completed smoke direct tile source tiles[{record_index}].shape does not match manifest"
        )
    if str(tile.dtype) != record["dtype"]:
        raise GenerationExecutionError(
            f"completed smoke direct tile source tiles[{record_index}].dtype does not match manifest"
        )


def _refresh_smoke_direct_tile_source_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    tiles = manifest["tiles"]
    completed = sum(1 for record in tiles if record.get("status") == "completed")
    pending = sum(1 for record in tiles if record.get("status") == "pending")
    failed = sum(1 for record in tiles if record.get("status") == "failed")
    updated = dict(manifest)
    updated["completed_tile_count"] = completed
    updated["pending_tile_count"] = pending
    updated["failed_tile_count"] = failed
    updated["generation_status"] = "completed" if pending == 0 and failed == 0 else "in_progress"
    return updated


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _smoke_rgb_image(numpy, height: int, width: int, base_rgb, offset: int):
    yy, xx = numpy.indices((height, width), dtype=numpy.uint16)
    image = numpy.empty((height, width, 3), dtype=numpy.uint8)
    image[..., 0] = (base_rgb[0] + xx + offset) % 256
    image[..., 1] = (base_rgb[1] + yy * 2 + offset) % 256
    image[..., 2] = (base_rgb[2] + (xx // 2) + (yy // 3) + offset) % 256
    return image


def _build_smoke_mask(numpy, shape: tuple[int, int]):
    height, width = shape
    yy, xx = numpy.indices((height, width), dtype=numpy.uint16)
    mask = numpy.ones((height, width), dtype=numpy.uint8)
    mask[(xx > width // 3) & (yy < height // 2)] = 2
    mask[(xx <= width // 3) & (yy >= height // 2)] = 3
    mask[(xx > width // 3) & (xx < 2 * width // 3) & (yy >= height // 2)] = 4
    mask[(xx >= 2 * width // 3) & (yy >= height // 2)] = 5
    mask[(xx < width // 12) | (yy < height // 12)] = 0
    return mask


def _load_sample_preview(numpy, path: str | Path):
    source = Path(path)
    if not source.exists():
        raise GenerationExecutionError(f"sample preview does not exist: {source}")
    try:
        preview = numpy.load(source)
    except Exception as exc:
        raise GenerationExecutionError(f"sample preview cannot be loaded: {source}") from exc
    if preview.ndim != 4 or preview.shape[-1] != 3:
        raise GenerationExecutionError("sample preview must have shape [batch, height, width, 3]")
    if preview.shape[0] <= 0:
        raise GenerationExecutionError("sample preview batch must not be empty")
    if preview.dtype != numpy.uint8:
        raise GenerationExecutionError("sample preview dtype must be uint8")
    return preview


def _build_torch_diffusion_smoke_cascade_from_samples(
    numpy,
    cascade_sample_manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    shapes = {
        "1/32": (16, 16),
        "1/16": (32, 32),
        "1/4": (128, 128),
        "1/1": tuple(TILE_SIZE_40X),
    }
    levels: dict[str, Any] = {}
    for record in cascade_sample_manifests:
        level = record.get("cascade_level")
        if level not in shapes:
            raise GenerationExecutionError("cascade sample manifest has unsupported level")
        preview = _load_sample_preview(numpy, record["sample_preview_path"])[0]
        height, width = shapes[level]
        levels[level] = _resize_nearest(numpy, preview, height, width)
    missing = [level for level in CASCADE_LEVELS if level not in levels]
    if missing:
        raise GenerationExecutionError(f"missing cascade sample levels: {missing}")
    return levels


def _resize_nearest(numpy, array, height: int, width: int):
    if array.ndim not in {2, 3}:
        raise GenerationExecutionError("resize input must be a 2D mask or 3D RGB image")
    y_index = (numpy.arange(height) * array.shape[0] / height).astype(numpy.int64)
    x_index = (numpy.arange(width) * array.shape[1] / width).astype(numpy.int64)
    return array[y_index[:, None], x_index[None, :]]


def _load_qc_reference_distribution(prior_manifest_path: str | Path) -> dict[str, Any]:
    try:
        prior = load_prior_manifest(prior_manifest_path, verify_files=True)
    except PriorArtifactError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    artifact = prior["artifacts"]["qc_reference_distribution"]
    if artifact["kind"] != "json":
        raise GenerationExecutionError("qc_reference_distribution artifact must be JSON")
    path = Path(artifact["path"])
    try:
        reference = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationExecutionError(f"{path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(reference, dict):
        raise GenerationExecutionError("qc_reference_distribution artifact must be a JSON object")
    return reference


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise GenerationExecutionError("smoke generation requires numpy") from exc
    return numpy


def _complete_generation_stages(stages: Any) -> list[dict[str, Any]]:
    if not isinstance(stages, list):
        raise GenerationExecutionError("plan.stages must be a list")
    completed_stages: list[dict[str, Any]] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise GenerationExecutionError(f"plan.stages[{index}] must be an object")
        updated_stage = dict(stage)
        updated_stage["status"] = "completed"
        completed_stages.append(updated_stage)
    return completed_stages


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
