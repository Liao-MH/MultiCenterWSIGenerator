import json
from datetime import datetime, timezone
from pathlib import Path

from ..qc.review import load_qc_review
from ..schemas import validate_metadata, validate_qc_report


VALID_JOB_STATUSES = ("queued", "running", "completed", "failed", "cancelled")


class JobStateError(ValueError):
    """Raised when UI job state cannot be represented safely."""


class JobStateStore:
    def __init__(self):
        self._jobs: dict[str, dict] = {}

    def set_status(self, job_id: str, status: str, message: str = "") -> dict:
        if not isinstance(job_id, str) or not job_id:
            raise JobStateError("job_id must be a non-empty string")
        if status not in VALID_JOB_STATUSES:
            raise JobStateError(f"invalid job status: {status}")
        record = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        self._jobs[job_id] = record
        return record

    def get_status(self, job_id: str) -> dict:
        if job_id not in self._jobs:
            raise JobStateError(f"unknown job_id: {job_id}")
        return dict(self._jobs[job_id])

    def list_jobs(self) -> list[dict]:
        return [dict(value) for value in self._jobs.values()]


def collect_output_summary(
    metadata_path: str | Path,
    qc_path: str | Path,
    qc_review_path: str | Path | None = None,
) -> dict:
    metadata = validate_metadata(json.loads(Path(metadata_path).read_text(encoding="utf-8")))
    qc = validate_qc_report(json.loads(Path(qc_path).read_text(encoding="utf-8")))
    if metadata["generated_id"] != qc["generated_id"]:
        raise ValueError("metadata.generated_id must match qc.generated_id")
    output = metadata.get("output", {})
    summary = {
        "generated_id": metadata["generated_id"],
        "qc_status": qc["overall_status"],
        "outputs": {
            "wsi_path": output.get("wsi_path"),
            "mask_path": output.get("mask_path"),
            "qc_json_path": output.get("qc_json_path", str(qc_path)),
            "metadata_path": str(metadata_path),
        },
        "level_status": {
            "wsi": qc["levels"]["wsi"]["status"],
            "tile": qc["levels"]["tile"]["status"],
            "mask_region": qc["levels"]["mask_region"]["status"],
        },
    }
    if qc_review_path is not None:
        review = load_qc_review(qc_review_path)
        if review["generated_id"] != summary["generated_id"]:
            raise ValueError("qc_review.generated_id must match metadata.generated_id and qc.generated_id")
        summary["review"] = {
            "review_required": review["review_required"],
            "decision": review["decision"],
            "reviewer": review.get("reviewer"),
            "review_item_count": len(review["review_items"]),
        }
    return summary
