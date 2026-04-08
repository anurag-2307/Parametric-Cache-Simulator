# theme.py
# ─────────────────────────────────────────────────────────────────────────────
# Design Language: "Clean Slate" — near-black base, single blue accent,
# large readable fonts, zero gradients, zero glow. Looks like a real tool.
# ─────────────────────────────────────────────────────────────────────────────

COLOR = {
    # Backgrounds
    "bg_deep":      "#0D0D0D",
    "bg_base":      "#111111",
    "bg_card":      "#1A1A1A",
    "bg_elevated":  "#222222",
    "bg_selected":  "#1E2A3A",

    # Borders
    "border_faint": "#1F1F1F",
    "border_dim":   "#2A2A2A",
    "border_mid":   "#3A3A3A",
    "border_bright":"#4A4A4A",

    # Single accent — clean blue
    "accent":       "#3B82F6",
    "accent_dim":   "#1D4ED8",
    "accent_glow":  "#93C5FD",

    # Semantic
    "accent_green": "#22C55E",
    "accent_red":   "#EF4444",
    "accent_amber": "#F59E0B",
    "accent_purple":"#A78BFA",

    # Text
    "text_primary":  "#FAFAFA",
    "text_secondary":"#CFCFCF",
    "text_muted":    "#9A9A9A",
    "text_accent":   "#3B82F6",
    "text_mono":     "#D0D0D0",

    # Graph palette
    "graph_1":  "#3B82F6",
    "graph_2":  "#22C55E",
    "graph_3":  "#F59E0B",
    "graph_4":  "#EF4444",
    "graph_5":  "#A78BFA",
    "graph_6":  "#EC4899",
}

FONT = {
    "display":  "Inter",
    "body":     "Inter",
    "mono":     "JetBrains Mono",
    "fallback": "Consolas",
}

FONT_SIZE = {
    "xs":   11,
    "sm":   12,
    "base": 13,
    "md":   14,
    "lg":   16,
    "xl":   18,
    "2xl":  22,
    "3xl":  28,
}


def get_stylesheet() -> str:
    c = COLOR
    return f"""
/* ── Base ── */
QMainWindow, QWidget {{
    background-color: {c['bg_deep']};
    color: {c['text_primary']};
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {c['border_mid']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['border_bright']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 5px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border_mid']};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── ComboBox ── */
QComboBox {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_dim']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {c['border_mid']}; }}
QComboBox:focus {{ border-color: {c['accent']}; }}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_secondary']};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border_mid']};
    border-radius: 6px;
    selection-background-color: {c['bg_selected']};
    selection-color: {c['accent']};
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 7px 12px;
    min-height: 26px;
    border-radius: 4px;
}}

/* ── LineEdit ── */
QLineEdit {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_dim']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}
QLineEdit:hover {{ border-color: {c['border_mid']}; }}
QLineEdit:focus {{ border-color: {c['accent']}; }}

/* ── PushButton base ── */
QPushButton {{
    background-color: {c['bg_elevated']};
    color: {c['text_primary']};
    border: 1px solid {c['border_dim']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['bg_card']};
    border-color: {c['border_mid']};
}}
QPushButton:pressed {{ background-color: {c['bg_base']}; }}
QPushButton:disabled {{
    color: {c['text_muted']};
    border-color: {c['border_faint']};
    background-color: {c['bg_base']};
}}

/* ── Primary button ── */
QPushButton#primaryBtn {{
    background-color: {c['accent']};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 12px 32px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{ background-color: #2563EB; }}
QPushButton#primaryBtn:pressed {{ background-color: {c['accent_dim']}; }}
QPushButton#primaryBtn:disabled {{
    background-color: {c['bg_elevated']};
    color: {c['text_muted']};
}}

/* ── Ghost button ── */
QPushButton#ghostBtn {{
    background-color: transparent;
    color: {c['text_secondary']};
    border: 1px solid {c['border_dim']};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 11px;
}}
QPushButton#ghostBtn:hover {{
    color: {c['text_primary']};
    border-color: {c['border_mid']};
    background-color: {c['bg_elevated']};
}}

/* ── Compare button ── */
QPushButton#compareBtn {{
    background-color: transparent;
    color: {c['accent_amber']};
    border: 1px solid {c['accent_amber']};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 500;
}}
QPushButton#compareBtn:hover {{
    background-color: rgba(245,158,11,0.1);
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: none;
    background-color: {c['bg_deep']};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c['text_secondary']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 22px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    color: {c['text_primary']};
    border-bottom: 2px solid {c['accent']};
}}
QTabBar::tab:hover:!selected {{ color: {c['text_primary']}; }}

/* ── Labels ── */
QLabel {{
    color: {c['text_primary']};
    background: transparent;
}}

/* ── Separators ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {c['border_faint']};
    background-color: {c['border_faint']};
    border: none;
}}

/* ── ToolTip ── */
QToolTip {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
    border: 1px solid {c['border_mid']};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 11px;
}}

/* ── List Widget ── */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{ border-radius: 6px; margin: 2px; }}
QListWidget::item:selected {{
    background-color: {c['bg_selected']};
    color: {c['accent']};
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {c['bg_elevated']};
    border: none;
    border-radius: 3px;
    height: 4px;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 3px;
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {c['text_secondary']};
    spacing: 8px;
    font-size: 11px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {c['border_dim']};
    border-radius: 4px;
    background: {c['bg_elevated']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
}}

/* ── Dialogs ── */
QDialog, QMessageBox, QInputDialog {{
    background-color: {c['bg_card']};
}}
"""


CARD_STYLE = f"""
    background-color: {COLOR['bg_card']};
    border: 1px solid {COLOR['border_faint']};
    border-radius: 8px;
"""

PANEL_STYLE = f"""
    background-color: {COLOR['bg_base']};
    border-right: 1px solid {COLOR['border_faint']};
"""

MPL_STYLE = {
    "figure.facecolor":   COLOR["bg_card"],
    "axes.facecolor":     COLOR["bg_elevated"],
    "axes.edgecolor":     COLOR["border_dim"],
    "axes.labelcolor":    COLOR["text_secondary"],
    "axes.titlecolor":    COLOR["text_primary"],
    "axes.titlesize":     12,
    "axes.labelsize":     10,
    "axes.grid":          True,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "grid.color":         COLOR["border_faint"],
    "grid.linewidth":     0.8,
    "grid.alpha":         0.6,
    "xtick.color":        COLOR["text_secondary"],
    "ytick.color":        COLOR["text_secondary"],
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.facecolor":   COLOR["bg_card"],
    "legend.edgecolor":   COLOR["border_dim"],
    "legend.labelcolor":  COLOR["text_secondary"],
    "legend.fontsize":    9,
    "text.color":         COLOR["text_primary"],
    "font.family":        ["Inter", "Segoe UI", "sans-serif"],
    "lines.linewidth":    2.0,
    "patch.linewidth":    0.5,
    "figure.dpi":         96,
}

GRAPH_COLORS = [
    COLOR["graph_1"],
    COLOR["graph_2"],
    COLOR["graph_3"],
    COLOR["graph_4"],
    COLOR["graph_5"],
    COLOR["graph_6"],
]