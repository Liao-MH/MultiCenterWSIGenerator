import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import (
    ANCHOR_PRESETS,
    CASCADE_LEVELS,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    MODEL_FAMILY,
    PROJECT_VERSION,
    TILE_SIZE_40X,
)
from ..priors.artifacts import PriorArtifactError, load_prior_manifest
from .training import (
    ModelRunError,
    PRODUCTION_TARGET_TYPE,
    REQUIRED_INFERENCE_CONDITION_INPUTS,
    create_training_run,
    load_checkpoint_manifest,
)
from .training_batch import TrainingBatchError, load_training_batch, training_batch_summary


LATENT_DIFFUSION_BACKEND = "latent_diffusion_unet"
LATENT_DIFFUSION_CHECKPOINT_BACKEND = "latent_diffusion_unet_checkpoint"
DEFAULT_RUNTIME = {
    "batch_size": None,
    "split": "train",
    "device": "cpu",
    "latent_channels": 4,
    "latent_size": 32,
    "vae_epochs": 1,
    "image_generator_epochs": 1,
    "wsi_consistency_epochs": 1,
    "learning_rate": 1e-3,
    "diffusion_timesteps": 8,
    "beta_start": 1e-4,
    "beta_end": 0.02,
}
ANCHOR_TRAINING_PRESETS = (
    {"name": "low", "value": 0.05, "source_enabled": False},
    {"name": "medium", "value": 0.50, "source_enabled": True},
    {"name": "high", "value": 0.95, "source_enabled": True},
)
PREVIOUS_SCALE_RATIO = {
    "1/32": None,
    "1/16": 2,
    "1/4": 4,
    "1/1": 4,
}
REAL_CONDITION_FEATURES = (
    {
        "name": "style_mean_r_norm",
        "source": "style_prior.rgb_statistics.mean_rgb_normalized[0]",
    },
    {
        "name": "style_mean_g_norm",
        "source": "style_prior.rgb_statistics.mean_rgb_normalized[1]",
    },
    {
        "name": "style_mean_b_norm",
        "source": "style_prior.rgb_statistics.mean_rgb_normalized[2]",
    },
    {
        "name": "texture_cluster_id_norm",
        "source": "texture_prior.texture_prototypes[].cluster_id / cluster_count",
    },
    {
        "name": "tile_origin_x_40x_norm",
        "source": "training_index.tile.x / 100000",
    },
    {
        "name": "tile_origin_y_40x_norm",
        "source": "training_index.tile.y / 100000",
    },
    {
        "name": "cascade_level_scale",
        "source": "training_index.cascade_level",
    },
    {
        "name": "source_condition_enabled",
        "source": "anchor_preset.source_enabled",
    },
    {
        "name": "structure_anchor",
        "source": "anchor_preset.value",
    },
)
REAL_CONDITION_FEATURE_NAMES = [item["name"] for item in REAL_CONDITION_FEATURES]
REAL_CONDITION_FEATURE_COUNT = len(REAL_CONDITION_FEATURES)
CASCADE_LEVEL_SCALE = {
    "1/32": 0.0,
    "1/16": 0.333333,
    "1/4": 0.666667,
    "1/1": 1.0,
}
DENOISER_BASE_CHANNELS = 32
DENOISER_BOTTLENECK_CHANNELS = 64
SOURCE_CONDITION_CHANNELS = 3
PREVIOUS_SCALE_CHANNELS = 3
MASK_CHANNELS = len(MASK_CLASSES)
TIME_CHANNELS = 1


class LatentDiffusionTrainingError(ValueError):
    """Raised when the real Stage4 latent diffusion backend cannot execute safely."""


