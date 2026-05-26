import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import (
    CASCADE_LEVELS,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    MODEL_FAMILY,
    PROJECT_VERSION,
    TILE_SIZE_40X,
)
from ..priors.artifacts import PriorArtifactError, load_prior_manifest


class ModelRunError(ValueError):
    """Raised when a training or generation run cannot be initialized safely."""


TRAINING_STAGES = ("prior_ready", "image_generator", "wsi_consistency")
PRODUCTION_TRAINING_BACKEND = MODEL_FAMILY
PRODUCTION_TARGET_TYPE = "latent_diffusion_unet_generation"
REQUIRED_DATASET_CONDITION_INPUTS = (
    "mask",
    "style",
    "texture",
    "coord",
    "source_condition",
    "structure_anchor",
)
TRAINING_OBJECTIVE_SCHEMA = "five_training_constraints_v1"
REQUIRED_TRAINING_OBJECTIVES = (
    "diffusion_generation",
    "semantic_mask_consistency",
    "cross_scale_consistency",
    "tile_seam_consistency",
    "slide_style_consistency",
)
REQUIRED_OBJECTIVES_BY_STAGE = {
    "image_generator": (
        "diffusion_generation",
        "semantic_mask_consistency",
        "cross_scale_consistency",
    ),
    "wsi_consistency": (
        "cross_scale_consistency",
        "tile_seam_consistency",
        "slide_style_consistency",
    ),
}
REQUIRED_QC_MAPPING = {
    "diffusion_generation": ("color_distribution", "sharpness", "texture_quality"),
    "semantic_mask_consistency": (
        "mask_region_validity",
        "mask_image_semantic_alignment",
    ),
    "cross_scale_consistency": ("pyramid_consistency",),
    "tile_seam_consistency": ("seam_score", "overlap_region_delta"),
    "slide_style_consistency": ("slide_style_consistency",),
}
REQUIRED_INFERENCE_CONDITION_INPUTS = (
    "mask",
    "style_seed",
    "texture_token",
    "coord",
    "structure_anchor",
    "source_condition",
    "previous_scale",
)


