from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MASK_CLASSES, MODEL_FAMILY, PROJECT_VERSION, TILE_SIZE_40X


class TorchTrainingError(ValueError):
    """Raised when the PyTorch smoke training backend cannot run safely."""


TORCH_SMOKE_BACKEND = "torch-smoke-mask-conditioned-rgb-reconstructor"
TORCH_VAE_SMOKE_BACKEND = "torch-smoke-rgb-vae-latent-autoencoder"
TORCH_DIFFUSION_SMOKE_BACKEND = "torch-smoke-mask-conditioned-latent-diffusion"
TORCH_DIFFUSION_SMOKE_SAMPLER = "torch-smoke-mask-conditioned-latent-diffusion-sampler"
DENOISER_ARCHITECTURE_NAME = "smoke_latent_unet"
DENOISER_BASE_CHANNELS = 32
DENOISER_BOTTLENECK_CHANNELS = 64
CROSS_SCALE_CONDITION_CHANNELS = 3
CONDITION_FEATURES = (
    {
        "name": "style_seed_value_norm",
        "source": "condition_packet.conditions.style_seed.value",
        "normalization": "clamp(value / 10000, 0, 1)",
    },
    {
        "name": "texture_cluster_id_norm",
        "source": "condition_packet.conditions.texture_token.cluster_id",
        "normalization": "clamp(value / 1000, 0, 1)",
    },
    {
        "name": "tile_origin_x_40x_norm",
        "source": "condition_packet.conditions.coord.tile_origin_40x[0]",
        "normalization": "clamp(value / 100000, 0, 1)",
    },
    {
        "name": "tile_origin_y_40x_norm",
        "source": "condition_packet.conditions.coord.tile_origin_40x[1]",
        "normalization": "clamp(value / 100000, 0, 1)",
    },
    {
        "name": "cascade_level_scale",
        "source": "condition_packet.conditions.coord.cascade_level",
        "normalization": "1/32=0, 1/16=0.333333, 1/4=0.666667, 1/1=1",
    },
    {
        "name": "source_condition_enabled",
        "source": "condition_packet.conditions.source_condition.enabled",
        "normalization": "false=0, true=1",
    },
    {
        "name": "structure_anchor",
        "source": "condition_packet.conditions.structure_anchor.value",
        "normalization": "clamp(value, 0, 1)",
    },
)
CONDITION_FEATURE_NAMES = [feature["name"] for feature in CONDITION_FEATURES]
CONDITION_FEATURE_COUNT = len(CONDITION_FEATURES)
CASCADE_LEVEL_SCALE = {
    "1/32": 0.0,
    "1/16": 0.333333,
    "1/4": 0.666667,
    "1/1": 1.0,
}


def checkpoint_manifest(
    torch,
    training_index_path: str | Path,
    checkpoint_path: Path,
    checkpoint_hash: str,
    log_path: Path,
    batch_summary: dict[str, Any],
    epochs: int,
    learning_rate: float,
    random_seed: int,
    device: str,
    loss_history: list[float],
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "trained",
        "usable_for_inference": False,
        "model_version": f"{PROJECT_VERSION}+{TORCH_SMOKE_BACKEND}",
        "created_at": _now_iso(),
        "training_backend": TORCH_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_hash,
        "training_log_path": str(log_path),
        "torch_version": torch.__version__,
        "target_type": "rgb_image",
        "input_channels": len(MASK_CLASSES),
        "output_channels": 3,
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "training_parameters": {
            "epochs": epochs,
            "batch_size": batch_summary["batch_size"],
            "learning_rate": learning_rate,
            "random_seed": random_seed,
            "device": device,
            "cascade_levels": batch_summary["cascade_levels"],
            "target_type": "rgb_image",
            "loss_name": "mse_rgb_reconstruction",
        },
        "loss_summary": {
            "initial_loss": loss_history[0],
            "final_loss": loss_history[-1],
            "history": loss_history,
        },
        "batch_summary": batch_summary,
        "note": (
            "PyTorch smoke checkpoint validates training mechanics only; "
            "it learns a tiny mask-conditioned RGB reconstruction task, not latent "
            "diffusion, and is not usable for inference."
        ),
    }


