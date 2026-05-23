import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller import VALID_JOB_STATUSES


class JobRunnerError(ValueError):
    """Raised when a local UI job cannot be created or executed safely."""


class JobRunner:
    def __init__(self, job_root: str | Path):
        self.job_root = Path(job_root)
        self.job_root.mkdir(parents=True, exist_ok=True)

    def create_job(
        self,
        job_id: str,
        command: list[str],
        cwd: str | Path | None = None,
    ) -> dict[str, Any]:
        _validate_job_id(job_id)
        _validate_command(command)
        job_dir = self._job_dir(job_id)
        if job_dir.exists():
            raise JobRunnerError(f"job already exists: {job_id}")
        job_dir.mkdir(parents=True)
        now = _now_iso()
        record = {
            "job_id": job_id,
            "status": "queued",
            "command": list(command),
            "cwd": str(cwd) if cwd is not None else None,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
            "return_code": None,
            "message": "",
            "stdout_path": str(job_dir / "stdout.txt"),
            "stderr_path": str(job_dir / "stderr.txt"),
            "record_path": str(job_dir / "job.json"),
        }
        self._write_record(record)
        return dict(record)

    def run_job(self, job_id: str) -> dict[str, Any]:
        record = self.load_job(job_id)
        if record["status"] != "queued":
            raise JobRunnerError(f"job {job_id} is not queued")
        started_at = _now_iso()
        record.update({"status": "running", "started_at": started_at, "updated_at": started_at})
        self._write_record(record)

        try:
            result = subprocess.run(
                record["command"],
                cwd=record["cwd"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            stdout = result.stdout
            stderr = result.stderr
            return_code = int(result.returncode)
            message = "command completed" if return_code == 0 else "command failed"
        except OSError as exc:
            # Process launch failures have no return code, but the UI still needs a
            # durable failed job record instead of a stale "running" state.
            stdout = ""
            stderr = f"{exc.__class__.__name__}: {exc}\n"
            return_code = None
            message = f"command launch failed: {exc}"
        Path(record["stdout_path"]).write_text(stdout, encoding="utf-8")
        Path(record["stderr_path"]).write_text(stderr, encoding="utf-8")
        finished_at = _now_iso()
        record.update(
            {
                "status": "completed" if return_code == 0 else "failed",
                "finished_at": finished_at,
                "updated_at": finished_at,
                "return_code": return_code,
                "message": message,
            }
        )
        self._write_record(record)
        return dict(record)

    def cancel_job(self, job_id: str, message: str = "job cancelled") -> dict[str, Any]:
        if not isinstance(message, str):
            raise JobRunnerError("cancel message must be a string")
        record = self.load_job(job_id)
        if record["status"] != "queued":
            raise JobRunnerError(f"job {job_id} is not queued")
        finished_at = _now_iso()
        Path(record["stdout_path"]).write_text("", encoding="utf-8")
        Path(record["stderr_path"]).write_text("", encoding="utf-8")
        record.update(
            {
                "status": "cancelled",
                "finished_at": finished_at,
                "updated_at": finished_at,
                "return_code": None,
                "message": message or "job cancelled",
            }
        )
        self._write_record(record)
        return dict(record)

    def load_job(self, job_id: str) -> dict[str, Any]:
        _validate_job_id(job_id)
        record_path = self._job_dir(job_id) / "job.json"
        if not record_path.exists():
            raise JobRunnerError(f"unknown job_id: {job_id}")
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise JobRunnerError(f"{record_path} is not valid JSON: {exc.msg}") from exc
        _validate_record(record)
        return record

    def list_jobs(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for job_dir in sorted(self.job_root.iterdir(), key=lambda path: path.name):
            if not job_dir.is_dir():
                continue
            record_path = job_dir / "job.json"
            if not record_path.exists():
                raise JobRunnerError(f"missing job record: {record_path}")
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise JobRunnerError(f"{record_path} is not valid JSON: {exc.msg}") from exc
            _validate_record(record)
            records.append(record)
        return records

    def _job_dir(self, job_id: str) -> Path:
        return self.job_root / job_id

    def _write_record(self, record: dict[str, Any]) -> None:
        _validate_record(record)
        Path(record["record_path"]).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _validate_record(record: dict[str, Any]) -> None:
    if not isinstance(record, dict):
        raise JobRunnerError("job record must be an object")
    _validate_job_id(record.get("job_id"))
    status = record.get("status")
    if status not in VALID_JOB_STATUSES:
        raise JobRunnerError(f"invalid job status: {status}")
    _validate_command(record.get("command"))
    record_path = record.get("record_path")
    if not isinstance(record_path, str) or record_path == "":
        raise JobRunnerError("record_path must be a non-empty string")


def _validate_job_id(job_id: Any) -> None:
    if not isinstance(job_id, str) or job_id == "":
        raise JobRunnerError("job_id must be a non-empty string")
    if "/" in job_id or "\\" in job_id or job_id in {".", ".."}:
        raise JobRunnerError("job_id must not contain path separators")


def _validate_command(command: Any) -> None:
    if not isinstance(command, list) or not command:
        raise JobRunnerError("command must be a non-empty list")
    for index, item in enumerate(command):
        if not isinstance(item, str) or item == "":
            raise JobRunnerError(f"command[{index}] must be a non-empty string")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
