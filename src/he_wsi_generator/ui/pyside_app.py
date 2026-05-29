import json
import sys
from pathlib import Path
from typing import Any

from ..constants import ANCHOR_PRESETS, DEFAULT_GENERATION_CONFIG, MASK_CLASSES
from .workflow import (
    UIWorkflowError,
    build_generation_config_from_form,
    collect_generation_job_output_summary,
    create_run_generation_job,
    load_generation_job_status,
    run_queued_generation_job,
)


class UIUnavailableError(RuntimeError):
    """Raised when the optional PySide6 UI dependency is unavailable."""


def ensure_pyside_available():
    try:
        import PySide6
    except ImportError as exc:
        raise UIUnavailableError(
            "PySide6 is required for launch-ui; install with python -m pip install -e '.[ui]'"
        ) from exc
    return PySide6


def create_main_window(config: dict | None = None):
    ensure_pyside_available()
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFormLayout,
        QFrame,
        QGroupBox,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QVBoxLayout,
        QWidget,
    )

    class GenerationConfigWindow(QMainWindow):
        def __init__(self, initial_config: dict | None = None):
            super().__init__()
            self._initial_config = initial_config if isinstance(initial_config, dict) else {}
            self._label_inputs: dict[str, Any] = {}
            self.setWindowTitle("MultiCenterWSIGenerator")
            self._build_form()

        def _build_form(self) -> None:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            central = QWidget()
            layout = QVBoxLayout(central)

            config_group = QGroupBox("Generation Config")
            config_layout = QFormLayout(config_group)
            self.generation_config_path_input = _line_edit("generation_config_path_input")
            config_layout.addRow("Save path", self.generation_config_path_input)
            layout.addWidget(config_group)

            run_group = QGroupBox("Run Inputs")
            run_layout = QFormLayout(run_group)
            self.prior_manifest_input = _line_edit("prior_manifest_input")
            self.checkpoint_manifest_input = _line_edit("checkpoint_manifest_input")
            self.output_root_input = _line_edit("output_root_input")
            self.generated_id_input = _line_edit("generated_id_input")
            self.source_wsi_id_input = _line_edit("source_wsi_id_input")
            self.style_seed_input = _line_edit("style_seed_input")
            self.backend_select = QComboBox()
            self.backend_select.setObjectName("backend_select")
            self.backend_select.addItems(
                ["smoke-cascade", "torch-diffusion-smoke", "production-tile-stream"]
            )
            self.condition_packet_input = _line_edit("condition_packet_input")
            self.training_index_input = _line_edit("training_index_input")
            run_layout.addRow("Prior manifest", self.prior_manifest_input)
            run_layout.addRow("Checkpoint manifest", self.checkpoint_manifest_input)
            run_layout.addRow("Output root", self.output_root_input)
            run_layout.addRow("Generated ID", self.generated_id_input)
            run_layout.addRow("Source WSI ID", self.source_wsi_id_input)
            run_layout.addRow("Style seed", self.style_seed_input)
            run_layout.addRow("Backend", self.backend_select)
            run_layout.addRow("Condition packet", self.condition_packet_input)
            run_layout.addRow("Training index", self.training_index_input)
            layout.addWidget(run_group)

            parameters_group = QGroupBox("Generation Parameters")
            parameters_layout = QFormLayout(parameters_group)
            self.anchor_preset_select = QComboBox()
            self.anchor_preset_select.setObjectName("anchor_preset_select")
            self.anchor_preset_select.addItems(list(ANCHOR_PRESETS))
            self.structure_anchor_input = QDoubleSpinBox()
            self.structure_anchor_input.setObjectName("structure_anchor_input")
            self.structure_anchor_input.setRange(0.0, 1.0)
            self.structure_anchor_input.setSingleStep(0.05)
            self.structure_anchor_input.setDecimals(2)
            self.random_seed_input = QSpinBox()
            self.random_seed_input.setObjectName("random_seed_input")
            self.random_seed_input.setRange(-(2**31), 2**31 - 1)
            self.sample_steps_input = QSpinBox()
            self.sample_steps_input.setObjectName("sample_steps_input")
            self.sample_steps_input.setRange(1, 10000)
            self.overlap_input = QSpinBox()
            self.overlap_input.setObjectName("overlap_input")
            self.overlap_input.setRange(0, 511)
            self.non_copy_checkbox = QCheckBox("Patch nearest-neighbor non-copy search")
            self.non_copy_checkbox.setObjectName("non_copy_checkbox")
            parameters_layout.addRow("Anchor preset", self.anchor_preset_select)
            parameters_layout.addRow("Structure anchor", self.structure_anchor_input)
            parameters_layout.addRow("Random seed", self.random_seed_input)
            parameters_layout.addRow("Sample steps", self.sample_steps_input)
            parameters_layout.addRow("Overlap", self.overlap_input)
            parameters_layout.addRow("QC non-copy", self.non_copy_checkbox)
            layout.addWidget(parameters_group)

            mapping_group = QGroupBox("Label Mapping")
            mapping_layout = QFormLayout(mapping_group)
            for class_name in MASK_CLASSES:
                line_edit = _line_edit(f"label_mapping_{class_name}_input")
                line_edit.setPlaceholderText("raw labels, comma separated")
                self._label_inputs[class_name] = line_edit
                mapping_layout.addRow(class_name, line_edit)
            layout.addWidget(mapping_group)

            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            layout.addWidget(separator)

            self.save_config_button = QPushButton("保存配置")
            self.save_config_button.setObjectName("save_config_button")
            self.save_config_button.clicked.connect(self._on_save_config)
            self.create_job_button = QPushButton("创建运行命令/任务")
            self.create_job_button.setObjectName("create_job_button")
            self.create_job_button.clicked.connect(self._on_create_job)
            self.run_job_button = QPushButton("执行 queued job")
            self.run_job_button.setObjectName("run_job_button")
            self.run_job_button.clicked.connect(self._on_run_job)
            self.refresh_job_button = QPushButton("刷新 job 状态")
            self.refresh_job_button.setObjectName("refresh_job_button")
            self.refresh_job_button.clicked.connect(self._on_refresh_job)
            self.load_output_summary_button = QPushButton("加载输出摘要")
            self.load_output_summary_button.setObjectName("load_output_summary_button")
            self.load_output_summary_button.clicked.connect(self._on_load_output_summary)
            self.ui_status_label = QLabel("Ready")
            self.ui_status_label.setObjectName("ui_status_label")
            self.ui_status_label.setWordWrap(True)
            self.job_status_label = QLabel("No job loaded")
            self.job_status_label.setObjectName("job_status_label")
            self.job_status_label.setWordWrap(True)
            self.output_summary_label = QLabel("No output summary loaded")
            self.output_summary_label.setObjectName("output_summary_label")
            self.output_summary_label.setWordWrap(True)
            layout.addWidget(self.save_config_button)
            layout.addWidget(self.create_job_button)
            layout.addWidget(self.run_job_button)
            layout.addWidget(self.refresh_job_button)
            layout.addWidget(self.load_output_summary_button)
            layout.addWidget(self.ui_status_label)
            layout.addWidget(self.job_status_label)
            layout.addWidget(self.output_summary_label)

            self._apply_initial_values()
            scroll.setWidget(central)
            self.setCentralWidget(scroll)

        def _apply_initial_values(self) -> None:
            generation_config = dict(DEFAULT_GENERATION_CONFIG)
            if self._initial_config.get("schema_version") == DEFAULT_GENERATION_CONFIG["schema_version"]:
                generation_config.update(
                    {
                        key: value
                        for key, value in self._initial_config.items()
                        if key in DEFAULT_GENERATION_CONFIG
                    }
                )
            self.anchor_preset_select.setCurrentText(str(generation_config["anchor_preset"]))
            self.structure_anchor_input.setValue(float(generation_config["structure_anchor"]))
            self.random_seed_input.setValue(int(generation_config["random_seed"]))
            self.sample_steps_input.setValue(int(generation_config["sample_steps"]))
            self.overlap_input.setValue(int(generation_config["overlap_px_40x"]))
            self.style_seed_input.setText(str(generation_config["style_seed"]))
            source_wsi_id = generation_config.get("source_wsi_id")
            self.source_wsi_id_input.setText("" if source_wsi_id is None else str(source_wsi_id))
            self.non_copy_checkbox.setChecked(
                bool(generation_config["non_copy_patch_nearest_neighbor_search"])
            )

        def _on_save_config(self) -> None:
            try:
                target = self._save_generation_config()
            except ValueError as exc:
                self._set_error(str(exc))
                return
            self._set_status(f"Saved generation config: {target}")

        def _on_create_job(self) -> None:
            try:
                record = self._create_local_job()
            except ValueError as exc:
                self._set_error(str(exc))
                return
            self._set_job_status(_format_job_record(record))
            self._set_status(f"Queued job {record['job_id']}: {record['record_path']}")

        def _on_run_job(self) -> None:
            try:
                record = run_queued_generation_job(self._form_state())
            except (ValueError, OSError) as exc:
                self._set_job_error(str(exc))
                return
            self._set_job_status(_format_job_record(record))

        def _on_refresh_job(self) -> None:
            try:
                record = load_generation_job_status(self._form_state())
            except (ValueError, OSError) as exc:
                self._set_job_error(str(exc))
                return
            self._set_job_status(_format_job_record(record))

        def _on_load_output_summary(self) -> None:
            try:
                summary = collect_generation_job_output_summary(self._form_state())
            except (ValueError, OSError) as exc:
                self._set_summary_error(str(exc))
                return
            self.output_summary_label.setText(_format_output_summary(summary))

        def _save_generation_config(self) -> Path:
            target = _required_path(self.generation_config_path_input, "generation config save path")
            config_data = self._build_generation_config()
            self._write_generation_config(target, config_data)
            return target

        def _write_generation_config(self, target: Path, config_data: dict[str, Any]) -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_text(json.dumps(config_data, indent=2) + "\n", encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"failed to write generation config: {exc}") from exc

        def _create_local_job(self) -> dict[str, Any]:
            config_path = _required_path(
                self.generation_config_path_input, "generation config save path"
            )
            config_data = self._build_generation_config()
            self._write_generation_config(config_path, config_data)
            try:
                return create_run_generation_job(
                    self._form_state(),
                    _required_path(self.output_root_input, "output root") / "ui_jobs",
                    config_path,
                )
            except UIWorkflowError as exc:
                raise ValueError(str(exc)) from exc

        def _build_generation_config(self) -> dict[str, Any]:
            try:
                return build_generation_config_from_form(self._form_state())
            except UIWorkflowError as exc:
                raise ValueError(str(exc)) from exc

        def _form_state(self) -> dict[str, Any]:
            return {
                "backend": self.backend_select.currentText(),
                "prior_manifest_path": _text_value(self.prior_manifest_input),
                "checkpoint_manifest_path": _text_value(self.checkpoint_manifest_input),
                "output_root": _text_value(self.output_root_input),
                "generated_id": _text_value(self.generated_id_input),
                "random_seed": int(self.random_seed_input.value()),
                "anchor_preset": self.anchor_preset_select.currentText(),
                "structure_anchor": float(self.structure_anchor_input.value()),
                "source_wsi_id": _text_value(self.source_wsi_id_input),
                "style_seed": _text_value(self.style_seed_input) or "auto",
                "sample_steps": int(self.sample_steps_input.value()),
                "overlap_px_40x": int(self.overlap_input.value()),
                "non_copy_patch_nearest_neighbor_search": self.non_copy_checkbox.isChecked(),
                "condition_packet_path": _text_value(self.condition_packet_input),
                "training_index_path": _text_value(self.training_index_input),
                "label_mapping_rows": self._label_mapping_rows(),
            }

        def _label_mapping_rows(self) -> list[dict[str, str]]:
            rows: list[dict[str, str]] = []
            for class_name, widget in self._label_inputs.items():
                for raw_label in _parse_raw_label_tokens(widget.text(), class_name):
                    rows.append({"raw_label": raw_label, "class_name": class_name})
            if not rows:
                raise ValueError("label mapping must include at least one raw label")
            return rows

        def _set_status(self, message: str) -> None:
            self.ui_status_label.setText(message)

        def _set_error(self, message: str) -> None:
            self.ui_status_label.setText(f"Error: {message}")

        def _set_job_status(self, message: str) -> None:
            self.job_status_label.setText(message)
            self._set_status(message)

        def _set_job_error(self, message: str) -> None:
            self.job_status_label.setText(f"Error: {message}")
            self._set_error(message)

        def _set_summary_error(self, message: str) -> None:
            self.output_summary_label.setText(f"Error: {message}")
            self._set_error(message)

    window = GenerationConfigWindow(config)
    return window


