from datetime import datetime, timezone

from ..constants import PROJECT_VERSION
from ..schemas import validate_input_manifest
from .readers import FixtureImageSlideReader, OpenSlideReader, SlideReader, WSIReadError


def build_reader(backend: str) -> SlideReader:
    if backend == "openslide":
        return OpenSlideReader()
    if backend == "fixture-image":
        return FixtureImageSlideReader()
    raise ValueError("backend must be openslide or fixture-image")


def audit_manifest(manifest: dict, reader: SlideReader | None = None) -> dict:
    validated = validate_input_manifest(manifest)
    selected_reader = reader or OpenSlideReader()
    records = []
    for record in validated["records"]:
        wsi_id = record["wsi_id"]
        try:
            metadata = selected_reader.read_metadata(record["wsi_path"], wsi_id=wsi_id)
        except WSIReadError as exc:
            records.append(
                {
                    "wsi_id": wsi_id,
                    "wsi_path": record["wsi_path"],
                    "status": "error",
                    "backend": selected_reader.backend,
                    "error": str(exc),
                }
            )
            continue

        audited = metadata.to_record()
        audited["status"] = "ok"
        audited["split"] = record["split"]
        audited["cancer_type"] = record["cancer_type"]
        audited["annotation_count"] = len(record.get("annotations", []))
        records.append(audited)

    return {
        "schema_version": PROJECT_VERSION,
        "dataset_id": validated["dataset_id"],
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "backend": selected_reader.backend,
        "records": records,
    }
