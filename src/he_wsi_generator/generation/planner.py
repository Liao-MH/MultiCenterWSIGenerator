from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import CASCADE_LEVELS, PROJECT_VERSION
from ..models.training import ModelRunError, load_checkpoint_manifest
from ..priors.artifacts import PriorArtifactError, load_prior_manifest
from ..schemas import ValidationError, validate_generation_config
from .tiling import GenerationTilingError, create_tile_traversal_plan


DEFAULT_GENERATION_BACKEND = "smoke-cascade"


def create_generation_plan(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    checkpoint_manifest_path: str | Path,
    generation_backend: str = DEFAULT_GENERATION_BACKEND,
) -> dict[str, Any]:
    try:
        config = validate_generation_config(generation_config)
    except ValidationError as exc:
        raise ModelRunError(str(exc)) from exc
    try:
        prior = load_prior_manifest(prior_manifest_path, verify_files=True)
    except PriorArtifactError as exc:
        raise ModelRunError(str(exc)) from exc
    checkpoint = load_checkpoint_manifest(checkpoint_manifest_path)
    if checkpoint["status"] != "trained" or not checkpoint["usable_for_inference"]:
        raise ModelRunError("checkpoint is not trained and cannot be used for inference")
    inference_contract = checkpoint["inference_contract"]
    compatible_backends = inference_contract["compatible_generation_backends"]
    if generation_backend not in compatible_backends:
        raise ModelRunError(
            f"checkpoint inference_contract is not compatible with generation backend: {generation_backend}"
        )
    try:
        tile_traversal_plan = create_tile_traversal_plan(
            canvas_size_40x=config.get("canvas_size_40x", config["tile_size_40x"]),
            tile_size_40x=config["tile_size_40x"],
            overlap_px_40x=config["overlap_px_40x"],
            resume_index=0,
            cascade_level="1/1",
        )
    except GenerationTilingError as exc:
        raise ModelRunError(str(exc)) from exc

    stages = []
    for index, level in enumerate(CASCADE_LEVELS):
        stages.append(
            {
                "order": index,
                "level": level,
                "status": "planned",
                "condition_inputs": [
                    "mask",
                    "style_seed",
                    "texture_token",
                    "coord",
                    "structure_anchor",
                    "source_condition",
                    "previous_scale",
                ],
                "resume_index": 0,
            }
        )

    return {
        "schema_version": PROJECT_VERSION,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model_family": config["model_family"],
        "prior_manifest_path": str(prior_manifest_path),
        "prior_id": prior["prior_id"],
        "checkpoint_manifest_path": str(checkpoint_manifest_path),
        "checkpoint_model_version": checkpoint["model_version"],
        "generation_backend": generation_backend,
        "checkpoint_inference_contract": {
            "backend_type": inference_contract["backend_type"],
            "artifact_role": inference_contract["artifact_role"],
            "production_ready": inference_contract["production_ready"],
            "limitations": list(inference_contract["limitations"]),
            "compatible_generation_backends": list(compatible_backends),
            "model_architecture_contract": dict(
                inference_contract["model_architecture_contract"]
            ),
            "condition_input_contract": {
                "required_condition_inputs": list(
                    inference_contract["condition_input_contract"][
                        "required_condition_inputs"
                    ]
                ),
                "cascade_levels": list(
                    inference_contract["condition_input_contract"]["cascade_levels"]
                ),
                "condition_feature_policy": inference_contract["condition_input_contract"][
                    "condition_feature_policy"
                ],
            },
        },
        "random_seed": config["random_seed"],
        "structure_anchor": config["structure_anchor"],
        "style_seed": config["style_seed"],
        "source_wsi_id": config["source_wsi_id"],
        "sample_steps": config["sample_steps"],
        "overlap_px_40x": config["overlap_px_40x"],
        "tile_traversal": "row_major_with_resume_index",
        "tile_traversal_plan": tile_traversal_plan,
        "blending": "overlap_weighted_average",
        "write_mode": "chunked_pyramid_write",
        "stages": stages,
    }
