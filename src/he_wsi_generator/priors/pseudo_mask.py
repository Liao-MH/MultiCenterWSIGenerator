import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..embeddings.cache import save_embedding_cache
from ..embeddings.cluster import cluster_embeddings
from ..io.audit import build_reader
from ..io.readers import WSIReadError
from ..schemas import ValidationError, load_document, validate_input_manifest


class PseudoMaskBuildError(ValueError):
    """Raised when a WSI cannot produce an auditable pseudo-mask artifact."""


def build_pseudo_mask_from_manifest(
    *,
    manifest_path: str | Path,
    output_dir: str | Path,
    backend: str,
    embedder,
    patch_size: tuple[int, int],
    n_clusters: int,
    batch_size: int = 512,
) -> dict[str, Any]:
    if not (
        isinstance(patch_size, tuple)
        and len(patch_size) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in patch_size)
    ):
        raise PseudoMaskBuildError("patch_size must contain two positive integers")
    if not isinstance(n_clusters, int) or isinstance(n_clusters, bool) or n_clusters <= 0:
        raise PseudoMaskBuildError("n_clusters must be a positive integer")
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise PseudoMaskBuildError("batch_size must be a positive integer")

    try:
        manifest = validate_input_manifest(load_document(manifest_path))
    except ValidationError as exc:
        raise PseudoMaskBuildError(str(exc)) from exc
    try:
        reader = build_reader(backend)
    except ValueError as exc:
        raise PseudoMaskBuildError(str(exc)) from exc

    records = manifest["records"]
    if len(records) != 1:
        raise PseudoMaskBuildError("build_pseudo_mask_from_manifest currently requires exactly one WSI record")
    record = records[0]

    image_shape = _read_image_shape(
        reader=reader,
        wsi_path=record["wsi_path"],
        wsi_id=record["wsi_id"],
    )
    patch_count = _patch_grid_count(image_shape=image_shape, patch_size=patch_size)
    if n_clusters > patch_count:
        raise PseudoMaskBuildError("n_clusters cannot exceed extracted patch count")

    embeddings, embedding_metadata, patch_records, embedding_batch_count = _extract_patch_embeddings(
        reader=reader,
        wsi_path=record["wsi_path"],
        image_shape=image_shape,
        patch_size=patch_size,
        batch_size=batch_size,
        embedder=embedder,
    )

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    cache_key = f"{record['wsi_id']}-pseudo-mask"
    cache_paths = save_embedding_cache(root / "embedding_cache", cache_key, embeddings, embedding_metadata)
    cluster_report = cluster_embeddings(embeddings, n_clusters=n_clusters)
    cluster_report_path = root / "cluster_report.json"
    cluster_report_path.write_text(json.dumps(cluster_report, indent=2) + "\n", encoding="utf-8")

    numpy = _import_numpy()
    pseudo_mask_path = root / "pseudo_mask.npy"
    _write_pseudo_mask_from_clusters(
        numpy=numpy,
        output_path=pseudo_mask_path,
        labels=cluster_report["labels"],
        patch_records=patch_records,
        image_shape=image_shape,
    )
    annotation_manifest = {
        "schema_version": manifest["schema_version"],
        "wsi_id": record["wsi_id"],
        "annotation_id": f"{record['wsi_id']}-cluster-pseudo-mask",
        "annotation_type": "cluster_pseudo_mask",
        "annotation_path": str(pseudo_mask_path),
        "coordinate_level": 0,
        "label_encoding": "integer_index",
        "transform_to_level0": {
            "scale_x": 1.0,
            "scale_y": 1.0,
            "offset_x": 0,
            "offset_y": 0,
        },
        "status": "raw",
        "mask_shape": [int(image_shape[0]), int(image_shape[1])],
        "patch_size": [int(patch_size[0]), int(patch_size[1])],
        "batch_size": int(batch_size),
        "patch_count": len(patch_records),
        "embedding_batch_count": int(embedding_batch_count),
        "streaming_patch_embedding": True,
        "mask_write_mode": "open_memmap",
        "cluster_count": int(n_clusters),
        # Surface the actual embedding contract at the pseudo-mask artifact level
        # so downstream users do not need to infer whether this came from a
        # statistical checkpoint config or a smoke-only fixture embedder.
        "embedding_summary": _build_embedding_summary(embedding_metadata),
        "embedding_cache": cache_paths,
        "cluster_report_path": str(cluster_report_path),
        "created_at": _now_iso(),
    }
    annotation_manifest_path = root / "cluster_pseudo_mask.json"
    annotation_manifest_path.write_text(
        json.dumps(annotation_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "embedding_cache_dir": str(root / "embedding_cache"),
        "embedding_cache_key": cache_key,
        "cluster_report_path": str(cluster_report_path),
        "pseudo_mask_path": str(pseudo_mask_path),
        "annotation_manifest_path": str(annotation_manifest_path),
    }


def _read_image_shape(
    *,
    reader,
    wsi_path: str,
    wsi_id: str,
) -> tuple[int, int]:
    try:
        metadata = reader.read_metadata(wsi_path, wsi_id=wsi_id)
    except WSIReadError as exc:
        raise PseudoMaskBuildError(str(exc)) from exc
    height = int(metadata.dimensions[1])
    width = int(metadata.dimensions[0])
    if height <= 0 or width <= 0:
        raise PseudoMaskBuildError(f"{metadata.path} produced no patches")
    return int(height), int(width)


def _patch_grid_count(*, image_shape: tuple[int, int], patch_size: tuple[int, int]) -> int:
    height, width = image_shape
    patch_width, patch_height = patch_size
    columns = (int(width) + int(patch_width) - 1) // int(patch_width)
    rows = (int(height) + int(patch_height) - 1) // int(patch_height)
    return int(rows * columns)


def _extract_patch_embeddings(
    *,
    reader,
    wsi_path: str,
    image_shape: tuple[int, int],
    patch_size: tuple[int, int],
    batch_size: int,
    embedder,
) -> tuple[Any, dict[str, Any], list[dict[str, int]], int]:
    numpy = _import_numpy()
    patch_width, patch_height = patch_size
    height, width = image_shape
    embedding_chunks = []
    patch_records: list[dict[str, int]] = []
    embedding_metadata: dict[str, Any] | None = None
    embedding_dim: int | None = None
    embedding_batch_count = 0

    try:
        batches = (
            _iter_openslide_level0_patch_batches(
                wsi_path=wsi_path,
                width=int(width),
                height=int(height),
                patch_width=patch_width,
                patch_height=patch_height,
                batch_size=batch_size,
            )
            if getattr(reader, "backend", None) == "openslide"
            else _iter_fixture_image_patch_batches(
                wsi_path=wsi_path,
                width=int(width),
                height=int(height),
                patch_width=patch_width,
                patch_height=patch_height,
                batch_size=batch_size,
            )
        )
        for patches, record_batch in batches:
            try:
                result = embedder.embed(
                    patches,
                    magnification="40x",
                    normalization={"mode": "none"},
                )
            except Exception as exc:  # explicit surface, no silent fallback
                raise PseudoMaskBuildError(str(exc)) from exc
            chunk = numpy.asarray(result.embeddings, dtype=numpy.float32)
            if chunk.ndim != 2:
                raise PseudoMaskBuildError("embedding batch output must be a 2D array")
            if int(chunk.shape[0]) != len(record_batch):
                raise PseudoMaskBuildError("embedding batch row count does not match patch count")
            if embedding_dim is None:
                embedding_dim = int(chunk.shape[1])
            elif int(chunk.shape[1]) != embedding_dim:
                raise PseudoMaskBuildError("embedding batch dimensions are inconsistent")
            if embedding_metadata is None:
                embedding_metadata = dict(result.metadata)
            embedding_chunks.append(chunk)
            patch_records.extend(record_batch)
            embedding_batch_count += 1
    except PseudoMaskBuildError:
        raise
    except Exception as exc:
        raise PseudoMaskBuildError(f"Failed to extract patches from {wsi_path}: {exc}") from exc

    if not embedding_chunks:
        raise PseudoMaskBuildError(f"{wsi_path} produced no patches")
    embeddings = numpy.concatenate(embedding_chunks, axis=0)
    metadata = embedding_metadata or {}
    metadata["patch_count"] = int(embeddings.shape[0])
    metadata["embedding_dim"] = int(embeddings.shape[1])
    metadata["batch_size"] = int(batch_size)
    metadata["embedding_batch_count"] = int(embedding_batch_count)
    metadata["streaming_patch_embedding"] = True
    return embeddings, metadata, patch_records, embedding_batch_count


def _iter_fixture_image_patch_batches(
    *,
    wsi_path: str,
    width: int,
    height: int,
    patch_width: int,
    patch_height: int,
    batch_size: int,
):
    source = Path(wsi_path)
    try:
        from PIL import Image
    except ImportError as exc:
        raise PseudoMaskBuildError("Pseudo-mask patch extraction requires Pillow") from exc
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        yield from _iter_patch_batches_from_region_reader(
            width=width,
            height=height,
            patch_width=patch_width,
            patch_height=patch_height,
            batch_size=batch_size,
            read_region=lambda x, y, read_width, read_height: rgb.crop((x, y, x + read_width, y + read_height)),
        )


def _iter_openslide_level0_patch_batches(
    *,
    wsi_path: str,
    width: int,
    height: int,
    patch_width: int,
    patch_height: int,
    batch_size: int,
):
    try:
        import openslide
    except ImportError as exc:
        raise PseudoMaskBuildError("Pseudo-mask OpenSlide extraction requires openslide-python") from exc
    slide = openslide.OpenSlide(str(wsi_path))
    try:
        yield from _iter_patch_batches_from_region_reader(
            width=int(width),
            height=int(height),
            patch_width=patch_width,
            patch_height=patch_height,
            batch_size=batch_size,
            read_region=lambda x, y, read_width, read_height: slide.read_region((x, y), 0, (read_width, read_height)).convert("RGB"),
        )
    finally:
        slide.close()


def _iter_patch_batches_from_region_reader(
    *,
    width: int,
    height: int,
    patch_width: int,
    patch_height: int,
    batch_size: int,
    read_region,
):
    numpy = _import_numpy()
    patches: list[Any] = []
    patch_records: list[dict[str, int]] = []
    for y in range(0, height, patch_height):
        for x in range(0, width, patch_width):
            read_width = int(min(patch_width, width - x))
            read_height = int(min(patch_height, height - y))
            patch = read_region(x, y, read_width, read_height)
            if read_width != patch_width or read_height != patch_height:
                patch = patch.resize((patch_width, patch_height))
            patches.append(numpy.asarray(patch, dtype=numpy.float32))
            patch_records.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "width": int(read_width),
                    "height": int(read_height),
                }
            )
            if len(patches) == batch_size:
                yield patches, patch_records
                patches = []
                patch_records = []
    if patches:
        yield patches, patch_records


