# main.py
# ─────────────────────────────────────────────────────────────────────────────
# Entry point. Wires ConfigPanel, ResultsPanel, HistoryPanel together.
# Runs the simulation in a background QThread so the UI never freezes.
# Handles screen transitions (config ↔ results), compare requests,
# history navigation, and DB persistence.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import sys
import os
import traceback

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QSizePolicy,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QObject,
    QPropertyAnimation, QEasingCurve, QTimer, QSize,
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from theme import COLOR, FONT_SIZE, get_stylesheet
from simulator import SimConfig, SimResult, run_simulation
from database import init_db, save_run
from config_panel import ConfigPanel
from history_panel import HistoryPanel
from results_panel import ResultsPanel


# ─────────────────────────────────────────────────────────────────────────────
# Background worker thread
# ─────────────────────────────────────────────────────────────────────────────

class SimWorker(QObject):
    """Runs the simulator in a background thread. Never blocks the UI."""
    finished = pyqtSignal(object)   # SimResult
    error    = pyqtSignal(str)

    def __init__(self, cfg: SimConfig):
        super().__init__()
        self._cfg = cfg

    def run(self):
        try:
            result = run_simulation(self._cfg)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ─────────────────────────────────────────────────────────────────────────────
# Title bar widget (custom, sits above the two-panel layout)
# ─────────────────────────────────────────────────────────────────────────────

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-bottom: 1px solid {COLOR['border_faint']};"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        # App icon dot (accent)
        dot = QLabel("◈")
        dot.setFont(QFont("DM Sans", 14))
        dot.setStyleSheet(f"color: {COLOR['accent']}; background: transparent;")
        lay.addWidget(dot)

        title = QLabel("Cache Simulator")
        title.setFont(QFont("DM Sans", FONT_SIZE["md"], QFont.Weight.Bold))
        title.setStyleSheet(
            f"color: {COLOR['text_primary']}; background: transparent; letter-spacing: 0.3px;"
        )
        lay.addWidget(title)

        self._status_dot = QLabel("●")
        self._status_dot.setFont(QFont("DM Sans", 8))
        self._status_dot.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        lay.addWidget(self._status_dot)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("DM Sans", FONT_SIZE["xs"]))
        self._status_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        lay.addWidget(self._status_lbl)

        lay.addStretch()

        # Screen indicator pills
        self._pill_config  = self._make_pill("Configure")
        self._pill_results = self._make_pill("Results", active=False)
        lay.addWidget(self._pill_config)
        lay.addWidget(self._pill_results)

    def _make_pill(self, text: str, active: bool = True) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("DM Sans", FONT_SIZE["xs"]))
        lbl.setContentsMargins(10, 3, 10, 3)
        self._set_pill_style(lbl, active)
        return lbl

    def _set_pill_style(self, lbl: QLabel, active: bool):
        if active:
            lbl.setStyleSheet(
                f"color: {COLOR['accent']};"
                f"background: rgba(79,195,247,0.12);"
                f"border: 1px solid {COLOR['accent_dim']};"
                f"border-radius: 10px;"
            )
        else:
            lbl.setStyleSheet(
                f"color: {COLOR['text_muted']};"
                f"background: transparent;"
                f"border: 1px solid {COLOR['border_faint']};"
                f"border-radius: 10px;"
            )

    def set_screen(self, screen: str):
        """screen = 'config' | 'results'"""
        self._set_pill_style(self._pill_config,  screen == "config")
        self._set_pill_style(self._pill_results, screen == "results")

    def set_status(self, text: str, color: str = COLOR["text_muted"]):
        self._status_lbl.setText(text)
        self._status_dot.setStyleSheet(
            f"color: {color}; background: transparent;"
        )

    def clear_status(self):
        self._status_lbl.setText("")
        self._status_dot.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fade transition helper
# ─────────────────────────────────────────────────────────────────────────────

