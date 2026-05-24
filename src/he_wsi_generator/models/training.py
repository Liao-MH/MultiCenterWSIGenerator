import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, MAX_MAGNIFICATION, MODEL_FAMILY, PROJECT_VERSION, TILE_SIZE_40X
from ..priors.artifacts import PriorArtifactError, load_prior_manifest


class ModelRunError(ValueError):
    """Raised when a training or generation run cannot be initialized safely."""


TRAINING_STAGES = ("prior_ready", "image_generator", "wsi_consistency")


def create_training_run(config: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_training_config(config)
    output_dir = Path(validated["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        prior = load_prior_manifest(validated["prior_manifest_path"], verify_files=True)
    except PriorArtifactError as exc:
        raise ModelRunError(str(exc)) from exc

    checkpoint_manifest = _checkpoint_manifest(validated, prior)
    checkpoint_path = output_dir / "checkpoint_manifest.json"
    checkpoint_path.write_text(json.dumps(checkpoint_manifest, indent=2) + "\n", encoding="utf-8")

    run = {
        "schema_version": PROJECT_VERSION,
        "run_id": validated["run_id"],
        "created_at": _now_iso(),
        "model_family": MODEL_FAMILY,
        "random_seed": validated["random_seed"],
        "prior_manifest_path": validated["prior_manifest_path"],
        "prior_id": prior["prior_id"],
        "training_index_path": validated["training_index_path"],
        "output_dir": str(output_dir),
        "checkpoint_manifest_path": str(checkpoint_path),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "max_magnification": MAX_MAGNIFICATION,
        "condition_dropout": "enabled",
        "source_condition": "required_when_anchor_gt_0",
        "stages": list(TRAINING_STAGES),
        "status": "initialized_not_trained",
    }
    run_path = output_dir / "training_run.json"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return run


def load_checkpoint_manifest(path: str | Path) -> dict[str, Any]:
    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        raise ModelRunError(f"checkpoint manifest does not exist: {checkpoint_path}")
    try:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelRunError(f"{checkpoint_path} is not valid JSON: {exc.msg}") from exc
    return validate_checkpoint_manifest(data, manifest_path=checkpoint_path)


def validate_checkpoint_manifest(
    data: dict[str, Any],
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ModelRunError("checkpoint manifest must be a JSON object")
    if data.get("schema_version") != PROJECT_VERSION:
        raise ModelRunError(f"checkpoint schema_version must be {PROJECT_VERSION}")
    if data.get("model_family") != MODEL_FAMILY:
        raise ModelRunError(f"checkpoint model_family must be {MODEL_FAMILY}")
    if tuple(data.get("cascade_levels", [])) != CASCADE_LEVELS:
        raise ModelRunError(f"checkpoint cascade_levels must be {list(CASCADE_LEVELS)}")
    if tuple(data.get("tile_size_40x", [])) != TILE_SIZE_40X:
        raise ModelRunError(f"checkpoint tile_size_40x must be {list(TILE_SIZE_40X)}")
    status = data.get("status")
    if status not in {"not_trained", "trained"}:
        raise ModelRunError("checkpoint status must be not_trained or trained")
    if not isinstance(data.get("usable_for_inference"), bool):
        raise ModelRunError("checkpoint usable_for_inference must be boolean")
    if data["usable_for_inference"]:
        _validate_inference_checkpoint_contract(data, manifest_path=manifest_path)
    return data


def _validate_inference_checkpoint_contract(
    data: dict[str, Any],
    manifest_path: str | Path | None,
) -> None:
    if data.get("status") != "trained":
        raise ModelRunError("checkpoint status must be trained when usable_for_inference is true")
    for key in (
        "training_backend",
        "target_type",
        "checkpoint_path",
        "checkpoint_sha256",
    ):
        _require_non_empty_str(data, key)

    resolved_checkpoint_path = _resolve_checkpoint_path(data["checkpoint_path"], manifest_path)
    if not resolved_checkpoint_path.exists() or not resolved_checkpoint_path.is_file():
        raise ModelRunError(f"checkpoint_path must exist and be a file: {resolved_checkpoint_path}")
    actual_hash = _sha256_file(resolved_checkpoint_path)
    if actual_hash != data["checkpoint_sha256"]:
        raise ModelRunError("checkpoint_sha256 does not match checkpoint_path contents")

    # Only inference-ready manifests need the heavier artifact contract.  Skeleton
    # and smoke training manifests stay loadable with usable_for_inference=false,
    # while a true flag must carry explicit backend role and production status.
    contract = data.get("inference_contract")
    if not isinstance(contract, dict):
        raise ModelRunError("inference_contract must be a JSON object")
    for key in ("backend_type", "artifact_role"):
        _require_non_empty_str(contract, key)
    if "production_ready" not in contract:
        raise ModelRunError("inference_contract.production_ready must be explicitly declared")
    if not isinstance(contract["production_ready"], bool):
        raise ModelRunError("inference_contract.production_ready must be boolean")
    if "limitations" not in contract:
        raise ModelRunError("inference_contract.limitations must be explicitly declared")
    if not isinstance(contract["limitations"], list):
        raise ModelRunError("inference_contract.limitations must be a list")


def _resolve_checkpoint_path(
    checkpoint_path: str,
    manifest_path: str | Path | None,
) -> Path:
    path = Path(checkpoint_path)
    if path.is_absolute() or manifest_path is None:
        return path
    return Path(manifest_path).parent / path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_training_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ModelRunError("training config must be a JSON object")
    if config.get("schema_version") != PROJECT_VERSION:
        raise ModelRunError(f"schema_version must be {PROJECT_VERSION}")
    _require_non_empty_str(config, "run_id")
    random_seed = config.get("random_seed")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise ModelRunError("random_seed must be an integer")
    if config.get("model_family") != MODEL_FAMILY:
        raise ModelRunError(f"model_family must be {MODEL_FAMILY}")
    prior_path = Path(_require_non_empty_str(config, "prior_manifest_path"))
    if not prior_path.exists():
        raise ModelRunError(f"prior manifest does not exist: {prior_path}")
    _require_non_empty_str(config, "training_index_path")
    _require_non_empty_str(config, "output_dir")
    if tuple(config.get("cascade_levels", [])) != CASCADE_LEVELS:
        raise ModelRunError(f"cascade_levels must be {list(CASCADE_LEVELS)}")
    if tuple(config.get("tile_size_40x", [])) != TILE_SIZE_40X:
        raise ModelRunError(f"tile_size_40x must be {list(TILE_SIZE_40X)}")
    if config.get("max_magnification") != MAX_MAGNIFICATION:
        raise ModelRunError(f"max_magnification must be {MAX_MAGNIFICATION}")
    if config.get("condition_dropout") != "enabled":
        raise ModelRunError("condition_dropout must be enabled")
    if config.get("source_condition") != "required_when_anchor_gt_0":
        raise ModelRunError("source_condition must be required_when_anchor_gt_0")
    return dict(config)


def _checkpoint_manifest(config: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "not_trained",
        "usable_for_inference": False,
        "model_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "training_run_id": config["run_id"],
        "prior_id": prior["prior_id"],
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "note": "Skeleton checkpoint manifest only; no model weights were trained.",
    }


def _require_non_empty_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise ModelRunError(f"{key} must be a non-empty string")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
