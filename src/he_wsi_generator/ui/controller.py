import json
from datetime import datetime, timezone
from pathlib import Path

from ..schemas import validate_qc_report


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


def collect_output_summary(metadata_path: str | Path, qc_path: str | Path) -> dict:
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    qc = validate_qc_report(json.loads(Path(qc_path).read_text(encoding="utf-8")))
    output = metadata.get("output", {})
    return {
        "generated_id": metadata.get("generated_id", qc["generated_id"]),
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
