import hashlib
import json
from pathlib import Path
from typing import Any

from ..constants import MASK_CLASSES, MODEL_FAMILY, PROJECT_VERSION
from .training import ModelRunError, load_checkpoint_manifest
from .training_batch import TrainingBatchError, load_training_batch, training_batch_summary
from .torch_training_contracts import (
    CASCADE_LEVEL_SCALE,
    CONDITION_FEATURE_COUNT,
    CROSS_SCALE_CONDITION_CHANNELS,
    DENOISER_BASE_CHANNELS,
    DENOISER_BOTTLENECK_CHANNELS,
    TORCH_DIFFUSION_SMOKE_BACKEND,
    TORCH_DIFFUSION_SMOKE_SAMPLER,
    TORCH_SMOKE_BACKEND,
    TORCH_VAE_SMOKE_BACKEND,
    TorchTrainingError,
    checkpoint_manifest as _checkpoint_manifest,
    condition_feature_schema as _condition_feature_schema,
    cross_scale_condition_schema as _cross_scale_condition_schema,
    denoiser_architecture as _denoiser_architecture,
    diffusion_checkpoint_manifest as _diffusion_checkpoint_manifest,
    validate_diffusion_checkpoint_manifest as _validate_diffusion_checkpoint_manifest,
    validate_diffusion_checkpoint_payload as _validate_diffusion_checkpoint_payload,
    validate_vae_checkpoint_manifest as _validate_vae_checkpoint_manifest,
    validate_vae_checkpoint_payload as _validate_vae_checkpoint_payload,
    vae_checkpoint_manifest as _vae_checkpoint_manifest,
    vae_diffusion_manifest_fields as _vae_diffusion_manifest_fields,
)

CROSS_SCALE_PREVIOUS_LEVEL = {
    "1/32": None,
    "1/16": "1/32",
    "1/4": "1/16",
    "1/1": "1/4",
}
CROSS_SCALE_PROXY_DOWNSAMPLE_RATIO = {
    "1/16": 2,
    "1/4": 4,
    "1/1": 4,
}


