import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..embeddings.cache import load_embedding_cache


class TexturePriorBuildError(ValueError):
    """Raised when embeddings and cluster labels cannot define a texture prior."""


def build_texture_prior_from_embedding_cache(
    cache_dir: str | Path,
    cache_key: str,
    cluster_report_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    try:
        embeddings, metadata = load_embedding_cache(cache_dir, cache_key)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise TexturePriorBuildError(str(exc)) from exc

    numpy = _import_numpy()
    array = numpy.asarray(embeddings, dtype=numpy.float32)
    if array.ndim != 2:
        raise TexturePriorBuildError("embeddings must be a 2D array")
    if not numpy.isfinite(array).all():
        raise TexturePriorBuildError("embeddings contain non-finite values")

    cluster_report = _load_cluster_report(cluster_report_path)
    labels = _validate_cluster_report(cluster_report, array, metadata)
    cluster_count = int(cluster_report["n_clusters"])
    stats_array = array.astype(numpy.float64)
    prototypes = _texture_prototypes(numpy, stats_array, labels, cluster_count)

    prior = {
        "schema_version": PROJECT_VERSION,
        "prior_type": "texture_prior",
        "created_at": _now_iso(),
        "source": {
            "source_type": "embedding_cache_cluster_report",
            "cache_dir": str(cache_dir),
            "cache_key": cache_key,
            "cluster_report_path": str(cluster_report_path),
        },
        "embedding_metadata": metadata,
        "cluster_report_summary": {
            "n_clusters": cluster_count,
            "cluster_counts": cluster_report["cluster_counts"],
            "inertia": float(cluster_report["inertia"]),
            "embedding_count": int(cluster_report["embedding_count"]),
            "embedding_dim": int(cluster_report["embedding_dim"]),
        },
        "embedding_count": int(array.shape[0]),
        "embedding_dim": int(array.shape[1]),
        "cluster_count": cluster_count,
        "global_embedding_mean": [_round_float(value) for value in stats_array.mean(axis=0).tolist()],
        "global_embedding_std": [_round_float(value) for value in stats_array.std(axis=0).tolist()],
        "texture_prototypes": prototypes,
        "limitations": [
            "statistical_embedding_texture_prior_only",
            "not_a_trainable_texture_codebook",
            "not_a_vq_vae_or_morphology_token_sampler",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")
    return prior


def _load_cluster_report(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise TexturePriorBuildError(f"cluster report does not exist: {source}")
    if not source.is_file():
        raise TexturePriorBuildError(f"cluster report path is not a file: {source}")
    try:
        report = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TexturePriorBuildError(f"{source} is not valid JSON: {exc.msg}") from exc
    if not isinstance(report, dict):
        raise TexturePriorBuildError("cluster report must be a JSON object")
    return report


def _validate_cluster_report(
    report: dict[str, Any],
    embeddings,
    metadata: dict[str, Any],
):
    numpy = _import_numpy()
    required = ("n_clusters", "labels", "cluster_counts", "inertia", "embedding_count", "embedding_dim")
    for key in required:
        if key not in report:
            raise TexturePriorBuildError(f"cluster report missing {key}")
    n_clusters = report["n_clusters"]
    if not isinstance(n_clusters, int) or isinstance(n_clusters, bool) or n_clusters <= 0:
        raise TexturePriorBuildError("cluster report n_clusters must be a positive integer")
    labels = report["labels"]
    if not isinstance(labels, list) or not all(
        isinstance(label, int) and not isinstance(label, bool) for label in labels
    ):
        raise TexturePriorBuildError("cluster report labels must be a list of integers")
    if len(labels) != embeddings.shape[0]:
        raise TexturePriorBuildError("cluster report labels length must match embedding row count")
    if any(label < 0 or label >= n_clusters for label in labels):
        raise TexturePriorBuildError("cluster report labels contain an out-of-range cluster id")
    if report["embedding_count"] != embeddings.shape[0]:
        raise TexturePriorBuildError("cluster report embedding_count does not match embeddings")
    if report["embedding_dim"] != embeddings.shape[1]:
        raise TexturePriorBuildError("cluster report embedding_dim does not match embeddings")
    if int(metadata.get("embedding_dim", -1)) != embeddings.shape[1]:
        raise TexturePriorBuildError("embedding metadata embedding_dim does not match embeddings")
    if int(metadata.get("patch_count", -1)) != embeddings.shape[0]:
        raise TexturePriorBuildError("embedding metadata patch_count does not match embeddings")

    labels_array = numpy.asarray(labels, dtype=numpy.int64)
    counts = {
        str(cluster_id): int((labels_array == cluster_id).sum())
        for cluster_id in range(n_clusters)
    }
    if report["cluster_counts"] != counts:
        raise TexturePriorBuildError("cluster report cluster_counts do not match labels")
    return labels_array


def _texture_prototypes(numpy, embeddings, labels, cluster_count: int) -> list[dict[str, Any]]:
    prototypes = []
    total = int(embeddings.shape[0])
    for cluster_id in range(cluster_count):
        indices = numpy.where(labels == cluster_id)[0]
        if indices.size == 0:
            raise TexturePriorBuildError(f"cluster {cluster_id} has no embeddings")
        members = embeddings[indices]
        mean = members.mean(axis=0)
        distances = ((members - mean) ** 2).sum(axis=1)
        representative_index = int(indices[int(distances.argmin())])
        prototypes.append(
            {
                "cluster_id": cluster_id,
                "sample_count": int(indices.size),
                "fraction": _round_float(indices.size / total),
                "mean_embedding": [_round_float(value) for value in mean.tolist()],
                "std_embedding": [_round_float(value) for value in members.std(axis=0).tolist()],
                "representative_embedding_index": representative_index,
            }
        )
    return prototypes


def _round_float(value: float) -> float:
    rounded = round(float(value), 7)
    one_decimal = round(float(value), 1)
    if abs(rounded - one_decimal) < 1e-6:
        return one_decimal
    return rounded


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise TexturePriorBuildError("texture prior building requires numpy") from exc
    return numpy


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
