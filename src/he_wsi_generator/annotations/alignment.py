from typing import Any


def validate_mask_alignment(
    mask_size: tuple[int, int],
    wsi_level0_size: tuple[int, int],
    transform_to_level0: dict[str, Any],
) -> dict:
    mask_width, mask_height = _validate_size(mask_size, "mask_size")
    wsi_width, wsi_height = _validate_size(wsi_level0_size, "wsi_level0_size")
    scale_x = _positive_number(transform_to_level0, "scale_x")
    scale_y = _positive_number(transform_to_level0, "scale_y")
    offset_x = _number(transform_to_level0, "offset_x")
    offset_y = _number(transform_to_level0, "offset_y")

    x0 = offset_x
    y0 = offset_y
    x1 = offset_x + mask_width * scale_x
    y1 = offset_y + mask_height * scale_y

    if x0 < 0 or y0 < 0:
        raise ValueError("mask level0 extent has negative offset")
    if x1 > wsi_width or y1 > wsi_height:
        raise ValueError("mask level0 extent exceeds WSI level0 bounds")

    return {
        "status": "aligned",
        "mask_size": [mask_width, mask_height],
        "wsi_level0_size": [wsi_width, wsi_height],
        "level0_extent": [x0, y0, x1, y1],
        "transform_to_level0": {
            "scale_x": scale_x,
            "scale_y": scale_y,
            "offset_x": offset_x,
            "offset_y": offset_y,
        },
    }


def _validate_size(value: tuple[int, int], name: str) -> tuple[int, int]:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not all(isinstance(item, int) and item > 0 for item in value)
    ):
        raise ValueError(f"{name} must be a tuple of two positive integers")
    return value


def _positive_number(data: dict[str, Any], key: str) -> float:
    value = _number(data, key)
    if value <= 0:
        raise ValueError(f"transform_to_level0.{key} must be positive")
    return value


def _number(data: dict[str, Any], key: str) -> float:
    if key not in data:
        raise ValueError(f"transform_to_level0.{key} is required")
    value = data[key]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"transform_to_level0.{key} must be a number")
    return float(value)
