import json
from pathlib import Path


def save_embedding_cache(cache_dir: str | Path, cache_key: str, embeddings, metadata: dict) -> dict:
    numpy = _import_numpy()
    array = numpy.asarray(embeddings, dtype=numpy.float32)
    if array.ndim != 2:
        raise ValueError("embeddings must be a 2D array")
    if not numpy.isfinite(array).all():
        raise ValueError("embeddings contain non-finite values")
    required = {"model_id", "checkpoint_hash", "embedding_dim", "patch_count"}
    missing = sorted(required.difference(metadata))
    if missing:
        raise ValueError(f"embedding metadata missing required fields: {', '.join(missing)}")
    if int(metadata["patch_count"]) != int(array.shape[0]):
        raise ValueError("embedding metadata patch_count does not match embeddings")

    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    embeddings_path = root / f"{cache_key}.embeddings.npy"
    metadata_path = root / f"{cache_key}.metadata.json"
    numpy.save(embeddings_path, array)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"embeddings": str(embeddings_path), "metadata": str(metadata_path)}


def load_embedding_cache(cache_dir: str | Path, cache_key: str):
    numpy = _import_numpy()
    root = Path(cache_dir)
    embeddings_path = root / f"{cache_key}.embeddings.npy"
    metadata_path = root / f"{cache_key}.metadata.json"
    if not embeddings_path.exists():
        raise FileNotFoundError(f"{embeddings_path} does not exist")
    if not metadata_path.exists():
        raise FileNotFoundError(f"{metadata_path} does not exist")
    embeddings = numpy.load(embeddings_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return embeddings, metadata


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise RuntimeError("Embedding cache requires numpy") from exc
    return numpy
