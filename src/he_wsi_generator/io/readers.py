import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class WSIReadError(RuntimeError):
    """Raised when a WSI-like input cannot provide required audit metadata."""


@dataclass(frozen=True)
class SlideMetadata:
    wsi_id: str
    path: str
    dimensions: tuple[int, int]
    level_dimensions: list[tuple[int, int]]
    level_downsamples: list[float]
    mpp_x: float
    mpp_y: float
    max_magnification: str
    backend: str
    format: str

    def to_record(self) -> dict:
        return {
            "wsi_id": self.wsi_id,
            "wsi_path": self.path,
            "dimensions": list(self.dimensions),
            "level_dimensions": [list(item) for item in self.level_dimensions],
            "level_downsamples": self.level_downsamples,
            "mpp_x": self.mpp_x,
            "mpp_y": self.mpp_y,
            "max_magnification": self.max_magnification,
            "backend": self.backend,
            "format": self.format,
        }


class SlideReader(Protocol):
    backend: str

    def read_metadata(self, path: str | Path, wsi_id: str) -> SlideMetadata:
        ...

    def read_thumbnail(self, path: str | Path, max_size: tuple[int, int]):
        ...


class FixtureImageSlideReader:
    """Small-image reader for tests and smoke checks, not a production WSI backend."""

    backend = "fixture-image"

    def read_metadata(self, path: str | Path, wsi_id: str) -> SlideMetadata:
        source = _require_existing_file(path)
        sidecar = self._read_sidecar(source)
        image = self._open_image(source)
        try:
            dimensions = tuple(image.size)
        finally:
            image.close()

        mpp_x = _require_positive_float(sidecar, "mpp_x", f"{source}.json:mpp_x")
        mpp_y = _require_positive_float(sidecar, "mpp_y", f"{source}.json:mpp_y")
        max_magnification = sidecar.get("max_magnification")
        if not isinstance(max_magnification, str) or not max_magnification:
            raise WSIReadError(f"{source}.json:max_magnification is required")

        return SlideMetadata(
            wsi_id=wsi_id,
            path=str(source),
            dimensions=(int(dimensions[0]), int(dimensions[1])),
            level_dimensions=[(int(dimensions[0]), int(dimensions[1]))],
            level_downsamples=[1.0],
            mpp_x=mpp_x,
            mpp_y=mpp_y,
            max_magnification=max_magnification,
            backend=self.backend,
            format=source.suffix.lower().lstrip(".") or "image",
        )

    def read_thumbnail(self, path: str | Path, max_size: tuple[int, int]):
        source = _require_existing_file(path)
        image = self._open_image(source)
        thumbnail = image.copy()
        image.close()
        thumbnail.thumbnail(max_size)
        return thumbnail

    def _read_sidecar(self, source: Path) -> dict:
        sidecar_path = source.with_suffix(source.suffix + ".json")
        if not sidecar_path.exists():
            raise WSIReadError(f"MPP metadata is required in sidecar {sidecar_path}")
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WSIReadError(f"{sidecar_path} is not valid JSON: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise WSIReadError(f"{sidecar_path} must contain a JSON object")
        return data

    def _open_image(self, source: Path):
        try:
            from PIL import Image
        except ImportError as exc:
            raise WSIReadError("Fixture image reading requires Pillow") from exc
        try:
            return Image.open(source)
        except Exception as exc:  # Pillow can raise several format-specific exceptions.
            raise WSIReadError(f"{source} cannot be read as a fixture image: {exc}") from exc


class OpenSlideReader:
    backend = "openslide"

    def read_metadata(self, path: str | Path, wsi_id: str) -> SlideMetadata:
        source = _require_existing_file(path)
        openslide = self._import_openslide()
        try:
            slide = openslide.OpenSlide(str(source))
        except Exception as exc:
            raise WSIReadError(f"OpenSlide cannot read {source}: {exc}") from exc
        try:
            props = slide.properties
            mpp_x = _property_float(
                props,
                getattr(openslide, "PROPERTY_NAME_MPP_X", "openslide.mpp-x"),
                "MPP_X",
                source,
            )
            mpp_y = _property_float(
                props,
                getattr(openslide, "PROPERTY_NAME_MPP_Y", "openslide.mpp-y"),
                "MPP_Y",
                source,
            )
            objective_key = getattr(
                openslide,
                "PROPERTY_NAME_OBJECTIVE_POWER",
                "openslide.objective-power",
            )
            max_magnification = props.get(objective_key)
            if not max_magnification:
                raise WSIReadError(f"{source} is missing objective power metadata")
            return SlideMetadata(
                wsi_id=wsi_id,
                path=str(source),
                dimensions=tuple(int(v) for v in slide.dimensions),
                level_dimensions=[
                    tuple(int(v) for v in dims) for dims in slide.level_dimensions
                ],
                level_downsamples=[float(v) for v in slide.level_downsamples],
                mpp_x=mpp_x,
                mpp_y=mpp_y,
                max_magnification=f"{max_magnification}x",
                backend=self.backend,
                format=props.get("openslide.vendor", source.suffix.lower().lstrip(".")),
            )
        finally:
            slide.close()

    def read_thumbnail(self, path: str | Path, max_size: tuple[int, int]):
        source = _require_existing_file(path)
        openslide = self._import_openslide()
        try:
            slide = openslide.OpenSlide(str(source))
        except Exception as exc:
            raise WSIReadError(f"OpenSlide cannot read {source}: {exc}") from exc
        try:
            return slide.get_thumbnail(max_size)
        finally:
            slide.close()

    def _import_openslide(self):
        try:
            import openslide
        except ImportError as exc:
            raise WSIReadError("OpenSlide reading requires openslide-python") from exc
        return openslide


def _require_existing_file(path: str | Path) -> Path:
    source = Path(path)
    if not source.exists():
        raise WSIReadError(f"{source} does not exist")
    if not source.is_file():
        raise WSIReadError(f"{source} is not a file")
    return source


def _require_positive_float(data: dict, key: str, path: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise WSIReadError(f"{path} must be a positive number")
    return float(value)


def _property_float(props, key: str, label: str, source: Path) -> float:
    value = props.get(key)
    if value is None:
        raise WSIReadError(f"{source} is missing {label} metadata")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise WSIReadError(f"{source} has non-numeric {label} metadata") from exc
    if parsed <= 0:
        raise WSIReadError(f"{source} has non-positive {label} metadata")
    return parsed