def train_torch_smoke_model(
    training_index_path: str | Path,
    output_dir: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str = "1/1",
    epochs: int = 1,
    learning_rate: float = 1e-3,
    random_seed: int = 0,
    device: str = "cpu",
) -> dict[str, Any]:
    _validate_training_args(epochs, learning_rate, random_seed, device)
    torch = _import_torch()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise TorchTrainingError(f"output_dir already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    try:
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            split=split,
            cascade_level=cascade_level,
            include_image=True,
        )
    except TrainingBatchError as exc:
        raise TorchTrainingError(str(exc)) from exc

    torch.manual_seed(random_seed)
    device_obj = torch.device(device)
    if device_obj.type != "cpu" and not torch.cuda.is_available():
        raise TorchTrainingError(f"requested device is unavailable: {device}")

    model = _MaskConditionedRgbReconstructor(torch, class_count=len(MASK_CLASSES)).to(device_obj)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    mask_targets = torch.as_tensor(batch["mask_batch"], dtype=torch.long, device=device_obj)
    inputs = torch.nn.functional.one_hot(mask_targets, num_classes=len(MASK_CLASSES))
    inputs = inputs.permute(0, 3, 1, 2).to(dtype=torch.float32)
    # Smoke training now validates the image-generation data path: mask conditions
    # are the model input, and RGB image tiles are the reconstruction target.
    image_targets = torch.as_tensor(batch["image_batch"], dtype=torch.float32, device=device_obj)
    image_targets = image_targets.permute(0, 3, 1, 2) / 255.0

    log_path = output / "training_log.jsonl"
    loss_history: list[float] = []
    with log_path.open("w", encoding="utf-8") as log_handle:
        for epoch in range(1, epochs + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            reconstructed = model(inputs)
            loss = torch.nn.functional.mse_loss(reconstructed, image_targets)
            loss_value = float(loss.detach().cpu().item())
            if not torch.isfinite(loss).item():
                raise TorchTrainingError(f"non-finite loss at epoch {epoch}: {loss_value}")
            loss.backward()
            optimizer.step()
            loss_history.append(loss_value)
            log_handle.write(
                json.dumps(
                    {
                        "schema_version": PROJECT_VERSION,
                        "epoch": epoch,
                        "loss": loss_value,
                        "loss_name": "mse_rgb_reconstruction",
                        "backend": TORCH_SMOKE_BACKEND,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    checkpoint_path = output / "model.pt"
    checkpoint_payload = {
        "schema_version": PROJECT_VERSION,
        "backend": TORCH_SMOKE_BACKEND,
        "model_family": MODEL_FAMILY,
        "state_dict": model.state_dict(),
        "target_type": "rgb_image",
        "input_channels": len(MASK_CLASSES),
        "output_channels": 3,
        "mask_classes": list(MASK_CLASSES),
        "image_dtype": batch["image_dtype"],
        "cascade_level": cascade_level,
        "random_seed": random_seed,
        "loss_history": loss_history,
    }
    torch.save(checkpoint_payload, checkpoint_path)
    checkpoint_hash = _sha256_file(checkpoint_path)
    manifest = _checkpoint_manifest(
        torch=torch,
        training_index_path=training_index_path,
        checkpoint_path=checkpoint_path,
        checkpoint_hash=checkpoint_hash,
        log_path=log_path,
        batch_summary=training_batch_summary(batch),
        epochs=epochs,
        learning_rate=learning_rate,
        random_seed=random_seed,
        device=device,
        loss_history=loss_history,
    )
    manifest_path = output / "checkpoint_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    run = {
        "schema_version": PROJECT_VERSION,
        "status": "completed",
        "training_backend": TORCH_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "output_dir": str(output),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_manifest_path": str(manifest_path),
        "training_log_path": str(log_path),
        "loss_history": loss_history,
    }
    run_path = output / "training_run.json"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def train_torch_vae_smoke_model(
    training_index_path: str | Path,
    output_dir: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str = "1/1",
    epochs: int = 1,
    learning_rate: float = 1e-3,
    random_seed: int = 0,
    device: str = "cpu",
    latent_channels: int = 4,
    latent_size: int = 64,
    kl_weight: float = 1e-4,
) -> dict[str, Any]:
    _validate_training_args(epochs, learning_rate, random_seed, device)
    _validate_vae_args(latent_channels, latent_size, kl_weight)
    torch = _import_torch()
    numpy = _import_numpy()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise TorchTrainingError(f"output_dir already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    try:
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            split=split,
            cascade_level=cascade_level,
            include_image=True,
        )
    except TrainingBatchError as exc:
        raise TorchTrainingError(str(exc)) from exc

    torch.manual_seed(random_seed)
    device_obj = torch.device(device)
    if device_obj.type != "cpu" and not torch.cuda.is_available():
        raise TorchTrainingError(f"requested device is unavailable: {device}")

    image_targets = torch.as_tensor(batch["image_batch"], dtype=torch.float32, device=device_obj)
    image_targets = image_targets.permute(0, 3, 1, 2) / 255.0
    # The smoke VAE trains on a bounded downsampled RGB target so the encoder,
    # reparameterization, decoder, and KL path are exercised without claiming a
    # production-scale VAE for full-resolution WSI tiles.
    vae_targets = torch.nn.functional.interpolate(
        image_targets,
        size=(latent_size, latent_size),
        mode="area",
    )
    model = _RgbVaeSmokeAutoencoder(
        torch,
        latent_channels=latent_channels,
    ).to(device_obj)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    log_path = output / "training_log.jsonl"
    loss_history: list[float] = []
    reconstruction_loss_history: list[float] = []
    kl_loss_history: list[float] = []
    with log_path.open("w", encoding="utf-8") as log_handle:
        for epoch in range(1, epochs + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            reconstruction, mu, logvar = model(vae_targets)
            reconstruction_loss = torch.nn.functional.mse_loss(reconstruction, vae_targets)
            kl_loss = -0.5 * torch.mean(1.0 + logvar - mu.pow(2) - logvar.exp())
            loss = reconstruction_loss + kl_weight * kl_loss
            loss_value = float(loss.detach().cpu().item())
            reconstruction_loss_value = float(reconstruction_loss.detach().cpu().item())
            kl_loss_value = float(kl_loss.detach().cpu().item())
            if not torch.isfinite(loss).item():
                raise TorchTrainingError(f"non-finite loss at epoch {epoch}: {loss_value}")
            loss.backward()
            optimizer.step()
            loss_history.append(loss_value)
            reconstruction_loss_history.append(reconstruction_loss_value)
            kl_loss_history.append(kl_loss_value)
            log_handle.write(
                json.dumps(
                    {
                        "schema_version": PROJECT_VERSION,
                        "epoch": epoch,
                        "loss": loss_value,
                        "reconstruction_loss": reconstruction_loss_value,
                        "kl_loss": kl_loss_value,
                        "kl_weight": kl_weight,
                        "loss_name": "mse_rgb_reconstruction_plus_kl",
                        "backend": TORCH_VAE_SMOKE_BACKEND,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    model.eval()
    with torch.no_grad():
        reconstruction, mu, logvar = model(vae_targets)
    latent_preview = mu.permute(0, 2, 3, 1).detach().cpu().numpy().astype(numpy.float32)
    reconstruction_preview = (reconstruction.clamp(0.0, 1.0) * 255.0).round()
    reconstruction_preview = (
        reconstruction_preview.permute(0, 2, 3, 1)
        .to(dtype=torch.uint8)
        .detach()
        .cpu()
        .numpy()
    )
    latent_preview_path = output / "latent_preview.npy"
    reconstruction_preview_path = output / "reconstruction_preview.npy"
    numpy.save(latent_preview_path, latent_preview)
    numpy.save(reconstruction_preview_path, reconstruction_preview)

    latent_batch_shape = [int(value) for value in mu.shape]
    checkpoint_path = output / "model.pt"
    checkpoint_payload = {
        "schema_version": PROJECT_VERSION,
        "backend": TORCH_VAE_SMOKE_BACKEND,
        "model_family": MODEL_FAMILY,
        "state_dict": model.state_dict(),
        "target_type": "vae_rgb_reconstruction",
        "latent_source": "trainable_vae_smoke",
        "latent_channels": latent_channels,
        "latent_size": latent_size,
        "latent_batch_shape": latent_batch_shape,
        "input_channels": 3,
        "output_channels": 3,
        "image_dtype": batch["image_dtype"],
        "cascade_level": cascade_level,
        "random_seed": random_seed,
        "kl_weight": kl_weight,
        "loss_history": loss_history,
        "reconstruction_loss_history": reconstruction_loss_history,
        "kl_loss_history": kl_loss_history,
    }
    torch.save(checkpoint_payload, checkpoint_path)
    checkpoint_hash = _sha256_file(checkpoint_path)
    manifest = _vae_checkpoint_manifest(
        torch=torch,
        training_index_path=training_index_path,
        checkpoint_path=checkpoint_path,
        checkpoint_hash=checkpoint_hash,
        log_path=log_path,
        latent_preview_path=latent_preview_path,
        reconstruction_preview_path=reconstruction_preview_path,
        batch_summary=training_batch_summary(batch),
        epochs=epochs,
        learning_rate=learning_rate,
        random_seed=random_seed,
        device=device,
        latent_channels=latent_channels,
        latent_size=latent_size,
        latent_batch_shape=latent_batch_shape,
        kl_weight=kl_weight,
        loss_history=loss_history,
        reconstruction_loss_history=reconstruction_loss_history,
        kl_loss_history=kl_loss_history,
    )
    manifest_path = output / "checkpoint_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    run = {
        "schema_version": PROJECT_VERSION,
        "status": "completed",
        "training_backend": TORCH_VAE_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "output_dir": str(output),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_manifest_path": str(manifest_path),
        "training_log_path": str(log_path),
        "latent_preview_path": str(latent_preview_path),
        "reconstruction_preview_path": str(reconstruction_preview_path),
        "loss_history": loss_history,
        "reconstruction_loss_history": reconstruction_loss_history,
        "kl_loss_history": kl_loss_history,
    }
    run_path = output / "training_run.json"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def train_torch_diffusion_smoke_model(
    training_index_path: str | Path,
    output_dir: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str = "1/1",
    epochs: int = 1,
    learning_rate: float = 1e-3,
    random_seed: int = 0,
    device: str = "cpu",
    diffusion_timesteps: int = 16,
    beta_start: float = 1e-4,
    beta_end: float = 0.02,
    latent_size: int = 64,
    vae_checkpoint_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    _validate_training_args(epochs, learning_rate, random_seed, device)
    _validate_diffusion_args(diffusion_timesteps, beta_start, beta_end, latent_size)
    torch = _import_torch()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise TorchTrainingError(f"output_dir already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    try:
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            split=split,
            cascade_level=cascade_level,
            include_image=True,
        )
    except TrainingBatchError as exc:
        raise TorchTrainingError(str(exc)) from exc

    torch.manual_seed(random_seed)
    device_obj = torch.device(device)
    if device_obj.type != "cpu" and not torch.cuda.is_available():
        raise TorchTrainingError(f"requested device is unavailable: {device}")

    vae_components = None
    if vae_checkpoint_manifest_path is not None:
        vae_components = _load_vae_smoke_components(
            torch,
            vae_checkpoint_manifest_path,
            device_obj,
        )
        vae_latent_size = int(vae_components["manifest"]["latent_size"])
        if latent_size != vae_latent_size:
            raise TorchTrainingError("latent_size must match VAE checkpoint latent_size")

    mask_targets = torch.as_tensor(batch["mask_batch"], dtype=torch.long, device=device_obj)
    mask_conditions = torch.nn.functional.one_hot(mask_targets, num_classes=len(MASK_CLASSES))
    mask_conditions = mask_conditions.permute(0, 3, 1, 2).to(dtype=torch.float32)
    mask_conditions = torch.nn.functional.interpolate(
        mask_conditions,
        size=(latent_size, latent_size),
        mode="nearest",
    )
    image_targets = torch.as_tensor(batch["image_batch"], dtype=torch.float32, device=device_obj)
    image_targets = image_targets.permute(0, 3, 1, 2) / 255.0
    condition_features = _batch_condition_feature_channels(torch, batch, latent_size, device_obj)
    cross_scale_condition = _training_cross_scale_condition_channels(
        torch,
        image_targets,
        cascade_level,
        latent_size,
        device_obj,
    )
    if vae_components is None:
        # This is a bounded smoke-test latent: it verifies DDPM-style mechanics on a
        # downsampled RGB proxy while keeping memory small and explicitly avoiding a
        # fake VAE claim.
        latents = torch.nn.functional.interpolate(
            image_targets,
            size=(latent_size, latent_size),
            mode="area",
        )
        latent_source = "rgb_downsample_proxy"
        latent_channels = 3
        output_channels = 3
    else:
        with torch.no_grad():
            latents = _encode_vae_smoke_mu(
                torch,
                vae_components["model"],
                image_targets,
                latent_size,
            )
        latent_source = "trainable_vae_smoke"
        latent_channels = int(vae_components["manifest"]["latent_channels"])
        output_channels = latent_channels
    latent_batch_shape = [int(value) for value in latents.shape]

    betas = torch.linspace(beta_start, beta_end, diffusion_timesteps, device=device_obj)
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)
    input_channels = (
        latent_channels
        + CROSS_SCALE_CONDITION_CHANNELS
        + len(MASK_CLASSES)
        + 1
        + CONDITION_FEATURE_COUNT
    )
    denoiser_architecture = _denoiser_architecture(input_channels, output_channels)
    model = _MaskConditionedLatentDenoiser(
        torch,
        input_channels=input_channels,
        output_channels=output_channels,
    ).to(device_obj)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    log_path = output / "training_log.jsonl"
    loss_history: list[float] = []
    with log_path.open("w", encoding="utf-8") as log_handle:
        for epoch in range(1, epochs + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            timesteps = torch.randint(
                0,
                diffusion_timesteps,
                (latents.shape[0],),
                device=device_obj,
            )
            noise = torch.randn_like(latents)
            alpha_bar = alpha_bars[timesteps].view(-1, 1, 1, 1)
            noisy_latents = alpha_bar.sqrt() * latents + (1.0 - alpha_bar).sqrt() * noise
            time_denominator = float(max(diffusion_timesteps - 1, 1))
            time_channel = timesteps.to(dtype=torch.float32).view(-1, 1, 1, 1) / time_denominator
            time_channel = time_channel.expand(-1, 1, latent_size, latent_size)
            inputs = torch.cat(
                [
                    noisy_latents,
                    cross_scale_condition,
                    mask_conditions,
                    time_channel,
                    condition_features,
                ],
                dim=1,
            )
            predicted_noise = model(inputs)
            loss = torch.nn.functional.mse_loss(predicted_noise, noise)
            loss_value = float(loss.detach().cpu().item())
            if not torch.isfinite(loss).item():
                raise TorchTrainingError(f"non-finite loss at epoch {epoch}: {loss_value}")
            loss.backward()
            optimizer.step()
            loss_history.append(loss_value)
            log_handle.write(
                json.dumps(
                    {
                        "schema_version": PROJECT_VERSION,
                        "epoch": epoch,
                        "loss": loss_value,
                        "loss_name": "mse_noise_prediction",
                        "backend": TORCH_DIFFUSION_SMOKE_BACKEND,
                        "timestep_min": int(timesteps.min().detach().cpu().item()),
                        "timestep_max": int(timesteps.max().detach().cpu().item()),
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    diffusion = {
        "scheduler": "linear_ddpm",
        "timesteps": diffusion_timesteps,
        "beta_start": beta_start,
        "beta_end": beta_end,
        "latent_source": latent_source,
        "latent_batch_shape": latent_batch_shape,
    }
    if vae_checkpoint_manifest_path is not None:
        diffusion["vae_checkpoint_manifest_path"] = str(vae_checkpoint_manifest_path)
        diffusion["vae_checkpoint_sha256"] = vae_components["manifest"]["checkpoint_sha256"]
    checkpoint_path = output / "model.pt"
    checkpoint_payload = {
        "schema_version": PROJECT_VERSION,
        "backend": TORCH_DIFFUSION_SMOKE_BACKEND,
        "model_family": MODEL_FAMILY,
        "state_dict": model.state_dict(),
        "target_type": "diffusion_noise",
        "input_channels": input_channels,
        "output_channels": output_channels,
        "denoiser_architecture": denoiser_architecture,
        "cross_scale_condition_schema": _cross_scale_condition_schema(),
        "condition_feature_schema": _condition_feature_schema(),
        "mask_classes": list(MASK_CLASSES),
        "image_dtype": batch["image_dtype"],
        "cascade_level": cascade_level,
        "random_seed": random_seed,
        "diffusion": diffusion,
        "loss_history": loss_history,
    }
    torch.save(checkpoint_payload, checkpoint_path)
    checkpoint_hash = _sha256_file(checkpoint_path)
    manifest = _diffusion_checkpoint_manifest(
        torch=torch,
        training_index_path=training_index_path,
        checkpoint_path=checkpoint_path,
        checkpoint_hash=checkpoint_hash,
        log_path=log_path,
        batch_summary=training_batch_summary(batch),
        epochs=epochs,
        learning_rate=learning_rate,
        random_seed=random_seed,
        device=device,
        loss_history=loss_history,
        diffusion=diffusion,
        input_channels=input_channels,
        output_channels=output_channels,
        denoiser_architecture=denoiser_architecture,
        cross_scale_condition_schema=_cross_scale_condition_schema(),
    )
    manifest_path = output / "checkpoint_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    run = {
        "schema_version": PROJECT_VERSION,
        "status": "completed",
        "training_backend": TORCH_DIFFUSION_SMOKE_BACKEND,
        "training_index_path": str(training_index_path),
        "output_dir": str(output),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_manifest_path": str(manifest_path),
        "training_log_path": str(log_path),
        "loss_history": loss_history,
    }
    run_path = output / "training_run.json"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def sample_torch_diffusion_smoke_model(
    checkpoint_manifest_path: str | Path,
    training_index_path: str | Path,
    output_dir: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str = "1/1",
    sample_steps: int = 8,
    random_seed: int = 0,
    device: str = "cpu",
    condition_packet_path: str | Path | None = None,
    expected_prior_id: str | None = None,
    previous_scale_condition_path: str | Path | None = None,
) -> dict[str, Any]:
    _validate_sampling_args(sample_steps, random_seed, device)
    torch = _import_torch()
    numpy = _import_numpy()
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise TorchTrainingError(f"output_dir already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    try:
        checkpoint_manifest = load_checkpoint_manifest(checkpoint_manifest_path)
    except ModelRunError as exc:
        raise TorchTrainingError(str(exc)) from exc
    _validate_diffusion_checkpoint_manifest(checkpoint_manifest, sample_steps)

    try:
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            split=split,
            cascade_level=cascade_level,
            include_image=False,
        )
    except TrainingBatchError as exc:
        raise TorchTrainingError(str(exc)) from exc
    condition_packet = _load_condition_packet(condition_packet_path, expected_prior_id)

    torch.manual_seed(random_seed)
    device_obj = torch.device(device)
    if device_obj.type != "cpu" and not torch.cuda.is_available():
        raise TorchTrainingError(f"requested device is unavailable: {device}")

    checkpoint_path = Path(checkpoint_manifest["checkpoint_path"])
    if not checkpoint_path.exists():
        raise TorchTrainingError(f"checkpoint file does not exist: {checkpoint_path}")
    try:
        checkpoint_payload = torch.load(checkpoint_path, map_location=device_obj, weights_only=False)
    except Exception as exc:
        raise TorchTrainingError(f"checkpoint file cannot be loaded: {checkpoint_path}") from exc
    _validate_diffusion_checkpoint_payload(checkpoint_payload)
    if checkpoint_payload["denoiser_architecture"] != checkpoint_manifest["denoiser_architecture"]:
        raise TorchTrainingError("checkpoint payload denoiser_architecture does not match manifest")
    if (
        checkpoint_payload["cross_scale_condition_schema"]
        != checkpoint_manifest["cross_scale_condition_schema"]
    ):
        raise TorchTrainingError(
            "checkpoint payload cross_scale_condition_schema does not match manifest"
        )

    diffusion = checkpoint_payload["diffusion"]
    latent_shape = diffusion["latent_batch_shape"]
    latent_channels = int(latent_shape[1])
    latent_size = int(latent_shape[2])
    diffusion_timesteps = int(diffusion["timesteps"])
    beta_start = float(diffusion["beta_start"])
    beta_end = float(diffusion["beta_end"])
    input_channels = int(checkpoint_payload["input_channels"])
    output_channels = int(checkpoint_payload["output_channels"])
    vae_components = None
    if diffusion["latent_source"] == "trainable_vae_smoke":
        vae_components = _load_vae_smoke_components(
            torch,
            diffusion["vae_checkpoint_manifest_path"],
            device_obj,
        )

    mask_targets = torch.as_tensor(batch["mask_batch"], dtype=torch.long, device=device_obj)
    mask_conditions = torch.nn.functional.one_hot(mask_targets, num_classes=len(MASK_CLASSES))
    mask_conditions = mask_conditions.permute(0, 3, 1, 2).to(dtype=torch.float32)
    mask_conditions = torch.nn.functional.interpolate(
        mask_conditions,
        size=(latent_size, latent_size),
        mode="nearest",
    )
    condition_feature_vector = _sample_condition_feature_vector(condition_packet)
    condition_features = _sample_condition_feature_channels(
        torch,
        condition_feature_vector,
        batch_size,
        latent_size,
        device_obj,
    )
    cross_scale_condition = _sample_cross_scale_condition_channels(
        torch,
        numpy,
        previous_scale_condition_path,
        batch_size,
        latent_size,
        device_obj,
    )
    model = _MaskConditionedLatentDenoiser(
        torch,
        input_channels=input_channels,
        output_channels=output_channels,
    ).to(device_obj)
    model.load_state_dict(checkpoint_payload["state_dict"])
    model.eval()

    betas = torch.linspace(beta_start, beta_end, diffusion_timesteps, device=device_obj)
    alphas = 1.0 - betas
    alpha_bars = torch.cumprod(alphas, dim=0)
    sample = torch.randn((batch_size, latent_channels, latent_size, latent_size), device=device_obj)
    timestep_schedule = torch.linspace(
        diffusion_timesteps - 1,
        0,
        sample_steps,
        device=device_obj,
    ).round().to(dtype=torch.long)
    with torch.no_grad():
        for timestep in timestep_schedule:
            timestep_index = int(timestep.detach().cpu().item())
            time_denominator = float(max(diffusion_timesteps - 1, 1))
            time_channel = torch.full(
                (batch_size, 1, latent_size, latent_size),
                timestep_index / time_denominator,
                dtype=torch.float32,
                device=device_obj,
            )
            predicted_noise = model(
                torch.cat(
                    [
                        sample,
                        cross_scale_condition["channels"],
                        mask_conditions,
                        time_channel,
                        condition_features,
                    ],
                    dim=1,
                )
            )
            if predicted_noise.shape[1] != output_channels:
                raise TorchTrainingError("diffusion checkpoint output_channels is incompatible")
            alpha_t = alphas[timestep_index]
            alpha_bar_t = alpha_bars[timestep_index]
            beta_t = betas[timestep_index]
            sample = (sample - (beta_t / torch.sqrt(1.0 - alpha_bar_t)) * predicted_noise)
            sample = sample / torch.sqrt(alpha_t)
            if timestep_index > 0:
                sample = sample + torch.sqrt(beta_t) * torch.randn_like(sample)

    latent_preview = sample.permute(0, 2, 3, 1).detach().cpu().numpy()
    if vae_components is None:
        decoded = sample.clamp(0.0, 1.0)
    else:
        with torch.no_grad():
            decoded = vae_components["model"].decoder(sample).clamp(0.0, 1.0)
    preview = (decoded * 255.0).round()
    preview = preview.permute(0, 2, 3, 1).to(dtype=torch.uint8).detach().cpu().numpy()
    preview_path = output / "sample_preview.npy"
    numpy.save(preview_path, preview)
    sample_manifest = {
        "schema_version": PROJECT_VERSION,
        "status": "completed",
        "sampling_backend": TORCH_DIFFUSION_SMOKE_SAMPLER,
        "checkpoint_manifest_path": str(checkpoint_manifest_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_training_backend": checkpoint_manifest["training_backend"],
        "training_index_path": str(training_index_path),
        "sample_preview_path": str(preview_path),
        "latent_sample_shape": [int(value) for value in latent_preview.shape],
        "sample_shape": [int(value) for value in preview.shape],
        "sample_dtype": str(preview.dtype),
        "sample_steps": sample_steps,
        "random_seed": random_seed,
        "condition_feature_schema": _condition_feature_schema(),
        "denoiser_architecture": checkpoint_payload["denoiser_architecture"],
        "cross_scale_condition_schema": _cross_scale_condition_schema(),
        "cross_scale_condition_source": cross_scale_condition["source"],
        "cross_scale_condition_shape": cross_scale_condition["shape"],
        "condition_feature_source": (
            "condition_packet" if condition_packet is not None else "default_zero"
        ),
        "condition_feature_vector": condition_feature_vector,
        "diffusion": {
            "scheduler": diffusion["scheduler"],
            "timesteps": diffusion_timesteps,
            "beta_start": beta_start,
            "beta_end": beta_end,
            "latent_source": diffusion["latent_source"],
            "latent_batch_shape": [int(value) for value in latent_shape],
            **_vae_diffusion_manifest_fields(diffusion),
        },
        "batch_summary": training_batch_summary(batch),
        "usable_for_production": False,
        "note": (
            "Smoke sampler validates reverse DDPM-style mechanics on downsampled RGB proxy "
            "latents only; it is not a production WSI diffusion inference backend."
        ),
    }
    if condition_packet is not None:
        sample_manifest["condition_packet_path"] = condition_packet["path"]
        sample_manifest["condition_summary"] = condition_packet["summary"]
    if cross_scale_condition["path"] is not None:
        sample_manifest["previous_scale_condition_path"] = cross_scale_condition["path"]
    manifest_path = output / "sample_manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest, indent=2) + "\n", encoding="utf-8")
    return {**sample_manifest, "sample_manifest_path": str(manifest_path)}


def _validate_training_args(
    epochs: int,
    learning_rate: float,
    random_seed: int,
    device: str,
) -> None:
    if not isinstance(epochs, int) or isinstance(epochs, bool) or epochs <= 0:
        raise TorchTrainingError("epochs must be a positive integer")
    if not isinstance(learning_rate, (int, float)) or isinstance(learning_rate, bool):
        raise TorchTrainingError("learning_rate must be a positive number")
    if learning_rate <= 0:
        raise TorchTrainingError("learning_rate must be a positive number")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise TorchTrainingError("random_seed must be an integer")
    if not isinstance(device, str) or device == "":
        raise TorchTrainingError("device must be a non-empty string")


def _validate_sampling_args(sample_steps: int, random_seed: int, device: str) -> None:
    if not isinstance(sample_steps, int) or isinstance(sample_steps, bool) or sample_steps <= 0:
        raise TorchTrainingError("sample_steps must be a positive integer")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise TorchTrainingError("random_seed must be an integer")
    if not isinstance(device, str) or device == "":
        raise TorchTrainingError("device must be a non-empty string")


def _validate_diffusion_args(
    diffusion_timesteps: int,
    beta_start: float,
    beta_end: float,
    latent_size: int,
) -> None:
    if (
        not isinstance(diffusion_timesteps, int)
        or isinstance(diffusion_timesteps, bool)
        or diffusion_timesteps <= 0
    ):
        raise TorchTrainingError("diffusion_timesteps must be a positive integer")
    if not isinstance(latent_size, int) or isinstance(latent_size, bool) or latent_size <= 0:
        raise TorchTrainingError("latent_size must be a positive integer")
    for name, value in (("beta_start", beta_start), ("beta_end", beta_end)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TorchTrainingError(f"{name} must be a number between 0 and 1")
    if not 0 < beta_start < beta_end < 1:
        raise TorchTrainingError("beta schedule must satisfy 0 < beta_start < beta_end < 1")


def _validate_vae_args(latent_channels: int, latent_size: int, kl_weight: float) -> None:
    if (
        not isinstance(latent_channels, int)
        or isinstance(latent_channels, bool)
        or latent_channels <= 0
    ):
        raise TorchTrainingError("latent_channels must be a positive integer")
    if not isinstance(latent_size, int) or isinstance(latent_size, bool) or latent_size <= 0:
        raise TorchTrainingError("latent_size must be a positive integer")
    if not isinstance(kl_weight, (int, float)) or isinstance(kl_weight, bool) or kl_weight < 0:
        raise TorchTrainingError("kl_weight must be a non-negative number")


def _load_vae_smoke_components(
    torch,
    vae_checkpoint_manifest_path: str | Path,
    device_obj,
) -> dict[str, Any]:
    try:
        manifest = load_checkpoint_manifest(vae_checkpoint_manifest_path)
    except ModelRunError as exc:
        raise TorchTrainingError(str(exc)) from exc
    _validate_vae_checkpoint_manifest(manifest)
    checkpoint_path = Path(manifest["checkpoint_path"])
    if not checkpoint_path.exists():
        raise TorchTrainingError(f"VAE checkpoint file does not exist: {checkpoint_path}")
    try:
        payload = torch.load(checkpoint_path, map_location=device_obj, weights_only=False)
    except Exception as exc:
        raise TorchTrainingError(f"VAE checkpoint file cannot be loaded: {checkpoint_path}") from exc
    _validate_vae_checkpoint_payload(payload, manifest)
    model = _RgbVaeSmokeAutoencoder(
        torch,
        latent_channels=int(manifest["latent_channels"]),
    ).to(device_obj)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return {"manifest": manifest, "payload": payload, "model": model}


def _encode_vae_smoke_mu(torch, vae_model, image_targets, latent_size: int):
    vae_targets = torch.nn.functional.interpolate(
        image_targets,
        size=(latent_size, latent_size),
        mode="area",
    )
    encoded = vae_model.encoder(vae_targets)
    mu, _logvar = torch.chunk(encoded, 2, dim=1)
    return mu


def _batch_condition_feature_channels(torch, batch: dict[str, Any], latent_size: int, device_obj):
    vectors = [
        _training_condition_feature_vector(sample_id, tile_record)
        for sample_id, tile_record in zip(batch["sample_ids"], batch["tile_records"], strict=True)
    ]
    tensor = torch.tensor(vectors, dtype=torch.float32, device=device_obj)
    return tensor.view(len(vectors), CONDITION_FEATURE_COUNT, 1, 1).expand(
        -1,
        -1,
        latent_size,
        latent_size,
    )


def _training_condition_feature_vector(sample_id: str, tile_record: dict[str, Any]) -> list[float]:
    # Training-index records do not yet carry learned style/texture/source priors.
    # The smoke trainer still exercises the real model-input path by using
    # deterministic spatial metadata for coord/cascade channels and zeroing the
    # unavailable learned-prior channels instead of pretending they were learned.
    cascade_level = _cascade_level_from_sample_id(sample_id)
    summary = {
        "style_seed_value": 0,
        "texture_cluster_id": 0,
        "tile_origin_40x": [tile_record["x"], tile_record["y"]],
        "cascade_level": cascade_level,
        "source_condition_enabled": False,
        "structure_anchor": 0.0,
    }
    return _condition_feature_vector_from_summary(summary, strict=False)


def _sample_condition_feature_vector(condition_packet: dict[str, Any] | None) -> list[float]:
    if condition_packet is None:
        return [0.0] * CONDITION_FEATURE_COUNT
    return _condition_feature_vector_from_summary(condition_packet["summary"], strict=True)


def _sample_condition_feature_channels(
    torch,
    feature_vector: list[float],
    batch_size: int,
    latent_size: int,
    device_obj,
):
    tensor = torch.tensor(feature_vector, dtype=torch.float32, device=device_obj)
    return tensor.view(1, CONDITION_FEATURE_COUNT, 1, 1).expand(
        batch_size,
        -1,
        latent_size,
        latent_size,
    )


def _training_cross_scale_condition_channels(
    torch,
    image_targets,
    cascade_level: str,
    latent_size: int,
    device_obj,
):
    previous_level = CROSS_SCALE_PREVIOUS_LEVEL.get(cascade_level)
    if previous_level is None:
        return torch.zeros(
            (
                image_targets.shape[0],
                CROSS_SCALE_CONDITION_CHANNELS,
                latent_size,
                latent_size,
            ),
            dtype=torch.float32,
            device=device_obj,
        )
    ratio = CROSS_SCALE_PROXY_DOWNSAMPLE_RATIO[cascade_level]
    coarse_size = max(1, latent_size // ratio)
    coarse = torch.nn.functional.interpolate(
        image_targets,
        size=(coarse_size, coarse_size),
        mode="area",
    )
    # Smoke training has no previous generated cascade yet. This proxy preserves
    # the real RGB tile source, degrades it to the previous cascade scale, and
    # upsamples it to the target latent grid so the denoiser consumes a real
    # cross-scale tensor without claiming production cascade inference.
    return torch.nn.functional.interpolate(
        coarse,
        size=(latent_size, latent_size),
        mode="bilinear",
        align_corners=False,
    )


def _sample_cross_scale_condition_channels(
    torch,
    numpy,
    previous_scale_condition_path: str | Path | None,
    batch_size: int,
    latent_size: int,
    device_obj,
) -> dict[str, Any]:
    if previous_scale_condition_path is None:
        channels = torch.zeros(
            (
                batch_size,
                CROSS_SCALE_CONDITION_CHANNELS,
                latent_size,
                latent_size,
            ),
            dtype=torch.float32,
            device=device_obj,
        )
        return {
            "channels": channels,
            "source": "default_zero_previous_scale",
            "path": None,
            "shape": [int(value) for value in channels.shape],
        }

    path = Path(previous_scale_condition_path)
    if not path.exists():
        raise TorchTrainingError(f"previous_scale_condition_path does not exist: {path}")
    if not path.is_file():
        raise TorchTrainingError(f"previous_scale_condition_path is not a file: {path}")
    try:
        array = numpy.load(path)
    except Exception as exc:
        raise TorchTrainingError(f"previous_scale_condition_path cannot be loaded: {path}") from exc
    if array.ndim == 3:
        array = array[numpy.newaxis, ...]
    if array.ndim != 4 or array.shape[-1] != CROSS_SCALE_CONDITION_CHANNELS:
        raise TorchTrainingError(
            "previous_scale_condition_path must contain [batch, height, width, 3] RGB data"
        )
    if array.shape[0] == 1 and batch_size > 1:
        array = numpy.repeat(array, batch_size, axis=0)
    if array.shape[0] != batch_size:
        raise TorchTrainingError("previous_scale_condition_path batch dimension is incompatible")
    if not numpy.issubdtype(array.dtype, numpy.number):
        raise TorchTrainingError("previous_scale_condition_path must contain numeric RGB data")
    tensor = torch.as_tensor(array, dtype=torch.float32, device=device_obj).permute(0, 3, 1, 2)
    if tensor.numel() == 0 or not torch.isfinite(tensor).all().item():
        raise TorchTrainingError("previous_scale_condition_path contains non-finite RGB data")
    if float(tensor.max().detach().cpu().item()) > 1.0:
        tensor = tensor / 255.0
    tensor = tensor.clamp(0.0, 1.0)
    if tensor.shape[-2:] != (latent_size, latent_size):
        tensor = torch.nn.functional.interpolate(
            tensor,
            size=(latent_size, latent_size),
            mode="bilinear",
            align_corners=False,
        )
    return {
        "channels": tensor,
        "source": "previous_scale_condition_path",
        "path": str(path),
        "shape": [int(value) for value in tensor.shape],
    }


def _condition_feature_vector_from_summary(
    summary: dict[str, Any],
    strict: bool,
) -> list[float]:
    tile_origin = summary.get("tile_origin_40x")
    if not isinstance(tile_origin, list) or len(tile_origin) < 2:
        if strict:
            raise TorchTrainingError("condition packet coord.tile_origin_40x must contain x and y")
        tile_origin = [0, 0]
    cascade_level = summary.get("cascade_level")
    if cascade_level not in CASCADE_LEVEL_SCALE:
        if strict:
            raise TorchTrainingError("condition packet coord.cascade_level is unsupported")
        cascade_level = "1/32"
    return [
        _normalized_number(summary.get("style_seed_value"), 10000.0, "style_seed.value", strict),
        _normalized_number(
            summary.get("texture_cluster_id"),
            1000.0,
            "texture_token.cluster_id",
            strict,
        ),
        _normalized_number(tile_origin[0], 100000.0, "coord.tile_origin_40x[0]", strict),
        _normalized_number(tile_origin[1], 100000.0, "coord.tile_origin_40x[1]", strict),
        CASCADE_LEVEL_SCALE[cascade_level],
        1.0 if summary.get("source_condition_enabled") else 0.0,
        _normalized_number(summary.get("structure_anchor"), 1.0, "structure_anchor.value", strict),
    ]


def _normalized_number(value: Any, denominator: float, field_name: str, strict: bool) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        if strict:
            raise TorchTrainingError(f"condition packet {field_name} must be numeric")
        value = 0.0
    return round(_clamp01(float(value) / denominator), 6)


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _cascade_level_from_sample_id(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) >= 2 and parts[1] in CASCADE_LEVEL_SCALE:
        return parts[1]
    return "1/32"


def _load_condition_packet(
    condition_packet_path: str | Path | None,
    expected_prior_id: str | None = None,
) -> dict[str, Any] | None:
    if condition_packet_path is None:
        return None
    path = Path(condition_packet_path)
    if not path.exists():
        raise TorchTrainingError(f"condition packet does not exist: {path}")
    if not path.is_file():
        raise TorchTrainingError(f"condition packet path is not a file: {path}")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TorchTrainingError(f"condition packet is not valid JSON: {exc.msg}") from exc
    if not isinstance(packet, dict):
        raise TorchTrainingError("condition packet must be a JSON object")
    if packet.get("schema_version") != PROJECT_VERSION:
        raise TorchTrainingError(f"condition packet schema_version must be {PROJECT_VERSION}")
    if packet.get("condition_packet_type") != "generation_condition_packet":
        raise TorchTrainingError("condition packet type must be generation_condition_packet")
    if expected_prior_id is not None and packet.get("prior_id") != expected_prior_id:
        raise TorchTrainingError("condition packet prior_id must match prior manifest")
    conditions = packet.get("conditions")
    if not isinstance(conditions, dict):
        raise TorchTrainingError("condition packet conditions must be an object")
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
            raise TorchTrainingError(f"condition packet conditions.{key} must be an object")
    return {
        "path": str(path),
        "summary": _condition_packet_summary(conditions),
    }


def _condition_packet_summary(conditions: dict[str, Any]) -> dict[str, Any]:
    coord = conditions["coord"]
    layout = conditions["layout"]
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
    if "wsi_tissue_overview" in layout:
        summary["wsi_tissue_overview"] = _wsi_tissue_overview_summary(
            layout["wsi_tissue_overview"]
        )
    return summary


def _wsi_tissue_overview_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TorchTrainingError(
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
        raise TorchTrainingError(
            "condition packet conditions.layout.wsi_tissue_overview.records must be a list"
        )
    summarized_records = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TorchTrainingError(
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
        raise TorchTrainingError(f"{path} must be a non-empty string")
    return value


def _require_condition_list(data: dict[str, Any], key: str, path: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise TorchTrainingError(f"{path} must be a list")
    return value


def _require_condition_number(data: dict[str, Any], key: str, path: str) -> int | float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TorchTrainingError(f"{path} must be a number")
    return value


def _require_condition_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TorchTrainingError(f"{path} must be an integer")
    return value


class _MaskConditionedRgbReconstructor:
    def __new__(cls, torch, class_count: int):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.layers = torch.nn.Sequential(
                    torch.nn.Conv2d(class_count, 16, kernel_size=3, padding=1),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(16, 3, kernel_size=1),
                    torch.nn.Sigmoid(),
                )

            def forward(self, inputs):
                return self.layers(inputs)

        return Model()


class _RgbVaeSmokeAutoencoder:
    def __new__(cls, torch, latent_channels: int):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = torch.nn.Sequential(
                    torch.nn.Conv2d(3, 16, kernel_size=3, padding=1),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(16, 2 * latent_channels, kernel_size=1),
                )
                self.decoder = torch.nn.Sequential(
                    torch.nn.Conv2d(latent_channels, 16, kernel_size=3, padding=1),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(16, 3, kernel_size=1),
                    torch.nn.Sigmoid(),
                )

            def forward(self, inputs):
                encoded = self.encoder(inputs)
                mu, logvar = torch.chunk(encoded, 2, dim=1)
                logvar = logvar.clamp(min=-8.0, max=8.0)
                std = torch.exp(0.5 * logvar)
                epsilon = torch.randn_like(std)
                latent = mu + epsilon * std
                return self.decoder(latent), mu, logvar

        return Model()


class _MaskConditionedLatentDenoiser:
    def __new__(cls, torch, input_channels: int, output_channels: int = 3):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder_block = torch.nn.Sequential(
                    torch.nn.Conv2d(
                        input_channels,
                        DENOISER_BASE_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(
                        DENOISER_BASE_CHANNELS,
                        DENOISER_BASE_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
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
                    torch.nn.Conv2d(
                        DENOISER_BOTTLENECK_CHANNELS,
                        DENOISER_BOTTLENECK_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(
                        DENOISER_BOTTLENECK_CHANNELS,
                        DENOISER_BOTTLENECK_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
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
                    torch.nn.Conv2d(
                        DENOISER_BASE_CHANNELS * 2,
                        DENOISER_BASE_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
                    torch.nn.ReLU(),
                    torch.nn.Conv2d(
                        DENOISER_BASE_CHANNELS,
                        DENOISER_BASE_CHANNELS,
                        kernel_size=3,
                        padding=1,
                    ),
                    torch.nn.ReLU(),
                )
                self.output_block = torch.nn.Conv2d(
                    DENOISER_BASE_CHANNELS,
                    output_channels,
                    kernel_size=1,
                )

            def forward(self, inputs):
                encoder_features = self.encoder_block(inputs)
                downsampled = self.downsample(encoder_features)
                bottleneck = self.bottleneck(downsampled)
                upsampled = self.upsample(bottleneck)
                if upsampled.shape[-2:] != encoder_features.shape[-2:]:
                    # Keep the smoke U-Net tolerant of odd latent sizes while still
                    # failing loudly on incompatible channel contracts elsewhere.
                    upsampled = torch.nn.functional.interpolate(
                        upsampled,
                        size=encoder_features.shape[-2:],
                        mode="nearest",
                    )
                decoded = self.decoder_block(torch.cat([upsampled, encoder_features], dim=1))
                return self.output_block(decoded)

        return Model()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _import_torch():
    try:
        import torch
    except ImportError as exc:
        raise TorchTrainingError(
            "PyTorch is required for torch training commands; install the torch optional dependency "
            "or run inside a PyTorch conda environment"
        ) from exc
    return torch


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise TorchTrainingError("torch diffusion smoke sampling requires numpy") from exc
    return numpy
