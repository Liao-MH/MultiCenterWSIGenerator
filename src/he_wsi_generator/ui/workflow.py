import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..constants import DEFAULT_GENERATION_CONFIG, MASK_CLASSES
from ..schemas import ValidationError, validate_generation_config
from .jobs import JobRunner, JobRunnerError


class UIWorkflowError(ValueError):
    """Raised when UI form state cannot be converted into a runnable local job."""


_MISSING = object()
_BACKENDS = {"smoke-cascade", "torch-diffusion-smoke"}
_FIELD_LABELS = {
    "checkpoint_manifest_path": "checkpoint manifest",
    "condition_packet_path": "condition packet",
    "generation_config_path": "generation config",
    "generated_id": "generated id",
    "output_root": "output root",
    "prior_manifest_path": "prior manifest",
    "training_index_path": "training index",
}


def build_generation_config_from_form(form_state: dict) -> dict:
    _require_form_state(form_state)
    _validate_label_mapping_rows(form_state.get("label_mapping_rows"))

    config = deepcopy(DEFAULT_GENERATION_CONFIG)
    _set_int_if_present(form_state, config, "random_seed")
    _set_str_if_present(form_state, config, "anchor_preset")
    _set_float_if_present(form_state, config, "structure_anchor")
    _set_style_seed_if_present(form_state, config)
    _set_source_wsi_if_present(form_state, config)
    _set_int_if_present(form_state, config, "sample_steps")
    _set_int_if_present(form_state, config, "overlap_px_40x")
    _set_bool_if_present(form_state, config, "non_copy_patch_nearest_neighbor_search")

    try:
        return validate_generation_config(config)
    except ValidationError as exc:
        raise UIWorkflowError(str(exc)) from exc


def build_run_generation_command(
    form_state: dict,
    generation_config_path: str | Path,
) -> list[str]:
    _require_form_state(form_state)
    _validate_label_mapping_rows(form_state.get("label_mapping_rows"))

    config_path = _path_argument(generation_config_path, "generation_config_path")
    backend = _required_choice_field(form_state, "backend", _BACKENDS)
    prior_manifest = _required_path_field(
        form_state,
        "prior_manifest_path",
        aliases=("prior_manifest",),
    )
    checkpoint_manifest = _required_path_field(
        form_state,
        "checkpoint_manifest_path",
        aliases=("checkpoint_manifest",),
    )
    output_root = _required_path_field(form_state, "output_root", aliases=("output_dir",))
    generated_id = _required_text_field(form_state, "generated_id")

    command = [
        sys.executable,
        "-m",
        "he_wsi_generator.cli",
        "run-generation",
        config_path,
        "--backend",
        backend,
        "--prior-manifest",
        prior_manifest,
        "--checkpoint-manifest",
        checkpoint_manifest,
    ]
    if backend == "torch-diffusion-smoke":
        training_index = _required_path_field(
            form_state,
            "training_index_path",
            aliases=("training_index",),
        )
        command.extend(["--training-index", training_index])
    command.extend(
        [
            "--output-root",
            output_root,
            "--generated-id",
            generated_id,
        ]
    )

    condition_packet = _optional_path_field(
        form_state,
        "condition_packet_path",
        aliases=("condition_packet",),
    )
    if condition_packet is not None:
        command.extend(["--condition-packet", condition_packet])
    return command


def create_run_generation_job(
    form_state: dict,
    job_root: str | Path,
    generation_config_path: str | Path,
    cwd: str | Path | None = None,
) -> dict:
    build_generation_config_from_form(form_state)
    command = build_run_generation_command(form_state, generation_config_path)
    job_id = _optional_text_field(form_state, "job_id") or _required_text_field(
        form_state,
        "generated_id",
    )
    try:
        return JobRunner(job_root).create_job(job_id=job_id, command=command, cwd=cwd)
    except JobRunnerError as exc:
        raise UIWorkflowError(str(exc)) from exc


def _require_form_state(form_state: Any) -> None:
    if not isinstance(form_state, dict):
        raise UIWorkflowError("form_state must be an object")


def _set_int_if_present(form_state: dict, config: dict, key: str) -> None:
    value = _get_field(form_state, key)
    if value is not _MISSING:
        config[key] = _coerce_int(value, key)


def _set_float_if_present(form_state: dict, config: dict, key: str) -> None:
    value = _get_field(form_state, key)
    if value is not _MISSING:
        config[key] = _coerce_float(value, key)


def _set_bool_if_present(form_state: dict, config: dict, key: str) -> None:
    value = _get_field(form_state, key)
    if value is not _MISSING:
        if not isinstance(value, bool):
            raise UIWorkflowError(f"{key} must be a boolean")
        config[key] = value


def _set_str_if_present(form_state: dict, config: dict, key: str) -> None:
    value = _get_field(form_state, key)
    if value is not _MISSING:
        config[key] = _required_text_value(value, key)


