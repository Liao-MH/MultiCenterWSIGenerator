import json
from pathlib import Path

from ..constants import PROJECT_VERSION


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
    target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return target


def load_ui_config(path: str | Path) -> dict:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    _validate_ui_config(data)
    return data


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
