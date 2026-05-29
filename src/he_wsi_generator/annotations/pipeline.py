import json
from pathlib import Path
from typing import Any

from .masks import MaskMappingError, build_six_class_mask, load_annotation_source
from ..outputs.masks import write_mask_metadata
from ..schemas import load_document, validate_input_manifest, validate_label_mapping


class AnnotationPipelineError(ValueError):
    """Raised when manifest annotations cannot produce a unified six-class mask."""


def build_six_class_mask_artifact(
    *,
    manifest_path: str | Path,
    audit_path: str | Path,
    label_mapping_paths: list[str | Path],
    output_dir: str | Path,
) -> dict[str, Any]:
    manifest = validate_input_manifest(load_document(manifest_path))
    audit = _load_audit_records(load_document(audit_path))
    mappings = {
        (mapping["wsi_id"], mapping["source_annotation_id"]): mapping
        for mapping in (validate_label_mapping(load_document(path)) for path in label_mapping_paths)
    }

    records = []
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    for manifest_record in manifest["records"]:
        annotations = manifest_record.get("annotations", [])
        if not annotations:
            continue
        wsi_id = manifest_record["wsi_id"]
        audit_record = audit.get(wsi_id)
        if audit_record is None or audit_record.get("status") != "ok":
            raise AnnotationPipelineError(f"missing ok audit record for {wsi_id}")
        annotation_sources = []
        for annotation in annotations:
            mapping_key = (wsi_id, annotation["annotation_id"])
            if mapping_key not in mappings:
                raise AnnotationPipelineError(
                    f"missing label mapping for {wsi_id}/{annotation['annotation_id']}"
                )
            loaded = load_annotation_source(annotation)
            loaded["label_mapping"] = mappings[mapping_key]
            loaded["priority"] = _annotation_priority(annotation["annotation_type"])
            annotation_sources.append(loaded)

        sample_dir = root / wsi_id
        sample_dir.mkdir(parents=True, exist_ok=True)
        mask_path = sample_dir / "mask.npy"
        try:
            merged = build_six_class_mask(
                wsi_id=wsi_id,
                wsi_level0_size=tuple(int(value) for value in audit_record["dimensions"]),
                annotation_sources=annotation_sources,
                output_path=mask_path,
            )
        except MaskMappingError as exc:
            raise AnnotationPipelineError(str(exc)) from exc
        mask_report = write_mask_metadata(
            mask_path=mask_path,
            output_dir=sample_dir,
            stem="mask",
            shape=merged["mask_shape"],
            dtype="uint8",
        )
        manifest_payload = {
            "schema_version": manifest["schema_version"],
            "wsi_id": wsi_id,
            "mask_path": mask_report["path"],
            "mask_metadata_path": mask_report["metadata_path"],
            "mask_shape": merged["mask_shape"],
            "source_priority_order": merged["source_priority_order"],
            "compact_provenance_summary": merged["compact_provenance_summary"],
            "annotation_ids": [annotation["annotation_id"] for annotation in annotations],
            "temporary_intermediate": True,
            "cleanup_policy": "delete_after_full_workflow_success",
        }
        artifact_path = sample_dir / "six_class_mask.json"
        artifact_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
        records.append(
            {
                "wsi_id": wsi_id,
                "artifact_path": str(artifact_path),
                **manifest_payload,
            }
        )

    if not records:
        raise AnnotationPipelineError("manifest contains no annotations to build six-class masks")
    result = {
        "schema_version": manifest["schema_version"],
        "record_count": len(records),
        "records": records,
    }
    summary_path = root / "six_class_mask_summary.json"
    summary_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    return result


def cleanup_temporary_six_class_masks(
    summary: dict[str, Any] | str | Path,
    *,
    required_output_paths: list[str | Path],
) -> dict[str, Any]:
    payload = load_document(summary) if isinstance(summary, (str, Path)) else summary
    if not isinstance(payload, dict):
        raise AnnotationPipelineError("six-class mask summary must be a JSON object")
    if not isinstance(required_output_paths, list) or not required_output_paths:
        raise AnnotationPipelineError("required_output_paths must contain at least one path")
    missing_outputs = [str(path) for path in required_output_paths if not Path(path).exists()]
    if missing_outputs:
        raise AnnotationPipelineError(f"required output does not exist: {missing_outputs[0]}")

    deleted_paths = []
    skipped_paths = []
    for record in payload.get("records", []):
        if not isinstance(record, dict) or not record.get("temporary_intermediate", False):
            continue
        mask_path = Path(record.get("mask_path", ""))
        if not mask_path.exists():
            skipped_paths.append(str(mask_path))
            continue
        try:
            mask_path.unlink()
        except OSError as exc:
            raise AnnotationPipelineError(f"failed to delete temporary mask {mask_path}: {exc}") from exc
        deleted_paths.append(str(mask_path))
    return {
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "skipped_missing_paths": skipped_paths,
        "required_output_paths": [str(path) for path in required_output_paths],
    }


def _load_audit_records(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(audit, dict):
        raise AnnotationPipelineError("audit must be a JSON object")
    records = audit.get("records")
    if not isinstance(records, list):
        raise AnnotationPipelineError("audit.records must be a list")
    by_wsi = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise AnnotationPipelineError(f"audit.records[{index}] must be an object")
        wsi_id = record.get("wsi_id")
        if not isinstance(wsi_id, str) or wsi_id == "":
            raise AnnotationPipelineError(f"audit.records[{index}].wsi_id must be a non-empty string")
        by_wsi[wsi_id] = record
    return by_wsi


def _annotation_priority(annotation_type: str) -> str:
    if annotation_type == "roi_json":
        return "roi_json"
    if annotation_type == "cluster_pseudo_mask":
        return "cluster_pseudo_mask"
    return "manual_mask"