def diffusion_checkpoint_manifest(
    torch,
    training_index_path: str | Path,
    checkpoint_path: Path,
    checkpoint_hash: str,
    log_path: Path,
    batch_summary: dict[str, Any],
    epochs: int,
    learning_rate: float,
    random_seed: int,
    device: str,
    loss_history: list[float],
    diffusion: dict[str, Any],
    input_channels: int,
    output_channels: int,
    denoiser_architecture: dict[str, Any],
    cross_scale_condition_schema: dict[str, Any],
) -> dict[str, Any]:
    inference_contract = _diffusion_smoke_inference_contract(
        denoiser_architecture=denoiser_architecture,
        cross_scale_condition_schema=cross_scale_condition_schema,
    )
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "trained",
        "usable_for_inference": True,
        "model_version": f"{PROJECT_VERSION}+{TORCH_DIFFUSION_SMOKE_BACKEND}",
        "created_at": _now_iso(),
        "training_backend": TORCH_DIFFUSION_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_hash,
        "training_log_path": str(log_path),
        "torch_version": torch.__version__,
        "target_type": "diffusion_noise",
        "input_channels": input_channels,
        "output_channels": output_channels,
        "denoiser_architecture": dict(denoiser_architecture),
        "cross_scale_condition_schema": dict(cross_scale_condition_schema),
        "condition_feature_schema": condition_feature_schema(),
        "inference_contract": inference_contract,
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "diffusion": diffusion,
        "training_parameters": {
            "epochs": epochs,
            "batch_size": batch_summary["batch_size"],
            "learning_rate": learning_rate,
            "random_seed": random_seed,
            "device": device,
            "cascade_levels": batch_summary["cascade_levels"],
            "target_type": "diffusion_noise",
            "loss_name": "mse_noise_prediction",
            "diffusion_timesteps": diffusion["timesteps"],
            "latent_source": diffusion["latent_source"],
            "vae_checkpoint_manifest_path": diffusion.get("vae_checkpoint_manifest_path"),
            "denoiser_architecture": denoiser_architecture["architecture"],
            "cross_scale_condition_channels": CROSS_SCALE_CONDITION_CHANNELS,
            "condition_feature_count": CONDITION_FEATURE_COUNT,
            "condition_feature_default_policy": (
                "training-index tile metadata for coord/cascade; zero style, texture, "
                "source, and structure_anchor for smoke training"
            ),
        },
        "loss_summary": {
            "initial_loss": loss_history[0],
            "final_loss": loss_history[-1],
            "history": loss_history,
        },
        "batch_summary": batch_summary,
        "note": (
            "PyTorch diffusion smoke checkpoint validates DDPM-style noise prediction "
            "on smoke latents with explicit condition feature channels; it is usable "
            "only by the torch-diffusion-smoke planning/sampling path and is not a "
            "production WSI latent diffusion generator."
        ),
    }


def _diffusion_smoke_inference_contract(
    *,
    denoiser_architecture: dict[str, Any],
    cross_scale_condition_schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "backend_type": "torch-diffusion-smoke",
        "artifact_role": "mask_conditioned_latent_diffusion_smoke_checkpoint",
        "production_ready": False,
        "limitations": [
            "smoke_backend_only",
            "not_production_latent_diffusion_backend",
            "not_controlnet_or_dit",
            "not_gigapixel_production_inference",
        ],
        "compatible_generation_backends": ["torch-diffusion-smoke"],
        "model_architecture_contract": {
            "model_family": MODEL_FAMILY,
            "architecture_name": denoiser_architecture["architecture"],
            "input_space": (
                "latent_or_rgb_proxy_with_previous_scale_mask_timestep_and_condition_features"
            ),
            "output_space": "predicted_diffusion_noise",
            "denoiser_architecture": dict(denoiser_architecture),
        },
        "condition_input_contract": {
            "required_condition_inputs": [
                "mask",
                "style_seed",
                "texture_token",
                "coord",
                "structure_anchor",
                "source_condition",
                "previous_scale",
            ],
            "cascade_levels": list(CASCADE_LEVELS),
            "condition_feature_policy": (
                "condition_packet features are projected to fixed scalar channels; "
                "previous_scale uses the prior cascade sample preview or zero root condition"
            ),
            "condition_feature_schema": condition_feature_schema(),
            "cross_scale_condition_schema": dict(cross_scale_condition_schema),
        },
    }


