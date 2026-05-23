import sys

from .config import create_default_ui_config


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
        QLabel,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    ui_config = config or create_default_ui_config()
    window = QMainWindow()
    window.setWindowTitle("MultiCenterWSIGenerator")
    central = QWidget()
    layout = QVBoxLayout(central)
    for section_name, section in ui_config["sections"].items():
        label = QLabel(section_name.replace("_", " ").title())
        layout.addWidget(label)
        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(", ".join(section.get("fields", section.keys())))
        layout.addWidget(details)
    launch_button = QPushButton("Run CLI/Core Workflow")
    launch_button.setEnabled(False)
    launch_button.setToolTip("Configure jobs here; execution remains in CLI/core modules.")
    layout.addWidget(launch_button)
    window.setCentralWidget(central)
    return window


def launch_ui(config: dict | None = None) -> int:
    ensure_pyside_available()
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    window = create_main_window(config)
    window.show()
    return app.exec()
