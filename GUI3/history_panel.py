# history_panel.py
# ─────────────────────────────────────────────────────────────────────────────
# Right-side panel: lists all past runs with brief summaries.
# Compare button is visible on each card — no right-click needed.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QMenu,
    QMessageBox, QDialog, QCheckBox, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor

from theme import COLOR, FONT_SIZE
import database as db


# ── Helpers ───────────────────────────────────────────────────────────────────
def _size_label(b: int) -> str:
    if b >= 1_048_576: return f"{b // 1_048_576}M"
    if b >= 1_024:     return f"{b // 1_024}K"
    return str(b)


def _rel_time(iso: str) -> str:
    try:
        dt   = datetime.fromisoformat(iso)
        diff = datetime.now() - dt
        s    = int(diff.total_seconds())
        if s < 60:       return "Just now"
        if s < 3600:     return f"{s // 60}m ago"
        if s < 86400:    return f"{s // 3600}h ago"
        if s < 172800:   return "Yesterday"
        return dt.strftime("%d %b %Y")
    except Exception:
        return iso[:10] if iso else "—"


# ── Single run card ────────────────────────────────────────────────────────────
class RunCard(QWidget):
    clicked        = pyqtSignal(int)
    compare_pinned = pyqtSignal(int)
    delete_req     = pyqtSignal(int)
    rename_req     = pyqtSignal(int)

    def __init__(self, run: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.run_id    = run["id"]
        self._run      = run
        self._selected = False
        self._pinned   = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(94)
        self.setMaximumHeight(94)
        self._build_ui(run)
        self._apply_style()

    def _build_ui(self, run: dict):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 10, 10)
        root.setSpacing(10)

        # Left accent bar
        bar = QFrame()
        bar.setFixedWidth(2)
        bar.setFixedHeight(58)
        status_color = (
            COLOR["accent_green"] if run.get("status") == "success"
            else COLOR["accent_red"]
        )
        bar.setStyleSheet(
            f"background-color: {status_color}; border-radius: 1px;"
        )
        root.addWidget(bar, 0, Qt.AlignmentFlag.AlignVCenter)

        # Text block
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setContentsMargins(0, 0, 0, 0)

        # Run number + timestamp row
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        run_number = run.get("run_number", run.get("id", "?"))
        run_num  = QLabel(f"Run #{run_number}")
        run_num.setFont(QFont("Inter", FONT_SIZE["xs"], QFont.Weight.Bold))
        run_num.setStyleSheet(
            f"color: {COLOR['text_secondary']}; background: transparent;"
        )
        top_row.addWidget(run_num)
        top_row.addStretch()

        ts = QLabel(_rel_time(run.get("timestamp", "")))
        ts.setFont(QFont("Inter", FONT_SIZE["xs"] - 1))
        ts.setStyleSheet(f"color: {COLOR['text_muted']}; background: transparent;")
        top_row.addWidget(ts)
        text_col.addLayout(top_row)

        # Simulation label (reflects user rename)
        sim_label = (
            run.get("display_label")
            or run.get("label")
            or f"Run #{run_number}"
        ).strip()
        if len(sim_label) > 34:
            sim_label = sim_label[:31] + "..."
        file_lbl = QLabel(sim_label)
        file_lbl.setFont(QFont("Inter", FONT_SIZE["sm"], QFont.Weight.Medium))
        file_lbl.setStyleSheet(
            f"color: {COLOR['text_primary']}; background: transparent;"
        )
        file_lbl.setMaximumWidth(180)
        file_lbl.setToolTip(run.get("display_label") or run.get("label", ""))
        text_col.addWidget(file_lbl)

        # Trace summary
        summary = run.get("trace_summary", "")
        if summary:
            sum_lbl = QLabel(summary)
            sum_lbl.setFont(QFont("Inter", FONT_SIZE["xs"]))
            sum_lbl.setStyleSheet(
                f"color: {COLOR['text_secondary']}; background: transparent;"
            )
            text_col.addWidget(sum_lbl)

        # Config line: L1 L2 policy prefetch
        cfg_str = (
            f"L1 {_size_label(run.get('l1_size',0))}/{run.get('l1_assoc','?')}w  "
            f"L2 {_size_label(run.get('l2_size',0))}/{run.get('l2_assoc','?')}w  "
            f"{run.get('policy','—')}  "
            f"{'PF' if run.get('prefetch')=='ON' else 'No PF'}"
        )
        cfg_lbl = QLabel(cfg_str)
        cfg_lbl.setFont(QFont("JetBrains Mono", FONT_SIZE["xs"] - 1))
        cfg_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        text_col.addWidget(cfg_lbl)

        root.addLayout(text_col, 1)

        # Right: compare button + overflow menu
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setObjectName("compareBtn")
        self._compare_btn.setFont(QFont("Inter", FONT_SIZE["xs"] - 1))
        self._compare_btn.setFixedSize(72, 24)
        self._compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compare_btn.setToolTip(
            "Pin this run, then click another to compare side by side"
        )
        self._compare_btn.clicked.connect(
            lambda: self.compare_pinned.emit(self.run_id)
        )
        btn_col.addWidget(self._compare_btn)

        more_btn = QPushButton("•••")
        more_btn.setObjectName("ghostBtn")
        more_btn.setFont(QFont("Inter", FONT_SIZE["xs"] - 1))
        more_btn.setFixedSize(34, 22)
        more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        more_btn.clicked.connect(self._show_menu)
        btn_col.addWidget(more_btn)
        btn_col.addStretch()

        root.addLayout(btn_col)

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{"
            f"  background-color: {COLOR['bg_card']};"
            f"  border: 1px solid {COLOR['border_mid']};"
            f"  border-radius: 6px; padding: 4px;"
            f"}}"
            f"QMenu::item {{"
            f"  padding: 7px 18px;"
            f"  color: {COLOR['text_primary']};"
            f"  border-radius: 4px;"
            f"}}"
            f"QMenu::item:selected {{"
            f"  background-color: {COLOR['bg_elevated']};"
            f"}}"
        )
        a_rename = menu.addAction("Rename")
        menu.addSeparator()
        a_delete = menu.addAction("Delete")

        action = menu.exec(QCursor.pos())
        if action == a_rename:
            self.rename_req.emit(self.run_id)
        elif action == a_delete:
            self.delete_req.emit(self.run_id)

    def _apply_style(self):
        if self._pinned:
            bg     = "rgba(245,158,11,0.08)"
            border = COLOR["accent_amber"]
        elif self._selected:
            bg     = COLOR["bg_selected"]
            border = COLOR["accent"]
        else:
            bg     = COLOR["bg_card"]
            border = COLOR["border_faint"]

        self.setStyleSheet(
            f"RunCard {{"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"}}"
        )

        # Update compare button label
        self._compare_btn.setText("Pinned" if self._pinned else "Compare")

    def set_selected(self, v: bool):
        self._selected = v
        self._apply_style()

    def set_pinned(self, v: bool):
        self._pinned = v
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only emit click if the user didn't click a child button
            child = self.childAt(event.pos())
            if child is None or not isinstance(child, QPushButton):
                self.clicked.emit(self.run_id)
        super().mousePressEvent(event)