def vae_checkpoint_manifest(
    torch,
    training_index_path: str | Path,
    checkpoint_path: Path,
    checkpoint_hash: str,
    log_path: Path,
    latent_preview_path: Path,
    reconstruction_preview_path: Path,
    batch_summary: dict[str, Any],
    epochs: int,
    learning_rate: float,
    random_seed: int,
    device: str,
    latent_channels: int,
    latent_size: int,
    latent_batch_shape: list[int],
    kl_weight: float,
    loss_history: list[float],
    reconstruction_loss_history: list[float],
    kl_loss_history: list[float],
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "trained",
        "usable_for_inference": False,
        "model_version": f"{PROJECT_VERSION}+{TORCH_VAE_SMOKE_BACKEND}",
        "created_at": _now_iso(),
        "training_backend": TORCH_VAE_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_hash,
        "training_log_path": str(log_path),
        "latent_preview_path": str(latent_preview_path),
        "reconstruction_preview_path": str(reconstruction_preview_path),
        "torch_version": torch.__version__,
        "target_type": "vae_rgb_reconstruction",
        "latent_source": "trainable_vae_smoke",
        "latent_channels": latent_channels,
        "latent_size": latent_size,
        "latent_batch_shape": latent_batch_shape,
        "input_channels": 3,
        "output_channels": 3,
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "training_parameters": {
            "epochs": epochs,
            "batch_size": batch_summary["batch_size"],
            "learning_rate": learning_rate,
            "random_seed": random_seed,
            "device": device,
            "cascade_levels": batch_summary["cascade_levels"],
            "target_type": "vae_rgb_reconstruction",
            "latent_source": "trainable_vae_smoke",
            "latent_channels": latent_channels,
            "latent_size": latent_size,
            "kl_weight": kl_weight,
            "loss_name": "mse_rgb_reconstruction_plus_kl",
        },
        "loss_summary": {
            "initial_loss": loss_history[0],
            "final_loss": loss_history[-1],
            "history": loss_history,
            "reconstruction_history": reconstruction_loss_history,
            "kl_history": kl_loss_history,
        },
        "batch_summary": batch_summary,
        "note": (
            "PyTorch VAE smoke checkpoint validates a trainable latent autoencoder path "
            "on downsampled RGB tiles only; it is not a production WSI VAE and is not "
            "usable for inference."
        ),
    }


def validate_vae_checkpoint_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("training_backend") != TORCH_VAE_SMOKE_BACKEND:
        raise TorchTrainingError("VAE checkpoint manifest is not a VAE smoke checkpoint")
    if manifest.get("target_type") != "vae_rgb_reconstruction":
        raise TorchTrainingError("VAE checkpoint target_type must be vae_rgb_reconstruction")
    if manifest.get("latent_source") != "trainable_vae_smoke":
        raise TorchTrainingError("VAE checkpoint latent_source must be trainable_vae_smoke")
    for key in ("latent_channels", "latent_size"):
        value = manifest.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise TorchTrainingError(f"VAE checkpoint {key} must be a positive integer")
    if not isinstance(manifest.get("checkpoint_path"), str) or manifest["checkpoint_path"] == "":
        raise TorchTrainingError("VAE checkpoint manifest missing checkpoint_path")