def _fade_transition(widget: QWidget, duration: int = 220):
    """Quick opacity fade-in on a widget."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    # Screen indices in the QStackedWidget
    SCREEN_CONFIG  = 0
    SCREEN_RESULTS = 1

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cache Simulator")
        self.setMinimumSize(1100, 680)

        self._thread: QThread  | None = None
        self._worker: SimWorker | None = None

        self._build_ui()
        self._connect_signals()

    # ── Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root_widget = QWidget()
        root_widget.setStyleSheet(f"background-color: {COLOR['bg_deep']};")
        self.setCentralWidget(root_widget)

        root_lay = QVBoxLayout(root_widget)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar()
        root_lay.addWidget(self._title_bar)

        # Main body: [left content stack] | [history panel]
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # Stacked widget (config screen / results screen)
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        self._config_panel  = ConfigPanel()
        self._results_panel = ResultsPanel()

        self._stack.addWidget(self._config_panel)   # index 0
        self._stack.addWidget(self._results_panel)  # index 1

        body_lay.addWidget(self._stack, 1)

        # History panel (always visible)
        self._history_panel = HistoryPanel()
        body_lay.addWidget(self._history_panel)

        root_lay.addWidget(body, 1)

    # ── Connect signals ────────────────────────────────────────────────────
    def _connect_signals(self):
        # Config panel → run requested
        self._config_panel.run_requested.connect(self._on_run_requested)

        # Results panel → back to config
        self._results_panel.new_simulation_requested.connect(self._show_config)

        # History panel → load a past run into results
        self._history_panel.run_selected.connect(self._on_history_run_selected)

        # History panel → compare two runs
        self._history_panel.compare_requested.connect(self._on_compare_requested)

    # ── Screen transitions ─────────────────────────────────────────────────
    def _show_config(self):
        self._stack.setCurrentIndex(self.SCREEN_CONFIG)
        self._title_bar.set_screen("config")
        self._config_panel.set_running(False)
        self._title_bar.clear_status()
        _fade_transition(self._config_panel)

    def _show_results(self):
        self._stack.setCurrentIndex(self.SCREEN_RESULTS)
        self._title_bar.set_screen("results")
        _fade_transition(self._results_panel)

    # ── Run simulation ─────────────────────────────────────────────────────
    def _on_run_requested(self, cfg: SimConfig):
        # Lock the UI
        self._config_panel.set_running(True)
        self._title_bar.set_status("Running simulation…", COLOR["accent_amber"])

        # Spin up background thread
        self._thread = QThread(self)
        self._worker = SimWorker(cfg)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_sim_finished)
        self._worker.error.connect(self._on_sim_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_sim_finished(self, result: SimResult):
        self._config_panel.set_running(False)

        if result.status == "error":
            self._title_bar.set_status(
                f"Error: {result.error_message[:80]}", COLOR["accent_red"]
            )
            self._config_panel.set_error(result.error_message)
            return

        # Persist to DB
        run_id = save_run(
            trace_path  = result.config.trace_path,
            config      = result.to_config_dict(),
            command     = result.command,
            raw_output  = result.raw_output,
            metrics     = result.to_metrics_dict(),
            duration_s  = result.duration_s,
            status      = result.status,
        )

        # Build the full run dict the same way DB returns it
        import database as db
        saved_run = db.get_run_by_id(run_id)

        # Update history panel
        self._history_panel.set_current_run(saved_run)

        # Load results
        self._results_panel.show_result(saved_run)
        self._show_results()

        self._title_bar.set_status(
            f"Completed in {result.duration_s:.2f}s", COLOR["accent_green"]
        )
        QTimer.singleShot(4000, self._title_bar.clear_status)

    def _on_sim_error(self, msg: str):
        self._config_panel.set_running(False)
        self._title_bar.set_status("Simulation failed", COLOR["accent_red"])
        self._config_panel.set_error(msg[:120])

    # ── History interactions ───────────────────────────────────────────────
    def _on_history_run_selected(self, run: dict):
        """User clicked a past run — show its results."""
        self._results_panel.show_result(run)
        self._show_results()

    def _on_compare_requested(self, run_a: dict, run_b: dict):
        """User pinned + clicked two runs — show compare view."""
        self._results_panel.show_comparison(run_a, run_b)
        self._show_results()


# ─────────────────────────────────────────────────────────────────────────────
# App entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Cache Simulator")
    app.setOrganizationName("cs1op")

    # Apply global stylesheet
    app.setStyleSheet(get_stylesheet())

    # Force dark palette so native dialogs (file picker etc.) also go dark
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(COLOR["bg_deep"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(COLOR["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(COLOR["bg_card"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLOR["bg_elevated"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(COLOR["bg_card"]))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLOR["text_primary"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(COLOR["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(COLOR["bg_elevated"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(COLOR["text_primary"]))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(COLOR["accent_glow"]))
    palette.setColor(QPalette.ColorRole.Link,            QColor(COLOR["accent"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(COLOR["accent_dim"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLOR["text_primary"]))
    app.setPalette(palette)

    # Initialise DB
    init_db()

    # Launch window fullscreen
    window = MainWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()