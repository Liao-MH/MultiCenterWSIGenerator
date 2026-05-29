import json
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, PROJECT_VERSION, TILE_SIZE_40X
from ..models.latent_diffusion_training import (
    LATENT_DIFFUSION_BACKEND,
    LATENT_DIFFUSION_CHECKPOINT_BACKEND,
    REAL_CONDITION_FEATURE_COUNT,
    _build_latent_denoiser,
    _build_mask_head,
    _build_tile_vae,
)
from ..models.training import ModelRunError, load_checkpoint_manifest


INTERNAL_LATENT_DIFFUSION_BACKEND_NAME = "internal_latent_diffusion_unet"
INTERNAL_LATENT_DIFFUSION_TILE_SOURCE = (
    "internal_latent_diffusion_unet_cascade_tile_streaming_manifest"
)
# Pyramid divisor by cascade level. Mirrors design §7.2 / §3 — 1/32 captures
# global tissue contour, 1/16 stabilises region boundaries, 1/4 fills mid-scale
# texture context, 1/1 emits 40x detail tiles.
_LEVEL_DIVISOR = {"1/32": 32, "1/16": 16, "1/4": 4, "1/1": 1}
_LEVEL_INDEX = {"1/1": 0, "1/4": 1, "1/16": 2, "1/32": 3}


class InternalLatentDiffusionError(RuntimeError):
    """Raised when the internal Stage5 latent diffusion backend cannot sample a pyramid."""


def materialize_internal_latent_diffusion_tile_sources(
    *,
    generation_config: dict[str, Any],
    plan: dict[str, Any],
    checkpoint_manifest_path: str | Path,
    output_root: str | Path,
    generated_id: str,
    condition_packet: dict[str, Any] | None,
    source_wsi_path: str | Path | None,
) -> dict[str, Any]:
    """Run the slide-level tile-grid latent diffusion cascade.

    Compared to the previous implementation, the cascade now samples the
    high-resolution levels (1/4 and 1/1) tile by tile against the WSI grid
    instead of materialising one canvas-sized array first. 1/32 and 1/16 are
    sampled once because their full-canvas memory footprint stays bounded
    (about 120 MB on a 100k slide) and they act as the global structure prior
    that conditions the higher-resolution tiles.
    """

    torch = _import_torch()
    numpy = _import_numpy()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    components = _load_checkpoint_components(torch, checkpoint_manifest_path)
    payload = components["payload"]

    canvas_size_40x = list(
        generation_config.get("canvas_size_40x", generation_config["tile_size_40x"])
    )
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    if canvas_width <= 0 or canvas_height <= 0:
        raise InternalLatentDiffusionError("canvas_size_40x must contain positive integers")

    condition_summary = condition_packet["summary"] if condition_packet is not None else None
    level0_mask = _load_level0_condition_mask(
        numpy=numpy,
        condition_summary=condition_summary,
        canvas_size_40x=canvas_size_40x,
    )
    source_summary = _source_condition_summary(
        generation_config=generation_config,
        canvas_size_40x=canvas_size_40x,
        source_wsi_path=source_wsi_path,
    )

    tile_width_40x, tile_height_40x = [int(value) for value in generation_config["tile_size_40x"]]
    if tile_width_40x <= 0 or tile_height_40x <= 0:
        raise InternalLatentDiffusionError("tile_size_40x must contain positive integers")

    # Each pyramid level keeps its own tile grid because the OME-TIFF writer
    # requires per-level alignment to chunk_shape. The level0 grid is the
    # canonical slide-tile grid; lower-resolution levels use a smaller grid
    # whose cells correspond to chunk_shape sized regions of that level.
    level_grids = {
        cascade_level: _level_tile_grid(
            canvas_size_40x=canvas_size_40x,
            tile_size_40x=(tile_width_40x, tile_height_40x),
            cascade_level=cascade_level,
        )
        for cascade_level in CASCADE_LEVELS
    }
    grid_y, grid_x = level_grids["1/1"]

    level_dirs = _ensure_level_dirs(root)
    full_levels = _sample_full_canvas_levels(
        torch=torch,
        numpy=numpy,
        components=components,
        generation_config=generation_config,
        condition_summary=condition_summary,
        level0_mask=level0_mask,
        source_summary=source_summary,
        canvas_size_40x=canvas_size_40x,
    )

    source_slide = _open_source_slide(source_summary)
    try:
        level_4_records = _sample_and_write_level(
            torch=torch,
            numpy=numpy,
            components=components,
            generation_config=generation_config,
            condition_summary=condition_summary,
            cascade_level="1/4",
            canvas_size_40x=canvas_size_40x,
            tile_size_40x=(tile_width_40x, tile_height_40x),
            grid=level_grids["1/4"],
            previous_full_level=full_levels["1/16"],
            previous_full_level_name="1/16",
            level0_mask=level0_mask,
            source_slide=source_slide,
            source_summary=source_summary,
            tile_dir=level_dirs[_LEVEL_INDEX["1/4"]],
            mask_dir=None,
        )
        level_1_records = _sample_and_write_level(
            torch=torch,
            numpy=numpy,
            components=components,
            generation_config=generation_config,
            condition_summary=condition_summary,
            cascade_level="1/1",
            canvas_size_40x=canvas_size_40x,
            tile_size_40x=(tile_width_40x, tile_height_40x),
            grid=level_grids["1/1"],
            previous_full_level=None,
            previous_full_level_name="1/4",
            previous_tile_dir=level_dirs[_LEVEL_INDEX["1/4"]],
            previous_grid=level_grids["1/4"],
            level0_mask=level0_mask,
            source_slide=source_slide,
            source_summary=source_summary,
            tile_dir=level_dirs[_LEVEL_INDEX["1/1"]],
            mask_dir=root / "production_mask_tiles",
        )
    finally:
        if source_slide is not None:
            source_slide.close()

    level_16_records = _split_full_level_to_tiles(
        numpy=numpy,
        full_level=full_levels["1/16"],
        cascade_level="1/16",
        canvas_size_40x=canvas_size_40x,
        tile_size_40x=(tile_width_40x, tile_height_40x),
        grid=level_grids["1/16"],
        tile_dir=level_dirs[_LEVEL_INDEX["1/16"]],
    )
    level_32_records = _split_full_level_to_tiles(
        numpy=numpy,
        full_level=full_levels["1/32"],
        cascade_level="1/32",
        canvas_size_40x=canvas_size_40x,
        tile_size_40x=(tile_width_40x, tile_height_40x),
        grid=level_grids["1/32"],
        tile_dir=level_dirs[_LEVEL_INDEX["1/32"]],
    )

    records: list[dict[str, Any]] = []
    records.extend(level_1_records)
    records.extend(level_4_records)
    records.extend(level_16_records)
    records.extend(level_32_records)

    levels_summary = _levels_summary(
        canvas_size_40x=canvas_size_40x,
        tile_size_40x=(tile_width_40x, tile_height_40x),
        level_grids=level_grids,
    )

    manifest_path = _write_internal_tile_source_manifest(
        output_root=root,
        canvas_size_40x=canvas_size_40x,
        tile_size_40x=(tile_width_40x, tile_height_40x),
        grid=(grid_y, grid_x),
        levels=levels_summary,
        records=records,
    )
    tile_source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "tile_source_manifest_path": manifest_path,
        "tile_source_manifest": tile_source_manifest,
        "summary": {
            "pipeline_role": "internal_stage5_latent_diffusion_core",
            "stages": [{"level": level, "status": "completed"} for level in CASCADE_LEVELS],
            "tile_traversal": {
                "strategy": plan["tile_traversal_plan"]["tile_traversal"],
                "blending": "ome_grid_tile_materialization",
                "slide_grid": {"rows": grid_y, "cols": grid_x},
                "per_level_inference": {
                    "1/32": "full_canvas_single_pass",
                    "1/16": "full_canvas_single_pass",
                    "1/4": "tile_grid_per_tile_inference",
                    "1/1": "tile_grid_per_tile_inference",
                },
            },
            "source_condition": source_summary,
        },
    }


