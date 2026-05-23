import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..io.audit import build_reader
from ..io.readers import WSIReadError
from ..schemas import ValidationError, load_document, validate_input_manifest


class WSITissueOverviewBuildError(ValueError):
    """Raised when WSI thumbnails cannot produce a tissue overview artifact."""


def build_wsi_tissue_overview_from_manifest(
    manifest_path: str | Path,
    output_path: str | Path,
    backend: str = "openslide",
    thumbnail_max_size: tuple[int, int] = (1024, 1024),
) -> dict[str, Any]:
    if not (
        isinstance(thumbnail_max_size, tuple)
        and len(thumbnail_max_size) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in thumbnail_max_size)
    ):
        raise WSITissueOverviewBuildError("thumbnail_max_size must contain two positive integers")
    try:
        manifest = validate_input_manifest(load_document(manifest_path))
    except ValidationError as exc:
        raise WSITissueOverviewBuildError(str(exc)) from exc

    try:
        reader = build_reader(backend)
    except ValueError as exc:
        raise WSITissueOverviewBuildError(str(exc)) from exc

    records = []
    for manifest_record in manifest["records"]:
        wsi_id = manifest_record["wsi_id"]
        wsi_path = manifest_record["wsi_path"]
        try:
            metadata = reader.read_metadata(wsi_path, wsi_id=wsi_id)
            thumbnail = reader.read_thumbnail(wsi_path, thumbnail_max_size)
        except WSIReadError as exc:
            raise WSITissueOverviewBuildError(str(exc)) from exc

        thumbnail_rgb = _thumbnail_pixels(thumbnail)
        tissue_mask = _detect_tissue_mask(thumbnail_rgb)
        tissue_metrics = _tissue_mask_metrics(tissue_mask)
        records.append(
            {
                "wsi_id": wsi_id,
                "slide": metadata.to_record(),
                "manifest": {
                    "split": manifest_record["split"],
                    "cancer_type": manifest_record["cancer_type"],
                    "tissue_type": manifest_record.get("tissue_type"),
                    "center_id": manifest_record.get("center_id"),
                    "annotation_count": len(manifest_record.get("annotations", [])),
                },
                "thumbnail": {
                    "size": [len(thumbnail_rgb[0]), len(thumbnail_rgb)],
                    "max_size": [int(thumbnail_max_size[0]), int(thumbnail_max_size[1])],
                    "rgb_mean": _rgb_mean(thumbnail_rgb),
                    "rgb_min": _rgb_min(thumbnail_rgb),
                    "rgb_max": _rgb_max(thumbnail_rgb),
                },
                "tissue_mask_proxy": tissue_metrics,
            }
        )

    overview = {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "wsi_tissue_overview",
        "created_at": _now_iso(),
        "source": {
            "source_type": "wsi_thumbnail_tissue_proxy",
            "manifest_path": str(manifest_path),
            "dataset_id": manifest["dataset_id"],
            "backend": reader.backend,
            "thumbnail_max_size": [int(thumbnail_max_size[0]), int(thumbnail_max_size[1])],
        },
        "record_count": len(records),
        "records": records,
        "limitations": [
            "thumbnail_level_tissue_proxy_only",
            "not_a_semantic_segmentation_mask",
            "not_a_tumor_stroma_classifier",
        ],
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(overview, indent=2) + "\n", encoding="utf-8")
    return overview


def _thumbnail_pixels(thumbnail) -> list[list[tuple[int, int, int]]]:
    try:
        image = thumbnail.convert("RGB")
    except AttributeError as exc:
        raise WSITissueOverviewBuildError("reader thumbnail must be a Pillow-compatible image") from exc
    width, height = image.size
    if width <= 0 or height <= 0:
        raise WSITissueOverviewBuildError("thumbnail must contain at least one pixel")
    access = image.load()
    return [
        [tuple(int(channel) for channel in access[x, y]) for x in range(width)]
        for y in range(height)
    ]


def _detect_tissue_mask(
    pixels: list[list[tuple[int, int, int]]],
) -> list[list[bool]]:
    # This intentionally remains a lightweight thumbnail proxy: bright low-saturation
    # glass/background is rejected, while darker or sufficiently saturated H&E-like
    # regions are retained for layout-prior and QC audit metadata.
    mask = []
    for row in pixels:
        mask_row = []
        for red, green, blue in row:
            max_channel = max(red, green, blue)
            min_channel = min(red, green, blue)
            brightness = (red + green + blue) / 3.0
            saturation = max_channel - min_channel
            mask_row.append(brightness < 240.0 and saturation > 15.0)
        mask.append(mask_row)
    return mask


def _tissue_mask_metrics(mask: list[list[bool]]) -> dict[str, Any]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    if width <= 0:
        raise WSITissueOverviewBuildError("thumbnail tissue mask must contain pixels")

    coords = [
        (x, y)
        for y, row in enumerate(mask)
        for x, value in enumerate(row)
        if value
    ]
    if not coords:
        raise WSITissueOverviewBuildError("no tissue pixels detected in thumbnail proxy")

    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    tissue_pixel_count = len(coords)
    return {
        "method": "thumbnail_brightness_saturation_threshold",
        "thresholds": {
            "brightness_lt": 240.0,
            "saturation_gt": 15.0,
        },
        "thumbnail_size": [width, height],
        "tissue_pixel_count": tissue_pixel_count,
        "background_pixel_count": (width * height) - tissue_pixel_count,
        "tissue_fraction": _round_float(tissue_pixel_count / (width * height)),
        "bounding_box_xywh": [min_x, min_y, max_x - min_x + 1, max_y - min_y + 1],
        "connected_component_count": _connected_component_count(mask),
    }


def _connected_component_count(mask: list[list[bool]]) -> int:
    height = len(mask)
    width = len(mask[0]) if height else 0
    visited = [[False for _ in range(width)] for _ in range(height)]
    count = 0
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or visited[y][x]:
                continue
            count += 1
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited[y][x] = True
            while queue:
                current_x, current_y = queue.popleft()
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and mask[next_y][next_x]
                        and not visited[next_y][next_x]
                    ):
                        visited[next_y][next_x] = True
                        queue.append((next_x, next_y))
    return count


def _rgb_mean(pixels: list[list[tuple[int, int, int]]]) -> list[float]:
    total = [0, 0, 0]
    count = 0
    for row in pixels:
        for red, green, blue in row:
            total[0] += red
            total[1] += green
            total[2] += blue
            count += 1
    return [_round_float(value / count) for value in total]


def _rgb_min(pixels: list[list[tuple[int, int, int]]]) -> list[int]:
    mins = [255, 255, 255]
    for row in pixels:
        for red, green, blue in row:
            mins[0] = min(mins[0], red)
            mins[1] = min(mins[1], green)
            mins[2] = min(mins[2], blue)
    return mins


def _rgb_max(pixels: list[list[tuple[int, int, int]]]) -> list[int]:
    maxes = [0, 0, 0]
    for row in pixels:
        for red, green, blue in row:
            maxes[0] = max(maxes[0], red)
            maxes[1] = max(maxes[1], green)
            maxes[2] = max(maxes[2], blue)
    return maxes


def _round_float(value: float) -> float:
    return round(float(value), 9)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
