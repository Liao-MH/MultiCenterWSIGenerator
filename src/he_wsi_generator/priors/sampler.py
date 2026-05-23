import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import MASK_CLASSES, PROJECT_VERSION


class LayoutMaskSamplerError(ValueError):
    """Raised when a statistical layout prior cannot produce a sampled mask."""


def sample_layout_mask_from_prior(
    *,
    layout_mask_prior_path: str | Path,
    output_dir: str | Path,
    sample_id: str,
    mask_shape: tuple[int, int],
    random_seed: int,
    wsi_tissue_overview_path: str | Path | None = None,
) -> dict[str, Any]:
    height, width = _validate_mask_shape(mask_shape)
    if not isinstance(sample_id, str) or sample_id == "":
        raise LayoutMaskSamplerError("sample_id must be a non-empty string")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise LayoutMaskSamplerError("random_seed must be an integer")

    prior = _load_layout_prior(layout_mask_prior_path)
    tissue_reference = (
        _load_tissue_reference(wsi_tissue_overview_path)
        if wsi_tissue_overview_path is not None
        else None
    )
    mask = _sample_mask(
        height=height,
        width=width,
        prior=prior,
        random_seed=random_seed,
        tissue_reference=tissue_reference,
    )
    counts = _class_counts(mask)
    total_pixels = height * width

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    mask_path = root / "sampled_layout_mask.npy"
    manifest_path = root / "sampled_layout_mask.json"

    numpy = _import_numpy()
    numpy.save(mask_path, numpy.asarray(mask, dtype=numpy.uint8))

    manifest = {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "sampled_layout_mask",
        "created_at": _now_iso(),
        "sample_id": sample_id,
        "random_seed": random_seed,
        "mask_path": str(mask_path),
        "mask_shape": [height, width],
        "source": {
            "source_type": "statistical_layout_mask_prior_sampler",
            "layout_mask_prior_path": str(layout_mask_prior_path),
            "wsi_tissue_overview_path": (
                str(wsi_tissue_overview_path) if wsi_tissue_overview_path is not None else None
            ),
        },
        "class_names": list(MASK_CLASSES),
        "class_pixel_counts_by_id": counts,
        "class_fractions_by_id": _fractions(counts, total_pixels),
        "tissue_overview_reference": tissue_reference,
        "limitations": [
            "statistical_layout_sampler_only",
            "not_a_mask_diffusion_model",
            "not_a_semantic_segmentation_model",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _sample_mask(
    *,
    height: int,
    width: int,
    prior: dict[str, Any],
    random_seed: int,
    tissue_reference: dict[str, Any] | None,
) -> list[list[int]]:
    class_fractions = _layout_class_fractions(prior)
    total_pixels = height * width
    tissue_indices = _tissue_indices(height, width, tissue_reference)
    mask = [[0 for _ in range(width)] for _ in range(height)]

    if not tissue_indices:
        return mask

    non_background_weights = (
        _tile_dominant_class_weights(prior)
        if tissue_reference is not None
        else class_fractions[1:]
    )
    non_background_total = sum(non_background_weights)
    prior_non_background_pixels = int(round(non_background_total * total_pixels))
    non_background_pixels = min(len(tissue_indices), prior_non_background_pixels)
    if tissue_reference is not None:
        non_background_pixels = len(tissue_indices)
    if non_background_total <= 0.0:
        primary_class = _dominant_non_background_class(prior)
        class_targets = {primary_class: non_background_pixels}
    else:
        class_targets = {}
        for class_offset, weight in enumerate(non_background_weights, start=1):
            class_targets[class_offset] = int(round((weight / non_background_total) * non_background_pixels))
        _rebalance_targets(class_targets, non_background_pixels)

    rng = random.Random(random_seed)
    shuffled = list(tissue_indices)
    rng.shuffle(shuffled)
    cursor = 0
    for class_id in range(1, len(MASK_CLASSES)):
        count = class_targets.get(class_id, 0)
        for y, x in shuffled[cursor : cursor + count]:
            mask[y][x] = class_id
        cursor += count

    return mask


def _layout_class_fractions(prior: dict[str, Any]) -> list[float]:
    fractions = prior.get("class_fractions_by_id")
    if not isinstance(fractions, list) or len(fractions) != len(MASK_CLASSES):
        raise LayoutMaskSamplerError("layout_mask_prior.class_fractions_by_id must contain six values")
    parsed = []
    for index, value in enumerate(fractions):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise LayoutMaskSamplerError(f"class_fractions_by_id[{index}] must be a non-negative number")
        parsed.append(float(value))
    if sum(parsed) <= 0.0:
        raise LayoutMaskSamplerError("class_fractions_by_id must contain at least one positive fraction")
    return parsed


def _tissue_indices(
    height: int,
    width: int,
    tissue_reference: dict[str, Any] | None,
) -> list[tuple[int, int]]:
    if tissue_reference is None:
        return [(y, x) for y in range(height) for x in range(width)]
    bbox = tissue_reference["bounding_box_xywh"]
    ref_width = max(1, int(tissue_reference.get("thumbnail_width", width)))
    ref_height = max(1, int(tissue_reference.get("thumbnail_height", height)))
    x, y, box_width, box_height = bbox
    left = max(0, min(width, int(round(x * width / ref_width))))
    top = max(0, min(height, int(round(y * height / ref_height))))
    right = max(left, min(width, int(round((x + box_width) * width / ref_width))))
    bottom = max(top, min(height, int(round((y + box_height) * height / ref_height))))
    if right <= left or bottom <= top:
        raise LayoutMaskSamplerError("wsi_tissue_overview bounding_box_xywh maps to an empty mask region")
    return [(row, col) for row in range(top, bottom) for col in range(left, right)]


def _dominant_non_background_class(prior: dict[str, Any]) -> int:
    records = prior.get("tile_layout_records")
    if isinstance(records, list):
        for record in records:
            if isinstance(record, dict):
                class_id = record.get("dominant_class_id")
                if isinstance(class_id, int) and not isinstance(class_id, bool) and 1 <= class_id < len(MASK_CLASSES):
                    return class_id
    return 1


def _tile_dominant_class_weights(prior: dict[str, Any]) -> list[float]:
    weights = [0.0 for _ in range(len(MASK_CLASSES) - 1)]
    records = prior.get("tile_layout_records")
    if not isinstance(records, list):
        return _layout_class_fractions(prior)[1:]
    for record in records:
        if not isinstance(record, dict):
            continue
        class_id = record.get("dominant_class_id")
        if isinstance(class_id, int) and not isinstance(class_id, bool) and 1 <= class_id < len(MASK_CLASSES):
            weights[class_id - 1] += 1.0
    if sum(weights) <= 0.0:
        return _layout_class_fractions(prior)[1:]
    return weights


def _rebalance_targets(class_targets: dict[int, int], total: int) -> None:
    current = sum(class_targets.values())
    if current == total:
        return
    adjustable = [class_id for class_id in range(1, len(MASK_CLASSES)) if class_targets.get(class_id, 0) > 0]
    if not adjustable:
        class_targets[1] = total
        return
    class_id = adjustable[0]
    class_targets[class_id] += total - current
    if class_targets[class_id] < 0:
        raise LayoutMaskSamplerError("class fractions produced negative sampled pixel counts")


def _load_layout_prior(path: str | Path) -> dict[str, Any]:
    data = _load_json(path, "layout_mask_prior")
    if data.get("schema_version") != PROJECT_VERSION:
        raise LayoutMaskSamplerError(f"layout_mask_prior.schema_version must be {PROJECT_VERSION}")
    if data.get("prior_type") != "layout_mask_prior":
        raise LayoutMaskSamplerError("layout_mask_prior.prior_type must be layout_mask_prior")
    _layout_class_fractions(data)
    return data


def _load_tissue_reference(path: str | Path) -> dict[str, Any]:
    overview = _load_json(path, "wsi_tissue_overview")
    if overview.get("artifact_type") != "wsi_tissue_overview":
        raise LayoutMaskSamplerError("wsi_tissue_overview.artifact_type must be wsi_tissue_overview")
    records = overview.get("records")
    if not isinstance(records, list) or not records:
        raise LayoutMaskSamplerError("wsi_tissue_overview.records must be a non-empty list")
    record = records[0]
    if not isinstance(record, dict):
        raise LayoutMaskSamplerError("wsi_tissue_overview.records[0] must be an object")
    proxy = record.get("tissue_mask_proxy")
    if not isinstance(proxy, dict):
        raise LayoutMaskSamplerError("wsi_tissue_overview.records[0].tissue_mask_proxy must be an object")
    fraction = proxy.get("tissue_fraction")
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise LayoutMaskSamplerError("wsi_tissue_overview tissue_fraction must be numeric")
    bbox = proxy.get("bounding_box_xywh")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in bbox)
    ):
        raise LayoutMaskSamplerError("wsi_tissue_overview bounding_box_xywh must contain four integers")
    thumbnail_size = proxy.get("thumbnail_size") or record.get("thumbnail", {}).get("size")
    thumbnail_width = bbox[0] + bbox[2]
    thumbnail_height = bbox[1] + bbox[3]
    if isinstance(thumbnail_size, list) and len(thumbnail_size) == 2:
        if all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in thumbnail_size):
            thumbnail_width, thumbnail_height = thumbnail_size
    return {
        "source": "wsi_tissue_overview",
        "wsi_id": record.get("wsi_id"),
        "tissue_fraction": float(fraction),
        "bounding_box_xywh": list(bbox),
        "connected_component_count": proxy.get("connected_component_count"),
        "thumbnail_width": int(thumbnail_width),
        "thumbnail_height": int(thumbnail_height),
    }


def _load_json(path: str | Path, label: str) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        raise LayoutMaskSamplerError(f"{label} file does not exist: {json_path}")
    if not json_path.is_file():
        raise LayoutMaskSamplerError(f"{label} path is not a file: {json_path}")
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LayoutMaskSamplerError(f"{label} is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LayoutMaskSamplerError(f"{label} must be a JSON object")
    return data


def _class_counts(mask: list[list[int]]) -> list[int]:
    counts = [0 for _ in MASK_CLASSES]
    for row in mask:
        for value in row:
            counts[value] += 1
    return counts


def _fractions(counts: list[int], total: int) -> list[float]:
    if total <= 0:
        raise LayoutMaskSamplerError("mask must contain at least one pixel")
    return [round(count / total, 9) for count in counts]


def _validate_mask_shape(mask_shape: tuple[int, int]) -> tuple[int, int]:
    if not (
        isinstance(mask_shape, tuple)
        and len(mask_shape) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in mask_shape)
    ):
        raise LayoutMaskSamplerError("mask_shape must contain two positive integers")
    return int(mask_shape[0]), int(mask_shape[1])


def _import_numpy():
    import numpy

    return numpy


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
