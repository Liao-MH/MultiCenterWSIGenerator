import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..models.training_batch import TrainingBatchError, load_training_batch, training_batch_summary


class StylePriorBuildError(ValueError):
    """Raised when RGB training tiles cannot define an auditable style prior."""


STYLE_LATENT_DIM = 3
STYLE_FEATURE_SCHEMA = (
    "mean_r_normalized",
    "mean_g_normalized",
    "mean_b_normalized",
    "std_r_normalized",
    "std_g_normalized",
    "std_b_normalized",
)


def build_style_prior_from_training_index(
    training_index_path: str | Path,
    output_path: str | Path,
    batch_size: int,
    split: str | None = None,
    cascade_level: str | None = "1/1",
) -> dict[str, Any]:
    try:
        batch = load_training_batch(
            training_index_path,
            batch_size=batch_size,
            split=split,
            cascade_level=cascade_level,
            include_image=True,
        )
    except TrainingBatchError as exc:
        raise StylePriorBuildError(str(exc)) from exc

    image_batch = batch["image_batch"]
    if image_batch.ndim != 4 or image_batch.shape[-1] != 3:
        raise StylePriorBuildError("image_batch must have shape [batch, height, width, 3]")
    style_latent_encoder, style_latents = _fit_style_latent_encoder(image_batch)

    style_prior = {
        "schema_version": PROJECT_VERSION,
        "prior_type": "style_prior",
        "created_at": _now_iso(),
        "source": {
            "source_type": "training_index_rgb_tiles",
            "training_index_path": str(training_index_path),
            "batch_size": int(batch["batch_size"]),
            "split": split,
            "cascade_level": cascade_level,
        },
        "sample_count": int(batch["batch_size"]),
        "sample_ids": list(batch["sample_ids"]),
        "wsi_ids": list(batch["wsi_ids"]),
        "tile_records": list(batch["tile_records"]),
        "image_batch_shape": list(batch["image_batch_shape"]),
        "image_dtype": batch["image_dtype"],
        "rgb_statistics": _rgb_statistics(image_batch),
        "style_latent_encoder": style_latent_encoder,
        "tile_style_records": _tile_style_records(image_batch, batch, style_latents),
        "batch_summary": training_batch_summary(batch),
        "limitations": [
            "fitted_rgb_stats_style_latent_only",
            "not_deep_trainable_style_encoder",
            "not_a_vae_style_latent",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(style_prior, indent=2) + "\n", encoding="utf-8")
    return style_prior


def sample_style_policy_from_prior(
    style_prior_path: str | Path,
    output_path: str | Path,
    sample_id: str,
    random_seed: int,
) -> dict[str, Any]:
    if not isinstance(sample_id, str) or sample_id == "":
        raise StylePriorBuildError("sample_id must be a non-empty string")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise StylePriorBuildError("random_seed must be an integer")

    prior = _load_style_prior(style_prior_path)
    records = prior.get("tile_style_records")
    if not isinstance(records, list) or not records:
        raise StylePriorBuildError("style_prior.tile_style_records must be a non-empty list")

    selected_index = random_seed % len(records)
    selected_record = records[selected_index]
    if not isinstance(selected_record, dict):
        raise StylePriorBuildError("style_prior.tile_style_records entries must be objects")
    mean_rgb = _validate_rgb_triplet(
        selected_record.get("mean_rgb"),
        "style_prior.tile_style_records.mean_rgb",
    )
    style_latent = _validate_numeric_vector(
        selected_record.get("style_latent"),
        "style_prior.tile_style_records.style_latent",
    )

    policy = {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "sampled_style_policy",
        "created_at": _now_iso(),
        "sample_id": sample_id,
        "random_seed": random_seed,
        "selection_policy": "deterministic_random_seed_mod_tile_count",
        "source": {
            "source_type": "statistical_style_prior_policy",
            "style_prior_path": str(style_prior_path),
            "tile_style_record_count": len(records),
        },
        "selected_style": {
            "tile_index": selected_index,
            "sample_id": selected_record.get("sample_id"),
            "wsi_id": selected_record.get("wsi_id"),
            "tile": selected_record.get("tile"),
            "mean_rgb": mean_rgb,
            "style_latent": style_latent,
        },
        "style_latent_encoder_reference": _style_latent_encoder_reference(prior),
        "rgb_statistics_reference": dict(prior.get("rgb_statistics", {})),
        "limitations": [
            "deterministic_fitted_style_latent_policy_only",
            "not_deep_trainable_style_encoder",
            "not_a_vae_style_latent",
            "not_production_style_transfer",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    return policy


def _rgb_statistics(image_batch) -> dict[str, Any]:
    pixels = image_batch.reshape(-1, image_batch.shape[-1])
    mean = pixels.mean(axis=0)
    std = pixels.std(axis=0)
    min_values = pixels.min(axis=0)
    max_values = pixels.max(axis=0)
    return {
        "mean_rgb": [_round_float(value) for value in mean.tolist()],
        "std_rgb": [_round_float(value) for value in std.tolist()],
        "min_rgb": [int(value) for value in min_values.tolist()],
        "max_rgb": [int(value) for value in max_values.tolist()],
        "mean_rgb_normalized": [_round_float(value / 255.0) for value in mean.tolist()],
        "std_rgb_normalized": [_round_float(value / 255.0) for value in std.tolist()],
    }


def _fit_style_latent_encoder(image_batch) -> tuple[dict[str, Any], list[list[float]]]:
    numpy = _import_numpy()
    features = _style_feature_matrix(numpy, image_batch)
    feature_mean = features.mean(axis=0)
    centered = features - feature_mean
    components = numpy.zeros((STYLE_LATENT_DIM, features.shape[1]), dtype=numpy.float64)
    explained_variance = numpy.zeros(STYLE_LATENT_DIM, dtype=numpy.float64)
    explained_variance_ratio = numpy.zeros(STYLE_LATENT_DIM, dtype=numpy.float64)

    # This is a fitted encoder over explicit RGB statistics, not a hidden deep
    # model. It gives downstream condition packets a stable style_latent vector
    # while keeping the artifact small and auditable.
    rank = min(STYLE_LATENT_DIM, max(0, features.shape[0] - 1), features.shape[1])
    if rank > 0:
        _, singular_values, right_vectors = numpy.linalg.svd(centered, full_matrices=False)
        variance = (singular_values[:rank] ** 2) / max(features.shape[0] - 1, 1)
        total_variance = float(variance.sum())
        for index in range(rank):
            component = right_vectors[index].astype(numpy.float64)
            anchor = int(numpy.argmax(numpy.abs(component)))
            if component[anchor] < 0:
                component = -component
            components[index] = component
            explained_variance[index] = variance[index]
            if total_variance > 0:
                explained_variance_ratio[index] = variance[index] / total_variance

    latents = centered @ components.T
    encoder = {
        "encoder_type": "fitted_rgb_stats_pca_v1",
        "latent_dim": STYLE_LATENT_DIM,
        "feature_schema": list(STYLE_FEATURE_SCHEMA),
        "feature_normalization": "rgb_mean_and_std_divided_by_255",
        "sample_count": int(features.shape[0]),
        "feature_mean": [_round_float(value) for value in feature_mean.tolist()],
        "components": [
            [_round_float(value) for value in component.tolist()]
            for component in components
        ],
        "explained_variance": [_round_float(value) for value in explained_variance.tolist()],
        "explained_variance_ratio": [
            _round_float(value) for value in explained_variance_ratio.tolist()
        ],
        "condition_outputs": ["style_seed", "style_latent"],
        "limitations": [
            "rgb_statistics_pca_latent_only",
            "not_deep_trainable_style_encoder",
            "not_vae_style_latent",
        ],
    }
    return encoder, [
        [_round_float(value) for value in latent.tolist()]
        for latent in latents
    ]


def _style_feature_matrix(numpy, image_batch):
    stats = image_batch.reshape(image_batch.shape[0], -1, image_batch.shape[-1])
    mean = stats.mean(axis=1) / 255.0
    std = stats.std(axis=1) / 255.0
    return numpy.concatenate([mean, std], axis=1).astype(numpy.float64)


def _tile_style_records(
    image_batch,
    batch: dict[str, Any],
    style_latents: list[list[float]],
) -> list[dict[str, Any]]:
    records = []
    for index, sample_id in enumerate(batch["sample_ids"]):
        tile = image_batch[index]
        records.append(
            {
                "sample_id": sample_id,
                "wsi_id": batch["source_records"][index]["wsi_id"]
                if "wsi_id" in batch["source_records"][index]
                else _sample_wsi_id(sample_id),
                "tile": batch["tile_records"][index],
                "mean_rgb": [_round_float(value) for value in tile.reshape(-1, 3).mean(axis=0)],
                "style_latent": list(style_latents[index]),
            }
        )
    return records


def _sample_wsi_id(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def _round_float(value: float) -> float:
    return round(float(value), 9)


def _load_style_prior(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise StylePriorBuildError(f"style prior does not exist: {source}")
    if not source.is_file():
        raise StylePriorBuildError(f"style prior path is not a file: {source}")
    try:
        prior = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StylePriorBuildError(f"style prior is not valid JSON: {exc.msg}") from exc
    if not isinstance(prior, dict):
        raise StylePriorBuildError("style prior must be a JSON object")
    if prior.get("schema_version") != PROJECT_VERSION:
        raise StylePriorBuildError(f"style_prior.schema_version must be {PROJECT_VERSION}")
    if prior.get("prior_type") != "style_prior":
        raise StylePriorBuildError("style_prior.prior_type must be style_prior")
    return prior


def _style_latent_encoder_reference(prior: dict[str, Any]) -> dict[str, Any]:
    encoder = prior.get("style_latent_encoder")
    if not isinstance(encoder, dict):
        raise StylePriorBuildError("style_prior.style_latent_encoder must be an object")
    encoder_type = encoder.get("encoder_type")
    if not isinstance(encoder_type, str) or encoder_type == "":
        raise StylePriorBuildError("style_prior.style_latent_encoder.encoder_type must be non-empty")
    latent_dim = encoder.get("latent_dim")
    if not isinstance(latent_dim, int) or isinstance(latent_dim, bool) or latent_dim <= 0:
        raise StylePriorBuildError("style_prior.style_latent_encoder.latent_dim must be positive")
    condition_outputs = encoder.get("condition_outputs")
    if not isinstance(condition_outputs, list) or "style_latent" not in condition_outputs:
        raise StylePriorBuildError(
            "style_prior.style_latent_encoder.condition_outputs must include style_latent"
        )
    return {
        "encoder_type": encoder_type,
        "latent_dim": latent_dim,
        "condition_outputs": list(condition_outputs),
    }


def _validate_rgb_triplet(value: Any, path: str) -> list[float]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(channel, (int, float)) and not isinstance(channel, bool) for channel in value)
    ):
        raise StylePriorBuildError(f"{path} must contain three numeric RGB values")
    return [_round_float(channel) for channel in value]


def _validate_numeric_vector(value: Any, path: str) -> list[float]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        raise StylePriorBuildError(f"{path} must be a non-empty numeric vector")
    return [_round_float(item) for item in value]


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise StylePriorBuildError("style latent encoder fitting requires numpy") from exc
    return numpy


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
