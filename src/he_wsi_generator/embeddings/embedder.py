import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION

STATISTICAL_EMBEDDING_BACKEND = "statistical_patch_moments"
CHECKPOINT_EMBEDDER_KIND = "checkpoint_backed_statistical_patch_embedder"
FIXTURE_EMBEDDER_KIND = "fixture_statistical_patch_embedder"


class EmbeddingError(RuntimeError):
    """Raised when patch embedding cannot be computed safely."""


@dataclass(frozen=True)
class EmbeddingResult:
    embeddings: Any
    metadata: dict[str, Any]


class CheckpointPatchEmbedder:
    """Checkpoint-configured statistical patch embedder used by the M08 pseudo-mask path."""

    def __init__(self, checkpoint_path: str | Path):
        self.checkpoint_path = Path(checkpoint_path)
        if not self.checkpoint_path.exists():
            raise EmbeddingError(f"checkpoint does not exist: {self.checkpoint_path}")
        if not self.checkpoint_path.is_file():
            raise EmbeddingError(f"checkpoint is not a file: {self.checkpoint_path}")
        payload = self.checkpoint_path.read_bytes()
        self.checkpoint_hash = hashlib.sha256(payload).hexdigest()
        try:
            checkpoint = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EmbeddingError(
                f"checkpoint must be a JSON config object in {PROJECT_VERSION}"
            ) from exc
        if not isinstance(checkpoint, dict):
            raise EmbeddingError(f"checkpoint must be a JSON config object in {PROJECT_VERSION}")
        model_id = checkpoint.get("model_id")
        embedding_dim = checkpoint.get("embedding_dim")
        if not isinstance(model_id, str) or not model_id:
            raise EmbeddingError("checkpoint.model_id must be a non-empty string")
        if not isinstance(embedding_dim, int) or embedding_dim <= 0:
            raise EmbeddingError("checkpoint.embedding_dim must be a positive integer")
        self.model_id = model_id
        self.embedding_dim = embedding_dim
        self.normalization = checkpoint.get("normalization", "unspecified")

    def embed(self, patches, magnification: str, normalization: dict[str, Any]) -> EmbeddingResult:
        embeddings = _statistical_embeddings(patches, self.embedding_dim)
        return EmbeddingResult(
            embeddings=embeddings,
            metadata={
                "model_id": self.model_id,
                "checkpoint_path": str(self.checkpoint_path),
                "checkpoint_hash": self.checkpoint_hash,
                "embedding_dim": self.embedding_dim,
                "patch_count": int(embeddings.shape[0]),
                "magnification": magnification,
                "normalization": normalization,
                "embedding_confidence": "checkpoint",
                "embedding_backend": STATISTICAL_EMBEDDING_BACKEND,
                "embedder_kind": CHECKPOINT_EMBEDDER_KIND,
                "checkpoint_format": "json_statistical_embedder_config",
                "production_ready": False,
                "limitations": [
                    "statistical_patch_moments_only",
                    "not_a_pathology_foundation_model",
                ],
            },
        )


class FixturePatchEmbedder:
    """Deterministic smoke-test embedder; not a pathology foundation model."""

    def __init__(self, embedding_dim: int = 8):
        if not isinstance(embedding_dim, int) or embedding_dim <= 0:
            raise EmbeddingError("embedding_dim must be a positive integer")
        self.embedding_dim = embedding_dim

    def embed(self, patches, magnification: str, normalization: dict[str, Any]) -> EmbeddingResult:
        embeddings = _statistical_embeddings(patches, self.embedding_dim)
        return EmbeddingResult(
            embeddings=embeddings,
            metadata={
                "model_id": "fixture-smoke-test-embedder",
                "checkpoint_path": None,
                "checkpoint_hash": "fixture-smoke-test",
                "embedding_dim": self.embedding_dim,
                "patch_count": int(embeddings.shape[0]),
                "magnification": magnification,
                "normalization": normalization,
                "embedding_confidence": "low",
                "embedding_backend": STATISTICAL_EMBEDDING_BACKEND,
                "embedder_kind": FIXTURE_EMBEDDER_KIND,
                "checkpoint_format": "fixture_statistical_embedder",
                "production_ready": False,
                "limitations": [
                    "statistical_patch_moments_only",
                    "not_a_pathology_foundation_model",
                    "fixture_smoke_only",
                ],
            },
        )


def _statistical_embeddings(patches, embedding_dim: int):
    numpy = _import_numpy()
    array = numpy.asarray(patches, dtype=numpy.float32)
    if array.ndim < 2:
        raise EmbeddingError("patch batch must have shape (n, ...)")
    if array.shape[0] <= 0:
        raise EmbeddingError("patch batch must contain at least one patch")
    flattened = array.reshape(array.shape[0], -1)
    features = numpy.stack(
        [
            flattened.mean(axis=1),
            flattened.std(axis=1),
            flattened.min(axis=1),
            flattened.max(axis=1),
        ],
        axis=1,
    ).astype(numpy.float32)
    if embedding_dim <= features.shape[1]:
        embeddings = features[:, :embedding_dim]
    else:
        embeddings = numpy.zeros((features.shape[0], embedding_dim), dtype=numpy.float32)
        embeddings[:, : features.shape[1]] = features
    if not numpy.isfinite(embeddings).all():
        raise EmbeddingError("embedding output contains non-finite values")
    return embeddings


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise EmbeddingError("Patch embedding requires numpy") from exc
    return numpy
