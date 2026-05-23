import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import PROJECT_VERSION
from ..schemas import ValidationError, validate_qc_report


FINAL_REVIEW_DECISIONS = ("accepted", "rejected", "needs_rerun")
REVIEW_DECISIONS = ("pending", *FINAL_REVIEW_DECISIONS)


class QCReviewError(ValueError):
    """Raised when a QC review artifact cannot be built or updated safely."""


def build_qc_review(
    metadata_path: str | Path,
    qc_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    metadata_source = Path(metadata_path)
    qc_source = Path(qc_path)
    try:
        metadata = _load_json_object(metadata_source, "metadata")
        qc = validate_qc_report(_load_json_object(qc_source, "qc"))
    except ValidationError as exc:
        raise QCReviewError(str(exc)) from exc

    metadata_generated_id = _require_non_empty_str(metadata, "generated_id", "metadata.generated_id")
    if metadata_generated_id != qc["generated_id"]:
        raise QCReviewError("metadata.generated_id must match qc.generated_id")

    review = {
        "schema_version": PROJECT_VERSION,
        "artifact_type": "qc_review",
        "generated_id": qc["generated_id"],
        "created_at": _now_iso(),
        "inputs": {
            "metadata_path": str(metadata_source),
            "metadata_sha256": _sha256_file(metadata_source),
            "qc_path": str(qc_source),
            "qc_sha256": _sha256_file(qc_source),
        },
        "qc_status": {
            "overall_status": qc["overall_status"],
            "levels": {
                "wsi": qc["levels"]["wsi"]["status"],
                "tile": qc["levels"]["tile"]["status"],
                "mask_region": qc["levels"]["mask_region"]["status"],
            },
        },
        "review_required": qc["overall_status"] in {"warning", "fail"},
        "decision": "pending",
        "reviewer": None,
        "note": "",
        "reviewed_at": None,
        "review_items": _review_items(qc),
    }
    validated = validate_qc_review(review)
    if output_path is not None:
        _write_json(validated, output_path)
    return validated


def load_qc_review(path: str | Path) -> dict[str, Any]:
    return validate_qc_review(_load_json_object(Path(path), "qc_review"))


def apply_qc_review_decision(
    review_path: str | Path,
    decision: str,
    reviewer: str,
    note: str = "",
) -> dict[str, Any]:
    if decision not in FINAL_REVIEW_DECISIONS:
        raise QCReviewError("decision must be accepted, rejected, or needs_rerun")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise QCReviewError("reviewer must be a non-empty string")
    if not isinstance(note, str):
        raise QCReviewError("note must be a string")

    source = Path(review_path)
    review = load_qc_review(source)
    if review["decision"] != "pending":
        raise QCReviewError("only pending qc_review artifacts can be updated")

    review["decision"] = decision
    review["reviewer"] = reviewer.strip()
    review["note"] = note
    review["reviewed_at"] = _now_iso()
    validated = validate_qc_review(review)
    _write_json(validated, source)
    return validated


def validate_qc_review(data: dict[str, Any]) -> dict[str, Any]:
    review = _ensure_mapping(data, "qc_review")
    _require_equal(review, "schema_version", PROJECT_VERSION, "schema_version")
    _require_equal(review, "artifact_type", "qc_review", "artifact_type")
    _require_non_empty_str(review, "generated_id", "generated_id")
    _require_non_empty_str(review, "created_at", "created_at")
    inputs = _ensure_mapping(_require(review, "inputs", "inputs"), "inputs")
    _require_non_empty_str(inputs, "metadata_path", "inputs.metadata_path")
    _require_sha256(inputs, "metadata_sha256", "inputs.metadata_sha256")
    _require_non_empty_str(inputs, "qc_path", "inputs.qc_path")
    _require_sha256(inputs, "qc_sha256", "inputs.qc_sha256")
    qc_status = _ensure_mapping(_require(review, "qc_status", "qc_status"), "qc_status")
    _require_status(qc_status, "overall_status", "qc_status.overall_status")
    levels = _ensure_mapping(_require(qc_status, "levels", "qc_status.levels"), "qc_status.levels")
    for level in ("wsi", "tile", "mask_region"):
        _require_status(levels, level, f"qc_status.levels.{level}")
    review_required = _require(review, "review_required", "review_required")
    if not isinstance(review_required, bool):
        raise QCReviewError("review_required must be a boolean")
    expected_review_required = qc_status["overall_status"] in {"warning", "fail"}
    if review_required != expected_review_required:
        raise QCReviewError("review_required must match qc_status.overall_status")
    decision = _require_non_empty_str(review, "decision", "decision")
    if decision not in REVIEW_DECISIONS:
        raise QCReviewError("decision must be pending, accepted, rejected, or needs_rerun")
    reviewer = review.get("reviewer")
    if reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip()):
        raise QCReviewError("reviewer must be null or a non-empty string")
    note = review.get("note", "")
    if not isinstance(note, str):
        raise QCReviewError("note must be a string")
    reviewed_at = review.get("reviewed_at")
    if reviewed_at is not None and (not isinstance(reviewed_at, str) or not reviewed_at.strip()):
        raise QCReviewError("reviewed_at must be null or a non-empty string")
    items = _require(review, "review_items", "review_items")
    if not isinstance(items, list):
        raise QCReviewError("review_items must be a list")
    for index, value in enumerate(items):
        item = _ensure_mapping(value, f"review_items[{index}]")
        level = _require_non_empty_str(item, "level", f"review_items[{index}].level")
        if level not in {"wsi", "tile", "mask_region"}:
            raise QCReviewError(f"review_items[{index}].level must be wsi, tile, or mask_region")
        _require_non_empty_str(item, "name", f"review_items[{index}].name")
        status = _require_non_empty_str(item, "status", f"review_items[{index}].status")
        if status not in {"warning", "fail"}:
            raise QCReviewError(f"review_items[{index}].status must be warning or fail")
    return json.loads(json.dumps(review))


