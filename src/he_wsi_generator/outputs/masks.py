import json
from pathlib import Path

from ..constants import MASK_CLASSES


def write_mask_array(mask_array, output_dir: str | Path, stem: str = "mask") -> dict:
    numpy = _import_numpy()
    array = numpy.asarray(mask_array, dtype=numpy.uint8)
    if array.ndim != 2:
        raise ValueError("mask array must be 2D")
    unique = set(int(value) for value in numpy.unique(array).tolist())
    valid = set(range(len(MASK_CLASSES)))
    invalid = sorted(unique.difference(valid))
    if invalid:
        raise ValueError(f"mask array contains invalid class id {invalid[0]}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    mask_path = root / f"{stem}.npy"
    metadata_path = root / f"{stem}.metadata.json"
    numpy.save(mask_path, array)
    metadata = {
        "status": "written",
        "path": str(mask_path),
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "classes": len(MASK_CLASSES),
        "class_names": list(MASK_CLASSES),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {**metadata, "metadata_path": str(metadata_path)}


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise RuntimeError("Mask output writing requires numpy") from exc
    return numpy
