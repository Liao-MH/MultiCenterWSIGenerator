import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION


PRIOR_ARTIFACT_TYPES = (
    "layout_mask_prior",
    "style_prior",
    "texture_prior",
    "qc_reference_distribution",
)
OPTIONAL_PRIOR_ARTIFACT_TYPES = ("wsi_tissue_overview",)
ALL_PRIOR_ARTIFACT_TYPES = PRIOR_ARTIFACT_TYPES + OPTIONAL_PRIOR_ARTIFACT_TYPES
PRODUCTION_PRIOR_COMPONENT_CONTRACT_VERSION = "production_prior_component_v1"
REQUIRED_PRODUCTION_CONDITION_OUTPUTS = {
    "layout_mask_prior": ("layout", "mask"),
    "style_prior": ("style_seed", "style_latent"),
    "texture_prior": ("texture_token", "morphology_latent"),
}


class PriorArtifactError(ValueError):
    """Raised when a prior artifact manifest is incomplete or inconsistent."""


def build_prior_manifest_from_artifacts(
    *,
    output_dir: str | Path,
    prior_id: str,
    dataset_id: str,
    input_manifest_path: str | Path,
    training_data_version: str,
    wsi_ids: list[str],
    random_seed: int,
    layout_mask_prior_path: str | Path,
    style_prior_path: str | Path,
    texture_prior_path: str | Path,
    qc_reference_distribution_path: str | Path,
    wsi_tissue_overview_path: str | Path | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    artifact_paths = {
        "layout_mask_prior": layout_mask_prior_path,
        "style_prior": style_prior_path,
        "texture_prior": texture_prior_path,
        "qc_reference_distribution": qc_reference_distribution_path,
    }
    if wsi_tissue_overview_path is not None:
        artifact_paths["wsi_tissue_overview"] = wsi_tissue_overview_path
    artifacts = {}
    for artifact_type, artifact_path in artifact_paths.items():
        artifact_json = _load_artifact_json(artifact_path, artifact_type)
        artifacts[artifact_type] = create_prior_artifact_entry(
            artifact_path,
            kind="json",
            metadata=_summarize_artifact_json(artifact_type, artifact_json),
        )

    # The builder is intentionally only an assembly step: artifact content stays
    # in its own JSON file, while the manifest records stable hashes, sizes, and
    # lightweight source summaries needed for reproducible generation runs.
    manifest = {
        "schema_version": PROJECT_VERSION,
        "prior_id": prior_id,
        "created_at": created_at or _now_iso(),
        "random_seed": random_seed,
        "input_data": {
            "dataset_id": dataset_id,
            "manifest_path": str(input_manifest_path),
            "training_data_version": training_data_version,
            "wsi_ids": list(wsi_ids),
        },
        "artifacts": artifacts,
        "production_readiness": _default_production_readiness_contract(),
    }
    manifest_path = save_prior_manifest(output_dir, manifest)
    return load_prior_manifest(manifest_path, verify_files=True)


def create_prior_artifact_entry(
    path: str | Path,
    kind: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise PriorArtifactError(f"artifact file does not exist: {artifact_path}")
    if not artifact_path.is_file():
        raise PriorArtifactError(f"artifact path is not a file: {artifact_path}")
    return {
        "path": str(artifact_path),
        "kind": _validate_kind(kind),
        "sha256": _sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "metadata": deepcopy(metadata or {}),
    }


def save_prior_manifest(output_dir: str | Path, manifest: dict[str, Any]) -> Path:
    validated = validate_prior_manifest(manifest, verify_files=True)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "prior_manifest.json"
    manifest_path.write_text(
        json.dumps(validated, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def load_prior_manifest(path: str | Path, verify_files: bool = True) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise PriorArtifactError(f"prior manifest does not exist: {manifest_path}")
    if not manifest_path.is_file():
        raise PriorArtifactError(f"prior manifest path is not a file: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PriorArtifactError(f"{manifest_path} is not valid JSON: {exc.msg}") from exc
    return validate_prior_manifest(data, verify_files=verify_files)


def validate_prior_manifest(
    manifest: dict[str, Any],
    verify_files: bool = True,
) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PriorArtifactError("prior manifest must be a JSON object")
    _require_equal(manifest, "schema_version", PROJECT_VERSION)
    _require_non_empty_str(manifest, "prior_id")
    _require_non_empty_str(manifest, "created_at")
    seed = manifest.get("random_seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise PriorArtifactError("random_seed must be an integer")

    input_data = _require_dict(manifest, "input_data")
    _require_non_empty_str(input_data, "dataset_id", "input_data.dataset_id")
    _require_non_empty_str(input_data, "manifest_path", "input_data.manifest_path")
    _require_non_empty_str(
        input_data,
        "training_data_version",
        "input_data.training_data_version",
    )
    wsi_ids = input_data.get("wsi_ids")
    if not isinstance(wsi_ids, list) or not all(isinstance(item, str) and item for item in wsi_ids):
        raise PriorArtifactError("input_data.wsi_ids must be a list of non-empty strings")

    artifacts = _require_dict(manifest, "artifacts")
    for artifact_type in PRIOR_ARTIFACT_TYPES:
        if artifact_type not in artifacts:
            raise PriorArtifactError(f"missing required artifact: {artifact_type}")
    extra = sorted(set(artifacts).difference(ALL_PRIOR_ARTIFACT_TYPES))
    if extra:
        raise PriorArtifactError(f"unknown artifact type: {extra[0]}")

    seen_paths: set[str] = set()
    for artifact_type in ALL_PRIOR_ARTIFACT_TYPES:
        if artifact_type not in artifacts:
            continue
        artifact = _require_dict(artifacts, artifact_type, f"artifacts.{artifact_type}")
        path = _require_non_empty_str(artifact, "path", f"artifacts.{artifact_type}.path")
        if path in seen_paths:
            raise PriorArtifactError(f"duplicate artifact path: {path}")
        seen_paths.add(path)
        _validate_kind(_require_non_empty_str(artifact, "kind", f"artifacts.{artifact_type}.kind"))
        sha256 = _require_non_empty_str(
            artifact,
            "sha256",
            f"artifacts.{artifact_type}.sha256",
        )
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
            raise PriorArtifactError(f"artifacts.{artifact_type}.sha256 must be a hex sha256")
        size_bytes = artifact.get("size_bytes")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise PriorArtifactError(f"artifacts.{artifact_type}.size_bytes must be non-negative")
        _require_dict(artifact, "metadata", f"artifacts.{artifact_type}.metadata")
        if verify_files:
            artifact_path = Path(path)
            if not artifact_path.exists():
                raise PriorArtifactError(f"artifact file does not exist: {artifact_path}")
            if not artifact_path.is_file():
                raise PriorArtifactError(f"artifact path is not a file: {artifact_path}")
            actual_hash = _sha256_file(artifact_path)
            if actual_hash != sha256:
                raise PriorArtifactError(f"sha256 mismatch for artifact {artifact_type}")
            actual_size = artifact_path.stat().st_size
            if actual_size != size_bytes:
                raise PriorArtifactError(f"size_bytes mismatch for artifact {artifact_type}")

    _validate_production_readiness(manifest)

    return deepcopy(manifest)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_artifact_json(path: str | Path, artifact_type: str) -> dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise PriorArtifactError(f"{artifact_type} artifact file does not exist: {artifact_path}")
    if not artifact_path.is_file():
        raise PriorArtifactError(f"{artifact_type} artifact path is not a file: {artifact_path}")
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PriorArtifactError(
            f"{artifact_type} artifact is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise PriorArtifactError(f"{artifact_type} artifact must be a JSON object")
    return data


def _summarize_artifact_json(artifact_type: str, data: dict[str, Any]) -> dict[str, Any]:
    schema_version = _require_non_empty_str(
        data,
        "schema_version",
        f"{artifact_type}.schema_version",
    )
    metadata: dict[str, Any] = {
        "artifact_type": artifact_type,
        "artifact_schema_version": schema_version,
    }
    if artifact_type in {"layout_mask_prior", "style_prior", "texture_prior"}:
        actual_type = _require_non_empty_str(
            data,
            "prior_type",
            f"{artifact_type} artifact prior_type",
        )
        if actual_type != artifact_type:
            raise PriorArtifactError(
                f"{artifact_type} artifact prior_type must be {artifact_type}"
            )
    elif artifact_type == "qc_reference_distribution":
        source = _require_non_empty_str(
            data,
            "source",
            "qc_reference_distribution artifact source",
        )
        if source != "qc_report_metric_distribution":
            raise PriorArtifactError(
                "qc_reference_distribution artifact source must be "
                "qc_report_metric_distribution"
            )
        metrics = _require_dict(
            data,
            "metrics",
            "qc_reference_distribution.metrics",
        )
        metadata["metric_count"] = len(metrics)
        stratification = data.get("stratification")
        if isinstance(stratification, dict):
            fields = stratification.get("fields")
            stratum_count = stratification.get("stratum_count")
            if isinstance(fields, list):
                metadata["stratification_fields"] = deepcopy(fields)
            if isinstance(stratum_count, int) and not isinstance(stratum_count, bool):
                metadata["stratum_count"] = stratum_count
    elif artifact_type == "wsi_tissue_overview":
        actual_type = _require_non_empty_str(
            data,
            "artifact_type",
            "wsi_tissue_overview artifact_type",
        )
        if actual_type != "wsi_tissue_overview":
            raise PriorArtifactError(
                "wsi_tissue_overview artifact_type must be wsi_tissue_overview"
            )
        source = _require_dict(data, "source", "wsi_tissue_overview.source")
        if "backend" in source:
            metadata["source_backend"] = deepcopy(source["backend"])
        if "thumbnail_max_size" in source:
            metadata["thumbnail_max_size"] = deepcopy(source["thumbnail_max_size"])

    for key in (
        "sample_count",
        "embedding_count",
        "embedding_dim",
        "cluster_count",
        "non_background_fraction",
        "record_count",
    ):
        if key in data:
            metadata[key] = deepcopy(data[key])
    return metadata


def _validate_kind(kind: str) -> str:
    if kind not in {"json", "npy", "npz", "pt", "pth", "directory"}:
        raise PriorArtifactError("artifact kind must be json, npy, npz, pt, pth, or directory")
    return kind


def _default_production_readiness_contract() -> dict[str, Any]:
    return {
        "production_ready": False,
        "declared_by": "he_wsi_generator.priors.artifacts.build_prior_manifest_from_artifacts",
        "component_contracts": {
            "layout_mask_prior": {
                "production_ready": False,
                "backend": "statistical_layout_mask_prior",
                "required_for_production": "trainable_layout_or_mask_generator",
                "limitations": [
                    "statistical_layout_mask_prior_only",
                    "not_a_trainable_layout_generator",
                    "not_a_mask_diffusion_model",
                ],
            },
            "style_prior": {
                "production_ready": False,
                "backend": "statistical_rgb_style_prior",
                "required_for_production": "trainable_style_encoder_or_style_latent_model",
                "limitations": [
                    "statistical_rgb_style_prior_only",
                    "not_a_trainable_style_encoder",
                    "not_a_vae_style_latent",
                ],
            },
            "texture_prior": {
                "production_ready": False,
                "backend": "statistical_embedding_texture_prior",
                "required_for_production": "trainable_texture_codebook_or_morphology_token_sampler",
                "limitations": [
                    "statistical_embedding_texture_prior_only",
                    "not_a_trainable_texture_codebook",
                    "not_a_vq_vae_or_morphology_token_sampler",
                ],
            },
        },
        "limitations": [
            "statistical_proxy_prior_only",
            "not_production_trainable_prior",
            "safe_for_auditable_conditioning_only",
        ],
    }


def _validate_production_readiness(manifest: dict[str, Any]) -> None:
    readiness = manifest.get("production_readiness")
    if readiness is None:
        return
    if not isinstance(readiness, dict):
        raise PriorArtifactError("production_readiness must be an object")
    production_ready = readiness.get("production_ready")
    if not isinstance(production_ready, bool):
        raise PriorArtifactError("production_readiness.production_ready must be a boolean")
    _require_non_empty_str(
        readiness,
        "declared_by",
        "production_readiness.declared_by",
    )
    component_contracts = _require_dict(
        readiness,
        "component_contracts",
        "production_readiness.component_contracts",
    )
    limitations = readiness.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(item, str) and item for item in limitations):
        raise PriorArtifactError("production_readiness.limitations must be a list of non-empty strings")

    for component_name, component in component_contracts.items():
        if component_name not in PRIOR_ARTIFACT_TYPES:
            raise PriorArtifactError(
                f"production_readiness.component_contracts unknown component: {component_name}"
            )
        if not isinstance(component, dict):
            raise PriorArtifactError(
                f"production_readiness.component_contracts.{component_name} must be an object"
            )
        component_ready = component.get("production_ready")
        if not isinstance(component_ready, bool):
            raise PriorArtifactError(
                f"production_readiness.component_contracts.{component_name}.production_ready must be a boolean"
            )
        backend = _require_non_empty_str(
            component,
            "backend",
            f"production_readiness.component_contracts.{component_name}.backend",
        )
        _require_non_empty_str(
            component,
            "required_for_production",
            f"production_readiness.component_contracts.{component_name}.required_for_production",
        )
        component_limitations = component.get("limitations")
        if not isinstance(component_limitations, list) or not all(
            isinstance(item, str) and item for item in component_limitations
        ):
            raise PriorArtifactError(
                f"production_readiness.component_contracts.{component_name}.limitations "
                "must be a list of non-empty strings"
            )
        if production_ready and (
            backend.startswith("statistical_")
            or any("not_a_" in item or "statistical" in item for item in component_limitations)
        ):
            raise PriorArtifactError(
                f"production_ready prior manifest cannot use proxy component: {component_name}"
            )

    if production_ready:
        for component_name in ("layout_mask_prior", "style_prior", "texture_prior"):
            if component_name not in component_contracts:
                raise PriorArtifactError(
                    f"production_readiness.component_contracts missing {component_name}"
                )
            if component_contracts[component_name].get("production_ready") is not True:
                raise PriorArtifactError(
                    f"production_ready prior manifest requires {component_name} production_ready=true"
                )
            _validate_production_component_contract(
                component_name,
                component_contracts[component_name],
                manifest["artifacts"][component_name],
            )


def _validate_production_component_contract(
    component_name: str,
    component: dict[str, Any],
    artifact: dict[str, Any],
) -> None:
    contract_version = _require_non_empty_str(
        component,
        "contract_version",
        f"production_readiness.component_contracts.{component_name}.contract_version",
    )
    if contract_version != PRODUCTION_PRIOR_COMPONENT_CONTRACT_VERSION:
        raise PriorArtifactError(
            f"production_readiness.component_contracts.{component_name}.contract_version "
            f"must be {PRODUCTION_PRIOR_COMPONENT_CONTRACT_VERSION}"
        )
    condition_outputs = component.get("condition_outputs")
    if not isinstance(condition_outputs, list) or not all(
        isinstance(item, str) and item for item in condition_outputs
    ):
        raise PriorArtifactError(
            f"production_readiness.component_contracts.{component_name}.condition_outputs "
            "must be a list of non-empty strings"
        )
    missing_outputs = [
        output
        for output in REQUIRED_PRODUCTION_CONDITION_OUTPUTS[component_name]
        if output not in condition_outputs
    ]
    if missing_outputs:
        joined = ", ".join(missing_outputs)
        raise PriorArtifactError(
            f"production_readiness.component_contracts.{component_name}.condition_outputs "
            f"missing: {joined}"
        )

    evidence = _require_dict(
        component,
        "training_evidence",
        f"production_readiness.component_contracts.{component_name}.training_evidence",
    )
    _require_non_empty_str(
        evidence,
        "training_run_id",
        f"production_readiness.component_contracts.{component_name}.training_evidence.training_run_id",
    )
    evidence_path = _require_non_empty_str(
        evidence,
        "artifact_path",
        f"production_readiness.component_contracts.{component_name}.training_evidence.artifact_path",
    )
    evidence_sha256 = _require_non_empty_str(
        evidence,
        "artifact_sha256",
        f"production_readiness.component_contracts.{component_name}.training_evidence.artifact_sha256",
    )
    if evidence_path != artifact["path"]:
        raise PriorArtifactError(
            f"production_readiness.component_contracts.{component_name}.training_evidence.artifact_path "
            "must match manifest artifact path"
        )
    if evidence_sha256 != artifact["sha256"]:
        raise PriorArtifactError(
            f"production_readiness.component_contracts.{component_name}.training_evidence.artifact_sha256 "
            "must match manifest artifact sha256"
        )


def _require_equal(data: dict[str, Any], key: str, expected: Any) -> None:
    actual = data.get(key)
    if actual != expected:
        raise PriorArtifactError(f"{key} must be {expected}")


def _require_non_empty_str(
    data: dict[str, Any],
    key: str,
    path: str | None = None,
) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise PriorArtifactError(f"{path or key} must be a non-empty string")
    return value


def _require_dict(
    data: dict[str, Any],
    key: str,
    path: str | None = None,
) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PriorArtifactError(f"{path or key} must be an object")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
