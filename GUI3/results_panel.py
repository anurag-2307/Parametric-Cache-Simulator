# results_panel.py
# ─────────────────────────────────────────────────────────────────────────────
# Screen 2: Simulation results.
# Tab 1 — Detailed Metrics : stat cards for I-Cache, D-Cache, L2 + summary row
# Tab 2 — Visual Metrics   : embedded matplotlib charts
# Compare mode             : side-by-side layout for two runs
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTabWidget, QFrame,
    QScrollArea, QSizePolicy, QSpacerItem,
    QDialog, QDialogButtonBox, QComboBox, QMessageBox, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QImage, QPixmap

from theme import COLOR, FONT_SIZE, MPL_STYLE, GRAPH_COLORS
import database as db


# ── Apply matplotlib theme once ───────────────────────────────────────────────
for k, v in MPL_STYLE.items():
    try:
        plt.rcParams[k] = v
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Small reusable components
# ─────────────────────────────────────────────────────────────────────────────

class _Divider(QFrame):
    def __init__(self, vertical: bool = False):
        super().__init__()
        if vertical:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFixedWidth(1)
        else:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFixedHeight(1)
        self.setStyleSheet(
            f"background-color: {COLOR['border_faint']}; border: none;"
        )


def _label(text: str, size: int = FONT_SIZE["base"],
           color: str = COLOR["text_primary"],
           bold: bool = False, mono: bool = False,
           align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    lbl = QLabel(text)
    family = "JetBrains Mono" if mono else "DM Sans"
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(QFont(family, size, weight))
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    lbl.setAlignment(align)
    return lbl


# ── Single metric row (label : value) ────────────────────────────────────────
class MetricRow(QWidget):
    def __init__(self, label: str, value: str,
                 value_color: str = COLOR["text_mono"],
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = _label(label, FONT_SIZE["sm"], COLOR["text_secondary"])
        lbl.setMinimumWidth(140)
        lay.addWidget(lbl)

        sep = _label(":", FONT_SIZE["sm"], COLOR["text_muted"])
        sep.setFixedWidth(8)
        lay.addWidget(sep)

        val = _label(value, FONT_SIZE["sm"], value_color, mono=True)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(val, 1)


# ── Cache metrics card ────────────────────────────────────────────────────────
class CacheCard(QWidget):
    """
    A card displaying all metrics for one cache (I, D, or L2).
    """
    CACHE_ACCENT = {
        "I-Cache":  COLOR["accent"],
        "D-Cache":  COLOR["accent_green"],
        "L2 Cache": COLOR["accent_purple"],
    }

    def __init__(self, cache_name: str, metrics: dict, parent=None):
        super().__init__(parent)
        accent = self.CACHE_ACCENT.get(cache_name, COLOR["accent"])
        self._build(cache_name, metrics, accent)

    def _build(self, name: str, m: dict, accent: str):
        self.setObjectName("cacheCard")
        self.setStyleSheet(
            f"QWidget#cacheCard {{"
            f"  background-color: {COLOR['bg_card']};"
            f"  border: 1px solid {COLOR['border_faint']};"
            f"  border-top: 1px solid {COLOR['border_faint']};"
            f"  border-radius: 10px;"
            f"}}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(6)

        # Card header
        hdr = QHBoxLayout()
        title = _label(name, FONT_SIZE["md"], accent, bold=True)
        hdr.addWidget(title)
        hdr.addStretch()

        # Hit rate chip
        hit_rate = m.get("hit_rate", 0.0)
        chip_color = (
            COLOR["accent_green"] if hit_rate >= 90 else
            COLOR["accent_amber"] if hit_rate >= 70 else
            COLOR["accent_red"]
        )
        chip = QLabel(f"{hit_rate:.2f}% hit")
        chip.setFont(QFont("JetBrains Mono", FONT_SIZE["xs"] - 1))
        chip.setStyleSheet(
            f"color: {chip_color};"
            f"background: transparent;"
            f"border: 1px solid {chip_color};"
            f"border-radius: 4px;"
            f"padding: 1px 7px;"
        )
        hdr.addWidget(chip)
        root.addLayout(hdr)
        root.addWidget(_Divider())
        root.addSpacing(2)

        # Metrics rows
        def _fmt_int(v) -> str:
            try:
                return f"{int(v):,}"
            except Exception:
                return str(v)

        def _fmt_float(v, decimals=4) -> str:
            try:
                return f"{float(v):.{decimals}f}"
            except Exception:
                return str(v)

        rows = [
            ("Total Accesses",    _fmt_int(m.get("total_accesses", 0)),   COLOR["text_mono"]),
            ("Reads",             _fmt_int(m.get("reads", 0)),            COLOR["text_secondary"]),
            ("Writes",            _fmt_int(m.get("writes", 0)),           COLOR["text_secondary"]),
            ("Cache Hits",        _fmt_int(m.get("cache_hits", 0)),       COLOR["accent_green"]),
            ("Cache Misses",      _fmt_int(m.get("cache_misses", 0)),     COLOR["accent_red"]),
            ("Write Backs",       _fmt_int(m.get("write_backs", 0)),      COLOR["text_secondary"]),
            ("Hit Rate",          f"{_fmt_float(m.get('hit_rate',0), 4)} %",  COLOR["accent_green"]),
            ("Miss Rate",         f"{_fmt_float(m.get('miss_rate',0), 4)} %", COLOR["accent_red"]),
            ("AMAT",              _fmt_float(m.get("amat", 0), 5),        COLOR["accent_amber"]),
            ("Split Accesses",    _fmt_int(m.get("split_accesses", 0)),   COLOR["text_secondary"]),
            ("Replacement Policy",str(m.get("replacement_policy", "—")), COLOR["text_muted"]),
        ]

        for label, value, color in rows:
            root.addWidget(MetricRow(label, value, color))


# ── Summary bar (top of detailed tab) ────────────────────────────────────────
class SummaryBar(QWidget):
    """
    Three big stat tiles: overall hit rates for I, D, L2.
    """
    def __init__(self, metrics: dict, modified_instr: int, duration: float, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryBar")
        self.setFixedHeight(100)
        self.setStyleSheet(
            f"QWidget#summaryBar {{"
            f"  background-color: {COLOR['bg_card']};"
            f"  border: 1px solid {COLOR['border_faint']};"
            f"  border-radius: 10px;"
            f"}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        tiles = [
            ("I-Cache Hit Rate",
             f"{metrics.get('i_cache', {}).get('hit_rate', 0):.4f} %",
             COLOR["accent"]),
            ("D-Cache Hit Rate",
             f"{metrics.get('d_cache', {}).get('hit_rate', 0):.4f} %",
             COLOR["accent_green"]),
            ("L2 Hit Rate",
             f"{metrics.get('l2_cache', {}).get('hit_rate', 0):.4f} %",
             COLOR["accent_purple"]),
            ("Modified Instr.",
             f"{modified_instr:,}",
             COLOR["accent_amber"]),
            ("Exec Time",
             f"{duration:.2f} s",
             COLOR["text_secondary"]),
        ]

        for i, (label, value, color) in enumerate(tiles):
            if i > 0:
                lay.addWidget(_Divider(vertical=True))

            tile = QWidget()
            tile.setStyleSheet("background: transparent;")
            t_lay = QVBoxLayout(tile)
            t_lay.setContentsMargins(20, 14, 20, 14)
            t_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

            v = _label(value, FONT_SIZE["xl"], color, bold=True, mono=True,
                       align=Qt.AlignmentFlag.AlignCenter)
            t_lay.addWidget(v)

            l = _label(label, FONT_SIZE["xs"], COLOR["text_secondary"],
                       align=Qt.AlignmentFlag.AlignCenter)
            t_lay.addWidget(l)

            lay.addWidget(tile, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Chart helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_canvas(fig: Figure) -> FigureCanvas:
    canvas = FigureCanvas(fig)
    canvas.setStyleSheet("background: transparent;")
    return canvas


def _run_display_name(run: dict) -> str:
    display_label = str(run.get("display_label", "")).strip()
    if display_label:
        return display_label

    label = str(run.get("label", "")).strip()
    if label:
        return label

    run_number = run.get("run_number", run.get("id", "?"))
    return f"Run #{run_number}"


def _attach_chart_interactions(canvas: FigureCanvas, parent: QWidget, scroll: QScrollArea | None = None):
    # Click inside plot area enlarges chart into a modal preview dialog.
    def _on_click(event):
        if event.inaxes is None:
            return
        _show_chart_preview(canvas, parent)

    canvas.mpl_connect("button_press_event", _on_click)

    if scroll is not None:
        # Preserve wheel scrolling in scroll areas while keeping click events enabled.
        def _wheel(ev):
            dy = ev.angleDelta().y()
            if dy:
                sb = scroll.verticalScrollBar()
                sb.setValue(sb.value() - dy)
                ev.accept()
                return
            QWidget.wheelEvent(canvas, ev)

        canvas.wheelEvent = _wheel


def _show_chart_preview(canvas: FigureCanvas, parent: QWidget):
    canvas.draw()
    buf = canvas.buffer_rgba()
    w, h = canvas.get_width_height()
    image = QImage(buf, w, h, QImage.Format.Format_RGBA8888)
    pixmap = QPixmap.fromImage(image)

    dlg = QDialog(parent)
    dlg.setWindowTitle("Chart Preview")
    dlg.resize(1000, 620)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    dlg.setWindowModality(Qt.WindowModality.NonModal)
    dlg.setStyleSheet(
        f"background-color: {COLOR['bg_deep']};"
        f"color: {COLOR['text_primary']};"
    )

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(12, 12, 12, 12)

    lbl = QLabel()
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setPixmap(pixmap)
    lbl.setScaledContents(False)
    lay.addWidget(lbl, 1)

    # Keep a reference so Python doesn't GC the non-modal dialog.
    previews = getattr(parent, "_chart_previews", None)
    if previews is None:
        previews = []
        setattr(parent, "_chart_previews", previews)
    previews.append(dlg)
    dlg.destroyed.connect(lambda *_: previews.remove(dlg) if dlg in previews else None)

    dlg.show()
    dlg.raise_()
    dlg.activateWindow()


def _hit_miss_bar_chart(metrics: dict) -> FigureCanvas:
    """Grouped bar chart: hits vs misses for each cache level."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches     = ["I-Cache", "D-Cache", "L2 Cache"]
    keys       = ["i_cache", "d_cache", "l2_cache"]
    hits       = [metrics.get(k, {}).get("cache_hits", 0) for k in keys]
    misses     = [metrics.get(k, {}).get("cache_misses", 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.35

    bars_h = ax.bar(x - width/2, hits,   width, label="Hits",
                    color=COLOR["accent_green"], alpha=0.85, zorder=3)
    bars_m = ax.bar(x + width/2, misses, width, label="Misses",
                    color=COLOR["accent_red"],   alpha=0.85, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(caches)
    ax.set_title("Cache Hits vs Misses", fontsize=11, pad=10)
    ax.set_ylabel("Count", fontsize=9)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6
                                         else f"{v/1e3:.0f}K" if v >= 1e3 else str(int(v)))
    )
    ax.legend(framealpha=0.2, loc="upper right")
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


def _hit_rate_bar_chart(metrics: dict) -> FigureCanvas:
    """Horizontal bar chart: hit rates for each cache."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches  = ["I-Cache", "D-Cache", "L2 Cache"]
    keys    = ["i_cache", "d_cache", "l2_cache"]
    colors  = [COLOR["accent"], COLOR["accent_green"], COLOR["accent_purple"]]
    rates   = [metrics.get(k, {}).get("hit_rate", 0) for k in keys]

    bars = ax.barh(caches, rates, color=colors, alpha=0.85, zorder=3, height=0.45)

    for bar, rate in zip(bars, rates):
        ax.text(
            min(rate + 0.5, 99), bar.get_y() + bar.get_height() / 2,
            f"{rate:.2f}%",
            va="center", ha="left",
            color=COLOR["text_primary"], fontsize=9,
            fontfamily="JetBrains Mono",
        )

    ax.set_xlim(0, 105)
    ax.set_xlabel("Hit Rate (%)", fontsize=9)
    ax.set_title("Hit Rate by Cache Level", fontsize=11, pad=10)
    ax.grid(axis="x", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


def _amat_chart(metrics: dict) -> FigureCanvas:
    """Bar chart: AMAT per cache level."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches = ["I-Cache", "D-Cache", "L2 Cache"]
    keys   = ["i_cache", "d_cache", "l2_cache"]
    colors = [COLOR["accent"], COLOR["accent_green"], COLOR["accent_purple"]]
    amats  = [metrics.get(k, {}).get("amat", 0) for k in keys]

    bars = ax.bar(caches, amats, color=colors, alpha=0.85, zorder=3, width=0.45)

    for bar, val in zip(bars, amats):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            f"{val:.3f}",
            ha="center", va="bottom",
            color=COLOR["text_primary"], fontsize=9,
            fontfamily="JetBrains Mono",
        )

    ax.set_ylabel("AMAT (cycles)", fontsize=9)
    ax.set_title("Average Memory Access Time", fontsize=11, pad=10)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


def _traffic_pie_chart(metrics: dict) -> FigureCanvas:
    """Pie chart: read vs write traffic per cache."""
    fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.2))
    fig.patch.set_facecolor(COLOR["bg_card"])

    cache_info = [
        ("I-Cache",  "i_cache",  COLOR["accent"]),
        ("D-Cache",  "d_cache",  COLOR["accent_green"]),
        ("L2 Cache", "l2_cache", COLOR["accent_purple"]),
    ]

    for ax, (name, key, color) in zip(axes, cache_info):
        ax.set_facecolor(COLOR["bg_card"])
        m      = metrics.get(key, {})
        reads  = m.get("reads", 0)
        writes = m.get("writes", 0)

        if reads + writes == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=COLOR["text_muted"], transform=ax.transAxes)
            ax.set_title(name, fontsize=10)
            ax.axis("off")
            continue

        sizes  = [reads, writes] if writes > 0 else [reads]
        labels = ["Reads", "Writes"] if writes > 0 else ["Reads"]
        cols   = [color, COLOR["accent_amber"]] if writes > 0 else [color]
        explode = [0.04] * len(sizes)

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=cols,
            autopct="%1.1f%%", startangle=90,
            explode=explode,
            textprops={"fontsize": 8, "color": COLOR["text_secondary"]},
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_color(COLOR["text_primary"])
            at.set_fontsize(8)

        ax.set_title(name, fontsize=10, pad=8)

    fig.suptitle("Read / Write Traffic", fontsize=11, y=1.0)
    fig.tight_layout(pad=1.0)
    return _make_canvas(fig)


def _miss_rate_chart(metrics: dict) -> FigureCanvas:
    """Stacked bar: miss rate breakdown (misses vs hits as %)."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches   = ["I-Cache", "D-Cache", "L2 Cache"]
    keys     = ["i_cache", "d_cache", "l2_cache"]
    hit_rates  = [metrics.get(k, {}).get("hit_rate",  0) for k in keys]
    miss_rates = [metrics.get(k, {}).get("miss_rate", 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.5

    ax.bar(x, hit_rates,  width, label="Hit %",  color=COLOR["accent"],        alpha=0.85, zorder=3)
    ax.bar(x, miss_rates, width, label="Miss %", color=COLOR["accent_red"],    alpha=0.6,  zorder=3,
           bottom=hit_rates)

    ax.set_xticks(x)
    ax.set_xticklabels(caches)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Percentage (%)", fontsize=9)
    ax.set_title("Hit / Miss Rate Breakdown", fontsize=11, pad=10)
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Comparison chart helpers (two runs)
# ─────────────────────────────────────────────────────────────────────────────

def _compare_hit_rate_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="hit_rate",
        title="Hit Rate Comparison",
        y_label="Hit Rate (%)",
        percent=True,
    )


def _compare_amat_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="amat",
        title="AMAT Comparison",
        y_label="AMAT (cycles)",
        percent=False,
    )


def _compare_miss_rate_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="miss_rate",
        title="Miss Rate Comparison",
        y_label="Miss Rate (%)",
        percent=True,
    )


def _compare_total_accesses_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="total_accesses",
        title="Total Accesses Comparison",
        y_label="Access Count",
        percent=False,
        count_axis=True,
    )


def _compare_cache_hits_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="cache_hits",
        title="Cache Hits Comparison",
        y_label="Hit Count",
        percent=False,
        count_axis=True,
    )


def _compare_cache_misses_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    return _compare_metric_chart(
        run_a, run_b,
        metric_key="cache_misses",
        title="Cache Misses Comparison",
        y_label="Miss Count",
        percent=False,
        count_axis=True,
    )


def _compare_metric_chart(
    run_a: dict,
    run_b: dict,
    metric_key: str,
    title: str,
    y_label: str,
    percent: bool,
    count_axis: bool = False,
) -> FigureCanvas:
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches = ["I-Cache", "D-Cache", "L2 Cache"]
    keys   = ["i_cache", "d_cache", "l2_cache"]

    ma = run_a.get("metrics", {})
    mb = run_b.get("metrics", {})

    vals_a = [ma.get(k, {}).get(metric_key, 0) for k in keys]
    vals_b = [mb.get(k, {}).get(metric_key, 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.32

    la = _run_display_name(run_a)[:22]
    lb = _run_display_name(run_b)[:22]

    ax.bar(x - width/2, vals_a, width, label=la, color=COLOR["accent"],       alpha=0.85, zorder=3)
    ax.bar(x + width/2, vals_b, width, label=lb, color=COLOR["accent_amber"], alpha=0.85, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(caches)
    if percent:
        ax.set_ylim(0, 110)
    ax.set_ylabel(y_label, fontsize=9)
    ax.set_title(title, fontsize=11, pad=10)

    if count_axis:
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6
                else f"{v/1e3:.0f}K" if v >= 1e3
                else str(int(v))
            )
        )
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Detailed Metrics Tab
# ─────────────────────────────────────────────────────────────────────────────

class DetailedMetricsTab(QWidget):
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build(result)

    def _build(self, result: dict):
        metrics  = result.get("metrics", {})
        mod_instr = metrics.get("modified_instructions", 0)
        duration  = result.get("duration_s", 0.0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # Summary bar
        lay.addWidget(SummaryBar(metrics, mod_instr, duration))

        # Config recap strip
        cfg_strip = self._make_config_strip(result)
        lay.addWidget(cfg_strip)

        # Three cache cards in a row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        for cache_name, key in [
            ("I-Cache",  "i_cache"),
            ("D-Cache",  "d_cache"),
            ("L2 Cache", "l2_cache"),
        ]:
            cache_data = metrics.get(key, {})
            card = CacheCard(cache_name, cache_data)
            cards_row.addWidget(card)

        lay.addLayout(cards_row)
        lay.addStretch()

        scroll.setWidget(inner)

    def _make_config_strip(self, result: dict) -> QWidget:
        w = QWidget()
        w.setFixedHeight(40)
        w.setStyleSheet(
            f"background-color: {COLOR['bg_elevated']};"
            f"border: 1px solid {COLOR['border_faint']};"
            f"border-radius: 8px;"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        def _size(b):
            if b >= 1_048_576: return f"{b // 1_048_576}M"
            if b >= 1_024:     return f"{b // 1_024}K"
            return str(b)

        items = [
            ("L1 Size",   _size(result.get("l1_size", 0))),
            ("L1 Assoc",  f"{result.get('l1_assoc', '—')}w"),
            ("L2 Size",   _size(result.get("l2_size", 0))),
            ("L2 Assoc",  f"{result.get('l2_assoc', '—')}w"),
            ("Policy",    result.get("policy", "—")),
            ("Prefetch",  result.get("prefetch", "—")),
            ("Trace",     os.path.basename(result.get("trace_filename", "—"))),
        ]

        for i, (k, v) in enumerate(items):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setFixedHeight(20)
                sep.setStyleSheet(f"color: {COLOR['border_dim']}; background: {COLOR['border_dim']};")
                lay.addWidget(sep)
                lay.addSpacing(14)

            pair = QHBoxLayout()
            pair.setSpacing(5)
            pair.addWidget(_label(k, FONT_SIZE["xs"], COLOR["text_muted"]))
            pair.addWidget(_label(v, FONT_SIZE["xs"], COLOR["text_secondary"], mono=True))
            lay.addLayout(pair)

            if i < len(items) - 1:
                lay.addSpacing(14)

        lay.addStretch()
        return w


# ─────────────────────────────────────────────────────────────────────────────
# Visual Metrics Tab
# ─────────────────────────────────────────────────────────────────────────────

class VisualMetricsTab(QWidget):
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build(result)

    def _build(self, result: dict):
        metrics = result.get("metrics", {})

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # Row 1: hit/miss bar + hit rate bar
        row1 = QHBoxLayout()
        row1.setSpacing(14)
        row1.addWidget(self._chart_card(_hit_miss_bar_chart(metrics),  "Hits vs Misses", scroll))
        row1.addWidget(self._chart_card(_hit_rate_bar_chart(metrics),  "Hit Rate (%)", scroll))
        lay.addLayout(row1)

        # Row 2: AMAT + miss rate breakdown
        row2 = QHBoxLayout()
        row2.setSpacing(14)
        row2.addWidget(self._chart_card(_amat_chart(metrics),       "AMAT per Cache", scroll))
        row2.addWidget(self._chart_card(_miss_rate_chart(metrics),  "Hit/Miss Stacked", scroll))
        lay.addLayout(row2)

        # Row 3: full-width traffic pie
        lay.addWidget(self._chart_card(_traffic_pie_chart(metrics), "Read/Write Traffic", scroll, full=True))

        lay.addStretch()
        scroll.setWidget(inner)

    def _chart_card(self, canvas: FigureCanvas, title: str, scroll: QScrollArea, full: bool = False) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border: 1px solid {COLOR['border_faint']};"
            f"border-radius: 10px;"
        )
        if full:
            card.setMinimumHeight(300)
        else:
            card.setMinimumHeight(280)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        _attach_chart_interactions(canvas, self, scroll)
        lay.addWidget(canvas)
        return card


# ─────────────────────────────────────────────────────────────────────────────
# Compare Tab (two runs side by side)
# ─────────────────────────────────────────────────────────────────────────────

class CompareTab(QWidget):
    def __init__(self, run_a: dict, run_b: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._build(run_a, run_b)

    def _build(self, run_a: dict, run_b: dict):
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # Fixed run headers: always visible while tab contents scroll.
        header_wrap = QWidget()
        header_wrap.setFixedHeight(78)
        header_wrap.setStyleSheet(
            f"background-color: {COLOR['bg_deep']};"
            f"border-bottom: 1px solid {COLOR['border_faint']};"
        )
        hdr = QHBoxLayout(header_wrap)
        hdr.setContentsMargins(24, 12, 24, 12)
        hdr.setSpacing(14)
        hdr.addWidget(self._run_header(run_a))
        hdr.addWidget(self._run_header(run_b))
        outer_lay.addWidget(header_wrap)

        tabs = QTabWidget()
        tabs.addTab(self._build_detailed_compare_tab(run_a, run_b), "Detailed Metrics")
        tabs.addTab(self._build_visual_compare_tab(run_a, run_b), "Visual Metrics")
        outer_lay.addWidget(tabs, 1)

    def _run_header(self, run: dict) -> QWidget:
        w = QWidget()
        w.setFixedHeight(64)
        w.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border: 1px solid {COLOR['border_faint']};"
            f"border-radius: 8px;"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        vlay = QVBoxLayout()
        vlay.setSpacing(3)
        cfg = (
            f"L1:{run.get('l1_size', 0)//1024 if run.get('l1_size', 0) >= 1024 else run.get('l1_size', 0)}"
            f"K/{run.get('l1_assoc', '?')}w  "
            f"L2:{run.get('l2_size', 0)//1048576 if run.get('l2_size', 0) >= 1048576 else run.get('l2_size', 0)}"
            f"M/{run.get('l2_assoc', '?')}w"
        )
        run_title = _run_display_name(run)
        if not run.get("label"):
            run_title = f"{run_title}  —  {cfg}"
        name = _label(run_title, FONT_SIZE["sm"], COLOR["text_primary"], bold=True)
        name.setWordWrap(True)
        vlay.addWidget(name)

        trace = _label(
            f"📄 {run.get('trace_filename','—')}  ·  {run.get('trace_summary','')}",
            FONT_SIZE["xs"], COLOR["text_muted"]
        )
        vlay.addWidget(trace)
        lay.addLayout(vlay, 1)

        ts = _label(run.get("timestamp", "")[:19], FONT_SIZE["xs"], COLOR["text_muted"])
        ts.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(ts)
        return w

    def _build_detailed_compare_tab(self, run_a: dict, run_b: dict) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 16, 24, 24)
        lay.setSpacing(16)

        for cache_name, key in [
            ("I-Cache",  "i_cache"),
            ("D-Cache",  "d_cache"),
            ("L2 Cache", "l2_cache"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(14)
            row.addWidget(CacheCard(cache_name, run_a.get("metrics", {}).get(key, {})))
            row.addWidget(CacheCard(cache_name, run_b.get("metrics", {}).get(key, {})))
            lay.addLayout(row)

        lay.addStretch()
        scroll.setWidget(inner)
        return tab

    def _build_visual_compare_tab(self, run_a: dict, run_b: dict) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(24, 16, 24, 24)
        lay.setSpacing(14)

        row1 = QHBoxLayout()
        row1.setSpacing(14)
        row1.addWidget(self._chart_card(_compare_hit_rate_chart(run_a, run_b), scroll))
        row1.addWidget(self._chart_card(_compare_miss_rate_chart(run_a, run_b), scroll))
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(14)
        row2.addWidget(self._chart_card(_compare_amat_chart(run_a, run_b), scroll))
        row2.addWidget(self._chart_card(_compare_total_accesses_chart(run_a, run_b), scroll))
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(14)
        row3.addWidget(self._chart_card(_compare_cache_hits_chart(run_a, run_b), scroll))
        row3.addWidget(self._chart_card(_compare_cache_misses_chart(run_a, run_b), scroll))
        lay.addLayout(row3)

        lay.addStretch()
        scroll.setWidget(inner)
        return tab

    def _chart_card(self, canvas: FigureCanvas, scroll: QScrollArea) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border: 1px solid {COLOR['border_faint']};"
            f"border-radius: 10px;"
        )
        card.setMinimumHeight(300)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(14, 12, 14, 12)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        _attach_chart_interactions(canvas, self, scroll)
        c_lay.addWidget(canvas)
        return card


class SingleRunTab(QWidget):
    """Per-run tab that keeps both detailed and visual metrics available."""
    def __init__(self, run: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(DetailedMetricsTab(run), "Detailed Metrics")
        tabs.addTab(VisualMetricsTab(run),   "Visual Metrics")
        lay.addWidget(tabs)


# ─────────────────────────────────────────────────────────────────────────────
# Main Results Panel
# ─────────────────────────────────────────────────────────────────────────────

class ResultsPanel(QWidget):
    """
    Screen 2. Contains the tab bar (Detailed / Visual / Compare if active)
    and a top bar with the run label + "New Simulation" back button.
    """
    new_simulation_requested = pyqtSignal()
    compare_runs_requested   = pyqtSignal(dict, dict)
    run_renamed              = pyqtSignal(dict)
    run_deleted              = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result: Optional[dict] = None
        self._in_compare_mode = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(94)
        top_bar.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-bottom: none;"
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 10, 24, 10)
        tb_lay.setSpacing(0)

        left_actions = QWidget()
        left_actions.setFixedWidth(340)
        la_lay = QHBoxLayout(left_actions)
        la_lay.setContentsMargins(0, 0, 0, 0)
        la_lay.setSpacing(12)

        back_btn = QPushButton("← New Simulation")
        back_btn.setObjectName("ghostBtn")
        back_btn.setFont(QFont("DM Sans", FONT_SIZE["sm"]))
        back_btn.setFixedHeight(44)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"border: none;"
            f"background: transparent;"
            f"padding: 0 12px;"
            f"border-radius: 8px;"
        )
        back_btn.clicked.connect(self.new_simulation_requested.emit)
        la_lay.addWidget(back_btn)

        self._compare_btn = QPushButton("Compare Runs")
        self._compare_btn.setObjectName("ghostBtn")
        self._compare_btn.setFont(QFont("DM Sans", FONT_SIZE["sm"]))
        self._compare_btn.setFixedHeight(44)
        self._compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compare_btn.setStyleSheet(
            f"border: none;"
            f"background: transparent;"
            f"padding: 0 12px;"
            f"border-radius: 8px;"
        )
        self._compare_btn.clicked.connect(self._open_compare_picker)
        la_lay.addWidget(self._compare_btn)
        la_lay.addStretch()

        center_block = QWidget()
        cb_lay = QVBoxLayout(center_block)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setSpacing(4)

        self._run_label = _label(
            "Simulation Results", FONT_SIZE["lg"],
            COLOR["text_primary"], bold=True,
            align=Qt.AlignmentFlag.AlignCenter
        )
        self._run_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_lay.addWidget(self._run_label)

        self._trace_lbl = _label("", FONT_SIZE["xs"], COLOR["text_muted"])
        self._trace_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_lay.addWidget(self._trace_lbl)

        right_actions = QWidget()
        right_actions.setFixedWidth(220)
        ra_lay = QHBoxLayout(right_actions)
        ra_lay.setContentsMargins(0, 0, 0, 0)
        ra_lay.setSpacing(12)
        ra_lay.addStretch()

        self._rename_btn = QPushButton("Rename")
        self._rename_btn.setObjectName("ghostBtn")
        self._rename_btn.setFont(QFont("DM Sans", FONT_SIZE["sm"]))
        self._rename_btn.setFixedHeight(44)
        self._rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rename_btn.setStyleSheet(
            f"border: none;"
            f"background: transparent;"
            f"padding: 0 12px;"
            f"border-radius: 8px;"
        )
        self._rename_btn.clicked.connect(self._rename_current_run)
        ra_lay.addWidget(self._rename_btn)

        tb_lay.addWidget(left_actions, 0, Qt.AlignmentFlag.AlignVCenter)
        tb_lay.addStretch(1)
        tb_lay.addWidget(center_block, 0, Qt.AlignmentFlag.AlignVCenter)
        tb_lay.addStretch(1)
        tb_lay.addWidget(right_actions, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(top_bar)

        # ── Tab widget ─────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane {{"
            f"  border: none;"
            f"  background-color: {COLOR['bg_deep']};"
            f"}}"
            f"QTabBar::tab {{"
            f"  background-color: transparent;"
            f"  color: {COLOR['text_secondary']};"
            f"  border: none;"
            f"  border-bottom: 2px solid transparent;"
            f"  padding: 10px 24px;"
            f"  font-family: 'DM Sans';"
            f"  font-size: 14px;"
            f"  font-weight: 500;"
            f"  margin-right: 2px;"
            f"}}"
            f"QTabBar::tab:selected {{"
            f"  color: {COLOR['accent']};"
            f"  border-bottom: 2px solid {COLOR['accent']};"
            f"  background-color: transparent;"
            f"}}"
            f"QTabBar::tab:hover:!selected {{"
            f"  color: {COLOR['text_primary']};"
            f"  border-bottom: 2px solid {COLOR['border_mid']};"
            f"}}"
            f"QTabWidget QWidget {{"
            f"  background-color: {COLOR['bg_deep']};"
            f"}}"
        )
        root.addWidget(self._tabs, 1)

    # ── Public API ──────────────────────────────────────────────────────────
    def show_result(self, result: dict):
        """Load a single run's results into the panel."""
        self._in_compare_mode = False
        self._tabs.tabBar().setVisible(True)
        self._current_result = result
        self._run_label.setText(_run_display_name(result))
        self._trace_lbl.setText(
            f"📄 {result.get('trace_filename','—')}  ·  {result.get('trace_summary','')}"
        )
        self._sync_compare_button_state()
        self._sync_run_action_buttons()
        self._populate_tabs(result)

    def show_comparison(self, run_a: dict, run_b: dict):
        """Load a side-by-side comparison of two runs."""
        self._in_compare_mode = True
        self._tabs.tabBar().setVisible(True)
        self._current_result = None
        self._run_label.setText("Comparison View")
        self._trace_lbl.setText("")
        self._sync_compare_button_state()
        self._sync_run_action_buttons()
        self._tabs.clear()

        self._tabs.addTab(CompareTab(run_a, run_b), "⚖  Compare")
        self._tabs.addTab(SingleRunTab(run_a), f"Run A — {_run_display_name(run_a)}")
        self._tabs.addTab(SingleRunTab(run_b), f"Run B — {_run_display_name(run_b)}")

    def _populate_tabs(self, result: dict):
        self._tabs.clear()
        self._tabs.addTab(DetailedMetricsTab(result), "📊  Detailed Metrics")
        self._tabs.addTab(VisualMetricsTab(result),   "📈  Visual Metrics")
        self._tabs.setCurrentIndex(1)

    def show_empty_state(self):
        self._in_compare_mode = False
        self._current_result = None
        self._run_label.setText("No Saved Runs")
        self._trace_lbl.setText("")
        self._sync_compare_button_state()
        self._sync_run_action_buttons()
        self._tabs.clear()

        empty = QWidget()
        lay = QVBoxLayout(empty)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        msg = QLabel("No simulations saved in history.\nRun a new simulation to populate results.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setFont(QFont("Inter", FONT_SIZE["md"]))
        msg.setStyleSheet(f"color: {COLOR['text_muted']}; background: transparent;")
        lay.addWidget(msg)

        self._tabs.addTab(empty, "")
        self._tabs.tabBar().setVisible(False)

    def _sync_compare_button_state(self):
        self._compare_btn.setEnabled(db.get_run_count() >= 2)

    def _sync_run_action_buttons(self):
        enabled = self._current_result is not None and not self._in_compare_mode
        self._rename_btn.setEnabled(enabled)

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

    def _show_info_dialog(self, title: str, message: str):
        dlg = self._new_dialog(title, 400)
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
        yes_btn.setObjectName("compareBtn")
        no_btn = QPushButton("Cancel")
        no_btn.setObjectName("ghostBtn")
        row.addWidget(yes_btn)
        row.addWidget(no_btn)
        lay.addLayout(row)

        yes_btn.clicked.connect(dlg.accept)
        no_btn.clicked.connect(dlg.reject)

        return dlg.exec() == QDialog.DialogCode.Accepted

    def _rename_current_run(self):
        if not self._current_result:
            return
        run_id = int(self._current_result.get("id", 0))
        if run_id <= 0:
            return

        new_name, ok = self._show_text_input_dialog(
            "Rename Simulation",
            "New name:",
            self._current_result.get("label", ""),
        )
        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            return

        if db.rename_run(run_id, new_name):
            updated = db.get_run_by_id(run_id)
            if updated:
                self.show_result(updated)
                self.run_renamed.emit(updated)

    def _delete_current_run(self):
        if not self._current_result:
            return
        run_id = int(self._current_result.get("id", 0))
        if run_id <= 0:
            return

        label = _run_display_name(self._current_result)
        if not self._show_confirm_dialog(
            "Delete Simulation",
            f"Delete {label}?\nThis cannot be undone.",
            "Delete",
        ):
            return

        if db.delete_run(run_id):
            self.run_deleted.emit(run_id)

    def _open_compare_picker(self):
        runs = db.get_all_runs()
        if len(runs) < 2:
            return

        dlg = self._new_dialog("Compare Runs", 360)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lbl = QLabel("Select two runs to compare")
        lbl.setFont(QFont("Inter", FONT_SIZE["sm"], QFont.Weight.Medium))
        lbl.setStyleSheet(f"color: {COLOR['text_primary']}; background: transparent;")
        lay.addWidget(lbl)

        combo_a = QComboBox()
        combo_b = QComboBox()
        combo_a.setFont(QFont("Inter", FONT_SIZE["sm"]))
        combo_b.setFont(QFont("Inter", FONT_SIZE["sm"]))

        for run in runs:
            text = _run_display_name(run)
            combo_a.addItem(text, run["id"])
            combo_b.addItem(text, run["id"])

        if combo_b.count() > 1:
            combo_b.setCurrentIndex(1)

        lay.addWidget(QLabel("Run A"))
        lay.addWidget(combo_a)
        lay.addWidget(QLabel("Run B"))
        lay.addWidget(combo_b)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        lay.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        id_a = combo_a.currentData()
        id_b = combo_b.currentData()
        if id_a == id_b:
            self._show_info_dialog("Compare Runs", "Please choose two different runs.")
            return

        run_a = db.get_run_by_id(int(id_a))
        run_b = db.get_run_by_id(int(id_b))
        if not run_a or not run_b:
            self._show_info_dialog("Compare Runs", "Unable to load selected runs.")
            return

        self.compare_runs_requested.emit(run_a, run_b)