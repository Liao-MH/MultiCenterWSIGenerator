import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import (
    CASCADE_LEVELS,
    MASK_CLASSES,
    MAX_MAGNIFICATION,
    PROJECT_VERSION,
    SOURCE_ANCHORED_PRESETS,
    TILE_SIZE_40X,
)
from ..priors.artifacts import PriorArtifactError, load_prior_manifest
from ..schemas import ValidationError, validate_generation_config


class GenerationConditionError(ValueError):
    """Raised when priors and generation config cannot form a condition packet."""


def build_generation_condition_packet(
    generation_config: dict[str, Any],
    prior_manifest_path: str | Path,
    output_path: str | Path,
    cascade_level: str,
    tile_origin_40x: tuple[int, int] | list[int],
) -> dict[str, Any]:
    try:
        config = validate_generation_config(generation_config)
        prior = load_prior_manifest(prior_manifest_path, verify_files=True)
    except (ValidationError, PriorArtifactError) as exc:
        raise GenerationConditionError(str(exc)) from exc

    coord = _coord_condition(cascade_level, tile_origin_40x)
    artifacts = {
        artifact_type: _load_artifact_json(prior, artifact_type)
        for artifact_type in (
            "layout_mask_prior",
            "style_prior",
            "texture_prior",
            "qc_reference_distribution",
        )
    }
    layout = _layout_condition(prior, artifacts["layout_mask_prior"])
    packet = {
        "schema_version": PROJECT_VERSION,
        "condition_packet_type": "generation_condition_packet",
        "created_at": _now_iso(),
        "prior_manifest_path": str(prior_manifest_path),
        "prior_id": prior["prior_id"],
        "generation_config": {
            "random_seed": config["random_seed"],
            "model_family": config["model_family"],
            "structure_anchor": config["structure_anchor"],
            "anchor_preset": config["anchor_preset"],
            "style_seed": config["style_seed"],
            "source_wsi_id": config["source_wsi_id"],
            "sample_steps": config["sample_steps"],
            "overlap_px_40x": config["overlap_px_40x"],
        },
        "artifact_inputs": _artifact_inputs(prior),
        "conditions": {
            "layout": layout,
            "mask": _mask_condition(layout),
            "style_seed": _style_seed_condition(config, prior, artifacts["style_prior"]),
            "texture_token": _texture_token_condition(
                config,
                prior,
                artifacts["texture_prior"],
            ),
            "coord": coord,
            "source_condition": _source_condition(config),
            "structure_anchor": _structure_anchor_condition(config),
        },
        "qc_reference": _qc_reference_condition(prior, artifacts["qc_reference_distribution"]),
        "limitations": [
            "auditable_condition_packet_only",
            "not_a_production_diffusion_condition_injection",
            "not_a_sampling_layout_or_texture_model",
        ],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return packet


def _load_artifact_json(prior: dict[str, Any], artifact_type: str) -> dict[str, Any]:
    artifact = prior["artifacts"][artifact_type]
    if artifact["kind"] != "json":
        raise GenerationConditionError(f"{artifact_type} artifact must be JSON")
    path = Path(artifact["path"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationConditionError(f"{artifact_type} artifact is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise GenerationConditionError(f"{artifact_type} artifact must be a JSON object")

    if artifact_type in {"layout_mask_prior", "style_prior", "texture_prior"}:
        actual = _require_non_empty_str(data, "prior_type", f"{artifact_type}.prior_type")
        if actual != artifact_type:
            raise GenerationConditionError(f"{artifact_type}.prior_type must be {artifact_type}")
    elif artifact_type == "qc_reference_distribution":
        source = _require_non_empty_str(
            data,
            "source",
            "qc_reference_distribution.source",
        )
        if source != "qc_report_metric_distribution":
            raise GenerationConditionError(
                "qc_reference_distribution.source must be qc_report_metric_distribution"
            )
    return data


def _layout_condition(prior: dict[str, Any], layout_prior: dict[str, Any]) -> dict[str, Any]:
    class_names = _require_list(layout_prior, "class_names", "layout_mask_prior.class_names")
    if tuple(class_names) != MASK_CLASSES:
        raise GenerationConditionError("layout_mask_prior.class_names must match project mask classes")
    fractions = _require_list(
        layout_prior,
        "class_fractions_by_id",
        "layout_mask_prior.class_fractions_by_id",
    )
    if len(fractions) != len(MASK_CLASSES):
        raise GenerationConditionError(
            "layout_mask_prior.class_fractions_by_id must contain six values"
        )
    return {
        "source": "layout_mask_prior",
        "artifact_path": prior["artifacts"]["layout_mask_prior"]["path"],
        "sample_count": layout_prior.get("sample_count"),
        "class_names": list(class_names),
        "class_fractions_by_id": deepcopy(fractions),
        "non_background_fraction": layout_prior.get("non_background_fraction"),
        "adjacency_counts": deepcopy(layout_prior.get("adjacency_counts", {})),
    }


def _mask_condition(layout: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "layout_mask_prior",
        "class_names": list(layout["class_names"]),
        "class_fractions_by_id": deepcopy(layout["class_fractions_by_id"]),
        "mask_role": "semantic_spatial_condition",
    }


def _style_seed_condition(
    config: dict[str, Any],
    prior: dict[str, Any],
    style_prior: dict[str, Any],
) -> dict[str, Any]:
    style_seed = config["style_seed"]
    if style_seed == "auto":
        value = config["random_seed"]
        source = "generation_config_auto_random_seed"
    elif isinstance(style_seed, int) and not isinstance(style_seed, bool):
        value = style_seed
        source = "generation_config"
    else:
        raise GenerationConditionError("style_seed must be auto or an integer")
    return {
        "source": source,
        "value": value,
        "artifact_path": prior["artifacts"]["style_prior"]["path"],
        "rgb_statistics": deepcopy(style_prior.get("rgb_statistics", {})),
    }


def _texture_token_condition(
    config: dict[str, Any],
    prior: dict[str, Any],
    texture_prior: dict[str, Any],
) -> dict[str, Any]:
    prototypes = texture_prior.get("texture_prototypes")
    if not isinstance(prototypes, list) or not prototypes:
        raise GenerationConditionError("texture_prior.texture_prototypes must be a non-empty list")
    selected = prototypes[config["random_seed"] % len(prototypes)]
    if not isinstance(selected, dict):
        raise GenerationConditionError("texture_prior.texture_prototypes entries must be objects")
    cluster_id = _require_int(selected, "cluster_id", "texture_prior.texture_prototypes.cluster_id")
    representative = _require_int(
        selected,
        "representative_embedding_index",
        "texture_prior.texture_prototypes.representative_embedding_index",
    )
    return {
        "source": "texture_prior",
        "artifact_path": prior["artifacts"]["texture_prior"]["path"],
        "selection_policy": "deterministic_random_seed_mod_cluster_count",
        "cluster_id": cluster_id,
        "representative_embedding_index": representative,
        "fraction": selected.get("fraction"),
        "mean_embedding": deepcopy(selected.get("mean_embedding", [])),
    }


def _coord_condition(cascade_level: str, tile_origin_40x: tuple[int, int] | list[int]) -> dict[str, Any]:
    if cascade_level not in CASCADE_LEVELS:
        raise GenerationConditionError(f"cascade_level must be one of {list(CASCADE_LEVELS)}")
    if not isinstance(tile_origin_40x, (tuple, list)) or len(tile_origin_40x) != 2:
        raise GenerationConditionError("tile_origin_40x must contain x and y")
    x, y = tile_origin_40x
    if (
        not isinstance(x, int)
        or isinstance(x, bool)
        or not isinstance(y, int)
        or isinstance(y, bool)
        or x < 0
        or y < 0
    ):
        raise GenerationConditionError("tile_origin_40x coordinates must be non-negative integers")
    return {
        "cascade_level": cascade_level,
        "tile_origin_40x": [x, y],
        "tile_size_40x": list(TILE_SIZE_40X),
        "max_magnification": MAX_MAGNIFICATION,
        "coord_frame": "level0_40x_pixels",
    }


def _source_condition(config: dict[str, Any]) -> dict[str, Any]:
    source_wsi_id = config.get("source_wsi_id")
    enabled = isinstance(source_wsi_id, str) and source_wsi_id != "" and config["structure_anchor"] > 0
    return {
        "enabled": enabled,
        "source_wsi_id": source_wsi_id if enabled else None,
        "strength": config["structure_anchor"],
        "policy": "enabled_by_source_wsi_id" if enabled else "disabled_for_de_novo_anchor",
    }


def _structure_anchor_condition(config: dict[str, Any]) -> dict[str, Any]:
    source_required = (
        config["structure_anchor"] > 0.3
        or config["anchor_preset"] in SOURCE_ANCHORED_PRESETS
    )
    return {
        "value": config["structure_anchor"],
        "anchor_preset": config["anchor_preset"],
        "source_condition_required": source_required,
        "semantic": "source_condition_strength",
    }


def _qc_reference_condition(prior: dict[str, Any], qc_reference: dict[str, Any]) -> dict[str, Any]:
    metrics = _require_dict(
        qc_reference,
        "metrics",
        "qc_reference_distribution.metrics",
    )
    return {
        "source": "qc_reference_distribution",
        "artifact_path": prior["artifacts"]["qc_reference_distribution"]["path"],
        "metric_names": sorted(metrics),
        "metric_count": len(metrics),
    }


def _artifact_inputs(prior: dict[str, Any]) -> dict[str, Any]:
    return {
        artifact_type: {
            "path": artifact["path"],
            "kind": artifact["kind"],
            "sha256": artifact["sha256"],
            "size_bytes": artifact["size_bytes"],
        }
        for artifact_type, artifact in prior["artifacts"].items()
    }


def _require_non_empty_str(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value == "":
        raise GenerationConditionError(f"{path} must be a non-empty string")
    return value


def _require_list(data: dict[str, Any], key: str, path: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise GenerationConditionError(f"{path} must be a list")
    return value


def _require_dict(data: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise GenerationConditionError(f"{path} must be an object")
    return value


def _require_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise GenerationConditionError(f"{path} must be an integer")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