def create_training_run(config: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_training_config(config)
    output_dir = Path(validated["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        prior = load_prior_manifest(validated["prior_manifest_path"], verify_files=True)
    except PriorArtifactError as exc:
        raise ModelRunError(str(exc)) from exc

    checkpoint_path = output_dir / "checkpoint_manifest.json"
    training_plan_path = output_dir / "training_plan.json"
    training_plan = _training_plan_manifest(
        validated,
        prior,
        checkpoint_manifest_path=checkpoint_path,
    )
    training_plan_path.write_text(json.dumps(training_plan, indent=2) + "\n", encoding="utf-8")

    checkpoint_manifest = _checkpoint_manifest(
        validated,
        prior,
        training_plan_path=training_plan_path,
    )
    checkpoint_path.write_text(json.dumps(checkpoint_manifest, indent=2) + "\n", encoding="utf-8")

    run = {
        "schema_version": PROJECT_VERSION,
        "run_id": validated["run_id"],
        "created_at": _now_iso(),
        "model_family": MODEL_FAMILY,
        "random_seed": validated["random_seed"],
        "prior_manifest_path": validated["prior_manifest_path"],
        "prior_id": prior["prior_id"],
        "training_backend": validated["training_backend"],
        "training_index_path": validated["training_index_path"],
        "dataset_contract": validated["dataset_contract"],
        "training_objective_contract": validated["training_objective_contract"],
        "output_dir": str(output_dir),
        "checkpoint_manifest_path": str(checkpoint_path),
        "training_plan_path": str(training_plan_path),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "max_magnification": MAX_MAGNIFICATION,
        "condition_dropout": "enabled",
        "source_condition": "required_when_anchor_gt_0",
        "stages": list(TRAINING_STAGES),
        "status": "initialized_not_trained",
    }
    training_plan["training_run_path"] = str(output_dir / "training_run.json")
    training_plan_path.write_text(json.dumps(training_plan, indent=2) + "\n", encoding="utf-8")

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
    compatible_backends = contract.get("compatible_generation_backends")
    if (
        not isinstance(compatible_backends, list)
        or not compatible_backends
        or not all(isinstance(value, str) and value for value in compatible_backends)
    ):
        raise ModelRunError(
            "inference_contract.compatible_generation_backends must be a non-empty list of strings"
        )
    _validate_inference_model_architecture_contract(contract.get("model_architecture_contract"))
    _validate_inference_condition_input_contract(contract.get("condition_input_contract"))


def _validate_inference_model_architecture_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise ModelRunError("inference_contract.model_architecture_contract must be a JSON object")
    for key in ("model_family", "architecture_name", "input_space", "output_space"):
        _require_non_empty_str(contract, key, prefix="inference_contract.model_architecture_contract")
    if contract["model_family"] != MODEL_FAMILY:
        raise ModelRunError(
            f"inference_contract.model_architecture_contract.model_family must be {MODEL_FAMILY}"
        )


def _validate_inference_condition_input_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise ModelRunError("inference_contract.condition_input_contract must be a JSON object")
    inputs = contract.get("required_condition_inputs")
    if not isinstance(inputs, list) or not all(isinstance(value, str) and value for value in inputs):
        raise ModelRunError(
            "inference_contract.condition_input_contract.required_condition_inputs must be a list of strings"
        )
    missing_inputs = [value for value in REQUIRED_INFERENCE_CONDITION_INPUTS if value not in inputs]
    if missing_inputs:
        joined = ", ".join(missing_inputs)
        raise ModelRunError(
            f"inference_contract.condition_input_contract.required_condition_inputs missing: {joined}"
        )
    if tuple(contract.get("cascade_levels", [])) != CASCADE_LEVELS:
        raise ModelRunError(
            "inference_contract.condition_input_contract.cascade_levels must match checkpoint cascade_levels"
        )
    _require_non_empty_str(
        contract,
        "condition_feature_policy",
        prefix="inference_contract.condition_input_contract",
    )


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
    if config.get("training_backend") != PRODUCTION_TRAINING_BACKEND:
        raise ModelRunError(f"training_backend must be {PRODUCTION_TRAINING_BACKEND}")
    prior_path = Path(_require_non_empty_str(config, "prior_manifest_path"))
    if not prior_path.exists():
        raise ModelRunError(f"prior manifest does not exist: {prior_path}")
    training_index_path = _require_non_empty_str(config, "training_index_path")
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
    validated = dict(config)
    validated["dataset_contract"] = _validate_dataset_contract(
        config.get("dataset_contract"),
        training_index_path=training_index_path,
    )
    validated["training_objective_contract"] = _validate_training_objective_contract(
        config.get("training_objective_contract"),
    )
    return validated


def _validate_dataset_contract(contract: Any, *, training_index_path: str) -> dict[str, Any]:
    # This is a production-training data contract gate, not a training loop.
    # It rejects incomplete dataset declarations up front while keeping the
    # emitted skeleton checkpoint explicitly unusable for inference.
    if not isinstance(contract, dict):
        raise ModelRunError("dataset_contract must be a JSON object")
    if contract.get("training_index_path") != training_index_path:
        raise ModelRunError("dataset_contract.training_index_path must match training_index_path")
    if contract.get("production_readiness_declared") is not True:
        raise ModelRunError("dataset_contract.production_readiness_declared must be true")
    minimum_sample_count = _require_positive_int(
        contract,
        "minimum_sample_count",
        "dataset_contract.minimum_sample_count",
    )
    sample_count = _require_positive_int(contract, "sample_count", "dataset_contract.sample_count")
    if sample_count < minimum_sample_count:
        raise ModelRunError("dataset_contract.sample_count must be >= minimum_sample_count")
    records_by_split = _require_mapping(
        contract,
        "records_by_split",
        "dataset_contract.records_by_split",
    )
    _require_positive_int(records_by_split, "train", "dataset_contract.records_by_split.train")
    records_by_level = _require_mapping(
        contract,
        "records_by_level",
        "dataset_contract.records_by_level",
    )
    for level in CASCADE_LEVELS:
        _require_positive_int(records_by_level, level, f"dataset_contract.records_by_level.{level}")
    condition_inputs = contract.get("required_condition_inputs")
    if not isinstance(condition_inputs, list) or not all(
        isinstance(value, str) and value for value in condition_inputs
    ):
        raise ModelRunError("dataset_contract.required_condition_inputs must be a list of strings")
    missing_inputs = [
        value for value in REQUIRED_DATASET_CONDITION_INPUTS if value not in condition_inputs
    ]
    if missing_inputs:
        joined = ", ".join(missing_inputs)
        raise ModelRunError(f"dataset_contract.required_condition_inputs missing: {joined}")
    mask_schema = _require_mapping(
        contract,
        "mask_class_schema",
        "dataset_contract.mask_class_schema",
    )
    if mask_schema.get("label_encoding") != "integer_index":
        raise ModelRunError(
            "dataset_contract.mask_class_schema.label_encoding must be integer_index"
        )
    if tuple(mask_schema.get("classes", [])) != MASK_CLASSES:
        raise ModelRunError(
            f"dataset_contract.mask_class_schema.classes must be {list(MASK_CLASSES)}"
        )
    index_summary = _summarize_training_index(training_index_path)
    if index_summary["sample_count"] != sample_count:
        raise ModelRunError(
            "dataset_contract.sample_count must match training index record count"
        )
    if index_summary["records_by_split"] != records_by_split:
        raise ModelRunError(
            "dataset_contract.records_by_split must match training index split counts"
        )
    if index_summary["records_by_level"] != records_by_level:
        raise ModelRunError(
            "dataset_contract.records_by_level must match training index cascade level counts"
        )
    return {
        "training_index_path": contract["training_index_path"],
        "production_readiness_declared": True,
        "minimum_sample_count": minimum_sample_count,
        "sample_count": sample_count,
        "records_by_split": dict(records_by_split),
        "records_by_level": dict(records_by_level),
        "required_condition_inputs": list(condition_inputs),
        "mask_class_schema": {
            "label_encoding": "integer_index",
            "classes": list(MASK_CLASSES),
        },
    }


def _summarize_training_index(path: str) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise ModelRunError(f"training index does not exist: {source}")
    if not source.is_file():
        raise ModelRunError(f"training index is not a file: {source}")

    split_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    sample_count = 0
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped == "":
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ModelRunError(
                    f"training index line {line_number} is not valid JSON: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise ModelRunError(f"training index line {line_number} must be a JSON object")
            _validate_training_index_record(record, line_number=line_number)
            split_counts[record["split"]] += 1
            level_counts[record["cascade_level"]] += 1
            sample_count += 1

    if sample_count == 0:
        raise ModelRunError("training index must contain at least one record")
    return {
        "sample_count": sample_count,
        "records_by_split": dict(split_counts),
        "records_by_level": dict(level_counts),
    }


def _validate_training_index_record(record: dict[str, Any], *, line_number: int) -> None:
    if record.get("schema_version") != PROJECT_VERSION:
        raise ModelRunError(
            f"training index line {line_number} schema_version must be {PROJECT_VERSION}"
        )
    split = record.get("split")
    if not isinstance(split, str) or split == "":
        raise ModelRunError(f"training index line {line_number} split must be a non-empty string")
    level = record.get("cascade_level")
    if level not in CASCADE_LEVELS:
        raise ModelRunError(
            f"training index line {line_number} cascade_level must be one of {list(CASCADE_LEVELS)}"
        )
    tile = record.get("tile")
    if not isinstance(tile, dict):
        raise ModelRunError(f"training index line {line_number} tile must be a JSON object")
    for key in ("x", "y", "width", "height", "coordinate_level"):
        if not isinstance(tile.get(key), int) or isinstance(tile.get(key), bool):
            raise ModelRunError(
                f"training index line {line_number} tile.{key} must be an integer"
            )
    mask = record.get("mask")
    if not isinstance(mask, dict):
        raise ModelRunError(f"training index line {line_number} mask must be a JSON object")
    class_mapping = mask.get("class_mapping")
    if not isinstance(class_mapping, dict):
        raise ModelRunError(
            f"training index line {line_number} mask.class_mapping must be a JSON object"
        )
    if _mask_classes_from_mapping(class_mapping) != list(MASK_CLASSES):
        raise ModelRunError(
            f"training index line {line_number} mask.class_mapping must cover {list(MASK_CLASSES)}"
        )
    conditioning = record.get("conditioning")
    if not isinstance(conditioning, dict):
        raise ModelRunError(
            f"training index line {line_number} conditioning must be a JSON object"
        )
    for key in ("structure_anchor_policy", "style_seed_source", "texture_token_source"):
        if not isinstance(conditioning.get(key), str) or conditioning.get(key) == "":
            raise ModelRunError(
                f"training index line {line_number} conditioning.{key} must be a non-empty string"
            )


def _mask_classes_from_mapping(class_mapping: dict[str, Any]) -> list[str]:
    classes_by_id: dict[int, str] = {}
    for raw_key, value in class_mapping.items():
        if not isinstance(raw_key, str) or not raw_key.isdigit() or not isinstance(value, str):
            raise ModelRunError("training index mask.class_mapping keys must be integer strings")
        classes_by_id[int(raw_key)] = value
    return [classes_by_id[index] for index in sorted(classes_by_id)]


def _validate_training_objective_contract(contract: Any) -> dict[str, Any]:
    # This gate keeps the five design-level training constraints explicit in
    # manifests without pretending the production diffusion losses are already
    # implemented.  Invalid or incomplete objective/QC mappings fail before a
    # skeleton training run is written.
    if not isinstance(contract, dict):
        raise ModelRunError("training_objective_contract must be a JSON object")
    if contract.get("objective_schema") != TRAINING_OBJECTIVE_SCHEMA:
        raise ModelRunError(
            f"training_objective_contract.objective_schema must be {TRAINING_OBJECTIVE_SCHEMA}"
        )
    objectives = contract.get("required_objectives")
    if objectives != list(REQUIRED_TRAINING_OBJECTIVES):
        raise ModelRunError(
            "training_objective_contract.required_objectives must list the five required constraints"
        )
    loss_weights = _require_mapping(
        contract,
        "loss_weights",
        "training_objective_contract.loss_weights",
    )
    validated_weights = {
        objective: _require_non_negative_number(
            loss_weights,
            objective,
            f"training_objective_contract.loss_weights.{objective}",
        )
        for objective in REQUIRED_TRAINING_OBJECTIVES
    }
    objectives_by_stage = _require_mapping(
        contract,
        "objectives_by_stage",
        "training_objective_contract.objectives_by_stage",
    )
    validated_by_stage: dict[str, list[str]] = {}
    for stage, expected_objectives in REQUIRED_OBJECTIVES_BY_STAGE.items():
        actual = objectives_by_stage.get(stage)
        if actual != list(expected_objectives):
            raise ModelRunError(
                f"training_objective_contract.objectives_by_stage.{stage} must be {list(expected_objectives)}"
            )
        validated_by_stage[stage] = list(expected_objectives)
    qc_mapping = _require_mapping(
        contract,
        "qc_mapping",
        "training_objective_contract.qc_mapping",
    )
    validated_qc_mapping: dict[str, list[str]] = {}
    for objective, expected_metrics in REQUIRED_QC_MAPPING.items():
        actual = qc_mapping.get(objective)
        if actual != list(expected_metrics):
            raise ModelRunError(
                f"training_objective_contract.qc_mapping.{objective} must be {list(expected_metrics)}"
            )
        validated_qc_mapping[objective] = list(expected_metrics)
    return {
        "objective_schema": TRAINING_OBJECTIVE_SCHEMA,
        "required_objectives": list(REQUIRED_TRAINING_OBJECTIVES),
        "loss_weights": validated_weights,
        "objectives_by_stage": validated_by_stage,
        "qc_mapping": validated_qc_mapping,
        "implementation_status": "contract_only_no_production_training_loop",
    }


def _training_plan_manifest(
    config: dict[str, Any],
    prior: dict[str, Any],
    *,
    checkpoint_manifest_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "production_training_plan",
        "run_id": config["run_id"],
        "created_at": _now_iso(),
        "model_family": MODEL_FAMILY,
        "training_backend": config["training_backend"],
        "target_type": PRODUCTION_TARGET_TYPE,
        "prior_id": prior["prior_id"],
        "prior_manifest_path": config["prior_manifest_path"],
        "training_index_path": config["training_index_path"],
        "checkpoint_manifest_path": str(checkpoint_manifest_path),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "condition_policy": {
            "condition_dropout": "enabled",
            "source_condition": "required_when_anchor_gt_0",
            "condition_inputs": list(REQUIRED_INFERENCE_CONDITION_INPUTS),
        },
        "dataset_contract_summary": _dataset_contract_summary(config["dataset_contract"]),
        "training_objective_contract_summary": _training_objective_contract_summary(
            config["training_objective_contract"]
        ),
        "stages": _training_plan_stages(config["training_objective_contract"]),
        "implementation_status": "plan_only_no_production_training_loop",
        "limitations": [
            "documents production training stages after contract validation",
            "does not execute diffusion loss optimization",
            "does not produce inference-ready production weights",
        ],
    }


def _training_plan_stages(objective_contract: dict[str, Any]) -> list[dict[str, Any]]:
    qc_mapping = objective_contract["qc_mapping"]
    return [
        {
            "stage": "prior_ready",
            "status": "ready_from_validated_prior_manifest",
            "objectives": ["layout_mask_style_texture_prior_readiness"],
            "condition_inputs": ["layout", "mask", "style", "texture"],
            "outputs": ["validated_prior_manifest"],
            "qc_mapping": {},
        },
        {
            "stage": "image_generator",
            "status": "planned_not_executed",
            "objectives": list(REQUIRED_OBJECTIVES_BY_STAGE["image_generator"]),
            "condition_inputs": [
                "mask",
                "style_seed",
                "texture_token",
                "coord",
                "structure_anchor",
                "source_condition",
                "previous_scale",
            ],
            "outputs": ["mask_conditioned_multiscale_generator_checkpoint"],
            "qc_mapping": {
                objective: list(qc_mapping[objective])
                for objective in REQUIRED_OBJECTIVES_BY_STAGE["image_generator"]
            },
        },
        {
            "stage": "wsi_consistency",
            "status": "planned_not_executed",
            "objectives": list(REQUIRED_OBJECTIVES_BY_STAGE["wsi_consistency"]),
            "condition_inputs": [
                "mask",
                "style_seed",
                "texture_token",
                "coord",
                "structure_anchor",
                "source_condition",
                "previous_scale",
                "neighbor_overlap_context",
            ],
            "outputs": ["wsi_consistency_finetuned_checkpoint"],
            "qc_mapping": {
                objective: list(qc_mapping[objective])
                for objective in REQUIRED_OBJECTIVES_BY_STAGE["wsi_consistency"]
            },
        },
    ]


def _checkpoint_manifest(
    config: dict[str, Any],
    prior: dict[str, Any],
    *,
    training_plan_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_VERSION,
        "model_family": MODEL_FAMILY,
        "status": "not_trained",
        "usable_for_inference": False,
        "model_version": PROJECT_VERSION,
        "created_at": _now_iso(),
        "training_run_id": config["run_id"],
        "training_backend": config["training_backend"],
        "target_type": PRODUCTION_TARGET_TYPE,
        "prior_id": prior["prior_id"],
        "training_plan_path": str(training_plan_path),
        "dataset_contract_summary": _dataset_contract_summary(config["dataset_contract"]),
        "training_objective_contract_summary": _training_objective_contract_summary(
            config["training_objective_contract"]
        ),
        "cascade_levels": list(CASCADE_LEVELS),
        "tile_size_40x": list(TILE_SIZE_40X),
        "note": "Skeleton checkpoint manifest only; no model weights were trained.",
    }


def _dataset_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "training_index_path": contract["training_index_path"],
        "sample_count": contract["sample_count"],
        "minimum_sample_count": contract["minimum_sample_count"],
        "records_by_split": dict(contract["records_by_split"]),
        "records_by_level": dict(contract["records_by_level"]),
        "required_condition_inputs": list(contract["required_condition_inputs"]),
        "mask_class_schema": dict(contract["mask_class_schema"]),
        "production_readiness_declared": contract["production_readiness_declared"],
    }


def _training_objective_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "objective_schema": contract["objective_schema"],
        "required_objectives": list(contract["required_objectives"]),
        "loss_weights": dict(contract["loss_weights"]),
        "objectives_by_stage": {
            stage: list(objectives)
            for stage, objectives in contract["objectives_by_stage"].items()
        },
        "qc_mapping": {
            objective: list(metrics) for objective, metrics in contract["qc_mapping"].items()
        },
        "implementation_status": contract["implementation_status"],
    }


def _require_non_empty_str(data: dict[str, Any], key: str, prefix: str | None = None) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        path = f"{prefix}.{key}" if prefix else key
        raise ModelRunError(f"{path} must be a non-empty string")
    return value


def _require_mapping(data: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ModelRunError(f"{path} must be a JSON object")
    return value


def _require_positive_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ModelRunError(f"{path} must be a positive integer")
    return value


def _require_non_negative_number(data: dict[str, Any], key: str, path: str) -> float:
    value = data.get(key)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not value >= 0
    ):
        raise ModelRunError(f"{path} must be a non-negative number")
    return float(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
