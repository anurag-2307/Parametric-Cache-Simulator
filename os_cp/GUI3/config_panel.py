# config_panel.py
# ─────────────────────────────────────────────────────────────────────────────
# Screen 1: Configuration panel.
# Settings grid — L1/L2 size & associativity, policy, prefetch.
# Trace file via Browse button or drag-and-drop.
# Binary is always ./cs1op resolved relative to the trace file directory.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QFileDialog, QFrame, QSizePolicy, QSpacerItem,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from theme import COLOR, FONT_SIZE
from simulator import SimConfig


# ── Reusable setting block (label + combo) ────────────────────────────────────
class SettingBlock(QWidget):
    def __init__(
        self,
        label: str,
        options: list[str],
        default: str = "",
        tooltip: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Inter", FONT_SIZE["xs"], QFont.Weight.Bold))
        lbl.setStyleSheet(
            f"color: {COLOR['text_secondary']};"
            f"letter-spacing: 1px;"
            f"background: transparent;"
        )
        layout.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.addItems(options)
        self.combo.setFont(QFont("JetBrains Mono", FONT_SIZE["md"]))
        self.combo.setMinimumHeight(46)
        self.combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if tooltip:
            self.combo.setToolTip(tooltip)
        if default and default in options:
            self.combo.setCurrentText(default)
        layout.addWidget(self.combo)

    def value(self) -> str:
        return self.combo.currentText()

    def set_value(self, v: str):
        idx = self.combo.findText(str(v))
        if idx >= 0:
            self.combo.setCurrentIndex(idx)


# ── Drag-and-drop trace file zone ─────────────────────────────────────────────
class TraceDropZone(QWidget):
    """
    Accepts drag-and-drop or Browse button to select a trace file.
    File dialog is opened as a blocking non-native dialog to avoid
    the platform re-open bug.
    """
    file_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        self._file_path    = ""
        self._dialog_open  = False   # guard against re-entrancy
        self._build_ui()
        self._refresh_style()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._main_lbl = QLabel("Drop trace file here, or")
        self._main_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_lbl.setFont(QFont("Inter", FONT_SIZE["base"]))
        self._main_lbl.setStyleSheet(
            f"color: {COLOR['text_secondary']}; background: transparent;"
        )
        lay.addWidget(self._main_lbl)

        lay.addSpacing(8)

        self._browse_btn = QPushButton("Browse file")
        self._browse_btn.setObjectName("ghostBtn")
        self._browse_btn.setFont(QFont("Inter", FONT_SIZE["sm"]))
        self._browse_btn.setFixedSize(110, 30)
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._open_dialog)
        lay.addWidget(self._browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

        lay.addSpacing(6)

        self._sub_lbl = QLabel("")
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_lbl.setFont(QFont("Inter", FONT_SIZE["xs"]))
        self._sub_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        lay.addWidget(self._sub_lbl)

    def _refresh_style(self, highlight: bool = False, error: bool = False):
        if error:
            border_color = COLOR["accent_red"]
            bg           = "rgba(239,68,68,0.05)"
        elif self._file_path:
            border_color = COLOR["accent"]
            bg           = "rgba(59,130,246,0.05)"
        elif highlight:
            border_color = COLOR["accent"]
            bg           = "rgba(59,130,246,0.07)"
        else:
            border_color = COLOR["border_mid"]
            bg           = COLOR["bg_elevated"]

        self.setStyleSheet(
            f"TraceDropZone {{"
            f"  background-color: {bg};"
            f"  border: 1.5px dashed {border_color};"
            f"  border-radius: 8px;"
            f"}}"
        )

    # ── Drag events ────────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._refresh_style(highlight=True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._refresh_style()

    def dropEvent(self, event):
        self._refresh_style()
        urls = event.mimeData().urls()
        if urls:
            self._accept_file(urls[0].toLocalFile())
        event.acceptProposedAction()

    # ── Browse dialog ──────────────────────────────────────────────────────
    def _open_dialog(self):
        # Guard: don't open a second dialog if one is already open
        if self._dialog_open:
            return
        self._dialog_open = True

        try:
            start = (
                os.path.dirname(self._file_path)
                if self._file_path else os.path.expanduser("~")
            )

            # Use a QFileDialog object (not the static helper) with
            # DontUseNativeDialog to prevent platform re-open bugs
            dlg = QFileDialog(self, "Select Trace File", start)
            dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
            dlg.setNameFilters([
                "Trace files (*.txt *.trace *.trc)",
                "All files (*.*)",
            ])
            dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)

            if dlg.exec() == QFileDialog.DialogCode.Accepted:
                files = dlg.selectedFiles()
                if files:
                    self._accept_file(files[0])
        finally:
            self._dialog_open = False

    def _accept_file(self, path: str):
        if os.path.isfile(path):
            self._file_path = path
            fname   = os.path.basename(path)
            size_kb = os.path.getsize(path) / 1024
            size_s  = f"{size_kb/1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB"
            self._main_lbl.setText(fname)
            self._main_lbl.setStyleSheet(
                f"color: {COLOR['text_primary']}; background: transparent; font-weight: 600;"
            )
            self._sub_lbl.setText(f"{size_s}   —   click Browse to change")
            self._browse_btn.setText("Change")
            self._refresh_style()
            self.file_selected.emit(path)

    # ── Public ─────────────────────────────────────────────────────────────
    def get_path(self) -> str:
        return self._file_path

    def flash_error(self):
        self._refresh_style(error=True)
        QTimer.singleShot(1800, self._refresh_style)

    def clear(self):
        self._file_path = ""
        self._main_lbl.setText("Drop trace file here, or")
        self._main_lbl.setStyleSheet(
            f"color: {COLOR['text_secondary']}; background: transparent;"
        )
        self._sub_lbl.setText("")
        self._browse_btn.setText("Browse file")
        self._refresh_style()