def _load_checkpoint_components(torch, checkpoint_manifest_path: str | Path) -> dict[str, Any]:
    try:
        checkpoint_manifest = load_checkpoint_manifest(checkpoint_manifest_path)
    except ModelRunError as exc:
        raise InternalLatentDiffusionError(str(exc)) from exc
    if checkpoint_manifest["training_backend"] != LATENT_DIFFUSION_BACKEND:
        raise InternalLatentDiffusionError(
            "internal latent diffusion backend requires a latent_diffusion_unet checkpoint"
        )
    if (
        checkpoint_manifest["inference_contract"]["backend_type"]
        != LATENT_DIFFUSION_CHECKPOINT_BACKEND
    ):
        raise InternalLatentDiffusionError(
            "checkpoint inference backend_type is incompatible with internal latent diffusion generation"
        )

    checkpoint_path = Path(checkpoint_manifest["checkpoint_path"])
    if not checkpoint_path.exists():
        raise InternalLatentDiffusionError(f"checkpoint file does not exist: {checkpoint_path}")

    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    except Exception as exc:
        raise InternalLatentDiffusionError(f"checkpoint cannot be loaded: {checkpoint_path}") from exc

    latent_channels = int(payload["latent_channels"])
    latent_size = int(payload["latent_size"])
    diffusion = payload["diffusion"]
    diffusion_timesteps = int(diffusion["timesteps"])
    beta_start = float(diffusion["beta_start"])
    beta_end = float(diffusion["beta_end"])
    input_channels = int(payload["input_channels"])
    output_channels = int(payload["output_channels"])
    if input_channels <= 0 or output_channels != latent_channels:
        raise InternalLatentDiffusionError("checkpoint payload channel contract is incompatible")

    model_components = payload.get("model_components")
    if not isinstance(model_components, dict):
        raise InternalLatentDiffusionError("checkpoint payload missing model_components")

    vae = _build_tile_vae(torch, latent_channels).to("cpu")
    denoiser = _build_latent_denoiser(
        torch,
        input_channels=input_channels,
        output_channels=output_channels,
    ).to("cpu")
    mask_head = _build_mask_head(torch, class_count=len(MASK_CLASSES)).to("cpu")
    vae.load_state_dict(model_components["vae"])
    denoiser.load_state_dict(model_components["denoiser"])
    mask_head.load_state_dict(model_components["mask_head"])
    vae.eval()
    denoiser.eval()
    mask_head.eval()

    betas = torch.linspace(beta_start, beta_end, diffusion_timesteps, device="cpu")
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)
    return {
        "checkpoint_manifest": checkpoint_manifest,
        "payload": payload,
        "vae": vae,
        "denoiser": denoiser,
        "mask_head": mask_head,
        "latent_channels": latent_channels,
        "latent_size": latent_size,
        "diffusion_timesteps": diffusion_timesteps,
        "betas": betas,
        "alphas": alphas,
        "alpha_bars": alpha_bars,
    }


