import json
from pathlib import Path
from typing import Any

from ..qc.engine import write_qc_report
from ..schemas import validate_metadata, validate_qc_report


def write_metadata(metadata: dict[str, Any], path: str | Path) -> Path:
    validated = validate_metadata(metadata)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    return target


def append_batch_index(batch_path: str | Path, record: dict[str, Any]) -> Path:
    required = {
        "generated_id",
        "metadata_path",
        "qc_json_path",
        "wsi_path",
        "mask_path",
        "status",
    }
    missing = sorted(required.difference(record))
    if missing:
        raise ValueError(f"batch record missing required fields: {', '.join(missing)}")
    if record["status"] not in {"pass", "warning", "fail"}:
        raise ValueError("batch record status must be pass, warning, or fail")
    target = Path(batch_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return target


def archive_sample(output_root: str | Path, metadata: dict[str, Any], qc_report: dict[str, Any]) -> dict:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    validated_qc = validate_qc_report(qc_report)
    metadata = dict(metadata)
    metadata.setdefault("qc", {})
    metadata["qc"]["overall_status"] = validated_qc["overall_status"]
    metadata["qc"]["summary"] = {
        "wsi_status": validated_qc["levels"]["wsi"]["status"],
        "tile_status": validated_qc["levels"]["tile"]["status"],
        "mask_region_status": validated_qc["levels"]["mask_region"]["status"],
    }
    metadata["qc"]["non_copy_report"] = validated_qc["non_copy_report"]
    generated_id = metadata["generated_id"]
    qc_path = root / "qc.json"
    metadata["output"]["qc_json_path"] = str(qc_path)
    metadata_path = root / "metadata.json"
    batch_path = root / "batch.jsonl"
    write_qc_report(validated_qc, qc_path)
    write_metadata(metadata, metadata_path)
    append_batch_index(
        batch_path,
        {
            "generated_id": generated_id,
            "metadata_path": str(metadata_path),
            "qc_json_path": str(qc_path),
            "wsi_path": metadata["output"]["wsi_path"],
            "mask_path": metadata["output"]["mask_path"],
            "status": validated_qc["overall_status"],
        },
    )
    return {
        "metadata_path": str(metadata_path),
        "qc_json_path": str(qc_path),
        "batch_index_path": str(batch_path),
    }
