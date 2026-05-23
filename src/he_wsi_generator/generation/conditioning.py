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
    sampled_layout_mask_path: str | Path | None = None,
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
    tissue_overview = None
    if "wsi_tissue_overview" in prior["artifacts"]:
        tissue_overview = _load_artifact_json(prior, "wsi_tissue_overview")
    layout = _layout_condition(prior, artifacts["layout_mask_prior"], tissue_overview)
    sampled_layout_mask = (
        _load_sampled_layout_mask(sampled_layout_mask_path)
        if sampled_layout_mask_path is not None
        else None
    )
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
        "artifact_inputs": {
            **_artifact_inputs(prior),
            **_sampled_layout_mask_input(sampled_layout_mask),
        },
        "conditions": {
            "layout": layout,
            "mask": _mask_condition(layout, sampled_layout_mask),
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
    elif artifact_type == "wsi_tissue_overview":
        actual = _require_non_empty_str(
            data,
            "artifact_type",
            "wsi_tissue_overview.artifact_type",
        )
        if actual != "wsi_tissue_overview":
            raise GenerationConditionError(
                "wsi_tissue_overview.artifact_type must be wsi_tissue_overview"
            )
    return data


def _layout_condition(
    prior: dict[str, Any],
    layout_prior: dict[str, Any],
    tissue_overview: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    condition = {
        "source": "layout_mask_prior",
        "artifact_path": prior["artifacts"]["layout_mask_prior"]["path"],
        "sample_count": layout_prior.get("sample_count"),
        "class_names": list(class_names),
        "class_fractions_by_id": deepcopy(fractions),
        "non_background_fraction": layout_prior.get("non_background_fraction"),
        "adjacency_counts": deepcopy(layout_prior.get("adjacency_counts", {})),
    }
    if tissue_overview is not None:
        condition["wsi_tissue_overview"] = _wsi_tissue_overview_condition(
            prior,
            tissue_overview,
        )
    return condition


def _wsi_tissue_overview_condition(
    prior: dict[str, Any],
    tissue_overview: dict[str, Any],
) -> dict[str, Any]:
    records = _require_list(tissue_overview, "records", "wsi_tissue_overview.records")
    source = _require_dict(tissue_overview, "source", "wsi_tissue_overview.source")
    summarized_records = []
    for index, record_value in enumerate(records):
        record = _ensure_dict(record_value, f"wsi_tissue_overview.records[{index}]")
        tissue_proxy = _require_dict(
            record,
            "tissue_mask_proxy",
            f"wsi_tissue_overview.records[{index}].tissue_mask_proxy",
        )
        summarized_records.append(
            {
                "wsi_id": _require_non_empty_str(
                    record,
                    "wsi_id",
                    f"wsi_tissue_overview.records[{index}].wsi_id",
                ),
                "tissue_fraction": _require_number(
                    tissue_proxy,
                    "tissue_fraction",
                    f"wsi_tissue_overview.records[{index}].tissue_mask_proxy.tissue_fraction",
                ),
                "bounding_box_xywh": deepcopy(
                    _require_list(
                        tissue_proxy,
                        "bounding_box_xywh",
                        f"wsi_tissue_overview.records[{index}].tissue_mask_proxy.bounding_box_xywh",
                    )
                ),
                "connected_component_count": _require_int(
                    tissue_proxy,
                    "connected_component_count",
                    f"wsi_tissue_overview.records[{index}].tissue_mask_proxy.connected_component_count",
                ),
            }
        )
        manifest = record.get("manifest")
        if isinstance(manifest, dict):
            # Only stable manifest fields used by runtime QC stratification are
            # propagated. Missing or non-string optional fields are omitted so
            # they trigger an audited global fallback later instead of creating
            # ambiguous stratum keys.
            manifest_summary = {}
            for key in ("cancer_type", "tissue_type", "center_id", "split"):
                value = manifest.get(key)
                if isinstance(value, str) and value:
                    manifest_summary[key] = value
            if manifest_summary:
                summarized_records[-1]["manifest"] = manifest_summary
    return {
        "source": "wsi_tissue_overview",
        "artifact_path": prior["artifacts"]["wsi_tissue_overview"]["path"],
        "record_count": tissue_overview.get("record_count"),
        "source_backend": source.get("backend"),
        "thumbnail_max_size": deepcopy(source.get("thumbnail_max_size")),
        "records": summarized_records,
    }


def _load_sampled_layout_mask(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise GenerationConditionError(f"sampled_layout_mask file does not exist: {manifest_path}")
    if not manifest_path.is_file():
        raise GenerationConditionError(f"sampled_layout_mask path is not a file: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationConditionError(f"sampled_layout_mask is not valid JSON: {exc.msg}") from exc
    if not isinstance(manifest, dict):
        raise GenerationConditionError("sampled_layout_mask must be a JSON object")
    if manifest.get("schema_version") != PROJECT_VERSION:
        raise GenerationConditionError(f"sampled_layout_mask.schema_version must be {PROJECT_VERSION}")
    if manifest.get("artifact_type") != "sampled_layout_mask":
        raise GenerationConditionError("sampled_layout_mask.artifact_type must be sampled_layout_mask")
    class_names = _require_list(manifest, "class_names", "sampled_layout_mask.class_names")
    if tuple(class_names) != MASK_CLASSES:
        raise GenerationConditionError("sampled_layout_mask.class_names must match project mask classes")
    mask_path = _require_non_empty_str(manifest, "mask_path", "sampled_layout_mask.mask_path")
    mask_shape = _require_list(manifest, "mask_shape", "sampled_layout_mask.mask_shape")
    if len(mask_shape) != 2 or not all(isinstance(value, int) and value > 0 for value in mask_shape):
        raise GenerationConditionError("sampled_layout_mask.mask_shape must contain two positive integers")
    counts = _require_list(
        manifest,
        "class_pixel_counts_by_id",
        "sampled_layout_mask.class_pixel_counts_by_id",
    )
    fractions = _require_list(
        manifest,
        "class_fractions_by_id",
        "sampled_layout_mask.class_fractions_by_id",
    )
    if len(counts) != len(MASK_CLASSES) or len(fractions) != len(MASK_CLASSES):
        raise GenerationConditionError("sampled_layout_mask class statistics must contain six values")
    return {
        "artifact_path": str(manifest_path),
        "mask_path": mask_path,
        "sample_id": _require_non_empty_str(manifest, "sample_id", "sampled_layout_mask.sample_id"),
        "random_seed": _require_int(manifest, "random_seed", "sampled_layout_mask.random_seed"),
        "mask_shape": list(mask_shape),
        "class_names": list(class_names),
        "class_pixel_counts_by_id": deepcopy(counts),
        "class_fractions_by_id": deepcopy(fractions),
        "limitations": deepcopy(manifest.get("limitations", [])),
    }


def _mask_condition(
    layout: dict[str, Any],
    sampled_layout_mask: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if sampled_layout_mask is not None:
        return {
            "source": "sampled_layout_mask",
            "artifact_path": sampled_layout_mask["artifact_path"],
            "mask_path": sampled_layout_mask["mask_path"],
            "sample_id": sampled_layout_mask["sample_id"],
            "random_seed": sampled_layout_mask["random_seed"],
            "mask_shape": list(sampled_layout_mask["mask_shape"]),
            "class_names": list(sampled_layout_mask["class_names"]),
            "class_pixel_counts_by_id": deepcopy(sampled_layout_mask["class_pixel_counts_by_id"]),
            "class_fractions_by_id": deepcopy(sampled_layout_mask["class_fractions_by_id"]),
            "mask_role": "semantic_spatial_condition",
            "limitations": deepcopy(sampled_layout_mask["limitations"]),
        }
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


def _sampled_layout_mask_input(sampled_layout_mask: dict[str, Any] | None) -> dict[str, Any]:
    if sampled_layout_mask is None:
        return {}
    return {
        "sampled_layout_mask": {
            "path": sampled_layout_mask["artifact_path"],
            "kind": "json",
            "metadata": {
                "artifact_type": "sampled_layout_mask",
                "sample_id": sampled_layout_mask["sample_id"],
                "mask_path": sampled_layout_mask["mask_path"],
                "mask_shape": list(sampled_layout_mask["mask_shape"]),
            },
        }
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


def _ensure_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GenerationConditionError(f"{path} must be an object")
    return value


def _require_int(data: dict[str, Any], key: str, path: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise GenerationConditionError(f"{path} must be an integer")
    return value


def _require_number(data: dict[str, Any], key: str, path: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GenerationConditionError(f"{path} must be a number")
    return float(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