def _write_pseudo_mask_from_clusters(
    *,
    numpy,
    output_path: str | Path,
    labels: list[int],
    patch_records: list[dict[str, int]],
    image_shape: tuple[int, int],
) -> None:
    height, width = image_shape
    mask = numpy.lib.format.open_memmap(
        str(output_path),
        mode="w+",
        dtype=numpy.uint8,
        shape=(int(height), int(width)),
    )
    mask[:, :] = 0
    for index, label in enumerate(labels):
        patch = patch_records[index]
        x = int(patch["x"])
        y = int(patch["y"])
        patch_width = int(patch["width"])
        patch_height = int(patch["height"])
        mask[y : y + patch_height, x : x + patch_width] = int(label)
    mask.flush()


def _build_embedding_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    limitations = metadata.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []
    return {
        "model_id": metadata.get("model_id"),
        "embedder_kind": metadata.get("embedder_kind"),
        "embedding_backend": metadata.get("embedding_backend"),
        "checkpoint_path": metadata.get("checkpoint_path"),
        "checkpoint_hash": metadata.get("checkpoint_hash"),
        "checkpoint_format": metadata.get("checkpoint_format"),
        "production_ready": bool(metadata.get("production_ready", False)),
        "limitations": [
            item
            for item in limitations
            if isinstance(item, str) and item
        ],
    }


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise PseudoMaskBuildError("Pseudo-mask building requires numpy") from exc
    return numpy


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