def _set_style_seed_if_present(form_state: dict, config: dict) -> None:
    value = _get_field(form_state, "style_seed")
    if value is _MISSING:
        return
    if value == "auto":
        config["style_seed"] = "auto"
        return
    if isinstance(value, str) and value.strip() == "auto":
        config["style_seed"] = "auto"
        return
    config["style_seed"] = _coerce_int(value, "style_seed")


def _set_source_wsi_if_present(form_state: dict, config: dict) -> None:
    value = _get_field(form_state, "source_wsi_id")
    if value is _MISSING:
        return
    if value is None:
        config["source_wsi_id"] = None
        return
    if not isinstance(value, str):
        raise UIWorkflowError("source_wsi_id must be a string or null")
    stripped = value.strip()
    config["source_wsi_id"] = stripped if stripped else None


def _coerce_int(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise UIWorkflowError(f"{key} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped, 10)
            except ValueError as exc:
                raise UIWorkflowError(f"{key} must be an integer") from exc
    raise UIWorkflowError(f"{key} must be an integer")


def _coerce_float(value: Any, key: str) -> float:
    if isinstance(value, bool):
        raise UIWorkflowError(f"{key} must be a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return float(stripped)
            except ValueError as exc:
                raise UIWorkflowError(f"{key} must be a number") from exc
    raise UIWorkflowError(f"{key} must be a number")


def _validate_label_mapping_rows(rows: Any) -> None:
    if rows is None:
        return
    if not isinstance(rows, list):
        raise UIWorkflowError("label_mapping_rows must be a list")

    seen: set[str] = set()
    valid_classes = set(MASK_CLASSES)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise UIWorkflowError(f"label_mapping_rows[{index}] must be an object")
        raw_label = _normalize_raw_label(row.get("raw_label"), f"label_mapping_rows[{index}].raw_label")
        if raw_label in seen:
            raise UIWorkflowError(f"duplicate raw label: {raw_label}")
        seen.add(raw_label)

        class_name = row.get("class_name")
        if class_name is not None:
            class_name = _required_text_value(
                class_name,
                f"label_mapping_rows[{index}].class_name",
            )
            if class_name not in valid_classes:
                raise UIWorkflowError(
                    f"label_mapping_rows[{index}].class_name has invalid mask class"
                )


def _required_choice_field(form_state: dict, key: str, choices: set[str]) -> str:
    value = _required_text_field(form_state, key)
    if value not in choices:
        raise UIWorkflowError(f"{key} must be one of: {', '.join(sorted(choices))}")
    return value


def _required_path_field(form_state: dict, key: str, aliases: tuple[str, ...] = ()) -> str:
    value = _get_field(form_state, key, aliases)
    if value is _MISSING or value is None:
        raise UIWorkflowError(f"{_field_label(key)} is required")
    return _path_argument(value, key)


def _optional_path_field(form_state: dict, key: str, aliases: tuple[str, ...] = ()) -> str | None:
    value = _get_field(form_state, key, aliases)
    if value is _MISSING or value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return _path_argument(value, key)


def _path_argument(value: Any, key: str) -> str:
    if isinstance(value, os.PathLike):
        text = os.fspath(value)
    elif isinstance(value, str):
        text = value
    else:
        raise UIWorkflowError(f"{_field_label(key)} must be a path string")
    if text.strip() == "":
        raise UIWorkflowError(f"{_field_label(key)} is required")
    return text


def _normalize_raw_label(value: Any, key: str) -> str:
    if isinstance(value, bool):
        raise UIWorkflowError(f"{key} must be a non-negative integer label")
    if isinstance(value, int):
        if value < 0:
            raise UIWorkflowError(f"{key} must be a non-negative integer label")
        return str(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdecimal():
            return str(int(stripped, 10))
    raise UIWorkflowError(f"{key} must be a non-negative integer label")


def _required_text_field(form_state: dict, key: str) -> str:
    value = _get_field(form_state, key)
    if value is _MISSING:
        raise UIWorkflowError(f"{_field_label(key)} is required")
    return _required_text_value(value, key)


def _optional_text_field(form_state: dict, key: str) -> str | None:
    value = _get_field(form_state, key)
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str):
        raise UIWorkflowError(f"{key} must be a string")
    stripped = value.strip()
    return stripped if stripped else None


def _required_text_value(value: Any, key: str) -> str:
    if not isinstance(value, str):
        raise UIWorkflowError(f"{_field_label(key)} must be a string")
    stripped = value.strip()
    if not stripped:
        raise UIWorkflowError(f"{_field_label(key)} is required")
    return stripped


def _get_field(form_state: dict, key: str, aliases: tuple[str, ...] = ()) -> Any:
    for candidate in (key, *aliases):
        if candidate in form_state:
            return form_state[candidate]
    return _MISSING


def _field_label(key: str) -> str:
    return _FIELD_LABELS.get(key, key)