def _review_items(qc: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for level in ("wsi", "tile", "mask_region"):
        for index, metric in enumerate(qc["levels"][level]["metrics"]):
            if not isinstance(metric, dict):
                raise QCReviewError(f"levels.{level}.metrics[{index}] must be an object")
            status = metric.get("status")
            if status not in {"warning", "fail"}:
                continue
            name = metric.get("name")
            if not isinstance(name, str) or not name:
                raise QCReviewError(f"levels.{level}.metrics[{index}].name must be a non-empty string")
            item = {"level": level, "name": name, "status": status}
            for key in ("value", "reference", "message", "reason"):
                if key in metric:
                    item[key] = metric[key]
            items.append(item)
    return items


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise QCReviewError(f"{label} path does not exist: {path}")
    if not path.is_file():
        raise QCReviewError(f"{label} path is not a file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QCReviewError(f"{label} is not valid JSON: {exc.msg}") from exc
    return _ensure_mapping(data, label)


def _write_json(data: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QCReviewError(f"{path} must be an object")
    return value


def _require(data: dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise QCReviewError(f"{path} is required")
    return data[key]


def _require_non_empty_str(data: dict[str, Any], key: str, path: str) -> str:
    value = _require(data, key, path)
    if not isinstance(value, str) or not value.strip():
        raise QCReviewError(f"{path} must be a non-empty string")
    return value


def _require_equal(data: dict[str, Any], key: str, expected: str, path: str) -> None:
    value = _require_non_empty_str(data, key, path)
    if value != expected:
        raise QCReviewError(f"{path} must be {expected}")


def _require_status(data: dict[str, Any], key: str, path: str) -> str:
    value = _require_non_empty_str(data, key, path)
    if value not in {"pass", "warning", "fail"}:
        raise QCReviewError(f"{path} must be pass, warning, or fail")
    return value


def _require_sha256(data: dict[str, Any], key: str, path: str) -> str:
    value = _require_non_empty_str(data, key, path)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise QCReviewError(f"{path} must be a lowercase sha256 hex digest")
    return value
