import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, MAX_MAGNIFICATION, PROJECT_VERSION, TILE_SIZE_40X
from ..metadata.archive import archive_sample
from ..models.torch_training import TorchTrainingError, sample_torch_diffusion_smoke_model
from ..models.training import ModelRunError, load_checkpoint_manifest
from ..models.training_batch import TrainingBatchError, load_training_batch
from ..outputs.masks import write_mask_array
from ..outputs.ome_tiff import OutputWriteError, write_pyramid_ome_tiff
from ..priors.artifacts import PriorArtifactError, load_prior_manifest
from ..qc.engine import QCReferenceError, build_qc_report
from ..schemas import ValidationError, validate_generation_config
from .tiling import blend_rgb_tiles, complete_tile_traversal_plan
from .planner import create_generation_plan


class GenerationExecutionError(RuntimeError):
    """Raised when a generation run cannot produce an auditable output object."""


SMOKE_BACKEND = "smoke-cascade"
TORCH_DIFFUSION_SMOKE_BACKEND = "torch-diffusion-smoke"


def run_smoke_generation(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    checkpoint_manifest_path: str | Path,
    output_root: str | Path,
    generated_id: str,
    condition_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(generated_id, str) or generated_id == "":
        raise GenerationExecutionError("generated_id must be a non-empty string")

    root = Path(output_root)
    if root.exists() and any(root.iterdir()):
        raise GenerationExecutionError(f"output_root already exists and is not empty: {root}")
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
    levels_by_cascade = _build_smoke_cascade(
        numpy,
        generation_config,
        plan["tile_traversal_plan"],
    )
    # The generation plan runs low-to-high, while OME-TIFF pyramid writing expects
    # the highest resolution image first followed by downsampled sub-resolutions.
    pyramid_levels = [
        levels_by_cascade["1/1"],
        levels_by_cascade["1/4"],
        levels_by_cascade["1/16"],
        levels_by_cascade["1/32"],
    ]
    plan = dict(plan)
    plan["stages"] = _complete_generation_stages(plan["stages"])
    plan["tile_traversal_plan"] = complete_tile_traversal_plan(plan["tile_traversal_plan"])

    wsi_path = root / "generated.ome.tiff"
    mask_dir = root / "generated_mask"
    try:
        pyramid_report = write_pyramid_ome_tiff(
            pyramid_levels,
            wsi_path,
            metadata={
                "GeneratedID": generated_id,
                "GeneratorBackend": SMOKE_BACKEND,
                "ProjectVersion": PROJECT_VERSION,
            },
        )
        mask_report = write_mask_array(
            _build_smoke_mask(numpy, levels_by_cascade["1/1"].shape[:2]),
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
        )
    except QCReferenceError as exc:
        raise GenerationExecutionError(str(exc)) from exc
    metadata = _metadata_payload(
        generated_id=generated_id,
        generation_config=generation_config,
        plan=plan,
        wsi_path=wsi_path,
        mask_path=mask_report["path"],
        qc_path=root / "qc.json",
        condition_packet=condition_packet,
    )
    try:
        archive = archive_sample(root, metadata, qc)
    except (ValueError, RuntimeError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    run_summary = _run_summary(
        generated_id=generated_id,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
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
) -> dict[str, Any]:
    if not isinstance(generated_id, str) or generated_id == "":
        raise GenerationExecutionError("generated_id must be a non-empty string")
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise GenerationExecutionError("batch_size must be a positive integer")

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
        pyramid_report = write_pyramid_ome_tiff(
            pyramid_levels,
            wsi_path,
            metadata={
                "GeneratedID": generated_id,
                "GeneratorBackend": TORCH_DIFFUSION_SMOKE_BACKEND,
                "ProjectVersion": PROJECT_VERSION,
            },
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
        )
    except QCReferenceError as exc:
        raise GenerationExecutionError(str(exc)) from exc

    plan = _torch_diffusion_smoke_plan(
        config=config,
        prior_manifest_path=prior_manifest_path,
        prior_id=prior["prior_id"],
        checkpoint_manifest_path=checkpoint_manifest_path,
        checkpoint_model_version=checkpoint["model_version"],
    )
    metadata = _metadata_payload(
        generated_id=generated_id,
        generation_config=config,
        plan=plan,
        wsi_path=wsi_path,
        mask_path=mask_report["path"],
        qc_path=root / "qc.json",
        generation_backend=TORCH_DIFFUSION_SMOKE_BACKEND,
        condition_packet=condition_packet,
        cascade_sample_manifests=cascade_sample_manifests,
    )
    try:
        archive = archive_sample(root, metadata, qc)
    except (ValueError, RuntimeError) as exc:
        raise GenerationExecutionError(str(exc)) from exc
    run_summary = _run_summary(
        generated_id=generated_id,
        plan=plan,
        archive=archive,
        pyramid_report=pyramid_report,
        mask_report=mask_report,
        backend=TORCH_DIFFUSION_SMOKE_BACKEND,
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

    return {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "output": {
            "wsi_path": str(wsi_path),
            "mask_path": str(mask_path),
            "qc_json_path": str(qc_path),
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
    cascade_sample_manifests: list[dict[str, Any]] | None = None,
    condition_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "schema_version": PROJECT_VERSION,
        "generated_id": generated_id,
        "backend": backend,
        "status": "completed",
        "created_at": _now_iso(),
        "plan": plan,
        "outputs": {
            **archive,
            "wsi_path": pyramid_report["path"],
            "mask_path": mask_report["path"],
        },
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
    style_seed = conditions["style_seed"]
    texture = conditions["texture_token"]
    source = conditions["source_condition"]
    anchor = conditions["structure_anchor"]
    return {
        "cascade_level": coord.get("cascade_level"),
        "tile_origin_40x": list(coord.get("tile_origin_40x", [])),
        "style_seed_value": style_seed.get("value"),
        "style_seed_source": style_seed.get("source"),
        "texture_cluster_id": texture.get("cluster_id"),
        "source_condition_enabled": bool(source.get("enabled")),
        "structure_anchor": anchor.get("value"),
    }


def _condition_packet_return(condition_packet: dict[str, Any] | None) -> dict[str, Any]:
    if condition_packet is None:
        return {}
    return {"condition_packet_path": condition_packet["path"]}


def _torch_diffusion_smoke_plan(
    config: dict[str, Any],
    prior_manifest_path: str | Path,
    prior_id: str,
    checkpoint_manifest_path: str | Path,
    checkpoint_model_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "model_family": config["model_family"],
        "prior_manifest_path": str(prior_manifest_path),
        "prior_id": prior_id,
        "checkpoint_manifest_path": str(checkpoint_manifest_path),
        "checkpoint_model_version": checkpoint_model_version,
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


def _build_smoke_cascade(
    numpy,
    generation_config: dict[str, Any],
    tile_traversal_plan: dict[str, Any],
) -> dict[str, Any]:
    seed = int(generation_config["random_seed"])
    style_seed = generation_config.get("style_seed")
    if isinstance(style_seed, int) and not isinstance(style_seed, bool):
        seed += style_seed
    anchor_offset = int(float(generation_config["structure_anchor"]) * 50)
    base_rgb = numpy.array([184, 122, 168], dtype=numpy.uint16)
    canvas_width, canvas_height = [int(value) for value in tile_traversal_plan["canvas_size_40x"]]
    tile_width, tile_height = [int(value) for value in tile_traversal_plan["model_tile_size_40x"]]
    overlap_px = int(tile_traversal_plan["overlap_px_40x"])
    tile_records = []
    for tile in tile_traversal_plan["tiles"]:
        tile_index = int(tile["tile_index"])
        tile_origin = tile["tile_origin_40x"]
        x_origin = int(tile_origin[0])
        y_origin = int(tile_origin[1])
        image = _smoke_rgb_image(
            numpy,
            tile_height,
            tile_width,
            base_rgb,
            seed + tile_index * 17 + anchor_offset + x_origin + y_origin,
        )
        tile_records.append(
            {
                "tile_origin_40x": [x_origin, y_origin],
                "image": image,
            }
        )
    canvas = blend_rgb_tiles(
        tile_records,
        canvas_size_40x=[canvas_width, canvas_height],
        overlap_px_40x=overlap_px,
    )
    shapes = {
        "1/32": (max(1, canvas_height // 32), max(1, canvas_width // 32)),
        "1/16": (max(1, canvas_height // 16), max(1, canvas_width // 16)),
        "1/4": (max(1, canvas_height // 4), max(1, canvas_width // 4)),
        "1/1": (canvas_height, canvas_width),
    }
    return {
        level: canvas if level == "1/1" else _resize_nearest(numpy, canvas, height, width)
        for level, (height, width) in shapes.items()
    }


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
