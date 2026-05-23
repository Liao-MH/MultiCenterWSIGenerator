from pathlib import Path

from ..constants import MASK_CLASSES
from ..schemas import validate_label_mapping


class MaskMappingError(ValueError):
    """Raised when a raw annotation mask cannot be mapped to project classes."""


def read_mask_labels(path: str | Path) -> list[int]:
    array = read_mask_array(path)
    numpy = _import_numpy()
    return [int(value) for value in sorted(numpy.unique(array).tolist())]


def read_mask_array(path: str | Path):
    source = Path(path)
    if not source.exists():
        raise MaskMappingError(f"{source} does not exist")
    suffix = source.suffix.lower()
    numpy = _import_numpy()
    if suffix == ".npy":
        return numpy.load(source)
    if suffix == ".npz":
        with numpy.load(source) as data:
            if "mask" not in data:
                raise MaskMappingError(f"{source} must contain an array named 'mask'")
            return data["mask"]
    if suffix in {".png", ".tif", ".tiff"}:
        try:
            from PIL import Image
        except ImportError as exc:
            raise MaskMappingError("PNG/TIFF mask reading requires Pillow") from exc
        try:
            with Image.open(source) as image:
                return numpy.asarray(image)
        except Exception as exc:
            raise MaskMappingError(f"{source} cannot be read as an integer mask: {exc}") from exc
    raise MaskMappingError(f"{source} must be a .png, .tif, .tiff, .npy, or .npz mask")


def apply_label_mapping(mask_array, label_mapping: dict):
    numpy = _import_numpy()
    mapping = validate_label_mapping(label_mapping)
    classes = mapping["classes"]
    mapped = numpy.zeros(mask_array.shape, dtype=numpy.uint8)
    for raw_label in sorted(numpy.unique(mask_array).tolist()):
        raw_key = str(int(raw_label))
        if raw_key not in classes:
            raise MaskMappingError(f"unmapped mask label {raw_key}")
        class_name = classes[raw_key]
        mapped[mask_array == raw_label] = MASK_CLASSES.index(class_name)
    return mapped


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise MaskMappingError("Mask operations require numpy") from exc
    return numpy
