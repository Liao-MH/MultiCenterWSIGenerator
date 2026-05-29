import json
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..embeddings.cache import load_embedding_cache

TEXTURE_CODEBOOK_TYPE = "fitted_embedding_cluster_codebook_v1"
TEXTURE_TOKEN_TYPE = "embedding_cluster_texture_token_v1"
TEXTURE_PRIOR_KIND = "statistical_embedding_cluster_texture_prior_v1"
# Dimensions listed in design §5.5 that are intentionally outside the current
# statistical embedding-cluster texture prior. They are recorded so downstream
# training/generation cannot silently treat the prior as a full morphology
# token sampler.
TEXTURE_COVERAGE_DIMENSIONS = (
    {"name": "embedding_cluster_codebook", "covered": True, "evidence": "fitted_embedding_cluster_codebook_v1"},
    {"name": "morphology_latent_per_cluster", "covered": True, "evidence": "global_z_score_cluster_centroid"},
    {"name": "trainable_codebook", "covered": False, "evidence": None},
    {"name": "vq_vae_token_sampler", "covered": False, "evidence": None},
    {"name": "morphology_semantic_class", "covered": False, "evidence": None},
    {"name": "region_specific_token_distribution", "covered": False, "evidence": None},
)


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
    global_mean = stats_array.mean(axis=0)
    global_std = stats_array.std(axis=0)
    prototypes = _texture_prototypes(
        numpy,
        stats_array,
        labels,
        cluster_count,
        global_mean,
        global_std,
    )

    prior = {
        "schema_version": PROJECT_VERSION,
        "prior_type": "texture_prior",
        "prior_kind": TEXTURE_PRIOR_KIND,
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
        "global_embedding_mean": [_round_float(value) for value in global_mean.tolist()],
        "global_embedding_std": [_round_float(value) for value in global_std.tolist()],
        "texture_codebook": _texture_codebook(
            embedding_dim=int(array.shape[1]),
            token_count=cluster_count,
        ),
        "texture_prototypes": prototypes,
        "coverage": {
            "covered_dimensions": [
                dim["name"] for dim in TEXTURE_COVERAGE_DIMENSIONS if dim["covered"]
            ],
            "uncovered_dimensions": [
                dim["name"] for dim in TEXTURE_COVERAGE_DIMENSIONS if not dim["covered"]
            ],
            "details": [dict(dim) for dim in TEXTURE_COVERAGE_DIMENSIONS],
        },
        "limitations": [
            "statistical_embedding_texture_prior_only",
            "fitted_embedding_cluster_codebook_only",
            "not_a_trainable_texture_codebook",
            "not_a_vq_vae_or_morphology_token_sampler",
            "no_morphology_semantic_class_label",
            "no_region_specific_token_distribution",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")
    return prior


def sample_texture_policy_from_prior(
    texture_prior_path: str | Path,
    output_path: str | Path,
    sample_id: str,
    random_seed: int,
) -> dict[str, Any]:
    if not isinstance(sample_id, str) or sample_id == "":
        raise TexturePriorBuildError("sample_id must be a non-empty string")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise TexturePriorBuildError("random_seed must be an integer")

    prior = _load_texture_prior(texture_prior_path)
    prototypes = prior.get("texture_prototypes")
    if not isinstance(prototypes, list) or not prototypes:
        raise TexturePriorBuildError("texture_prior.texture_prototypes must be a non-empty list")

    selected_index = random_seed % len(prototypes)
    selected = prototypes[selected_index]
    if not isinstance(selected, dict):
        raise TexturePriorBuildError("texture_prior.texture_prototypes entries must be objects")
    cluster_id = _require_int(
        selected,
        "cluster_id",
        "texture_prior.texture_prototypes.cluster_id",
    )
    representative_index = _require_int(
        selected,
        "representative_embedding_index",
        "texture_prior.texture_prototypes.representative_embedding_index",
    )
    morphology_latent = _validate_numeric_vector(
        selected.get("morphology_latent"),
        "texture_prior.texture_prototypes.morphology_latent",
    )
    texture_token = _validate_texture_token(
        selected,
        prototype_index=selected_index,
        cluster_id=cluster_id,
        representative_embedding_index=representative_index,
    )

    policy = {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "sampled_texture_policy",
        "created_at": _now_iso(),
        "sample_id": sample_id,
        "random_seed": random_seed,
        "selection_policy": "deterministic_random_seed_mod_cluster_count",
        "cluster_count": len(prototypes),
        "source": {
            "source_type": "statistical_texture_prior_policy",
            "texture_prior_path": str(texture_prior_path),
            "texture_prototype_count": len(prototypes),
        },
        "selected_texture_token": {
            "prototype_index": selected_index,
            "cluster_id": cluster_id,
            "representative_embedding_index": representative_index,
            "sample_count": selected.get("sample_count"),
            "fraction": selected.get("fraction"),
            "mean_embedding": list(selected.get("mean_embedding", [])),
            "std_embedding": list(selected.get("std_embedding", [])),
            "texture_token": texture_token,
            "morphology_latent": morphology_latent,
        },
        "texture_codebook_reference": _texture_codebook_reference(prior),
        "coverage_reference": _texture_coverage_reference(prior),
        "limitations": [
            "deterministic_statistical_texture_policy_only",
            "deterministic_fitted_embedding_cluster_codebook_policy_only",
            "not_a_trainable_texture_codebook",
            "not_a_vq_vae_or_morphology_token_sampler",
            "not_production_texture_model",
            "no_morphology_semantic_class_label",
            "no_region_specific_token_distribution",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    return policy


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


def _texture_prototypes(
    numpy,
    embeddings,
    labels,
    cluster_count: int,
    global_mean,
    global_std,
) -> list[dict[str, Any]]:
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
        morphology_latent = _morphology_latent(numpy, mean, global_mean, global_std)
        prototypes.append(
            {
                "cluster_id": cluster_id,
                "sample_count": int(indices.size),
                "fraction": _round_float(indices.size / total),
                "mean_embedding": [_round_float(value) for value in mean.tolist()],
                "std_embedding": [_round_float(value) for value in members.std(axis=0).tolist()],
                "representative_embedding_index": representative_index,
                "texture_token": {
                    "token_type": TEXTURE_TOKEN_TYPE,
                    "token_id": f"texture-cluster-{cluster_id}",
                    "prototype_index": cluster_id,
                    "cluster_id": cluster_id,
                    "representative_embedding_index": representative_index,
                },
                "morphology_latent": morphology_latent,
            }
        )
    return prototypes


def _texture_codebook(embedding_dim: int, token_count: int) -> dict[str, Any]:
    return {
        "codebook_type": TEXTURE_CODEBOOK_TYPE,
        "token_type": TEXTURE_TOKEN_TYPE,
        "embedding_dim": embedding_dim,
        "token_count": token_count,
        "token_schema": {
            "token_id": "texture-cluster-{cluster_id}",
            "cluster_id": "integer cluster label from embedding cluster report",
            "representative_embedding_index": "embedding row nearest to cluster centroid",
        },
        "morphology_latent_schema": {
            "latent_type": "global_z_score_cluster_centroid",
            "feature_source": "embedding_cache",
            "latent_dim": embedding_dim,
            "normalization": "global_embedding_mean_std_with_zero_std_guard",
        },
        "condition_outputs": ["texture_token", "morphology_latent"],
        "limitations": [
            "fitted_embedding_cluster_codebook_only",
            "not_trainable",
            "not_vq_vae",
        ],
    }


def _morphology_latent(numpy, mean, global_mean, global_std) -> list[float]:
    # Zero-variance embedding dimensions can occur in tiny fixtures or narrow
    # training subsets. Treat them as centered dimensions instead of silently
    # producing inf/nan latents.
    safe_std = numpy.where(global_std == 0, 1.0, global_std)
    return [_round_float(value) for value in ((mean - global_mean) / safe_std).tolist()]


def _load_texture_prior(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise TexturePriorBuildError(f"texture prior does not exist: {source}")
    if not source.is_file():
        raise TexturePriorBuildError(f"texture prior path is not a file: {source}")
    try:
        prior = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TexturePriorBuildError(f"texture prior is not valid JSON: {exc.msg}") from exc
    if not isinstance(prior, dict):
        raise TexturePriorBuildError("texture prior must be a JSON object")
    if prior.get("schema_version") != PROJECT_VERSION:
        raise TexturePriorBuildError(f"texture_prior.schema_version must be {PROJECT_VERSION}")
    if prior.get("prior_type") != "texture_prior":
        raise TexturePriorBuildError("texture_prior.prior_type must be texture_prior")
    return prior


def _texture_codebook_reference(prior: dict[str, Any]) -> dict[str, Any]:
    codebook = prior.get("texture_codebook")
    if not isinstance(codebook, dict):
        raise TexturePriorBuildError("texture_prior.texture_codebook must be an object")
    codebook_type = _require_non_empty_str(
        codebook,
        "codebook_type",
        "texture_prior.texture_codebook.codebook_type",
    )
    if codebook_type != TEXTURE_CODEBOOK_TYPE:
        raise TexturePriorBuildError(
            f"texture_prior.texture_codebook.codebook_type must be {TEXTURE_CODEBOOK_TYPE}"
        )
    token_count = _require_int(
        codebook,
        "token_count",
        "texture_prior.texture_codebook.token_count",
    )
    embedding_dim = _require_int(
        codebook,
        "embedding_dim",
        "texture_prior.texture_codebook.embedding_dim",
    )
    condition_outputs = codebook.get("condition_outputs")
    if not isinstance(condition_outputs, list) or "morphology_latent" not in condition_outputs:
        raise TexturePriorBuildError(
            "texture_prior.texture_codebook.condition_outputs must include morphology_latent"
        )
    if "texture_token" not in condition_outputs:
        raise TexturePriorBuildError(
            "texture_prior.texture_codebook.condition_outputs must include texture_token"
        )
    return {
        "codebook_type": codebook_type,
        "token_type": codebook.get("token_type"),
        "embedding_dim": embedding_dim,
        "token_count": token_count,
        "condition_outputs": list(condition_outputs),
    }


def _texture_coverage_reference(prior: dict[str, Any]) -> dict[str, Any]:
    coverage = prior.get("coverage")
    if not isinstance(coverage, dict):
        # Older artifacts written before coverage existed; surface this rather
        # than silently treat the prior as a full morphology token sampler.
        return {
            "covered_dimensions": [
                dim["name"] for dim in TEXTURE_COVERAGE_DIMENSIONS if dim["covered"]
            ],
            "uncovered_dimensions": [
                dim["name"] for dim in TEXTURE_COVERAGE_DIMENSIONS if not dim["covered"]
            ],
            "details": [dict(dim) for dim in TEXTURE_COVERAGE_DIMENSIONS],
            "note": "texture_prior.coverage missing; default coverage assumes statistical embedding clusters only",
        }
    covered = coverage.get("covered_dimensions")
    uncovered = coverage.get("uncovered_dimensions")
    details = coverage.get("details")
    if not isinstance(covered, list) or not isinstance(uncovered, list):
        raise TexturePriorBuildError(
            "texture_prior.coverage.covered_dimensions and uncovered_dimensions must be lists"
        )
    if not isinstance(details, list):
        raise TexturePriorBuildError("texture_prior.coverage.details must be a list")
    return {
        "covered_dimensions": list(covered),
        "uncovered_dimensions": list(uncovered),
        "details": [dict(item) for item in details if isinstance(item, dict)],
    }


def _validate_texture_token(
    prototype: dict[str, Any],
    *,
    prototype_index: int,
    cluster_id: int,
    representative_embedding_index: int,
) -> dict[str, Any]:
    token = prototype.get("texture_token")
    if not isinstance(token, dict):
        raise TexturePriorBuildError("texture_prior.texture_prototypes.texture_token must be an object")
    token_type = _require_non_empty_str(
        token,
        "token_type",
        "texture_prior.texture_prototypes.texture_token.token_type",
    )
    token_id = _require_non_empty_str(
        token,
        "token_id",
        "texture_prior.texture_prototypes.texture_token.token_id",
    )
    token_cluster_id = _require_int(
        token,
        "cluster_id",
        "texture_prior.texture_prototypes.texture_token.cluster_id",
    )
    token_prototype_index = _require_int(
        token,
        "prototype_index",
        "texture_prior.texture_prototypes.texture_token.prototype_index",
    )
    token_representative = _require_int(
        token,
        "representative_embedding_index",
        "texture_prior.texture_prototypes.texture_token.representative_embedding_index",
    )
    if token_type != TEXTURE_TOKEN_TYPE:
        raise TexturePriorBuildError(
            f"texture_prior.texture_prototypes.texture_token.token_type must be {TEXTURE_TOKEN_TYPE}"
        )
    if token_cluster_id != cluster_id:
        raise TexturePriorBuildError(
            "texture_prior.texture_prototypes.texture_token.cluster_id must match cluster_id"
        )
    if token_prototype_index != prototype_index:
        raise TexturePriorBuildError(
            "texture_prior.texture_prototypes.texture_token.prototype_index must match selected prototype"
        )
    if token_representative != representative_embedding_index:
        raise TexturePriorBuildError(
            "texture_prior.texture_prototypes.texture_token.representative_embedding_index must match representative_embedding_index"
        )
    return {
        "token_type": token_type,
        "token_id": token_id,
        "prototype_index": token_prototype_index,
        "cluster_id": token_cluster_id,
        "representative_embedding_index": token_representative,
    }


def _require_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TexturePriorBuildError(f"{path} must be an integer")
    return value


def _require_non_empty_str(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise TexturePriorBuildError(f"{path} must be a non-empty string")
    return value


def _validate_numeric_vector(value: Any, path: str) -> list[float]:
    if not isinstance(value, list) or not value:
        raise TexturePriorBuildError(f"{path} must be a non-empty numeric list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, (int, float)) or isinstance(item, bool) or not isfinite(float(item)):
            raise TexturePriorBuildError(f"{path}[{index}] must be a finite number")
        result.append(_round_float(float(item)))
    return result


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