def _line_edit(object_name: str):
    from PySide6.QtWidgets import QLineEdit

    line_edit = QLineEdit()
    line_edit.setObjectName(object_name)
    return line_edit


def _required_text(widget, label: str) -> str:
    value = widget.text().strip()
    if value == "":
        raise ValueError(f"{label} is required")
    return value


def _text_value(widget) -> str:
    value = widget.text().strip()
    return value


def _required_path(widget, label: str) -> Path:
    return Path(_required_text(widget, label))


def _parse_raw_label_tokens(text: str, class_name: str) -> list[str]:
    normalized = text.replace(",", " ").replace(";", " ").replace("\n", " ")
    tokens = [token.strip() for token in normalized.split() if token.strip()]
    labels: list[str] = []
    for token in tokens:
        if not token.isdecimal():
            raise ValueError(
                f"label mapping for {class_name} contains invalid raw label {token!r}"
            )
        labels.append(str(int(token)))
    return labels


def _format_job_record(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Job {record.get('job_id')}: {record.get('status')}",
            f"Message: {record.get('message') or '-'}",
            f"Record: {record.get('record_path')}",
        ]
    )


def _format_output_summary(summary: dict[str, Any]) -> str:
    outputs = summary.get("outputs", {})
    lines = [
        f"Generated ID: {summary.get('generated_id')}",
        f"QC status: {summary.get('qc_status')}",
        f"WSI: {outputs.get('wsi_path')}",
        f"Mask: {outputs.get('mask_path')}",
        f"Metadata: {outputs.get('metadata_path')}",
        f"QC: {outputs.get('qc_json_path')}",
    ]
    review = summary.get("review")
    if isinstance(review, dict):
        lines.append(f"Review decision: {review.get('decision')}")
    return "\n".join(lines)


def launch_ui(config: dict | None = None) -> int:
    ensure_pyside_available()
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = create_main_window(config)
    window.show()
    return app.exec()