# ── History Panel ──────────────────────────────────────────────────────────────
class HistoryPanel(QWidget):
    run_selected      = pyqtSignal(dict)
    compare_requested = pyqtSignal(dict, dict)
    history_cleared   = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(268)
        self.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-left: 1px solid {COLOR['border_faint']};"
        )
        self._cards:       dict[int, RunCard] = {}
        self._selected_id: Optional[int]      = None
        self._pinned_id:   Optional[int]      = None

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-bottom: 1px solid {COLOR['border_faint']};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 0, 12, 0)

        title = QLabel("HISTORY")
        title.setFont(QFont("Inter", FONT_SIZE["xs"], QFont.Weight.Bold))
        title.setStyleSheet(
            f"color: {COLOR['text_secondary']}; letter-spacing: 2px; background: transparent;"
        )
        h_lay.addWidget(title)
        h_lay.addStretch()

        self._count_lbl = QLabel("0 runs")
        self._count_lbl.setFont(QFont("Inter", FONT_SIZE["xs"] - 1))
        self._count_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; background: transparent;"
        )
        h_lay.addWidget(self._count_lbl)
        root.addWidget(header)

        # Compare banner
        self._compare_banner = QWidget()
        self._compare_banner.setVisible(False)
        self._compare_banner.setFixedHeight(38)
        self._compare_banner.setStyleSheet(
            f"background-color: rgba(245,158,11,0.08);"
            f"border-bottom: 1px solid rgba(245,158,11,0.2);"
        )
        cb_lay = QHBoxLayout(self._compare_banner)
        cb_lay.setContentsMargins(12, 0, 8, 0)

        cb_lbl = QLabel("Pinned — click any other run to compare")
        cb_lbl.setFont(QFont("Inter", FONT_SIZE["xs"]))
        cb_lbl.setStyleSheet(
            f"color: {COLOR['accent_amber']}; background: transparent;"
        )
        cb_lay.addWidget(cb_lbl, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ghostBtn")
        cancel_btn.setFont(QFont("Inter", FONT_SIZE["xs"] - 1))
        cancel_btn.setFixedHeight(22)
        cancel_btn.clicked.connect(self._cancel_compare)
        cb_lay.addWidget(cancel_btn)
        root.addWidget(self._compare_banner)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, 1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-top: 1px solid {COLOR['border_faint']};"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(10, 0, 10, 0)

        delete_history_btn = QPushButton("Delete History")
        delete_history_btn.setObjectName("ghostBtn")
        delete_history_btn.setFont(QFont("Inter", FONT_SIZE["xs"]))
        delete_history_btn.clicked.connect(self._open_delete_history_dialog)
        f_lay.addStretch()
        f_lay.addWidget(delete_history_btn)
        f_lay.addStretch()
        root.addWidget(footer)

    # ── Public API ─────────────────────────────────────────────────────────
    def refresh(self):
        runs = db.get_all_runs()
        self._rebuild_list(runs)

    def set_current_run(self, run: dict):
        self.refresh()
        if run and run.get("id"):
            self._select_card(run["id"])

    # ── Internal ───────────────────────────────────────────────────────────
    def _rebuild_list(self, runs: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        count = len(runs)
        self._count_lbl.setText(f"{count} run{'s' if count != 1 else ''}")

        if not runs:
            empty = QLabel("No simulations yet.\nRun one to see history here.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFont(QFont("Inter", FONT_SIZE["xs"]))
            empty.setStyleSheet(
                f"color: {COLOR['text_muted']}; background: transparent; padding: 24px 12px;"
            )
            empty.setWordWrap(True)
            self._list_layout.insertWidget(0, empty)
            return

        for run in runs:
            card = RunCard(run)
            card.clicked.connect(self._on_card_clicked)
            card.compare_pinned.connect(self._on_pin_compare)
            card.delete_req.connect(self._on_delete)
            card.rename_req.connect(self._on_rename)

            if run["id"] == self._pinned_id:
                card.set_pinned(True)
            if run["id"] == self._selected_id:
                card.set_selected(True)

            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
            self._cards[run["id"]] = card

    def _select_card(self, run_id: int):
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)
        self._selected_id = run_id
        if run_id in self._cards:
            self._cards[run_id].set_selected(True)

    def _on_card_clicked(self, run_id: int):
        run = db.get_run_by_id(run_id)
        if not run:
            return

        # If a pin is set and this is a different card — trigger compare
        if self._pinned_id is not None and run_id != self._pinned_id:
            pinned_run = db.get_run_by_id(self._pinned_id)
            if pinned_run:
                self._cancel_compare()
                self.compare_requested.emit(pinned_run, run)
                return

        self._select_card(run_id)
        self.run_selected.emit(run)

    def _on_pin_compare(self, run_id: int):
        if self._pinned_id == run_id:
            self._cancel_compare()
            return
        if self._pinned_id and self._pinned_id in self._cards:
            self._cards[self._pinned_id].set_pinned(False)
        self._pinned_id = run_id
        if run_id in self._cards:
            self._cards[run_id].set_pinned(True)
        self._compare_banner.setVisible(True)

    def _emit_selected_run_if_available(self):
        if self._selected_id is None:
            return
        run = db.get_run_by_id(self._selected_id)
        if run:
            self.run_selected.emit(run)

    def _cancel_compare(self):
        if self._pinned_id and self._pinned_id in self._cards:
            self._cards[self._pinned_id].set_pinned(False)
        self._pinned_id = None
        self._compare_banner.setVisible(False)

    def _new_dialog(self, title: str, min_width: int, min_height: int = 0) -> QDialog:
        dlg = QDialog(None)
        dlg.setWindowTitle(title)
        dlg.setMinimumWidth(min_width)
        if min_height > 0:
            dlg.setMinimumHeight(min_height)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setWindowFlag(Qt.WindowType.Window, True)
        dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        dlg.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"color: {COLOR['text_primary']};"
        )
        return dlg

    def _show_text_input_dialog(self, title: str, prompt: str, initial: str = "") -> tuple[str, bool]:
        dlg = self._new_dialog(title, 420)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lbl = QLabel(prompt)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        inp = QLineEdit(initial)
        inp.setMinimumHeight(36)
        lay.addWidget(inp)

        row = QHBoxLayout()
        row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("ghostBtn")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ghostBtn")
        row.addWidget(ok_btn)
        row.addWidget(cancel_btn)
        lay.addLayout(row)

        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)

        inp.selectAll()
        inp.setFocus()
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        return inp.text(), accepted

    def _show_confirm_dialog(self, title: str, message: str, confirm_text: str = "Delete") -> bool:
        dlg = self._new_dialog(title, 440)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        msg = QLabel(message)
        msg.setWordWrap(True)
        lay.addWidget(msg)

        row = QHBoxLayout()
        row.addStretch()
        yes_btn = QPushButton(confirm_text)
        yes_btn.setObjectName("ghostBtn")
        no_btn = QPushButton("Cancel")
        no_btn.setObjectName("ghostBtn")
        row.addWidget(yes_btn)
        row.addWidget(no_btn)
        lay.addLayout(row)

        yes_btn.clicked.connect(dlg.accept)
        no_btn.clicked.connect(dlg.reject)

        return dlg.exec() == QDialog.DialogCode.Accepted

    def _show_info_dialog(self, title: str, message: str):
        dlg = self._new_dialog(title, 380)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        msg = QLabel(message)
        msg.setWordWrap(True)
        lay.addWidget(msg)

        row = QHBoxLayout()
        row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("ghostBtn")
        row.addWidget(ok_btn)
        lay.addLayout(row)

        ok_btn.clicked.connect(dlg.accept)
        dlg.exec()

    def _on_delete(self, run_id: int):
        run   = db.get_run_by_id(run_id)
        if not run:
            label = f"Run #{run_id}"
        else:
            label = run.get("display_label") or run.get("label") or f"Run #{run.get('run_number', run_id)}"
        if not self._show_confirm_dialog(
            "Delete Run",
            f"Delete {label}?\nThis cannot be undone.",
            "Delete",
        ):
            return

        db.delete_run(run_id)
        if self._selected_id == run_id:
            self._selected_id = None
        if self._pinned_id == run_id:
            self._cancel_compare()
        self.refresh()
        self._emit_selected_run_if_available()

    def _on_rename(self, run_id: int):
        run = db.get_run_by_id(run_id)
        if not run:
            return
        new_name, ok = self._show_text_input_dialog(
            "Rename Run",
            "New name:",
            run.get("label", ""),
        )
        if ok and new_name.strip():
            db.rename_run(run_id, new_name.strip())
            self.refresh()
            self._emit_selected_run_if_available()

    def _open_delete_history_dialog(self):
        runs = db.get_all_runs(limit=500)
        if not runs:
            return

        dlg = self._new_dialog("Delete History", 520, 420)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        info = QLabel("Select simulations to delete, or delete the entire history.")
        info.setWordWrap(True)
        info.setFont(QFont("Inter", FONT_SIZE["sm"]))
        info.setStyleSheet(f"color: {COLOR['text_secondary']}; background: transparent;")
        lay.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"background-color: {COLOR['bg_elevated']};"
            f"border: 1px solid {COLOR['border_dim']};"
            f"border-radius: 8px;"
        )

        list_host = QWidget()
        list_lay = QVBoxLayout(list_host)
        list_lay.setContentsMargins(10, 10, 10, 10)
        list_lay.setSpacing(6)

        check_items: list[tuple[QCheckBox, int]] = []
        for run in runs:
            run_id = int(run["id"])
            run_label = run.get("display_label") or run.get("label") or f"Run #{run.get('run_number', run_id)}"
            text = (
                f"{run_label}"
                f"\n{run.get('trace_filename', '—')}  ·  {_rel_time(run.get('timestamp', ''))}"
            )
            cb = QCheckBox(text)
            cb.setFont(QFont("Inter", FONT_SIZE["xs"]))
            cb.setStyleSheet("padding: 5px 4px;")
            check_items.append((cb, run_id))
            list_lay.addWidget(cb)

        list_lay.addStretch()
        scroll.setWidget(list_host)
        lay.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ghostBtn")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.setObjectName("ghostBtn")
        btn_row.addWidget(delete_selected_btn)

        delete_all_btn = QPushButton("Delete History")
        delete_all_btn.setObjectName("ghostBtn")
        btn_row.addWidget(delete_all_btn)

        lay.addLayout(btn_row)

        def _delete_selected():
            selected_ids = [rid for cb, rid in check_items if cb.isChecked()]
            if not selected_ids:
                self._show_info_dialog("Delete Selected", "Select at least one simulation.")
                return

            if not self._show_confirm_dialog(
                "Delete Selected",
                f"Delete {len(selected_ids)} selected simulation{'s' if len(selected_ids) != 1 else ''}?\nThis cannot be undone.",
                "Delete Selected",
            ):
                return

            for rid in selected_ids:
                db.delete_run(rid)

            if self._selected_id in selected_ids:
                self._selected_id = None
            if self._pinned_id in selected_ids:
                self._cancel_compare()

            self.refresh()
            self._emit_selected_run_if_available()
            if db.get_run_count() == 0:
                self.history_cleared.emit()
            dlg.accept()

        def _delete_all_history():
            count = db.get_run_count()
            if count <= 0:
                dlg.accept()
                return

            if not self._show_confirm_dialog(
                "Delete History",
                f"Delete all {count} saved run{'s' if count != 1 else ''}?\nThis cannot be undone.",
                "Delete History",
            ):
                return

            db.clear_all_runs()
            self._selected_id = None
            self._pinned_id   = None
            self._compare_banner.setVisible(False)
            self.refresh()
            self.history_cleared.emit()
            dlg.accept()

        delete_selected_btn.clicked.connect(_delete_selected)
        delete_all_btn.clicked.connect(_delete_all_history)

        dlg.exec()