# ── Section header ────────────────────────────────────────────────────────────
def _section_header(title: str, subtitle: str = "") -> QWidget:
    w   = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 4, 0, 4)
    lay.setSpacing(2)

    t = QLabel(title)
    t.setFont(QFont("Inter", FONT_SIZE["lg"], QFont.Weight.Medium))
    t.setStyleSheet(f"color: {COLOR['text_primary']}; background: transparent;")
    lay.addWidget(t)

    if subtitle:
        s = QLabel(subtitle)
        s.setFont(QFont("Inter", FONT_SIZE["xs"]))
        s.setStyleSheet(f"color: {COLOR['text_secondary']}; background: transparent;")
        lay.addWidget(s)

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(
        f"background-color: {COLOR['border_faint']}; border: none; margin-top: 4px;"
    )
    lay.addWidget(line)
    return w


# ── Config Panel ──────────────────────────────────────────────────────────────
class ConfigPanel(QWidget):
    run_requested = pyqtSignal(object)   # emits SimConfig

    L1_SIZES = {
        "1 KB  (1024)":     1024,
        "2 KB  (2048)":     2048,
        "4 KB  (4096)":     4096,
        "8 KB  (8192)":     8192,
        "16 KB (16384)":    16384,
        "32 KB (32768)":    32768,
        "64 KB (65536)":    65536,
        "128 KB (131072)":  131072,
        "256 KB (262144)":  262144,
    }

    L2_SIZES = {
        "64 KB  (65536)":      65536,
        "128 KB (131072)":     131072,
        "256 KB (262144)":     262144,
        "512 KB (524288)":     524288,
        "1 MB  (1048576)":     1048576,
        "2 MB  (2097152)":     2097152,
        "4 MB  (4194304)":     4194304,
        "8 MB  (8388608)":     8388608,
    }

    ASSOC_OPTIONS   = ["1", "2", "4", "8", "16", "32", "64"]
    POLICY_OPTIONS  = ["LRU", "FIFO"]
    PREFETCH_OPTIONS= ["ON", "OFF"]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._trace_path  = ""
        self._is_running  = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(inner_widget)
        inner.setContentsMargins(40, 32, 40, 32)
        inner.setSpacing(26)

        # ── Page title + command preview ───────────────────────────────────
        title_row = QHBoxLayout()

        page_title = QLabel("Simulation Configuration")
        page_title.setFont(QFont("Inter", FONT_SIZE["2xl"], QFont.Weight.Bold))
        page_title.setStyleSheet(
            f"color: {COLOR['text_primary']}; background: transparent;"
        )
        title_row.addWidget(page_title)
        title_row.addStretch()

        self._cmd_preview = QLabel("")
        self._cmd_preview.setFont(QFont("JetBrains Mono", FONT_SIZE["xs"]))
        self._cmd_preview.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        self._cmd_preview.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._cmd_preview.setMaximumWidth(480)
        self._cmd_preview.setWordWrap(True)
        title_row.addWidget(self._cmd_preview)
        inner.addLayout(title_row)

        # ── L1 Cache ───────────────────────────────────────────────────────
        inner.addWidget(_section_header("L1 Cache", "Level 1  —  split I-Cache and D-Cache"))

        l1_grid = QGridLayout()
        l1_grid.setHorizontalSpacing(16)

        self._l1_size = SettingBlock(
            "Cache Size", list(self.L1_SIZES.keys()),
            default="32 KB (32768)",
            tooltip="Total L1 cache size in bytes",
        )
        self._l1_assoc = SettingBlock(
            "Associativity", self.ASSOC_OPTIONS,
            default="8",
            tooltip="Number of ways",
        )
        l1_grid.addWidget(self._l1_size,  0, 0)
        l1_grid.addWidget(self._l1_assoc, 0, 1)
        inner.addLayout(l1_grid)

        # ── L2 Cache ───────────────────────────────────────────────────────
        inner.addWidget(_section_header("L2 Cache", "Level 2  —  unified cache"))

        l2_grid = QGridLayout()
        l2_grid.setHorizontalSpacing(16)

        self._l2_size = SettingBlock(
            "Cache Size", list(self.L2_SIZES.keys()),
            default="2 MB  (2097152)",
            tooltip="Total L2 cache size in bytes",
        )
        self._l2_assoc = SettingBlock(
            "Associativity", self.ASSOC_OPTIONS,
            default="16",
            tooltip="Number of ways for L2",
        )
        l2_grid.addWidget(self._l2_size,  0, 0)
        l2_grid.addWidget(self._l2_assoc, 0, 1)
        inner.addLayout(l2_grid)

        # ── Policy & Prefetch ──────────────────────────────────────────────
        inner.addWidget(_section_header(
            "Policy & Prefetch",
            "Replacement strategy and hardware prefetching",
        ))

        pol_grid = QGridLayout()
        pol_grid.setHorizontalSpacing(16)

        self._policy = SettingBlock(
            "Replacement Policy", self.POLICY_OPTIONS,
            default="LRU",
            tooltip="Cache line eviction policy",
        )
        self._prefetch = SettingBlock(
            "Prefetching", self.PREFETCH_OPTIONS,
            default="ON",
            tooltip="Enable hardware prefetching",
        )
        pol_grid.addWidget(self._policy,   0, 0)
        pol_grid.addWidget(self._prefetch, 0, 1)
        inner.addLayout(pol_grid)

        # ── Trace File ─────────────────────────────────────────────────────
        inner.addWidget(_section_header(
            "Trace File",
            "Memory access trace  —  .txt, .trace, or .trc",
        ))

        self._drop_zone = TraceDropZone()
        self._drop_zone.file_selected.connect(self._on_trace_selected)
        inner.addWidget(self._drop_zone)

        # ── Bottom: status + Run button ────────────────────────────────────
        inner.addSpacerItem(
            QSpacerItem(0, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)
        bottom_row.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Inter", FONT_SIZE["xs"]))
        self._status_lbl.setStyleSheet(
            f"color: {COLOR['accent_red']}; background: transparent;"
        )
        bottom_row.addWidget(self._status_lbl)

        self._run_btn = QPushButton("Run Simulation")
        self._run_btn.setObjectName("primaryBtn")
        self._run_btn.setFont(QFont("Inter", FONT_SIZE["md"], QFont.Weight.Bold))
        self._run_btn.setFixedHeight(48)
        self._run_btn.setMinimumWidth(200)
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.clicked.connect(self._on_run_clicked)
        bottom_row.addWidget(self._run_btn)

        inner.addLayout(bottom_row)
        root.addWidget(inner_widget)

        # Wire command preview
        for sb in [self._l1_size, self._l1_assoc,
                   self._l2_size, self._l2_assoc,
                   self._policy,  self._prefetch]:
            sb.combo.currentIndexChanged.connect(self._update_cmd_preview)

        self._update_cmd_preview()

    # ── Slots ──────────────────────────────────────────────────────────────
    def _on_trace_selected(self, path: str):
        self._trace_path = path
        self._status_lbl.setText("")
        self._update_cmd_preview()

    def _update_cmd_preview(self):
        cfg   = self._build_config()
        trace = os.path.basename(cfg.trace_path) if cfg.trace_path else "<trace_file>"
        cmd   = (
            f"./cs1op "
            f"--l1-size {cfg.l1_size} --l1-assoc {cfg.l1_assoc} "
            f"--l2-size {cfg.l2_size} --l2-assoc {cfg.l2_assoc} "
            f"--prefetch {cfg.prefetch} --policy {cfg.policy} "
            f"--trace {trace}"
        )
        self._cmd_preview.setText(cmd)

    def _build_config(self) -> SimConfig:
        l1_key = self._l1_size.value()
        l2_key = self._l2_size.value()

        l1_bytes = self.L1_SIZES.get(l1_key)
        if l1_bytes is None:
            try:   l1_bytes = int(l1_key.split("(")[-1].rstrip(")").strip())
            except Exception: l1_bytes = 32768

        l2_bytes = self.L2_SIZES.get(l2_key)
        if l2_bytes is None:
            try:   l2_bytes = int(l2_key.split("(")[-1].rstrip(")").strip())
            except Exception: l2_bytes = 2097152

        return SimConfig(
            l1_size    = l1_bytes,
            l1_assoc   = int(self._l1_assoc.value()),
            l2_size    = l2_bytes,
            l2_assoc   = int(self._l2_assoc.value()),
            policy     = self._policy.value(),
            prefetch   = self._prefetch.value(),
            trace_path = self._trace_path,
        )

    def _on_run_clicked(self):
        if self._is_running:
            return
        if not self._trace_path:
            self._status_lbl.setText("Please select a trace file first.")
            self._drop_zone.flash_error()
            return
        self._status_lbl.setText("")
        self.run_requested.emit(self._build_config())

    # ── Public API ─────────────────────────────────────────────────────────
    def set_running(self, running: bool):
        self._is_running = running
        self._run_btn.setEnabled(not running)
        self._run_btn.setText("Running..." if running else "Run Simulation")
        for sb in [self._l1_size, self._l1_assoc,
                   self._l2_size, self._l2_assoc,
                   self._policy,  self._prefetch]:
            sb.combo.setEnabled(not running)

    def set_error(self, message: str):
        self._status_lbl.setText(message[:100])

    def load_config(self, cfg: dict):
        def _match(d, val):
            for k, v in d.items():
                if v == val: return k
            return list(d.keys())[0]

        self._l1_size.set_value(_match(self.L1_SIZES,  cfg.get("l1_size",  32768)))
        self._l1_assoc.set_value(str(cfg.get("l1_assoc", 8)))
        self._l2_size.set_value(_match(self.L2_SIZES,  cfg.get("l2_size",  2097152)))
        self._l2_assoc.set_value(str(cfg.get("l2_assoc", 16)))
        self._policy.set_value(cfg.get("policy",   "LRU"))
        self._prefetch.set_value(cfg.get("prefetch", "ON"))
        self._update_cmd_preview()