def _ensure_level_dirs(output_root: Path) -> dict[int, Path]:
    tile_root = output_root / "streaming_tiles"
    tile_root.mkdir(parents=True, exist_ok=True)
    return {index: tile_root for index in _LEVEL_INDEX.values()}


def _sample_full_canvas_levels(
    *,
    torch,
    numpy,
    components: dict[str, Any],
    generation_config: dict[str, Any],
    condition_summary: dict[str, Any] | None,
    level0_mask,
    source_summary: dict[str, Any],
    canvas_size_40x: list[int],
) -> dict[str, Any]:
    """Sample 1/32 and 1/16 once over the full canvas.

    Memory: 1/32 and 1/16 of a 100k canvas are about 30 MB and 120 MB
    respectively, which is acceptable as global structure context. The higher
    resolutions are sampled tile by tile to avoid materialising the full canvas.
    """

    sources_for_full_levels: dict[str, Any] = {}
    if source_summary["enabled"]:
        sources_for_full_levels["source_full_thumb"] = _read_source_full_canvas(
            numpy=numpy,
            source_summary=source_summary,
            canvas_size_40x=canvas_size_40x,
        )
    levels: dict[str, Any] = {}
    for cascade_level in ("1/32", "1/16"):
        target_height, target_width = _level_canvas_shape(canvas_size_40x, cascade_level)
        previous_full = levels.get("1/32") if cascade_level == "1/16" else None
        rgb = _sample_canvas_region(
            torch=torch,
            numpy=numpy,
            components=components,
            generation_config=generation_config,
            condition_summary=condition_summary,
            cascade_level=cascade_level,
            output_shape=(target_height, target_width),
            mask_region=_resize_nearest_mask(numpy, level0_mask, target_height, target_width),
            previous_scale_rgb=(
                _resize_nearest_rgb(numpy, previous_full, target_height, target_width)
                if previous_full is not None
                else None
            ),
            source_rgb_region=(
                _resize_nearest_rgb(
                    numpy,
                    sources_for_full_levels["source_full_thumb"],
                    target_height,
                    target_width,
                )
                if source_summary["enabled"]
                else None
            ),
            source_summary=source_summary,
            tile_origin_40x=(0, 0),
        )
        levels[cascade_level] = rgb
    return levels


