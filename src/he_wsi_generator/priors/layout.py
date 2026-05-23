import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import MASK_CLASSES, PROJECT_VERSION
from ..models.training_batch import TrainingBatchError, load_training_batch, training_batch_summary


class LayoutMaskPriorBuildError(ValueError):
    """Raised when mask training tiles cannot define an auditable layout prior."""


def build_layout_mask_prior_from_training_index(
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
            include_image=False,
        )
    except TrainingBatchError as exc:
        raise LayoutMaskPriorBuildError(str(exc)) from exc

    mask_batch = batch["mask_batch"]
    if mask_batch.ndim != 3:
        raise LayoutMaskPriorBuildError("mask_batch must have shape [batch, height, width]")

    counts = _class_counts(mask_batch)
    total_pixels = int(mask_batch.size)
    prior = {
        "schema_version": PROJECT_VERSION,
        "prior_type": "layout_mask_prior",
        "created_at": _now_iso(),
        "source": {
            "source_type": "training_index_mask_tiles",
            "training_index_path": str(training_index_path),
            "batch_size": int(batch["batch_size"]),
            "split": split,
            "cascade_level": cascade_level,
        },
        "sample_count": int(batch["batch_size"]),
        "sample_ids": list(batch["sample_ids"]),
        "wsi_ids": list(batch["wsi_ids"]),
        "tile_records": list(batch["tile_records"]),
        "mask_batch_shape": list(batch["mask_batch_shape"]),
        "mask_class_ids": list(batch["mask_class_ids"]),
        "class_names": list(MASK_CLASSES),
        "class_pixel_counts_by_id": counts,
        "class_fractions_by_id": _fractions(counts, total_pixels),
        "class_present_by_id": [count > 0 for count in counts],
        "non_background_fraction": _round_float(1.0 - (counts[0] / total_pixels)),
        "tile_layout_records": _tile_layout_records(mask_batch, batch),
        "adjacency_counts": _adjacency_counts(mask_batch),
        "batch_summary": training_batch_summary(batch),
        "limitations": [
            "statistical_mask_layout_prior_only",
            "not_a_sampling_layout_generator",
            "not_a_mask_diffusion_model",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")
    return prior


def _class_counts(mask_batch) -> list[int]:
    counts = []
    for class_id in range(len(MASK_CLASSES)):
        counts.append(int((mask_batch == class_id).sum()))
    return counts


def _fractions(counts: list[int], total: int) -> list[float]:
    if total <= 0:
        raise LayoutMaskPriorBuildError("mask_batch must contain at least one pixel")
    return [_round_float(count / total) for count in counts]


def _tile_layout_records(mask_batch, batch: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for index, sample_id in enumerate(batch["sample_ids"]):
        tile_mask = mask_batch[index]
        counts = _class_counts(tile_mask)
        fractions = _fractions(counts, int(tile_mask.size))
        dominant_class_id = max(range(len(counts)), key=lambda class_id: counts[class_id])
        records.append(
            {
                "sample_id": sample_id,
                "wsi_id": _sample_wsi_id(sample_id),
                "tile": batch["tile_records"][index],
                "class_pixel_counts_by_id": counts,
                "class_fractions_by_id": fractions,
                "dominant_class_id": dominant_class_id,
                "dominant_class_name": MASK_CLASSES[dominant_class_id],
            }
        )
    return records


def _adjacency_counts(mask_batch) -> dict[str, dict[str, int]]:
    horizontal: dict[str, int] = {}
    vertical: dict[str, int] = {}
    for tile_mask in mask_batch:
        _count_pairs(tile_mask[:, :-1], tile_mask[:, 1:], horizontal)
        _count_pairs(tile_mask[:-1, :], tile_mask[1:, :], vertical)
    return {"horizontal": horizontal, "vertical": vertical}


def _count_pairs(left, right, target: dict[str, int]) -> None:
    for class_a in range(len(MASK_CLASSES)):
        for class_b in range(len(MASK_CLASSES)):
            count = int(((left == class_a) & (right == class_b)).sum())
            if count > 0:
                key = f"{class_a}:{class_b}"
                target[key] = target.get(key, 0) + count


def _sample_wsi_id(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def _round_float(value: float) -> float:
    return round(float(value), 9)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
