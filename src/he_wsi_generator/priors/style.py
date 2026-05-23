import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..models.training_batch import TrainingBatchError, load_training_batch, training_batch_summary


class StylePriorBuildError(ValueError):
    """Raised when RGB training tiles cannot define an auditable style prior."""


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
        "tile_style_records": _tile_style_records(image_batch, batch),
        "batch_summary": training_batch_summary(batch),
        "limitations": [
            "statistical_rgb_style_prior_only",
            "not_a_trainable_style_encoder",
            "not_a_vae_style_latent",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(style_prior, indent=2) + "\n", encoding="utf-8")
    return style_prior


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


def _tile_style_records(image_batch, batch: dict[str, Any]) -> list[dict[str, Any]]:
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
            }
        )
    return records


def _sample_wsi_id(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def _round_float(value: float) -> float:
    return round(float(value), 9)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