def _level_tile_grid(
    *,
    canvas_size_40x: list[int],
    tile_size_40x: tuple[int, int],
    cascade_level: str,
) -> tuple[int, int]:
    """Compute the OME-TIFF tile grid for a cascade level.

    The OME-TIFF writer requires tiles to be aligned to ``chunk_shape`` *in the
    level frame*, not the level0 frame. Levels coarser than 1/1 therefore have
    fewer tiles than the slide grid because their pixel extent is smaller.
    """

    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    tile_width_40x, tile_height_40x = [int(value) for value in tile_size_40x]
    divisor = _LEVEL_DIVISOR[cascade_level]
    level_height = max(1, canvas_height // divisor)
    level_width = max(1, canvas_width // divisor)
    grid_y = (level_height + tile_height_40x - 1) // tile_height_40x
    grid_x = (level_width + tile_width_40x - 1) // tile_width_40x
    return grid_y, grid_x


def _sample_and_write_level(
    *,
    torch,
    numpy,
    components: dict[str, Any],
    generation_config: dict[str, Any],
    condition_summary: dict[str, Any] | None,
    cascade_level: str,
    canvas_size_40x: list[int],
    tile_size_40x: tuple[int, int],
    grid: tuple[int, int],
    previous_full_level=None,
    previous_full_level_name: str | None = None,
    previous_tile_dir: Path | None = None,
    previous_grid: tuple[int, int] | None = None,
    level0_mask=None,
    source_slide=None,
    source_summary: dict[str, Any] | None = None,
    tile_dir: Path,
    mask_dir: Path | None,
) -> list[dict[str, Any]]:
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    tile_width_40x, tile_height_40x = [int(value) for value in tile_size_40x]
    grid_y, grid_x = grid
    divisor = _LEVEL_DIVISOR[cascade_level]
    level_height = max(1, canvas_height // divisor)
    level_width = max(1, canvas_width // divisor)
    if mask_dir is not None:
        mask_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    level_index = _LEVEL_INDEX[cascade_level]
    for row in range(grid_y):
        for col in range(grid_x):
            x_origin_at_level = col * tile_width_40x
            y_origin_at_level = row * tile_height_40x
            tile_h = min(tile_height_40x, level_height - y_origin_at_level)
            tile_w = min(tile_width_40x, level_width - x_origin_at_level)
            if tile_h <= 0 or tile_w <= 0:
                continue
            # tile_origin_40x is the level0 origin used by condition features
            # so coord conditioning stays consistent across levels.
            tile_origin_40x = (x_origin_at_level * divisor, y_origin_at_level * divisor)

            mask_region = _crop_mask_region_at_level(
                numpy,
                level0_mask,
                cascade_level=cascade_level,
                canvas_size_40x=canvas_size_40x,
                target_height=tile_h,
                target_width=tile_w,
                origin_at_level=(x_origin_at_level, y_origin_at_level),
            )
            previous_scale_rgb = _previous_scale_for_tile(
                numpy=numpy,
                cascade_level=cascade_level,
                previous_full_level=previous_full_level,
                previous_full_level_name=previous_full_level_name,
                previous_tile_dir=previous_tile_dir,
                previous_grid=previous_grid,
                row=row,
                col=col,
                target_height=tile_h,
                target_width=tile_w,
                origin_at_level=(x_origin_at_level, y_origin_at_level),
                canvas_size_40x=canvas_size_40x,
            )
            source_rgb_region = _read_source_tile_region(
                numpy=numpy,
                source_slide=source_slide,
                source_summary=source_summary,
                cascade_level=cascade_level,
                tile_origin_40x=tile_origin_40x,
                target_height=tile_h,
                target_width=tile_w,
                canvas_size_40x=canvas_size_40x,
            )
            rgb = _sample_canvas_region(
                torch=torch,
                numpy=numpy,
                components=components,
                generation_config=generation_config,
                condition_summary=condition_summary,
                cascade_level=cascade_level,
                output_shape=(tile_h, tile_w),
                mask_region=mask_region,
                previous_scale_rgb=previous_scale_rgb,
                source_rgb_region=source_rgb_region,
                source_summary=source_summary or {"enabled": False},
                tile_origin_40x=tile_origin_40x,
            )
            tile_path = tile_dir / f"level-{level_index}-tile-{row:04d}-{col:04d}.npy"
            numpy.save(tile_path, rgb)
            record = {
                "level_index": level_index,
                "cascade_level": cascade_level,
                "tile_index": int(row * grid_x + col),
                "path": tile_path.relative_to(tile_dir.parent).as_posix(),
                "shape": [tile_h, tile_w, 3],
                "dtype": "uint8",
                "status": "completed",
                "tile_origin": [x_origin_at_level, y_origin_at_level],
                "write_region": [x_origin_at_level, y_origin_at_level, tile_w, tile_h],
            }
            if mask_dir is not None and cascade_level == "1/1":
                mask_tile = mask_region.astype(numpy.uint8)
                mask_path = mask_dir / f"tile-{row:04d}-{col:04d}.npy"
                numpy.save(mask_path, mask_tile)
                record["mask_path"] = mask_path.relative_to(tile_dir.parent).as_posix()
                record["mask_shape"] = [tile_h, tile_w]
                record["mask_dtype"] = "uint8"
            records.append(record)
    return records


def _split_full_level_to_tiles(
    *,
    numpy,
    full_level,
    cascade_level: str,
    canvas_size_40x: list[int],
    tile_size_40x: tuple[int, int],
    grid: tuple[int, int],
    tile_dir: Path,
) -> list[dict[str, Any]]:
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    tile_width_40x, tile_height_40x = [int(value) for value in tile_size_40x]
    grid_y, grid_x = grid
    divisor = _LEVEL_DIVISOR[cascade_level]
    level_height = max(1, canvas_height // divisor)
    level_width = max(1, canvas_width // divisor)
    array = numpy.asarray(full_level, dtype=numpy.uint8)
    if array.ndim != 3 or array.shape[2] != 3:
        raise InternalLatentDiffusionError("internal latent diffusion levels must be RGB uint8 arrays")
    level_index = _LEVEL_INDEX[cascade_level]
    records: list[dict[str, Any]] = []
    for row in range(grid_y):
        for col in range(grid_x):
            x_origin_at_level = col * tile_width_40x
            y_origin_at_level = row * tile_height_40x
            tile_h = min(tile_height_40x, level_height - y_origin_at_level)
            tile_w = min(tile_width_40x, level_width - x_origin_at_level)
            if tile_h <= 0 or tile_w <= 0:
                continue
            tile = array[
                y_origin_at_level : y_origin_at_level + tile_h,
                x_origin_at_level : x_origin_at_level + tile_w,
                :,
            ]
            tile_path = tile_dir / f"level-{level_index}-tile-{row:04d}-{col:04d}.npy"
            numpy.save(tile_path, tile)
            records.append(
                {
                    "level_index": level_index,
                    "cascade_level": cascade_level,
                    "tile_index": int(row * grid_x + col),
                    "path": tile_path.relative_to(tile_dir.parent).as_posix(),
                    "shape": [int(tile_h), int(tile_w), 3],
                    "dtype": "uint8",
                    "status": "completed",
                    "tile_origin": [int(x_origin_at_level), int(y_origin_at_level)],
                    "write_region": [
                        int(x_origin_at_level),
                        int(y_origin_at_level),
                        int(tile_w),
                        int(tile_h),
                    ],
                }
            )
    return records


def _sample_canvas_region(
    *,
    torch,
    numpy,
    components: dict[str, Any],
    generation_config: dict[str, Any],
    condition_summary: dict[str, Any] | None,
    cascade_level: str,
    output_shape: tuple[int, int],
    mask_region,
    previous_scale_rgb,
    source_rgb_region,
    source_summary: dict[str, Any],
    tile_origin_40x: tuple[int, int],
):
    latent_size = components["latent_size"]
    latent_channels = components["latent_channels"]
    diffusion_timesteps = components["diffusion_timesteps"]
    sample_steps = min(int(generation_config["sample_steps"]), diffusion_timesteps)

    mask_tensor = _mask_one_hot_at_latent(torch, numpy, mask_region, latent_size)
    previous_tensor = _previous_scale_to_latent(torch, numpy, previous_scale_rgb, latent_size)
    source_tensor = _source_rgb_to_latent(
        torch, numpy, source_rgb_region, source_summary, latent_size
    )
    condition_features = _condition_feature_channels(
        torch=torch,
        payload=components["payload"],
        condition_summary=condition_summary,
        generation_config=generation_config,
        tile_origin_40x=list(tile_origin_40x),
        cascade_level=cascade_level,
        latent_size=latent_size,
    )

    sample = torch.randn((1, latent_channels, latent_size, latent_size), device="cpu")
    timestep_schedule = (
        torch.linspace(diffusion_timesteps - 1, 0, sample_steps, device="cpu")
        .round()
        .to(dtype=torch.long)
    )
    betas = components["betas"]
    alphas = components["alphas"]
    alpha_bars = components["alpha_bars"]
    denoiser = components["denoiser"]
    vae = components["vae"]
    mask_head = components["mask_head"]
    with torch.no_grad():
        for timestep in timestep_schedule:
            timestep_index = int(timestep.detach().cpu().item())
            time_channel = _time_channel(torch, timestep_index, diffusion_timesteps, latent_size)
            predicted_noise = denoiser(
                torch.cat(
                    [
                        sample,
                        previous_tensor,
                        source_tensor,
                        mask_tensor,
                        time_channel,
                        condition_features,
                    ],
                    dim=1,
                )
            )
            alpha_t = alphas[timestep_index]
            alpha_bar_t = alpha_bars[timestep_index]
            beta_t = betas[timestep_index]
            sample = sample - (beta_t / torch.sqrt(1.0 - alpha_bar_t)) * predicted_noise
            sample = sample / torch.sqrt(alpha_t)
            if timestep_index > 0:
                sample = sample + torch.sqrt(beta_t) * torch.randn_like(sample)
        decoded = vae.decode(sample).clamp(0.0, 1.0)
        # Keep the semantic head in the path so Stage5 uses the same learned
        # structure channels as Stage4, even though the current artifact output
        # still writes the explicit conditioned mask for alignment.
        _ = mask_head(decoded)
    rgb_latent = (
        decoded.permute(0, 2, 3, 1).detach().cpu().numpy()[0] * 255.0
    ).round().clip(0, 255).astype(numpy.uint8)
    target_height, target_width = output_shape
    return _resize_nearest_rgb(numpy, rgb_latent, target_height, target_width)


def _previous_scale_for_tile(
    *,
    numpy,
    cascade_level: str,
    previous_full_level,
    previous_full_level_name: str | None,
    previous_tile_dir: Path | None,
    previous_grid: tuple[int, int] | None,
    row: int,
    col: int,
    target_height: int,
    target_width: int,
    origin_at_level: tuple[int, int],
    canvas_size_40x: list[int],
):
    if cascade_level == "1/4":
        if previous_full_level is None:
            return None
        return _crop_full_level_to_target(
            numpy=numpy,
            full_level=previous_full_level,
            full_level_name=previous_full_level_name,
            current_level=cascade_level,
            origin_at_current_level=origin_at_level,
            target_height=target_height,
            target_width=target_width,
            canvas_size_40x=canvas_size_40x,
        )
    if cascade_level == "1/1":
        if previous_tile_dir is None or previous_grid is None:
            return None
        # The 1/4 grid is coarser than the 1/1 grid: each 1/4 tile covers
        # multiple 1/1 tiles. Map (row, col) on the 1/1 grid to the 1/4 tile
        # that owns its level-0 origin and crop the relevant sub-region.
        x_origin_level0 = int(origin_at_level[0])
        y_origin_level0 = int(origin_at_level[1])
        previous_divisor = _LEVEL_DIVISOR["1/4"]
        x_origin_prev = x_origin_level0 // previous_divisor
        y_origin_prev = y_origin_level0 // previous_divisor
        prev_tile_w = max(1, target_width // previous_divisor)
        prev_tile_h = max(1, target_height // previous_divisor)
        prev_grid_y, prev_grid_x = previous_grid
        # Tiles on the 1/4 grid are addressed by their own row/col, also
        # using the chunk-aligned tile size (target_width, target_height in
        # the 40x frame == 512 pixels in level frame at all levels).
        prev_row = y_origin_prev // target_height
        prev_col = x_origin_prev // target_width
        prev_row = min(prev_row, prev_grid_y - 1)
        prev_col = min(prev_col, prev_grid_x - 1)
        previous_index = _LEVEL_INDEX["1/4"]
        previous_path = (
            previous_tile_dir
            / f"level-{previous_index}-tile-{prev_row:04d}-{prev_col:04d}.npy"
        )
        if not previous_path.exists():
            raise InternalLatentDiffusionError(
                f"previous-scale tile missing for 1/1 sampling: {previous_path}"
            )
        previous_tile = numpy.load(previous_path, allow_pickle=False)
        # Crop the sub-region of the 1/4 tile that corresponds to the current
        # 1/1 tile's level0 footprint, then resample to target shape.
        sub_x = (x_origin_prev) % target_width
        sub_y = (y_origin_prev) % target_height
        sub_x_end = min(previous_tile.shape[1], sub_x + prev_tile_w)
        sub_y_end = min(previous_tile.shape[0], sub_y + prev_tile_h)
        crop = previous_tile[sub_y:sub_y_end, sub_x:sub_x_end, :]
        if crop.shape[0] == 0 or crop.shape[1] == 0:
            crop = previous_tile
        return _resize_nearest_rgb(numpy, crop, target_height, target_width)
    return None


def _crop_full_level_to_target(
    *,
    numpy,
    full_level,
    full_level_name: str | None,
    current_level: str,
    origin_at_current_level: tuple[int, int],
    target_height: int,
    target_width: int,
    canvas_size_40x: list[int],
):
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    if full_level_name is None:
        return None
    full_divisor = _LEVEL_DIVISOR[full_level_name]
    current_divisor = _LEVEL_DIVISOR[current_level]
    scale = current_divisor / full_divisor  # < 1 because full_level is coarser
    full_height = max(1, canvas_height // full_divisor)
    full_width = max(1, canvas_width // full_divisor)
    x_origin_full = int(origin_at_current_level[0] * scale)
    y_origin_full = int(origin_at_current_level[1] * scale)
    crop_w = max(1, int(target_width * scale))
    crop_h = max(1, int(target_height * scale))
    x_end = min(full_width, x_origin_full + crop_w)
    y_end = min(full_height, y_origin_full + crop_h)
    crop = full_level[y_origin_full:y_end, x_origin_full:x_end, :]
    return _resize_nearest_rgb(numpy, crop, target_height, target_width)


def _crop_mask_region_at_level(
    numpy,
    level0_mask,
    *,
    cascade_level: str,
    canvas_size_40x: list[int],
    target_height: int,
    target_width: int,
    origin_at_level: tuple[int, int],
):
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    divisor = _LEVEL_DIVISOR[cascade_level]
    # origin_at_level is expressed in the level frame; convert it back to the
    # level0 frame so the mask crop uses the same source-of-truth coordinate
    # system as the WSI itself.
    x_origin_level0 = int(origin_at_level[0]) * divisor
    y_origin_level0 = int(origin_at_level[1]) * divisor
    crop_w_level0 = int(target_width) * divisor
    crop_h_level0 = int(target_height) * divisor
    x_end = min(canvas_width, x_origin_level0 + crop_w_level0)
    y_end = min(canvas_height, y_origin_level0 + crop_h_level0)
    crop = level0_mask[y_origin_level0:y_end, x_origin_level0:x_end]
    if crop.shape[0] == 0 or crop.shape[1] == 0:
        return numpy.zeros((target_height, target_width), dtype=numpy.uint8)
    return _resize_nearest_mask(numpy, crop.astype(numpy.uint8), target_height, target_width)


def _read_source_tile_region(
    *,
    numpy,
    source_slide,
    source_summary: dict[str, Any] | None,
    cascade_level: str,
    tile_origin_40x: tuple[int, int],
    target_height: int,
    target_width: int,
    canvas_size_40x: list[int],
):
    """Read the source RGB region matching this tile's level0 footprint.

    ``tile_origin_40x`` and the level0 footprint width/height are derived from
    the level frame so the source crop covers the same physical area as the
    tile being generated. The returned RGB is resized to ``target_height /
    target_width`` so it stacks cleanly with the model latent grid.
    """

    if source_summary is None or not source_summary.get("enabled"):
        return None
    if source_slide is None:
        return None
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    divisor = _LEVEL_DIVISOR[cascade_level]
    x_origin = max(0, min(canvas_width, int(tile_origin_40x[0])))
    y_origin = max(0, min(canvas_height, int(tile_origin_40x[1])))
    region_width = min(int(target_width) * divisor, canvas_width - x_origin)
    region_height = min(int(target_height) * divisor, canvas_height - y_origin)
    if region_width <= 0 or region_height <= 0:
        return None
    rgb = source_slide.read_region_rgb(
        x_origin=x_origin,
        y_origin=y_origin,
        width=region_width,
        height=region_height,
    )
    return _resize_nearest_rgb(numpy, rgb, target_height, target_width)


def _read_source_full_canvas(
    *,
    numpy,
    source_summary: dict[str, Any],
    canvas_size_40x: list[int],
):
    if not source_summary["enabled"]:
        return None
    path = Path(source_summary["source_wsi_path"])
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    if not path.exists():
        raise InternalLatentDiffusionError(f"source-conditioned WSI does not exist: {path}")
    return _SourceSlideHandle(path).read_region_rgb(0, 0, canvas_width, canvas_height)


class _SourceSlideHandle:
    """Lazy wrapper that reads source RGB tiles from PNG/TIFF or OpenSlide.

    The handle is constructed once at the start of generation so the tile loop
    does not reopen the slide every time a level-0 region is requested.
    """

    def __init__(self, path: Path):
        self.path = path
        self._slide = None
        self._image = None
        suffix = path.suffix.lower()
        if suffix in {".png", ".tif", ".tiff", ".jpg", ".jpeg"}:
            from PIL import Image

            self._image = Image.open(path).convert("RGB")
        else:
            try:
                import openslide
            except ImportError as exc:  # pragma: no cover
                raise InternalLatentDiffusionError(
                    "openslide is required for source-conditioned WSI generation"
                ) from exc
            self._slide = openslide.OpenSlide(str(path))

    def read_region_rgb(self, x_origin: int, y_origin: int, width: int, height: int):
        numpy = _import_numpy()
        if self._image is not None:
            crop = self._image.crop(
                (
                    x_origin,
                    y_origin,
                    x_origin + width,
                    y_origin + height,
                )
            )
            return numpy.asarray(crop, dtype=numpy.uint8)
        try:
            region = self._slide.read_region(
                (x_origin, y_origin), 0, (width, height)
            ).convert("RGB")
        except Exception as exc:
            raise InternalLatentDiffusionError(
                f"failed to read source-conditioned RGB from {self.path}"
            ) from exc
        return numpy.asarray(region, dtype=numpy.uint8)

    def close(self) -> None:
        if self._slide is not None:
            try:
                self._slide.close()
            except Exception:  # pragma: no cover
                pass


def _open_source_slide(source_summary: dict[str, Any]) -> _SourceSlideHandle | None:
    if not source_summary["enabled"]:
        return None
    return _SourceSlideHandle(Path(source_summary["source_wsi_path"]))


def _level_canvas_shape(canvas_size_40x: list[int], cascade_level: str) -> tuple[int, int]:
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    divisor = _LEVEL_DIVISOR[cascade_level]
    return max(1, canvas_height // divisor), max(1, canvas_width // divisor)


def _load_level0_condition_mask(
    *,
    numpy,
    condition_summary: dict[str, Any] | None,
    canvas_size_40x: list[int],
):
    if not isinstance(condition_summary, dict):
        raise InternalLatentDiffusionError(
            "internal latent diffusion generation requires a condition packet"
        )
    sampled_layout_mask = condition_summary.get("sampled_layout_mask")
    if not isinstance(sampled_layout_mask, dict):
        raise InternalLatentDiffusionError(
            "internal latent diffusion generation requires condition packet sampled_layout_mask"
        )
    mask_path = Path(sampled_layout_mask["mask_path"])
    if not mask_path.exists():
        raise InternalLatentDiffusionError(f"sampled layout mask does not exist: {mask_path}")
    try:
        mask = numpy.load(mask_path, allow_pickle=False)
    except Exception as exc:
        raise InternalLatentDiffusionError(f"sampled layout mask cannot be loaded: {mask_path}") from exc
    if mask.ndim != 2:
        raise InternalLatentDiffusionError("sampled layout mask must be 2D")
    invalid = [int(value) for value in numpy.unique(mask).tolist() if int(value) >= len(MASK_CLASSES)]
    if invalid:
        raise InternalLatentDiffusionError(f"sampled layout mask contains invalid class id {invalid[0]}")
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    if tuple(mask.shape) != (canvas_height, canvas_width):
        mask = _resize_nearest_mask(numpy, mask.astype(numpy.uint8), canvas_height, canvas_width)
    return mask.astype(numpy.uint8)


def _source_condition_summary(
    *,
    generation_config: dict[str, Any],
    canvas_size_40x: list[int],
    source_wsi_path: str | Path | None,
) -> dict[str, Any]:
    anchor = float(generation_config["structure_anchor"])
    source_wsi_id = generation_config.get("source_wsi_id")
    enabled = (
        anchor > 0.3
        and isinstance(source_wsi_id, str)
        and source_wsi_id != ""
    )
    if not enabled:
        return {
            "enabled": False,
            "mode": "de_novo_generation",
            "source_wsi_id": None,
            "source_wsi_path": None,
            "strength": 0.0,
        }
    if source_wsi_path is None:
        raise InternalLatentDiffusionError(
            "source-conditioned generation requires a resolvable source_wsi_path"
        )
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    return {
        "enabled": True,
        "mode": "source_tile_rgb_model_condition_per_tile",
        "source_wsi_id": source_wsi_id,
        "source_wsi_path": str(source_wsi_path),
        "strength": anchor,
        "source_region": [0, 0, canvas_width, canvas_height],
    }


def _mask_one_hot_at_latent(torch, numpy, mask_region, latent_size: int):
    mask = numpy.ascontiguousarray(mask_region.astype(numpy.int64)).copy()
    mask_tensor = torch.as_tensor(mask, dtype=torch.long).unsqueeze(0)
    mask_tensor = (
        torch.nn.functional.interpolate(
            mask_tensor.unsqueeze(1).to(dtype=torch.float32),
            size=(latent_size, latent_size),
            mode="nearest",
        )
        .squeeze(1)
        .to(dtype=torch.long)
    )
    one_hot = torch.nn.functional.one_hot(mask_tensor, num_classes=len(MASK_CLASSES))
    return one_hot.permute(0, 3, 1, 2).to(dtype=torch.float32)


def _previous_scale_to_latent(torch, numpy, previous_rgb, latent_size: int):
    if previous_rgb is None:
        return torch.zeros((1, 3, latent_size, latent_size), dtype=torch.float32)
    contiguous = numpy.ascontiguousarray(previous_rgb).copy()
    tensor = torch.as_tensor(contiguous, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0
    return torch.nn.functional.interpolate(
        tensor,
        size=(latent_size, latent_size),
        mode="bilinear",
        align_corners=False,
    )


def _source_rgb_to_latent(torch, numpy, source_rgb_region, source_summary, latent_size: int):
    if source_rgb_region is None:
        return torch.zeros((1, 3, latent_size, latent_size), dtype=torch.float32)
    contiguous = numpy.ascontiguousarray(source_rgb_region).copy()
    tensor = (
        torch.as_tensor(contiguous, dtype=torch.float32)
        .permute(2, 0, 1)
        .unsqueeze(0)
        / 255.0
    )
    scaled = torch.nn.functional.interpolate(
        tensor,
        size=(latent_size, latent_size),
        mode="bilinear",
        align_corners=False,
    )
    strength = float(source_summary.get("strength", 0.0)) if source_summary else 0.0
    return scaled * strength


def _condition_feature_channels(
    *,
    torch,
    payload: dict[str, Any],
    condition_summary: dict[str, Any] | None,
    generation_config: dict[str, Any],
    tile_origin_40x: list[int],
    cascade_level: str,
    latent_size: int,
):
    checkpoint_reference = payload.get("conditioning_reference", {})
    style_target = checkpoint_reference.get("style_target", {})
    texture_target = checkpoint_reference.get("texture_target", {})
    sampled_style = condition_summary.get("sampled_style_policy") if isinstance(condition_summary, dict) else None
    sampled_texture = condition_summary.get("sampled_texture_policy") if isinstance(condition_summary, dict) else None
    if isinstance(sampled_style, dict):
        mean_rgb = sampled_style["selected_style"]["mean_rgb"]
        style_means = [_clamp01(float(value) / 255.0) for value in mean_rgb]
    else:
        style_means = [
            float(value)
            for value in style_target.get("mean_rgb_normalized", [0.5, 0.5, 0.5])[:3]
        ]
        while len(style_means) < 3:
            style_means.append(0.5)
    if isinstance(sampled_texture, dict):
        cluster_id = int(sampled_texture["cluster_id"])
    else:
        cluster_ids = texture_target.get("cluster_ids", [0])
        cluster_id = int(cluster_ids[0]) if cluster_ids else 0
    cluster_count = max(1, int(texture_target.get("cluster_count", max(cluster_id + 1, 1))))
    vector = style_means[:3] + [
        _clamp01(float(cluster_id) / float(max(cluster_count - 1, 1))),
        _clamp01(float(tile_origin_40x[0]) / 100000.0),
        _clamp01(float(tile_origin_40x[1]) / 100000.0),
        {
            "1/32": 0.0,
            "1/16": 0.333333,
            "1/4": 0.666667,
            "1/1": 1.0,
        }[cascade_level],
        1.0 if float(generation_config["structure_anchor"]) > 0.3 else 0.0,
        float(generation_config["structure_anchor"]),
    ]
    if len(vector) != REAL_CONDITION_FEATURE_COUNT:
        raise InternalLatentDiffusionError("condition feature vector size is incompatible with checkpoint")
    tensor = torch.tensor(vector, dtype=torch.float32).view(1, REAL_CONDITION_FEATURE_COUNT, 1, 1)
    return tensor.expand(1, REAL_CONDITION_FEATURE_COUNT, latent_size, latent_size)


def _time_channel(torch, timestep_index: int, diffusion_timesteps: int, latent_size: int):
    denominator = float(max(diffusion_timesteps - 1, 1))
    value = float(timestep_index) / denominator
    return torch.full((1, 1, latent_size, latent_size), value, dtype=torch.float32)


def _levels_summary(
    *,
    canvas_size_40x: list[int],
    tile_size_40x: tuple[int, int],
    level_grids: dict[str, tuple[int, int]],
) -> list[dict[str, Any]]:
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    levels: list[dict[str, Any]] = []
    for cascade_level in ("1/1", "1/4", "1/16", "1/32"):
        divisor = _LEVEL_DIVISOR[cascade_level]
        level_height = max(1, canvas_height // divisor)
        level_width = max(1, canvas_width // divisor)
        grid_y, grid_x = level_grids[cascade_level]
        levels.append(
            {
                "level_index": _LEVEL_INDEX[cascade_level],
                "cascade_level": cascade_level,
                "shape": [level_height, level_width, 3],
                "tile_grid": [grid_y, grid_x],
                "expected_tile_count": int(grid_y * grid_x),
            }
        )
    return levels


def _write_internal_tile_source_manifest(
    *,
    output_root: Path,
    canvas_size_40x: list[int],
    tile_size_40x: tuple[int, int],
    grid: tuple[int, int],
    levels: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> Path:
    canvas_width, canvas_height = [int(value) for value in canvas_size_40x]
    tile_width_40x, tile_height_40x = [int(value) for value in tile_size_40x]
    grid_y, grid_x = grid
    manifest_path = output_root / "tile_source_manifest.streaming.json"
    payload = {
        "schema_version": PROJECT_VERSION,
        "manifest_type": "disk_npy_tile_source_manifest",
        "source": INTERNAL_LATENT_DIFFUSION_TILE_SOURCE,
        "canvas_size_40x": [canvas_width, canvas_height],
        "tile_size_40x": [tile_width_40x, tile_height_40x],
        "chunk_shape": [tile_height_40x, tile_width_40x],
        "tile_count": len(records),
        "expected_tile_count": len(records),
        "tile_grid": {"rows": grid_y, "cols": grid_x},
        "levels": levels,
        "tiles": records,
        "generation_status": "completed",
        "completed_tile_count": len(records),
        "pending_tile_count": 0,
        "failed_tile_count": 0,
        "resume_index": len(records),
        "next_tile_index": None,
        "limitations": [
            "stage4_latent_diffusion_checkpoint_not_full_stage5_production_validation",
            "sampled_layout_mask_required_for_current_internal_generation_path",
            "ome_tiff_file_resume_not_supported",
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _resize_nearest_mask(numpy, array, height: int, width: int):
    if array.shape[0] == height and array.shape[1] == width:
        return array
    y_index = (numpy.arange(height) * array.shape[0] / height).astype(numpy.int64)
    x_index = (numpy.arange(width) * array.shape[1] / width).astype(numpy.int64)
    return array[y_index[:, None], x_index[None, :]]


def _resize_nearest_rgb(numpy, array, height: int, width: int):
    if array.shape[0] == height and array.shape[1] == width:
        return array
    y_index = (numpy.arange(height) * array.shape[0] / height).astype(numpy.int64)
    x_index = (numpy.arange(width) * array.shape[1] / width).astype(numpy.int64)
    return array[y_index[:, None], x_index[None, :], :]


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _import_torch():
    try:
        import torch
    except ImportError as exc:  # pragma: no cover
        raise InternalLatentDiffusionError("PyTorch is required for internal latent diffusion generation") from exc
    return torch


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:  # pragma: no cover
        raise InternalLatentDiffusionError("numpy is required for internal latent diffusion generation") from exc
    return numpy
