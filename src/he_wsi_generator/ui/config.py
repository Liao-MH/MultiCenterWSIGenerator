import json
from pathlib import Path

from ..constants import PROJECT_VERSION
from ..schemas import ValidationError, load_document


def create_default_ui_config() -> dict:
    return {
        "schema_version": PROJECT_VERSION,
        "layout": "single_page_console",
        "sections": {
            "data_input": {
                "fields": [
                    "manifest_path",
                    "wsi_path",
                    "annotation_path",
                    "output_dir",
                ],
                "blocking_errors": ["missing_path", "unreadable_wsi", "missing_mpp"],
            },
            "label_mapping": {
                "fields": ["source_annotation_id", "raw_labels", "class_mapping", "confidence"],
                "classes": [
                    "background",
                    "tissue",
                    "target_pathology",
                    "supporting_tissue",
                    "necrosis_debris",
                    "artifact",
                ],
            },
            "prior_model": {
                "fields": [
                    "prior_manifest_path",
                    "checkpoint_manifest_path",
                    "train_or_load",
                ],
                "checkpoint_status_required": "trained_for_generation",
            },
            "generation_parameters": {
                "fields": [
                    "random_seed",
                    "structure_anchor",
                    "anchor_preset",
                    "source_wsi_id",
                    "style_seed",
                    "sample_steps",
                    "overlap_px_40x",
                ],
                "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            },
            "task_status": {
                "statuses": ["queued", "running", "completed", "failed", "cancelled"],
                "fields": ["job_id", "status", "message", "updated_at"],
            },
            "qc_output": {
                "fields": [
                    "metadata_path",
                    "qc_json_path",
                    "wsi_path",
                    "mask_path",
                    "batch_index_path",
                    "overall_status",
                ],
                "status_levels": ["pass", "warning", "fail"],
            },
        },
    }


def save_ui_config(config: dict, path: str | Path) -> Path:
    _validate_ui_config(config)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        payload = _dump_yaml(config)
    else:
        payload = json.dumps(config, indent=2)
    try:
        target.write_text(payload.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        raise ValueError(str(exc)) from exc
    return target


def load_ui_config(path: str | Path) -> dict:
    source = Path(path)
    if source.suffix.lower() in {".yaml", ".yml"}:
        try:
            data = load_document(source)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
    else:
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(str(exc)) from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source} is not valid JSON: {exc.msg}") from exc
    _validate_ui_config(data)
    return data


def _dump_yaml(config: dict) -> str:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(
            "YAML UI configs require PyYAML; install the optional yaml dependency or use JSON"
        ) from exc
    return yaml.safe_dump(config, sort_keys=False)


def _validate_ui_config(config: dict) -> None:
    if not isinstance(config, dict):
        raise ValueError("UI config must be an object")
    if config.get("schema_version") != PROJECT_VERSION:
        raise ValueError(f"UI config schema_version must be {PROJECT_VERSION}")
    sections = config.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("UI config sections must be an object")
    required = [
        "data_input",
        "label_mapping",
        "prior_model",
        "generation_parameters",
        "task_status",
        "qc_output",
    ]
    for section in required:
        if section not in sections:
            raise ValueError(f"UI config missing section {section}")