def train_latent_diffusion_unet(config: dict[str, Any]) -> dict[str, Any]:
    try:
        initialized_run = create_training_run(config)
    except ModelRunError as exc:
        raise LatentDiffusionTrainingError(str(exc)) from exc

    runtime = _validate_runtime_config(config.get("runtime"))
    torch = _import_torch()
    device_obj = _resolve_device(torch, runtime["device"])
    output_dir = Path(initialized_run["output_dir"])

    try:
        prior_manifest = load_prior_manifest(config["prior_manifest_path"], verify_files=True)
        conditioning_reference = _load_conditioning_reference(prior_manifest)
        level_batches = _load_level_batches(
            training_index_path=config["training_index_path"],
            records_by_level=initialized_run["dataset_contract"]["records_by_level"],
            split=runtime["split"],
            batch_size_limit=runtime["batch_size"],
        )
    except (PriorArtifactError, TrainingBatchError, ModelRunError) as exc:
        raise LatentDiffusionTrainingError(str(exc)) from exc

    torch.manual_seed(initialized_run["random_seed"])

    vae = _build_tile_vae(torch, runtime["latent_channels"]).to(device_obj)
    denoiser_input_channels = (
        runtime["latent_channels"]
        + PREVIOUS_SCALE_CHANNELS
        + SOURCE_CONDITION_CHANNELS
        + MASK_CHANNELS
        + TIME_CHANNELS
        + REAL_CONDITION_FEATURE_COUNT
    )
    denoiser = _build_latent_denoiser(
        torch,
        input_channels=denoiser_input_channels,
        output_channels=runtime["latent_channels"],
    ).to(device_obj)
    mask_head = _build_mask_head(torch, class_count=len(MASK_CLASSES)).to(device_obj)
    optimizer = torch.optim.AdamW(
        list(vae.parameters()) + list(denoiser.parameters()) + list(mask_head.parameters()),
        lr=runtime["learning_rate"],
    )
    betas = torch.linspace(
        runtime["beta_start"],
        runtime["beta_end"],
        runtime["diffusion_timesteps"],
        device=device_obj,
    )
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)

    training_log_path = output_dir / "training_log.jsonl"
    checkpoint_path = output_dir / "model.pt"
    checkpoint_manifest_path = Path(initialized_run["checkpoint_manifest_path"])
    training_plan_path = Path(initialized_run["training_plan_path"])
    stage_execution = {
        "stages": [],
        "completed_stages": [],
    }
    anchor_counter = Counter()

    with training_log_path.open("w", encoding="utf-8") as log_handle:
        _write_stage_log(
            log_handle,
            {
                "schema_version": PROJECT_VERSION,
                "stage": "prior_ready",
                "status": "completed",
                "backend": LATENT_DIFFUSION_BACKEND,
                "prior_id": prior_manifest["prior_id"],
                "style_reference_source": conditioning_reference["style"]["source_path"],
                "texture_reference_source": conditioning_reference["texture"]["source_path"],
            },
        )
        stage_execution["stages"].append(
            {
                "stage": "prior_ready",
                "status": "completed",
                "epochs_completed": 0,
                "loss_history": [],
            }
        )
        stage_execution["completed_stages"].append("prior_ready")

        vae_history = _run_vae_stage(
            torch=torch,
            vae=vae,
            optimizer=optimizer,
            level_batches=level_batches,
            runtime=runtime,
            device_obj=device_obj,
            log_handle=log_handle,
        )
        stage_execution["stages"].append(
            {
                "stage": "image_generator",
                "status": "completed",
                "epochs_completed": runtime["image_generator_epochs"],
                "vae_epochs_completed": runtime["vae_epochs"],
                "loss_history": deepcopy(vae_history["stage_loss_history"]),
                "last_epoch_loss": vae_history["stage_loss_history"][-1],
            }
        )
        stage_execution["completed_stages"].append("image_generator")

        image_generator_history = _run_diffusion_stage(
            torch=torch,
            vae=vae,
            denoiser=denoiser,
            mask_head=mask_head,
            optimizer=optimizer,
            level_batches=level_batches,
            conditioning_reference=conditioning_reference,
            runtime=runtime,
            device_obj=device_obj,
            alpha_bars=alpha_bars,
            stage_name="image_generator",
            epoch_count=runtime["image_generator_epochs"],
            objective_weights=config["training_objective_contract"]["loss_weights"],
            anchor_counter=anchor_counter,
            log_handle=log_handle,
            include_consistency_losses=False,
        )
        stage_execution["stages"][-1].update(
            {
                "loss_history": deepcopy(image_generator_history["stage_loss_history"]),
                "last_epoch_loss": image_generator_history["stage_loss_history"][-1],
            }
        )

        wsi_history = _run_diffusion_stage(
            torch=torch,
            vae=vae,
            denoiser=denoiser,
            mask_head=mask_head,
            optimizer=optimizer,
            level_batches=level_batches,
            conditioning_reference=conditioning_reference,
            runtime=runtime,
            device_obj=device_obj,
            alpha_bars=alpha_bars,
            stage_name="wsi_consistency",
            epoch_count=runtime["wsi_consistency_epochs"],
            objective_weights=config["training_objective_contract"]["loss_weights"],
            anchor_counter=anchor_counter,
            log_handle=log_handle,
            include_consistency_losses=True,
        )
        stage_execution["stages"].append(
            {
                "stage": "wsi_consistency",
                "status": "completed",
                "epochs_completed": runtime["wsi_consistency_epochs"],
                "loss_history": deepcopy(wsi_history["stage_loss_history"]),
                "last_epoch_loss": wsi_history["stage_loss_history"][-1],
            }
        )
        stage_execution["completed_stages"].append("wsi_consistency")

    checkpoint_payload = {
        "schema_version": PROJECT_VERSION,
        "backend": LATENT_DIFFUSION_BACKEND,
        "model_family": MODEL_FAMILY,
        "target_type": PRODUCTION_TARGET_TYPE,
        "model_components": {
            "vae": vae.state_dict(),
            "denoiser": denoiser.state_dict(),
            "mask_head": mask_head.state_dict(),
        },
        "latent_channels": runtime["latent_channels"],
        "latent_size": runtime["latent_size"],
        "input_channels": denoiser_input_channels,
        "output_channels": runtime["latent_channels"],
        "diffusion": {
            "scheduler": "linear_ddpm",
            "timesteps": runtime["diffusion_timesteps"],
            "beta_start": runtime["beta_start"],
            "beta_end": runtime["beta_end"],
            "latent_source": "trained_tile_vae",
            "latent_batch_shape": _latent_batch_shape(level_batches, runtime["latent_channels"], runtime["latent_size"]),
        },
        "condition_feature_schema": condition_feature_schema(),
        "cross_scale_condition_schema": cross_scale_condition_schema(),
        "source_condition_schema": source_condition_schema(),
        "denoiser_architecture": denoiser_architecture(
            input_channels=denoiser_input_channels,
            output_channels=runtime["latent_channels"],
        ),
        "stage_execution": deepcopy(stage_execution),
        "anchor_training": _anchor_training_summary(anchor_counter),
        "conditioning_reference": {
            "style_target": deepcopy(conditioning_reference["style"]["summary"]),
            "texture_target": deepcopy(conditioning_reference["texture"]["summary"]),
        },
    }
    torch.save(checkpoint_payload, checkpoint_path)
    checkpoint_hash = _sha256_file(checkpoint_path)

    checkpoint_manifest = _trained_checkpoint_manifest(
        config=config,
        initialized_run=initialized_run,
        runtime=runtime,
        prior_manifest=prior_manifest,
        checkpoint_path=checkpoint_path,
        checkpoint_hash=checkpoint_hash,
        training_log_path=training_log_path,
        checkpoint_payload=checkpoint_payload,
        stage_execution=stage_execution,
        anchor_counter=anchor_counter,
        conditioning_reference=conditioning_reference,
        torch_version=torch.__version__,
        level_batches=level_batches,
    )
    checkpoint_manifest_path.write_text(
        json.dumps(checkpoint_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    load_checkpoint_manifest(checkpoint_manifest_path)

    training_plan = json.loads(training_plan_path.read_text(encoding="utf-8"))
    training_plan["implementation_status"] = "executed_minimal_real_training_loop"
    for stage in training_plan["stages"]:
        stage["status"] = "completed"
    training_plan["training_log_path"] = str(training_log_path)
    training_plan["checkpoint_path"] = str(checkpoint_path)
    training_plan_path.write_text(json.dumps(training_plan, indent=2) + "\n", encoding="utf-8")

    run = json.loads((output_dir / "training_run.json").read_text(encoding="utf-8"))
    run.update(
        {
            "status": "completed",
            "training_log_path": str(training_log_path),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_manifest_path": str(checkpoint_manifest_path),
            "stage_execution": deepcopy(stage_execution),
            "anchor_training": _anchor_training_summary(anchor_counter),
            "runtime": deepcopy(runtime),
        }
    )
    run_path = output_dir / "training_run.json"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def _validate_runtime_config(runtime: Any) -> dict[str, Any]:
    if runtime is None:
        runtime = {}
    if not isinstance(runtime, dict):
        raise LatentDiffusionTrainingError("runtime must be a JSON object when provided")
    validated = dict(DEFAULT_RUNTIME)
    validated.update(runtime)
    positive_int_fields = (
        "latent_channels",
        "latent_size",
        "vae_epochs",
        "image_generator_epochs",
        "wsi_consistency_epochs",
        "diffusion_timesteps",
    )
    for field in positive_int_fields:
        value = validated.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise LatentDiffusionTrainingError(f"runtime.{field} must be a positive integer")
    batch_size = validated.get("batch_size")
    if batch_size is not None and (
        not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0
    ):
        raise LatentDiffusionTrainingError("runtime.batch_size must be a positive integer when provided")
    if not isinstance(validated.get("device"), str) or validated["device"] == "":
        raise LatentDiffusionTrainingError("runtime.device must be a non-empty string")
    if not isinstance(validated.get("split"), str) or validated["split"] == "":
        raise LatentDiffusionTrainingError("runtime.split must be a non-empty string")
    learning_rate = validated.get("learning_rate")
    if (
        not isinstance(learning_rate, (int, float))
        or isinstance(learning_rate, bool)
        or learning_rate <= 0
    ):
        raise LatentDiffusionTrainingError("runtime.learning_rate must be a positive number")
    beta_start = validated.get("beta_start")
    beta_end = validated.get("beta_end")
    if (
        not isinstance(beta_start, (int, float))
        or isinstance(beta_start, bool)
        or not isinstance(beta_end, (int, float))
        or isinstance(beta_end, bool)
        or not 0 < float(beta_start) < float(beta_end) < 1
    ):
        raise LatentDiffusionTrainingError(
            "runtime beta schedule must satisfy 0 < beta_start < beta_end < 1"
        )
    return validated


def _resolve_device(torch, requested_device: str):
    device_obj = torch.device(requested_device)
    if device_obj.type != "cpu" and not torch.cuda.is_available():
        raise LatentDiffusionTrainingError(f"requested device is unavailable: {requested_device}")
    return device_obj


def _load_conditioning_reference(prior_manifest: dict[str, Any]) -> dict[str, Any]:
    style_path = Path(prior_manifest["artifacts"]["style_prior"]["path"])
    texture_path = Path(prior_manifest["artifacts"]["texture_prior"]["path"])
    try:
        style_prior = json.loads(style_path.read_text(encoding="utf-8"))
        texture_prior = json.loads(texture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LatentDiffusionTrainingError(f"prior artifact is not valid JSON: {exc.msg}") from exc

    rgb_stats = style_prior.get("rgb_statistics")
    if not isinstance(rgb_stats, dict):
        raise LatentDiffusionTrainingError("style_prior.rgb_statistics must be an object")
    mean_rgb = rgb_stats.get("mean_rgb_normalized")
    if not isinstance(mean_rgb, list) or len(mean_rgb) != 3:
        raise LatentDiffusionTrainingError("style_prior.rgb_statistics.mean_rgb_normalized must contain 3 values")
    tile_style_records = style_prior.get("tile_style_records")
    sample_style_latents: dict[str, list[float]] = {}
    if isinstance(tile_style_records, list):
        for record in tile_style_records:
            if (
                isinstance(record, dict)
                and isinstance(record.get("sample_id"), str)
                and isinstance(record.get("style_latent"), list)
            ):
                sample_style_latents[record["sample_id"]] = [
                    float(value) for value in record["style_latent"][:3]
                ]
    style_coverage = _coverage_summary(style_prior, "style_prior")
    style_limitations = _string_list(style_prior.get("limitations"))
    style_kind = style_prior.get("prior_kind") if isinstance(style_prior.get("prior_kind"), str) else None

    texture_prototypes = texture_prior.get("texture_prototypes")
    if not isinstance(texture_prototypes, list) or not texture_prototypes:
        raise LatentDiffusionTrainingError("texture_prior.texture_prototypes must be a non-empty list")
    validated_texture_prototypes = []
    for prototype in texture_prototypes:
        if not isinstance(prototype, dict):
            raise LatentDiffusionTrainingError("texture_prior.texture_prototypes entries must be objects")
        cluster_id = prototype.get("cluster_id")
        if not isinstance(cluster_id, int) or isinstance(cluster_id, bool):
            raise LatentDiffusionTrainingError("texture_prior.texture_prototypes.cluster_id must be int")
        validated_texture_prototypes.append(
            {
                "cluster_id": cluster_id,
                "morphology_latent": [
                    float(value) for value in prototype.get("morphology_latent", [])[:3]
                ],
            }
        )
    texture_coverage = _coverage_summary(texture_prior, "texture_prior")
    texture_limitations = _string_list(texture_prior.get("limitations"))
    texture_kind = (
        texture_prior.get("prior_kind") if isinstance(texture_prior.get("prior_kind"), str) else None
    )
    return {
        "style": {
            "source_path": str(style_path),
            "mean_rgb_normalized": [float(value) for value in mean_rgb],
            "sample_style_latents": sample_style_latents,
            "summary": {
                "mean_rgb_normalized": [float(value) for value in mean_rgb],
                "sample_style_record_count": len(sample_style_latents),
                "prior_kind": style_kind,
                "coverage": style_coverage,
                "limitations": style_limitations,
            },
        },
        "texture": {
            "source_path": str(texture_path),
            "prototypes": validated_texture_prototypes,
            "summary": {
                "cluster_count": len(validated_texture_prototypes),
                "cluster_ids": [record["cluster_id"] for record in validated_texture_prototypes],
                "prior_kind": texture_kind,
                "coverage": texture_coverage,
                "limitations": texture_limitations,
            },
        },
    }


def _coverage_summary(prior: dict[str, Any], label: str) -> dict[str, Any]:
    coverage = prior.get("coverage")
    if coverage is None:
        return {
            "covered_dimensions": [],
            "uncovered_dimensions": [],
            "note": f"{label}.coverage missing in prior artifact",
        }
    if not isinstance(coverage, dict):
        raise LatentDiffusionTrainingError(f"{label}.coverage must be an object when present")
    covered = coverage.get("covered_dimensions") or []
    uncovered = coverage.get("uncovered_dimensions") or []
    if not isinstance(covered, list) or not isinstance(uncovered, list):
        raise LatentDiffusionTrainingError(
            f"{label}.coverage.covered_dimensions and uncovered_dimensions must be lists"
        )
    return {
        "covered_dimensions": [str(value) for value in covered],
        "uncovered_dimensions": [str(value) for value in uncovered],
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _load_level_batches(
    *,
    training_index_path: str,
    records_by_level: dict[str, Any],
    split: str,
    batch_size_limit: int | None,
) -> dict[str, dict[str, Any]]:
    level_batches: dict[str, dict[str, Any]] = {}
    for level in CASCADE_LEVELS:
        matched_count = records_by_level.get(level)
        if not isinstance(matched_count, int) or matched_count <= 0:
            raise LatentDiffusionTrainingError(
                f"dataset_contract.records_by_level.{level} must be a positive integer"
            )
        requested_batch_size = min(int(matched_count), int(batch_size_limit)) if batch_size_limit is not None else int(matched_count)
        try:
            batch = load_training_batch(
                training_index_path,
                batch_size=requested_batch_size,
                split=split,
                cascade_level=level,
                include_image=True,
            )
        except TrainingBatchError as exc:
            raise LatentDiffusionTrainingError(str(exc)) from exc
        level_batches[level] = batch
    return level_batches


def _run_vae_stage(
    *,
    torch,
    vae,
    optimizer,
    level_batches: dict[str, dict[str, Any]],
    runtime: dict[str, Any],
    device_obj,
    log_handle,
) -> dict[str, Any]:
    history = []
    for epoch in range(1, runtime["vae_epochs"] + 1):
        epoch_losses = []
        for level in CASCADE_LEVELS:
            batch = level_batches[level]
            image_targets = _image_targets(torch, batch, runtime["latent_size"], device_obj)
            optimizer.zero_grad(set_to_none=True)
            reconstruction, mu, logvar = vae(image_targets)
            reconstruction_loss = torch.nn.functional.mse_loss(reconstruction, image_targets)
            kl_loss = -0.5 * torch.mean(1.0 + logvar - mu.pow(2) - logvar.exp())
            loss = reconstruction_loss + 1e-4 * kl_loss
            _require_finite_loss(loss, "vae")
            loss.backward()
            optimizer.step()
            loss_value = float(loss.detach().cpu().item())
            epoch_losses.append(loss_value)
            _write_stage_log(
                log_handle,
                {
                    "schema_version": PROJECT_VERSION,
                    "stage": "image_generator",
                    "substage": "vae_pretrain",
                    "epoch": epoch,
                    "cascade_level": level,
                    "backend": LATENT_DIFFUSION_BACKEND,
                    "loss": loss_value,
                    "reconstruction_loss": float(reconstruction_loss.detach().cpu().item()),
                    "kl_loss": float(kl_loss.detach().cpu().item()),
                },
            )
        history.append(_round_float(sum(epoch_losses) / len(epoch_losses)))
    return {"stage_loss_history": history}


def _run_diffusion_stage(
    *,
    torch,
    vae,
    denoiser,
    mask_head,
    optimizer,
    level_batches: dict[str, dict[str, Any]],
    conditioning_reference: dict[str, Any],
    runtime: dict[str, Any],
    device_obj,
    alpha_bars,
    stage_name: str,
    epoch_count: int,
    objective_weights: dict[str, Any],
    anchor_counter: Counter,
    log_handle,
    include_consistency_losses: bool,
) -> dict[str, Any]:
    history = []
    for epoch in range(1, epoch_count + 1):
        epoch_losses = []
        for level in CASCADE_LEVELS:
            batch = level_batches[level]
            image_targets = _image_targets(torch, batch, runtime["latent_size"], device_obj)
            mask_targets = _mask_targets(torch, batch, runtime["latent_size"], device_obj)
            previous_scale = _previous_scale_condition(torch, image_targets, level, runtime["latent_size"])
            for anchor_preset in ANCHOR_TRAINING_PRESETS:
                optimizer.zero_grad(set_to_none=True)
                source_condition = _source_condition_channels(
                    image_targets=image_targets,
                    source_enabled=anchor_preset["source_enabled"],
                    anchor_value=anchor_preset["value"],
                )
                condition_features, condition_summary = _condition_feature_channels(
                    torch=torch,
                    batch=batch,
                    conditioning_reference=conditioning_reference,
                    anchor_preset=anchor_preset,
                    latent_size=runtime["latent_size"],
                    device_obj=device_obj,
                )
                with torch.no_grad():
                    mu, logvar = vae.encode(image_targets)
                    latents = vae.reparameterize(mu, logvar)

                timesteps = torch.randint(
                    0,
                    runtime["diffusion_timesteps"],
                    (latents.shape[0],),
                    device=device_obj,
                )
                noise = torch.randn_like(latents)
                alpha_bar = alpha_bars[timesteps].view(-1, 1, 1, 1)
                noisy_latents = alpha_bar.sqrt() * latents + (1.0 - alpha_bar).sqrt() * noise
                time_channel = _time_channel(
                    torch,
                    timesteps,
                    runtime["diffusion_timesteps"],
                    runtime["latent_size"],
                    device_obj,
                )
                mask_conditions = _mask_condition_channels(torch, mask_targets)
                predicted_noise = denoiser(
                    torch.cat(
                        [
                            noisy_latents,
                            previous_scale,
                            source_condition,
                            mask_conditions,
                            time_channel,
                            condition_features,
                        ],
                        dim=1,
                    )
                )
                diffusion_loss = torch.nn.functional.mse_loss(predicted_noise, noise)
                clean_latents = _predict_clean_latents(
                    noisy_latents=noisy_latents,
                    predicted_noise=predicted_noise,
                    alpha_bar=alpha_bar,
                )
                decoded_rgb = vae.decode(clean_latents)
                mask_logits = mask_head(decoded_rgb)
                semantic_loss = torch.nn.functional.cross_entropy(mask_logits, mask_targets)
                total_loss = (
                    float(objective_weights["diffusion_generation"]) * diffusion_loss
                    + float(objective_weights["semantic_mask_consistency"]) * semantic_loss
                )
                extra_losses = {
                    "cross_scale_consistency": 0.0,
                    "tile_seam_consistency": 0.0,
                    "slide_style_consistency": 0.0,
                }
                if include_consistency_losses:
                    cross_scale_loss = torch.nn.functional.l1_loss(decoded_rgb, previous_scale)
                    seam_loss = _tile_seam_loss(torch, decoded_rgb, batch["tile_records"])
                    style_loss = _style_consistency_loss(
                        torch,
                        decoded_rgb,
                        conditioning_reference["style"]["mean_rgb_normalized"],
                    )
                    total_loss = total_loss + (
                        float(objective_weights["cross_scale_consistency"]) * cross_scale_loss
                        + float(objective_weights["tile_seam_consistency"]) * seam_loss
                        + float(objective_weights["slide_style_consistency"]) * style_loss
                    )
                    extra_losses = {
                        "cross_scale_consistency": float(cross_scale_loss.detach().cpu().item()),
                        "tile_seam_consistency": float(seam_loss.detach().cpu().item()),
                        "slide_style_consistency": float(style_loss.detach().cpu().item()),
                    }
                _require_finite_loss(total_loss, stage_name)
                total_loss.backward()
                optimizer.step()
                total_value = float(total_loss.detach().cpu().item())
                epoch_losses.append(total_value)
                anchor_counter[anchor_preset["name"]] += batch["batch_size"]
                _write_stage_log(
                    log_handle,
                    {
                        "schema_version": PROJECT_VERSION,
                        "stage": stage_name,
                        "epoch": epoch,
                        "cascade_level": level,
                        "anchor_preset": anchor_preset["name"],
                        "backend": LATENT_DIFFUSION_BACKEND,
                        "loss": total_value,
                        "diffusion_loss": float(diffusion_loss.detach().cpu().item()),
                        "semantic_mask_loss": float(semantic_loss.detach().cpu().item()),
                        **extra_losses,
                        "source_condition_enabled": anchor_preset["source_enabled"],
                        "structure_anchor": anchor_preset["value"],
                        "conditioning_summary": condition_summary,
                    },
                )
        history.append(_round_float(sum(epoch_losses) / len(epoch_losses)))
    return {"stage_loss_history": history}


def _image_targets(torch, batch: dict[str, Any], latent_size: int, device_obj):
    image_batch = torch.as_tensor(batch["image_batch"], dtype=torch.float32, device=device_obj)
    image_batch = image_batch.permute(0, 3, 1, 2) / 255.0
    if image_batch.shape[-2:] != (latent_size, latent_size):
        image_batch = torch.nn.functional.interpolate(
            image_batch,
            size=(latent_size, latent_size),
            mode="area",
        )
    return image_batch


def _mask_targets(torch, batch: dict[str, Any], latent_size: int, device_obj):
    mask_targets = torch.as_tensor(batch["mask_batch"], dtype=torch.long, device=device_obj)
    if mask_targets.shape[-2:] != (latent_size, latent_size):
        mask_targets = torch.nn.functional.interpolate(
            mask_targets.unsqueeze(1).to(dtype=torch.float32),
            size=(latent_size, latent_size),
            mode="nearest",
        ).squeeze(1).to(dtype=torch.long)
    return mask_targets


def _previous_scale_condition(torch, image_targets, cascade_level: str, latent_size: int):
    ratio = PREVIOUS_SCALE_RATIO[cascade_level]
    if ratio is None:
        return torch.zeros_like(image_targets)
    coarse_size = max(1, latent_size // ratio)
    coarse = torch.nn.functional.interpolate(
        image_targets,
        size=(coarse_size, coarse_size),
        mode="area",
    )
    return torch.nn.functional.interpolate(
        coarse,
        size=(latent_size, latent_size),
        mode="bilinear",
        align_corners=False,
    )


def _source_condition_channels(*, image_targets, source_enabled: bool, anchor_value: float):
    if not source_enabled:
        return image_targets.new_zeros(image_targets.shape)
    return image_targets * float(anchor_value)


def _condition_feature_channels(
    *,
    torch,
    batch: dict[str, Any],
    conditioning_reference: dict[str, Any],
    anchor_preset: dict[str, Any],
    latent_size: int,
    device_obj,
):
    vectors = []
    summaries = []
    prototypes = conditioning_reference["texture"]["prototypes"]
    style_map = conditioning_reference["style"]["sample_style_latents"]
    global_style = conditioning_reference["style"]["mean_rgb_normalized"]
    for sample_id, tile in zip(batch["sample_ids"], batch["tile_records"], strict=True):
        style_latent = style_map.get(sample_id)
        style_vector = style_latent[:3] if style_latent else global_style
        texture_index = (int(tile["x"]) // max(int(tile["width"]), 1)) % len(prototypes)
        texture_cluster_id = prototypes[texture_index]["cluster_id"]
        vectors.append(
            [
                float(style_vector[0]),
                float(style_vector[1]),
                float(style_vector[2]),
                _normalized_texture_cluster_id(texture_cluster_id, len(prototypes)),
                _clamp01(float(tile["x"]) / 100000.0),
                _clamp01(float(tile["y"]) / 100000.0),
                CASCADE_LEVEL_SCALE[_cascade_level_from_sample_id(sample_id)],
                1.0 if anchor_preset["source_enabled"] else 0.0,
                float(anchor_preset["value"]),
            ]
        )
        summaries.append(
            {
                "sample_id": sample_id,
                "style_vector": [float(value) for value in style_vector],
                "texture_cluster_id": texture_cluster_id,
            }
        )
    tensor = torch.tensor(vectors, dtype=torch.float32, device=device_obj)
    return (
        tensor.view(len(vectors), REAL_CONDITION_FEATURE_COUNT, 1, 1).expand(
            -1,
            -1,
            latent_size,
            latent_size,
        ),
        {
            "feature_names": list(REAL_CONDITION_FEATURE_NAMES),
            "samples": summaries,
        },
    )


def _normalized_texture_cluster_id(cluster_id: int, cluster_count: int) -> float:
    if cluster_count <= 1:
        return 0.0
    return _clamp01(float(cluster_id) / float(cluster_count - 1))


def _time_channel(torch, timesteps, diffusion_timesteps: int, latent_size: int, device_obj):
    denominator = float(max(diffusion_timesteps - 1, 1))
    values = timesteps.to(dtype=torch.float32).view(-1, 1, 1, 1) / denominator
    return values.expand(-1, 1, latent_size, latent_size).to(device=device_obj)


def _mask_condition_channels(torch, mask_targets):
    one_hot = torch.nn.functional.one_hot(mask_targets, num_classes=len(MASK_CLASSES))
    return one_hot.permute(0, 3, 1, 2).to(dtype=torch.float32)


def _predict_clean_latents(*, noisy_latents, predicted_noise, alpha_bar):
    denominator = alpha_bar.sqrt().clamp(min=1e-6)
    return (noisy_latents - (1.0 - alpha_bar).sqrt() * predicted_noise) / denominator


def _tile_seam_loss(torch, decoded_rgb, tile_records: list[dict[str, Any]]):
    adjacency_losses = []
    for left_index, left_tile in enumerate(tile_records):
        for right_index in range(left_index + 1, len(tile_records)):
            right_tile = tile_records[right_index]
            if left_tile["y"] == right_tile["y"] and left_tile["x"] + left_tile["width"] == right_tile["x"]:
                adjacency_losses.append(
                    torch.nn.functional.l1_loss(
                        decoded_rgb[left_index, :, :, -1:],
                        decoded_rgb[right_index, :, :, :1],
                    )
                )
            if left_tile["x"] == right_tile["x"] and left_tile["y"] + left_tile["height"] == right_tile["y"]:
                adjacency_losses.append(
                    torch.nn.functional.l1_loss(
                        decoded_rgb[left_index, :, -1:, :],
                        decoded_rgb[right_index, :, :1, :],
                    )
                )
    if not adjacency_losses:
        return decoded_rgb.new_tensor(0.0)
    return torch.stack(adjacency_losses).mean()


def _style_consistency_loss(torch, decoded_rgb, style_mean_rgb_normalized: list[float]):
    batch_size = int(decoded_rgb.shape[0])
    target = (
        decoded_rgb.new_tensor(style_mean_rgb_normalized)
        .view(1, 3, 1, 1)
        .expand(batch_size, -1, -1, -1)
    )
    predicted_mean = decoded_rgb.mean(dim=(2, 3), keepdim=True)
    predicted_std = decoded_rgb.std(dim=(2, 3), keepdim=True, unbiased=False)
    target_std = (
        decoded_rgb.new_tensor([0.1, 0.1, 0.1])
        .view(1, 3, 1, 1)
        .expand(batch_size, -1, -1, -1)
    )
    return torch.nn.functional.l1_loss(predicted_mean, target) + torch.nn.functional.l1_loss(
        predicted_std,
        target_std,
    )


def _require_finite_loss(loss, stage_name: str) -> None:
    if not loss.isfinite().item():
        raise LatentDiffusionTrainingError(f"non-finite loss encountered during {stage_name}")


def _trained_checkpoint_manifest(
    *,
    config: dict[str, Any],
    initialized_run: dict[str, Any],
    runtime: dict[str, Any],
    prior_manifest: dict[str, Any],
    checkpoint_path: Path,
    checkpoint_hash: str,
    training_log_path: Path,
    checkpoint_payload: dict[str, Any],
    stage_execution: dict[str, Any],
    anchor_counter: Counter,
    conditioning_reference: dict[str, Any],
    torch_version: str,
    level_batches: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    input_channels = checkpoint_payload["input_channels"]
    output_channels = checkpoint_payload["output_channels"]
    denoiser_contract = denoiser_architecture(
        input_channels=input_channels,
        output_channels=output_channels,
    )
    feature_schema = condition_feature_schema()
    cross_scale_schema = cross_scale_condition_schema()
    source_schema = source_condition_schema()
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "trained",
        "usable_for_inference": True,
        "model_version": f"{PROJECT_VERSION}+{LATENT_DIFFUSION_BACKEND}",
        "created_at": _now_iso(),
        "training_run_id": initialized_run["run_id"],
        "training_backend": LATENT_DIFFUSION_BACKEND,
        "target_type": PRODUCTION_TARGET_TYPE,
        "prior_id": prior_manifest["prior_id"],
        "prior_manifest_path": str(Path(config["prior_manifest_path"]).resolve()),
        "training_index_path": str(Path(config["training_index_path"]).resolve()),
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_sha256": checkpoint_hash,
        "training_log_path": str(training_log_path.resolve()),
        "training_plan_path": str(Path(initialized_run["training_plan_path"]).resolve()),
        "torch_version": torch_version,
        "input_channels": input_channels,
        "output_channels": output_channels,
        "latent_channels": runtime["latent_channels"],
        "latent_size": runtime["latent_size"],
        "denoiser_architecture": denoiser_contract,
        "condition_feature_schema": feature_schema,
        "cross_scale_condition_schema": cross_scale_schema,
        "source_condition_schema": source_schema,
        "inference_contract": {
            "backend_type": LATENT_DIFFUSION_CHECKPOINT_BACKEND,
            "artifact_role": "mask_conditioned_multiscale_latent_diffusion_checkpoint",
            "production_ready": False,
            "limitations": [
                "stage4_minimal_real_training_backend",
                "stage5_generation_integration_pending",
                "validated_for_checkpoint_loading_not_full_wsi_generation",
            ],
            "compatible_generation_backends": ["production-tile-stream"],
            "model_architecture_contract": {
                "model_family": MODEL_FAMILY,
                "architecture_name": denoiser_contract["architecture"],
                "input_space": "latent_previous_scale_rgb_source_rgb_mask_timestep_condition_concat",
                "output_space": "predicted_diffusion_noise",
                "denoiser_architecture": deepcopy(denoiser_contract),
            },
            "condition_input_contract": {
                "required_condition_inputs": list(REQUIRED_INFERENCE_CONDITION_INPUTS),
                "cascade_levels": list(CASCADE_LEVELS),
                "condition_feature_policy": (
                    "style prior RGB means, deterministic texture cluster id, coord, "
                    "source flag, and structure_anchor are injected as constant channels"
                ),
                "condition_feature_schema": deepcopy(feature_schema),
                "cross_scale_condition_schema": deepcopy(cross_scale_schema),
                "source_condition_schema": deepcopy(source_schema),
            },
        },
        "stage_execution": deepcopy(stage_execution),
        "anchor_training": _anchor_training_summary(anchor_counter),
        "conditioning_reference": {
            "style_target": deepcopy(conditioning_reference["style"]["summary"]),
            "texture_target": deepcopy(conditioning_reference["texture"]["summary"]),
        },
        "dataset_sampling": {
            "split": runtime["split"],
            "batch_size_by_level": {
                level: int(batch["batch_size"]) for level, batch in level_batches.items()
            },
            "matched_record_count_by_level": {
                level: int(initialized_run["dataset_contract"]["records_by_level"][level])
                for level in level_batches
            },
        },
        "diffusion": deepcopy(checkpoint_payload["diffusion"]),
        "dataset_contract_summary": deepcopy(initialized_run["dataset_contract"]),
        "training_objective_contract_summary": deepcopy(initialized_run["training_objective_contract"]),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "max_magnification": MAX_MAGNIFICATION,
        "note": (
            "Minimal real Stage4 latent diffusion backend. It executes prior readiness, "
            "image generator training, and WSI consistency fine-tuning on real training-index "
            "tiles with anchor/source/previous-scale conditions. Stage5 generation backend "
            "integration remains out of scope for this checkpoint."
        ),
    }


def _anchor_training_summary(anchor_counter: Counter) -> dict[str, Any]:
    return {
        "presets": deepcopy(ANCHOR_TRAINING_PRESETS),
        "sample_count_by_preset": {preset["name"]: int(anchor_counter[preset["name"]]) for preset in ANCHOR_TRAINING_PRESETS},
        "policy": {
            "low_anchor": ANCHOR_PRESETS["fully_de_novo"],
            "medium_anchor": ANCHOR_PRESETS["layout_recombination"],
            "high_anchor": ANCHOR_PRESETS["rescan_simulation"],
            "source_condition_policy": "disabled_for_low_anchor_enabled_for_medium_and_high_anchor",
        },
    }


def condition_feature_schema() -> dict[str, Any]:
    return {
        "feature_count": REAL_CONDITION_FEATURE_COUNT,
        "feature_names": list(REAL_CONDITION_FEATURE_NAMES),
        "features": [deepcopy(item) for item in REAL_CONDITION_FEATURES],
        "spatial_injection": "concat_constant_feature_channels",
        "training_default_policy": (
            "style mean RGB comes from style prior, texture cluster id from deterministic prototype selection, "
            "coord from tile origin, and source/anchor from anchor training presets"
        ),
        "production_status": "stage4_real_condition_injection_contract",
    }


def cross_scale_condition_schema() -> dict[str, Any]:
    return {
        "condition_name": "previous_scale_observed_rgb",
        "channel_count": PREVIOUS_SCALE_CHANNELS,
        "channel_order": ["red", "green", "blue"],
        "spatial_injection": "concat_previous_scale_observed_rgb_channels",
        "training_source": "observed_wsi_previous_scale_rgb_from_same_tile_region",
        "sampling_sources": ["stage5_generation_backend"],
        "root_cascade_policy": "zero_previous_scale_condition_for_1/32",
        "production_status": "stage4_observed_previous_scale_condition_contract",
    }


def source_condition_schema() -> dict[str, Any]:
    return {
        "condition_name": "source_condition_observed_rgb",
        "channel_count": SOURCE_CONDITION_CHANNELS,
        "channel_order": ["red", "green", "blue"],
        "spatial_injection": "concat_source_condition_observed_rgb_channels",
        "training_source": "observed_source_wsi_rgb_same_tile_region",
        "anchor_policy": "medium_and_high_anchor_enable_source_rgb_low_anchor_zeros_it_out",
        "production_status": "stage4_anchor_source_condition_contract",
    }


def denoiser_architecture(*, input_channels: int, output_channels: int) -> dict[str, Any]:
    return {
        "architecture": "stage4_conditioned_latent_unet",
        "base_channels": DENOISER_BASE_CHANNELS,
        "bottleneck_channels": DENOISER_BOTTLENECK_CHANNELS,
        "downsample_stages": 1,
        "skip_connections": "encoder_decoder_concat",
        "latent_sources_supported": ["trained_tile_vae"],
        "input_channels": input_channels,
        "output_channels": output_channels,
        "production_status": "minimal_real_training_backend_not_stage5_validated",
    }


def _build_tile_vae(torch, latent_channels: int):
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Sequential(
                torch.nn.Conv2d(3, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(32, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(32, 2 * latent_channels, kernel_size=1),
            )
            self.decoder = torch.nn.Sequential(
                torch.nn.Conv2d(latent_channels, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(32, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(32, 3, kernel_size=1),
                torch.nn.Sigmoid(),
            )

        def encode(self, inputs):
            encoded = self.encoder(inputs)
            mu, logvar = torch.chunk(encoded, 2, dim=1)
            return mu, logvar.clamp(min=-8.0, max=8.0)

        def reparameterize(self, mu, logvar):
            std = torch.exp(0.5 * logvar)
            return mu + torch.randn_like(std) * std

        def decode(self, latents):
            return self.decoder(latents)

        def forward(self, inputs):
            mu, logvar = self.encode(inputs)
            latents = self.reparameterize(mu, logvar)
            return self.decode(latents), mu, logvar

    return Model()


def _build_latent_denoiser(torch, *, input_channels: int, output_channels: int):
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder_block = torch.nn.Sequential(
                torch.nn.Conv2d(input_channels, DENOISER_BASE_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(DENOISER_BASE_CHANNELS, DENOISER_BASE_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
            )
            self.downsample = torch.nn.Sequential(
                torch.nn.Conv2d(
                    DENOISER_BASE_CHANNELS,
                    DENOISER_BOTTLENECK_CHANNELS,
                    kernel_size=3,
                    stride=2,
                    padding=1,
                ),
                torch.nn.ReLU(),
            )
            self.bottleneck = torch.nn.Sequential(
                torch.nn.Conv2d(DENOISER_BOTTLENECK_CHANNELS, DENOISER_BOTTLENECK_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(DENOISER_BOTTLENECK_CHANNELS, DENOISER_BOTTLENECK_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
            )
            self.upsample = torch.nn.ConvTranspose2d(
                DENOISER_BOTTLENECK_CHANNELS,
                DENOISER_BASE_CHANNELS,
                kernel_size=4,
                stride=2,
                padding=1,
            )
            self.decoder_block = torch.nn.Sequential(
                torch.nn.Conv2d(DENOISER_BASE_CHANNELS * 2, DENOISER_BASE_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(DENOISER_BASE_CHANNELS, DENOISER_BASE_CHANNELS, kernel_size=3, padding=1),
                torch.nn.ReLU(),
            )
            self.output_block = torch.nn.Conv2d(DENOISER_BASE_CHANNELS, output_channels, kernel_size=1)

        def forward(self, inputs):
            encoder_features = self.encoder_block(inputs)
            downsampled = self.downsample(encoder_features)
            bottleneck = self.bottleneck(downsampled)
            upsampled = self.upsample(bottleneck)
            if upsampled.shape[-2:] != encoder_features.shape[-2:]:
                upsampled = torch.nn.functional.interpolate(
                    upsampled,
                    size=encoder_features.shape[-2:],
                    mode="nearest",
                )
            decoded = self.decoder_block(torch.cat([upsampled, encoder_features], dim=1))
            return self.output_block(decoded)

    return Model()


def _build_mask_head(torch, *, class_count: int):
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = torch.nn.Sequential(
                torch.nn.Conv2d(3, 16, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Conv2d(16, class_count, kernel_size=1),
            )

        def forward(self, inputs):
            return self.layers(inputs)

    return Model()


def _latent_batch_shape(level_batches: dict[str, dict[str, Any]], latent_channels: int, latent_size: int) -> list[int]:
    batch_size = max(batch["batch_size"] for batch in level_batches.values())
    return [int(batch_size), int(latent_channels), int(latent_size), int(latent_size)]


def _cascade_level_from_sample_id(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) >= 2 and parts[1] in CASCADE_LEVEL_SCALE:
        return parts[1]
    return "1/32"


def _write_stage_log(handle, payload: dict[str, Any]) -> None:
    handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _round_float(value: float) -> float:
    return round(float(value), 6)


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _import_torch():
    try:
        import torch
    except ImportError as exc:  # pragma: no cover
        raise LatentDiffusionTrainingError(
            "PyTorch is required for latent diffusion training; install the torch optional dependency "
            "or run inside a PyTorch conda environment"
        ) from exc
    return torch


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