def validate_vae_checkpoint_payload(payload: Any, manifest: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise TorchTrainingError("VAE checkpoint payload must be a dictionary")
    if payload.get("backend") != TORCH_VAE_SMOKE_BACKEND:
        raise TorchTrainingError("VAE checkpoint payload backend is incompatible")
    if payload.get("target_type") != "vae_rgb_reconstruction":
        raise TorchTrainingError("VAE checkpoint payload target_type must be vae_rgb_reconstruction")
    if payload.get("latent_source") != "trainable_vae_smoke":
        raise TorchTrainingError("VAE checkpoint payload latent_source must be trainable_vae_smoke")
    if payload.get("latent_channels") != manifest["latent_channels"]:
        raise TorchTrainingError("VAE checkpoint latent_channels mismatch")
    if payload.get("latent_size") != manifest["latent_size"]:
        raise TorchTrainingError("VAE checkpoint latent_size mismatch")
    if not isinstance(payload.get("state_dict"), dict):
        raise TorchTrainingError("VAE checkpoint payload missing state_dict")


def vae_diffusion_manifest_fields(diffusion: dict[str, Any]) -> dict[str, Any]:
    if diffusion.get("latent_source") != "trainable_vae_smoke":
        return {}
    return {
        "vae_checkpoint_manifest_path": diffusion["vae_checkpoint_manifest_path"],
        "vae_checkpoint_sha256": diffusion.get("vae_checkpoint_sha256"),
    }


def validate_diffusion_checkpoint_manifest(
    checkpoint_manifest: dict[str, Any],
    sample_steps: int,
) -> None:
    if checkpoint_manifest.get("training_backend") != TORCH_DIFFUSION_SMOKE_BACKEND:
        raise TorchTrainingError("checkpoint manifest is not a diffusion smoke checkpoint")
    if checkpoint_manifest.get("target_type") != "diffusion_noise":
        raise TorchTrainingError("checkpoint manifest target_type must be diffusion_noise")
    diffusion = checkpoint_manifest.get("diffusion")
    if not isinstance(diffusion, dict):
        raise TorchTrainingError("checkpoint manifest missing diffusion schedule")
    validate_condition_feature_schema(checkpoint_manifest.get("condition_feature_schema"))
    validate_cross_scale_condition_schema(
        checkpoint_manifest.get("cross_scale_condition_schema")
    )
    validate_denoiser_architecture(
        checkpoint_manifest.get("denoiser_architecture"),
        checkpoint_manifest.get("input_channels"),
        checkpoint_manifest.get("output_channels"),
        "checkpoint manifest",
    )
    validate_diffusion_schedule(diffusion, sample_steps)


def validate_diffusion_checkpoint_payload(checkpoint_payload: Any) -> None:
    if not isinstance(checkpoint_payload, dict):
        raise TorchTrainingError("checkpoint payload must be a dictionary")
    if checkpoint_payload.get("backend") != TORCH_DIFFUSION_SMOKE_BACKEND:
        raise TorchTrainingError("checkpoint payload is not a diffusion smoke checkpoint")
    if checkpoint_payload.get("target_type") != "diffusion_noise":
        raise TorchTrainingError("checkpoint payload target_type must be diffusion_noise")
    if not isinstance(checkpoint_payload.get("state_dict"), dict):
        raise TorchTrainingError("checkpoint payload missing state_dict")
    validate_condition_feature_schema(checkpoint_payload.get("condition_feature_schema"))
    validate_cross_scale_condition_schema(
        checkpoint_payload.get("cross_scale_condition_schema")
    )
    diffusion = checkpoint_payload.get("diffusion")
    if not isinstance(diffusion, dict):
        raise TorchTrainingError("checkpoint payload missing diffusion schedule")
    validate_diffusion_schedule(diffusion, sample_steps=1)
    latent_shape = diffusion["latent_batch_shape"]
    latent_channels = int(latent_shape[1])
    input_channels = checkpoint_payload.get("input_channels")
    output_channels = checkpoint_payload.get("output_channels")
    if (
        input_channels
        != latent_channels
        + CROSS_SCALE_CONDITION_CHANNELS
        + len(MASK_CLASSES)
        + 1
        + CONDITION_FEATURE_COUNT
    ):
        raise TorchTrainingError("checkpoint payload input_channels is incompatible")
    if output_channels != latent_channels:
        raise TorchTrainingError("checkpoint payload output_channels is incompatible")
    validate_denoiser_architecture(
        checkpoint_payload.get("denoiser_architecture"),
        input_channels,
        output_channels,
        "checkpoint payload",
    )


def validate_diffusion_schedule(diffusion: dict[str, Any], sample_steps: int) -> None:
    if diffusion.get("scheduler") != "linear_ddpm":
        raise TorchTrainingError("diffusion scheduler must be linear_ddpm")
    latent_source = diffusion.get("latent_source")
    if latent_source not in {"rgb_downsample_proxy", "trainable_vae_smoke"}:
        raise TorchTrainingError("diffusion latent_source is unsupported")
    if latent_source == "trainable_vae_smoke" and not isinstance(
        diffusion.get("vae_checkpoint_manifest_path"), str
    ):
        raise TorchTrainingError("diffusion VAE latent source missing vae_checkpoint_manifest_path")
    timesteps = diffusion.get("timesteps")
    latent_shape = diffusion.get("latent_batch_shape")
    beta_start = diffusion.get("beta_start")
    beta_end = diffusion.get("beta_end")
    if not isinstance(timesteps, int) or isinstance(timesteps, bool) or timesteps <= 0:
        raise TorchTrainingError("diffusion timesteps must be a positive integer")
    if sample_steps > timesteps:
        raise TorchTrainingError("sample_steps cannot exceed diffusion timesteps")
    if (
        not isinstance(latent_shape, list)
        or len(latent_shape) != 4
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in latent_shape)
    ):
        raise TorchTrainingError("diffusion latent_batch_shape must be four integer dimensions")
    if latent_shape[1] <= 0 or latent_shape[2] <= 0 or latent_shape[3] != latent_shape[2]:
        raise TorchTrainingError(
            "diffusion latent_batch_shape must be [batch, positive_channels, size, size]"
        )
    if latent_source == "rgb_downsample_proxy" and latent_shape[1] != 3:
        raise TorchTrainingError("rgb_downsample_proxy latent_batch_shape channel count must be 3")
    for name, value in (("beta_start", beta_start), ("beta_end", beta_end)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TorchTrainingError(f"diffusion {name} must be a number")
    if not 0 < float(beta_start) < float(beta_end) < 1:
        raise TorchTrainingError("diffusion beta schedule must satisfy 0 < beta_start < beta_end < 1")


def condition_feature_schema() -> dict[str, Any]:
    return {
        "feature_count": CONDITION_FEATURE_COUNT,
        "feature_names": list(CONDITION_FEATURE_NAMES),
        "features": [dict(feature) for feature in CONDITION_FEATURES],
        "spatial_injection": "concat_constant_feature_channels",
        "training_default_policy": (
            "training-index tile metadata sets coord/cascade features; unavailable "
            "style, texture, source, and structure_anchor features are zero for smoke training"
        ),
        "production_status": "smoke_condition_injection_only",
    }


def cross_scale_condition_schema() -> dict[str, Any]:
    return {
        "condition_name": "previous_scale_rgb_proxy",
        "channel_count": CROSS_SCALE_CONDITION_CHANNELS,
        "channel_order": ["red", "green", "blue"],
        "spatial_injection": "concat_previous_scale_rgb_proxy_channels",
        "training_source": "real_rgb_tile_coarse_to_target_proxy",
        "sampling_sources": ["previous_scale_condition_path", "default_zero_previous_scale"],
        "root_cascade_policy": "zero_previous_scale_condition_for_1/32",
        "production_status": "smoke_cross_scale_proxy_only_not_production",
    }


def validate_cross_scale_condition_schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise TorchTrainingError("checkpoint cross_scale_condition_schema must be an object")
    expected = cross_scale_condition_schema()
    for key, expected_value in expected.items():
        if schema.get(key) != expected_value:
            raise TorchTrainingError(
                f"checkpoint cross_scale_condition_schema {key} is incompatible"
            )


def denoiser_architecture(input_channels: int, output_channels: int) -> dict[str, Any]:
    return {
        "architecture": DENOISER_ARCHITECTURE_NAME,
        "base_channels": DENOISER_BASE_CHANNELS,
        "bottleneck_channels": DENOISER_BOTTLENECK_CHANNELS,
        "downsample_stages": 1,
        "skip_connections": "encoder_decoder_concat",
        "input_source": "latent_previous_scale_mask_timestep_condition_concat",
        "latent_sources_supported": ["rgb_downsample_proxy", "trainable_vae_smoke"],
        "input_channels": input_channels,
        "output_channels": output_channels,
        "production_status": "smoke_unet_only_not_production",
    }


def validate_denoiser_architecture(
    architecture: Any,
    input_channels: Any,
    output_channels: Any,
    location: str,
) -> None:
    if not isinstance(architecture, dict):
        raise TorchTrainingError(f"{location} denoiser_architecture must be an object")
    for key, value in (("input_channels", input_channels), ("output_channels", output_channels)):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise TorchTrainingError(f"{location} denoiser_architecture requires positive {key}")
    expected = denoiser_architecture(input_channels, output_channels)
    for key, expected_value in expected.items():
        if architecture.get(key) != expected_value:
            raise TorchTrainingError(
                f"{location} denoiser_architecture {key} is incompatible"
            )


def validate_condition_feature_schema(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise TorchTrainingError("checkpoint condition_feature_schema must be an object")
    if schema.get("feature_count") != CONDITION_FEATURE_COUNT:
        raise TorchTrainingError("checkpoint condition_feature_schema feature_count is incompatible")
    if schema.get("feature_names") != CONDITION_FEATURE_NAMES:
        raise TorchTrainingError("checkpoint condition_feature_schema feature_names are incompatible")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
