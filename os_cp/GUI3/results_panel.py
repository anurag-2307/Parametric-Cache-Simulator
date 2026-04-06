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
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from theme import COLOR, FONT_SIZE, MPL_STYLE, GRAPH_COLORS


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
    colors_h = [COLOR["accent"], COLOR["accent_green"], COLOR["accent_purple"]]

    hit_rates  = [metrics.get(k, {}).get("hit_rate",  0) for k in keys]
    miss_rates = [metrics.get(k, {}).get("miss_rate", 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.5

    ax.bar(x, hit_rates,  width, label="Hit %",  color=colors_h,               alpha=0.85, zorder=3)
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
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches = ["I-Cache", "D-Cache", "L2 Cache"]
    keys   = ["i_cache", "d_cache", "l2_cache"]

    ma = run_a.get("metrics", {})
    mb = run_b.get("metrics", {})

    rates_a = [ma.get(k, {}).get("hit_rate", 0) for k in keys]
    rates_b = [mb.get(k, {}).get("hit_rate", 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.32

    la = run_a.get("label", "Run A")[:22]
    lb = run_b.get("label", "Run B")[:22]

    ax.bar(x - width/2, rates_a, width, label=la, color=COLOR["accent"],       alpha=0.85, zorder=3)
    ax.bar(x + width/2, rates_b, width, label=lb, color=COLOR["accent_amber"], alpha=0.85, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(caches)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Hit Rate (%)", fontsize=9)
    ax.set_title("Hit Rate Comparison", fontsize=11, pad=10)
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.2)
    return _make_canvas(fig)


def _compare_amat_chart(run_a: dict, run_b: dict) -> FigureCanvas:
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(COLOR["bg_card"])
    ax.set_facecolor(COLOR["bg_elevated"])

    caches = ["I-Cache", "D-Cache", "L2 Cache"]
    keys   = ["i_cache", "d_cache", "l2_cache"]

    ma = run_a.get("metrics", {})
    mb = run_b.get("metrics", {})

    amats_a = [ma.get(k, {}).get("amat", 0) for k in keys]
    amats_b = [mb.get(k, {}).get("amat", 0) for k in keys]

    x     = np.arange(len(caches))
    width = 0.32

    la = run_a.get("label", "Run A")[:22]
    lb = run_b.get("label", "Run B")[:22]

    ax.bar(x - width/2, amats_a, width, label=la, color=COLOR["accent"],       alpha=0.85, zorder=3)
    ax.bar(x + width/2, amats_b, width, label=lb, color=COLOR["accent_amber"], alpha=0.85, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(caches)
    ax.set_ylabel("AMAT (cycles)", fontsize=9)
    ax.set_title("AMAT Comparison", fontsize=11, pad=10)
    ax.legend(framealpha=0.2)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

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
        row1.addWidget(self._chart_card(_hit_miss_bar_chart(metrics),  "Hits vs Misses"))
        row1.addWidget(self._chart_card(_hit_rate_bar_chart(metrics),  "Hit Rate (%)"))
        lay.addLayout(row1)

        # Row 2: AMAT + miss rate breakdown
        row2 = QHBoxLayout()
        row2.setSpacing(14)
        row2.addWidget(self._chart_card(_amat_chart(metrics),       "AMAT per Cache"))
        row2.addWidget(self._chart_card(_miss_rate_chart(metrics),  "Hit/Miss Stacked"))
        lay.addLayout(row2)

        # Row 3: full-width traffic pie
        lay.addWidget(self._chart_card(_traffic_pie_chart(metrics), "Read/Write Traffic", full=True))

        lay.addStretch()
        scroll.setWidget(inner)

    def _chart_card(self, canvas: FigureCanvas, title: str, full: bool = False) -> QWidget:
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
        lay.setSpacing(18)

        # ── Run headers ────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(14)
        hdr.addWidget(self._run_header(run_a, COLOR["accent"]))
        hdr.addWidget(self._run_header(run_b, COLOR["accent_amber"]))
        lay.addLayout(hdr)

        # ── Side-by-side stat tables ────────────────────────────────────────
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

        # ── Comparison charts ───────────────────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)

        for canvas, title in [
            (_compare_hit_rate_chart(run_a, run_b), "Hit Rate Comparison"),
            (_compare_amat_chart(run_a, run_b),     "AMAT Comparison"),
        ]:
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
            c_lay.addWidget(canvas)
            charts_row.addWidget(card)

        lay.addLayout(charts_row)
        lay.addStretch()
        scroll.setWidget(inner)

    def _run_header(self, run: dict, accent: str) -> QWidget:
        w = QWidget()
        w.setFixedHeight(64)
        w.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border: 1px solid {COLOR['border_faint']};"
            f"border-left: 3px solid {accent};"
            f"border-radius: 8px;"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        vlay = QVBoxLayout()
        vlay.setSpacing(3)
        name = _label(run.get("label", "Run"), FONT_SIZE["sm"], accent, bold=True)
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


# ─────────────────────────────────────────────────────────────────────────────
# Main Results Panel
# ─────────────────────────────────────────────────────────────────────────────

class ResultsPanel(QWidget):
    """
    Screen 2. Contains the tab bar (Detailed / Visual / Compare if active)
    and a top bar with the run label + "New Simulation" back button.
    """
    new_simulation_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result: Optional[dict] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(
            f"background-color: {COLOR['bg_base']};"
            f"border-bottom: 1px solid {COLOR['border_faint']};"
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 0, 24, 0)
        tb_lay.setSpacing(14)

        back_btn = QPushButton("← New Simulation")
        back_btn.setObjectName("ghostBtn")
        back_btn.setFont(QFont("DM Sans", FONT_SIZE["sm"]))
        back_btn.setFixedHeight(32)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.new_simulation_requested.emit)
        tb_lay.addWidget(back_btn)

        self._run_label = _label(
            "Simulation Results", FONT_SIZE["md"],
            COLOR["text_primary"], bold=True
        )
        tb_lay.addWidget(self._run_label)
        tb_lay.addStretch()

        self._trace_lbl = _label("", FONT_SIZE["xs"], COLOR["text_muted"])
        self._trace_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tb_lay.addWidget(self._trace_lbl)

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
            f"  font-size: 12px;"
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
        self._current_result = result
        self._run_label.setText(result.get("label", "Simulation Results"))
        self._trace_lbl.setText(
            f"📄 {result.get('trace_filename','—')}  ·  {result.get('trace_summary','')}"
        )
        self._populate_tabs(result)

    def show_comparison(self, run_a: dict, run_b: dict):
        """Load a side-by-side comparison of two runs."""
        self._run_label.setText("Comparison View")
        self._trace_lbl.setText("")
        self._tabs.clear()

        self._tabs.addTab(CompareTab(run_a, run_b), "⚖  Compare")
        self._tabs.addTab(DetailedMetricsTab(run_a), f"Run A — {run_a.get('label','')[:24]}")
        self._tabs.addTab(DetailedMetricsTab(run_b), f"Run B — {run_b.get('label','')[:24]}")

    def _populate_tabs(self, result: dict):
        self._tabs.clear()
        self._tabs.addTab(DetailedMetricsTab(result), "📊  Detailed Metrics")
        self._tabs.addTab(VisualMetricsTab(result),   "📈  Visual Metrics")