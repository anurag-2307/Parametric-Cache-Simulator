# ui/app_window.py
import customtkinter as ctk
from customtkinter import filedialog
import threading
import os
import re
import json
from datetime import datetime
from core.simulator import SimulatorRunner

try:
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from tkinterdnd2 import DND_FILES  # type: ignore
except ImportError:
    DND_FILES = None

FONT_FAMILY = "Calibri"
HISTORY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "simulation_history.json")
)


class MainView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#0b1220")

        self.simulator = SimulatorRunner()
        self.settings_vars = {}
        self.graph_canvas = None
        self.history_runs = []
        self.history_lookup = {}
        self.current_run_record = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_shell()
        self._build_left_configuration_panel()
        self._build_right_workspace_panel()
        self._bind_trace_entry_updates()
        self._load_history_runs()
        self._refresh_history_controls()

    def _build_shell(self):
        self.topbar = ctk.CTkFrame(self, height=68, corner_radius=0, fg_color="#111827")
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)
        self.topbar.grid_columnconfigure(1, weight=0)
        self.topbar.grid_propagate(False)

        title_wrap = ctk.CTkFrame(self.topbar, fg_color="transparent")
        title_wrap.grid(row=0, column=0, sticky="w", padx=20)
        ctk.CTkLabel(
            title_wrap,
            text="Cache Simulator Workbench",
            font=(FONT_FAMILY, 24, "bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(
            title_wrap,
            text="Configure, run, and analyze cache simulations in one place",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
        ).pack(anchor="w", pady=(0, 10))

        self.status_pill = ctk.CTkLabel(
            self.topbar,
            text="READY",
            width=88,
            height=30,
            corner_radius=15,
            fg_color="#0f766e",
            text_color="#e2e8f0",
            font=(FONT_FAMILY, 12, "bold"),
        )
        self.status_pill.grid(row=0, column=1, padx=20, pady=16, sticky="e")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=14, pady=14)
        self.content.grid_columnconfigure(0, weight=0)
        self.content.grid_columnconfigure(1, weight=1)
        self.content.grid_columnconfigure(2, weight=0)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_left_configuration_panel(self):
        self.config_frame = ctk.CTkFrame(
            self.content,
            width=380,
            corner_radius=16,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
        )
        self.config_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self.config_frame.grid_propagate(False)

        ctk.CTkLabel(
            self.config_frame,
            text="Simulation Settings",
            font=(FONT_FAMILY, 21, "bold"),
            text_color="#f8fafc",
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            self.config_frame,
            text="Choose cache architecture and execution parameters",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        self.form_card = ctk.CTkFrame(
            self.config_frame,
            fg_color="#0f172a",
            corner_radius=12,
            border_width=1,
            border_color="#1e293b",
        )
        self.form_card.pack(fill="x", padx=16, pady=(0, 10))

        self.create_dropdown("L1 Cache Size", "l1_size", ["8192", "16384", "32768", "65536"])
        self.create_dropdown("L1 Associativity", "l1_assoc", ["1", "2", "4", "8"])
        self.create_dropdown("L2 Cache Size", "l2_size", ["262144", "524288", "1048576", "2097152"])
        self.create_dropdown("L2 Associativity", "l2_assoc", ["4", "8", "16", "32"])
        self.create_dropdown("Replacement Policy", "policy", ["LRU", "FIFO", "LFU", "Random"])
        self.create_dropdown("Prefetching", "prefetch", ["ON", "OFF"])

        trace_section = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        trace_section.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(
            trace_section,
            text="Trace File",
            font=(FONT_FAMILY, 13, "bold"),
            text_color="#e2e8f0",
        ).pack(anchor="w", pady=(0, 4))

        self.file_entry = ctk.CTkEntry(
            trace_section,
            height=36,
            placeholder_text="Select a trace file...",
            border_color="#334155",
            fg_color="#111827",
            font=(FONT_FAMILY, 13),
        )
        self.file_entry.pack(fill="x", pady=(0, 8))

        self.drop_hint_label = ctk.CTkLabel(
            trace_section,
            text="You can browse or drag-and-drop a trace file here.",
            font=(FONT_FAMILY, 11),
            text_color="#64748b",
        )
        self.drop_hint_label.pack(anchor="w", pady=(0, 8))

        self.browse_btn = ctk.CTkButton(
            trace_section,
            text="Browse Trace File",
            height=34,
            fg_color="#1d4ed8",
            hover_color="#1e40af",
            command=self.browse_file,
            font=(FONT_FAMILY, 13, "bold"),
        )
        self.browse_btn.pack(fill="x")

        self._enable_drag_drop()

        self.validation_label = ctk.CTkLabel(
            self.config_frame,
            text="",
            text_color="#ef4444",
            font=(FONT_FAMILY, 12),
            justify="left",
            wraplength=330,
        )
        self.validation_label.pack(anchor="w", padx=20, pady=(8, 2))

        self.run_btn = ctk.CTkButton(
            self.config_frame,
            text="Compile and Run Simulation",
            height=42,
            font=(FONT_FAMILY, 15, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            command=self.start_simulation_thread,
        )
        self.run_btn.pack(fill="x", padx=16, pady=(8, 16))

    def _build_right_workspace_panel(self):
        self.dashboard_frame = ctk.CTkFrame(
            self.content,
            corner_radius=16,
            fg_color="#121a2e",
            border_width=1,
            border_color="#23304d",
        )
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.dashboard_frame,
            text="Analysis Workspace",
            font=(FONT_FAMILY, 24, "bold"),
            text_color="#f8fafc",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            self.dashboard_frame,
            text="Run simulation to populate this workspace with processed results.",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        center_panel = ctk.CTkFrame(
            self.dashboard_frame,
            corner_radius=12,
            fg_color="#0f172a",
            border_width=1,
            border_color="#1e293b",
        )
        center_panel.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        center_panel.grid_columnconfigure(0, weight=1)
        center_panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            center_panel,
            text="Simulation Analysis",
            font=(FONT_FAMILY, 15, "bold"),
            text_color="#e2e8f0",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        self.run_summary_label = ctk.CTkLabel(
            center_panel,
            text="No run yet. Configure settings and run the simulator.",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
            anchor="w",
        )
        self.run_summary_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.analysis_tabs = ctk.CTkTabview(
            center_panel,
            fg_color="#0b132b",
            segmented_button_fg_color="#111827",
            segmented_button_selected_color="#1d4ed8",
            segmented_button_selected_hover_color="#1e40af",
            segmented_button_unselected_color="#1f2937",
            segmented_button_unselected_hover_color="#334155",
            border_width=1,
            border_color="#1e293b",
        )
        self.analysis_tabs.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.analysis_tabs.add("Detailed Metrics")
        self.analysis_tabs.add("Visual Metrics")

        self.metrics_tab = self.analysis_tabs.tab("Detailed Metrics")
        self.metrics_tab.grid_columnconfigure(0, weight=1)
        self.metrics_tab.grid_rowconfigure(2, weight=1)

        self.visual_tab = self.analysis_tabs.tab("Visual Metrics")
        self.visual_tab.grid_columnconfigure(0, weight=1)
        self.visual_tab.grid_rowconfigure(1, weight=1)

        kpi_row = ctk.CTkFrame(self.metrics_tab, fg_color="transparent")
        kpi_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(6, 8))
        kpi_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.l1_miss_rate_label = self._create_kpi_item(kpi_row, "L1 Miss Rate", "-- %", 0)
        self.l2_miss_rate_label = self._create_kpi_item(kpi_row, "L2 Miss Rate", "-- %", 1)
        self.total_time_label = self._create_kpi_item(kpi_row, "L2 AMAT", "--", 2)

        self.comparison_summary_label = ctk.CTkLabel(
            self.metrics_tab,
            text="I/D Balance: --   |   D-Write Intensity: --   |   L2 per L1 Miss: --",
            font=(FONT_FAMILY, 12),
            text_color="#93c5fd",
            anchor="w",
            justify="left",
        )
        self.comparison_summary_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))

        self.graph_title = ctk.CTkLabel(
            self.visual_tab,
            text="Visual Performance Analytics",
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#e2e8f0",
        )
        self.graph_title.grid(row=0, column=0, sticky="w", padx=14, pady=(8, 4))

        self.graph_host = ctk.CTkFrame(
            self.visual_tab,
            corner_radius=10,
            fg_color="#0b132b",
            border_width=1,
            border_color="#1e293b",
        )
        self.graph_host.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.graph_host.grid_rowconfigure(0, weight=1)
        self.graph_host.grid_columnconfigure(0, weight=1)

        self.graph_placeholder = ctk.CTkLabel(
            self.graph_host,
            text="Run a simulation to generate performance graphs.",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
        )
        self.graph_placeholder.grid(row=0, column=0)

        self.detail_grid = ctk.CTkFrame(self.metrics_tab, fg_color="transparent")
        self.detail_grid.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 10))
        self.detail_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self.i_cache_labels = self._create_section_metrics(self.detail_grid, "Instruction Cache", 0)
        self.d_cache_labels = self._create_section_metrics(self.detail_grid, "Data Cache", 1)
        self.l2_cache_labels = self._create_section_metrics(self.detail_grid, "Unified L2 Cache", 2)

        self.status_label = ctk.CTkLabel(
            self.dashboard_frame,
            text="Ready. Select parameters and choose a trace file.",
            font=(FONT_FAMILY, 13),
            text_color="#94a3b8",
        )
        self.status_label.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 14))

        self.sidebar_frame = ctk.CTkFrame(
            self.content,
            width=370,
            corner_radius=16,
            fg_color="#121a2e",
            border_width=1,
            border_color="#23304d",
        )
        self.sidebar_frame.grid(row=0, column=2, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.sidebar_frame,
            text="Past Simulations",
            font=(FONT_FAMILY, 18, "bold"),
            text_color="#f8fafc",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.history_list_frame = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            fg_color="#0f172a",
            border_width=1,
            border_color="#1e293b",
            scrollbar_button_color="#334155",
            scrollbar_button_hover_color="#475569",
            corner_radius=10,
            height=270,
        )
        self.history_list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.history_list_frame.grid_columnconfigure(0, weight=1)

        compare_card = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color="#0f172a",
            border_width=1,
            border_color="#1e293b",
            corner_radius=10,
        )
        compare_card.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        compare_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            compare_card,
            text="Compare Runs",
            font=(FONT_FAMILY, 16, "bold"),
            text_color="#f8fafc",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        self.compare_a_var = ctk.StringVar(value="Current Run")
        self.compare_b_var = ctk.StringVar(value="Current Run")

        ctk.CTkLabel(compare_card, text="Run A", font=(FONT_FAMILY, 12), text_color="#94a3b8").grid(
            row=1, column=0, sticky="w", padx=12
        )
        self.compare_a_menu = ctk.CTkOptionMenu(
            compare_card,
            variable=self.compare_a_var,
            values=["Current Run"],
            height=30,
            fg_color="#334155",
            button_color="#1e293b",
            button_hover_color="#0f172a",
            dropdown_fg_color="#1e293b",
            dropdown_hover_color="#334155",
        )
        self.compare_a_menu.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 8))

        ctk.CTkLabel(compare_card, text="Run B", font=(FONT_FAMILY, 12), text_color="#94a3b8").grid(
            row=3, column=0, sticky="w", padx=12
        )
        self.compare_b_menu = ctk.CTkOptionMenu(
            compare_card,
            variable=self.compare_b_var,
            values=["Current Run"],
            height=30,
            fg_color="#334155",
            button_color="#1e293b",
            button_hover_color="#0f172a",
            dropdown_fg_color="#1e293b",
            dropdown_hover_color="#334155",
        )
        self.compare_b_menu.grid(row=4, column=0, sticky="ew", padx=12, pady=(2, 10))

        self.compare_button = ctk.CTkButton(
            compare_card,
            text="Compare Selected Runs",
            height=32,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=(FONT_FAMILY, 12, "bold"),
            command=self._compare_selected_runs,
        )
        self.compare_button.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.compare_result_label = ctk.CTkLabel(
            compare_card,
            text="Run comparison will appear here.",
            font=(FONT_FAMILY, 12),
            text_color="#cbd5e1",
            justify="left",
            anchor="w",
            wraplength=310,
        )
        self.compare_result_label.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _create_kpi_item(self, parent, title, initial_value, col):
        item = ctk.CTkFrame(parent, fg_color="transparent")
        item.grid(row=0, column=col, padx=10, sticky="nsew")
        ctk.CTkLabel(
            item,
            text=title,
            font=(FONT_FAMILY, 12),
            text_color="#94a3b8",
        ).pack(anchor="w")
        value_label = ctk.CTkLabel(
            item,
            text=initial_value,
            font=(FONT_FAMILY, 26, "bold"),
            text_color="#38bdf8",
        )
        value_label.pack(anchor="w", pady=(2, 0))
        return value_label

    def _create_section_metrics(self, parent, title, col):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            section,
            text=title,
            font=(FONT_FAMILY, 13, "bold"),
            text_color="#e2e8f0",
        ).pack(anchor="w", padx=10, pady=(10, 8))

        labels = {}
        fields = [
            "Total Accesses",
            "Reads",
            "Writes",
            "Cache Hits",
            "Cache Misses",
            "Hit Rate",
            "Miss Rate",
            "AMAT",
        ]

        for field in fields:
            row = ctk.CTkFrame(section, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(
                row,
                text=field,
                font=(FONT_FAMILY, 12),
                text_color="#94a3b8",
            ).pack(side="left")
            value_label = ctk.CTkLabel(
                row,
                text="--",
                font=(FONT_FAMILY, 12, "bold"),
                text_color="#cbd5e1",
            )
            value_label.pack(side="right")
            labels[field] = value_label

        return labels

    def create_dropdown(self, label_text, var_name, options):
        frame = ctk.CTkFrame(self.form_card, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(frame, text=label_text, font=(FONT_FAMILY, 13), text_color="#cbd5e1").pack(anchor="w")
        var = ctk.StringVar(value=options[0])
        dropdown = ctk.CTkOptionMenu(
            frame,
            values=options,
            variable=var,
            height=32,
            fg_color="#334155",
            button_color="#1e293b",
            button_hover_color="#0f172a",
            dropdown_fg_color="#1e293b",
            dropdown_hover_color="#334155",
        )
        dropdown.pack(fill="x", pady=(4, 0))
        self.settings_vars[var_name] = var

    def _enable_drag_drop(self):
        if DND_FILES is None:
            self.drop_hint_label.configure(
                text="Drag-and-drop unavailable: install tkinterdnd2 to enable it.",
                text_color="#f59e0b",
            )
            return

        try:
            self.file_entry.drop_target_register(DND_FILES)
            self.file_entry.dnd_bind("<<Drop>>", self._on_file_drop)
        except Exception:
            self.drop_hint_label.configure(
                text="Drag-and-drop unavailable in current runtime.",
                text_color="#f59e0b",
            )

    def _on_file_drop(self, event):
        dropped_path = event.data.strip().strip("{}").strip('"')
        if dropped_path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, dropped_path)
            self.validation_label.configure(text="")

    def _bind_trace_entry_updates(self):
        self.file_entry.bind("<FocusOut>", lambda _event: self.validation_label.configure(text=""))

    def _set_run_summary(self, text, color="#94a3b8"):
        self.run_summary_label.configure(text=text, text_color=color)

    def _format_trace_summary(self, trace_file):
        try:
            with open(trace_file, "r", encoding="utf-8", errors="ignore") as handle:
                line_count = sum(1 for _ in handle)
        except Exception:
            return "Unknown traces"

        if line_count >= 10_000_000:
            return f"{line_count / 10_000_000:.1f}Cr traces"
        if line_count >= 100_000:
            return f"{line_count / 100_000:.1f}L traces"
        return f"{line_count:,} traces"

    def _run_display_name(self, run):
        stamp = run.get("timestamp", "Unknown time")
        trace_name = os.path.basename(run.get("trace_file", "unknown_trace"))
        summary = run.get("trace_summary", "Unknown traces")
        return f"{stamp} | {trace_name} | {summary}"

    def _load_history_runs(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        if not os.path.exists(HISTORY_FILE):
            self.history_runs = []
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                self.history_runs = data if isinstance(data, list) else []
        except Exception:
            self.history_runs = []

    def _save_history_runs(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as handle:
                json.dump(self.history_runs[-50:], handle, indent=2)
        except Exception:
            pass

    def _refresh_history_controls(self):
        self.history_lookup = {}
        values = ["Current Run"]
        for run in reversed(self.history_runs):
            name = self._run_display_name(run)
            self.history_lookup[name] = run
            values.append(name)

        self.compare_a_menu.configure(values=values)
        self.compare_b_menu.configure(values=values)

        if self.compare_a_var.get() not in values:
            self.compare_a_var.set("Current Run")
        if self.compare_b_var.get() not in values:
            self.compare_b_var.set("Current Run")

        self._render_history_list()

    def _render_history_list(self):
        for child in self.history_list_frame.winfo_children():
            child.destroy()

        if not self.history_runs:
            ctk.CTkLabel(
                self.history_list_frame,
                text="No past runs yet.",
                font=(FONT_FAMILY, 12),
                text_color="#94a3b8",
            ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        for idx, run in enumerate(reversed(self.history_runs[-25:])):
            button = ctk.CTkButton(
                self.history_list_frame,
                text=self._run_display_name(run),
                font=(FONT_FAMILY, 11),
                fg_color="#1f2937",
                hover_color="#334155",
                text_color="#e2e8f0",
                anchor="w",
                height=30,
                command=lambda selected_run=run: self._load_run_into_dashboard(selected_run),
            )
            button.grid(row=idx, column=0, sticky="ew", padx=6, pady=(4, 0))

    def _load_run_into_dashboard(self, run):
        sections = run.get("sections", {})
        modified = run.get("modified", "--")
        self.current_run_record = run
        self._set_run_summary(
            f"Loaded past run from {run.get('timestamp', 'Unknown')} | Modified instructions: {modified}",
            color="#93c5fd",
        )
        self._apply_analysis_view_only(sections)

    def _resolve_selection(self, selected_name):
        if selected_name == "Current Run":
            return self.current_run_record
        return self.history_lookup.get(selected_name)

    def _compute_summary_metrics(self, run):
        sections = run.get("sections", {})
        i = sections.get("Instruction Cache", {})
        d = sections.get("Data Cache", {})
        l2 = sections.get("Unified L2 Cache", {})

        i_acc = self._safe_num(i.get("Total Accesses")) or 0
        d_acc = self._safe_num(d.get("Total Accesses")) or 0
        i_miss = self._safe_num(i.get("Cache Misses")) or 0
        d_miss = self._safe_num(d.get("Cache Misses")) or 0
        l2_miss = self._safe_num(l2.get("Miss Rate"))
        l2_amat = self._safe_num(l2.get("AMAT"))

        total_acc = i_acc + d_acc
        l1_miss_rate = ((i_miss + d_miss) / total_acc) * 100.0 if total_acc else None
        return {
            "l1_miss_rate": l1_miss_rate,
            "l2_miss_rate": l2_miss,
            "l2_amat": l2_amat,
        }

    def _compare_selected_runs(self):
        run_a = self._resolve_selection(self.compare_a_var.get())
        run_b = self._resolve_selection(self.compare_b_var.get())

        if run_a is None or run_b is None:
            self.compare_result_label.configure(
                text="Comparison unavailable. Run at least one simulation and select valid runs.",
                text_color="#ef4444",
            )
            return

        metrics_a = self._compute_summary_metrics(run_a)
        metrics_b = self._compute_summary_metrics(run_b)

        def fmt(value, suffix=""):
            return f"{value:.3f}{suffix}" if value is not None else "--"

        text = (
            f"L1 Miss Rate: {fmt(metrics_a['l1_miss_rate'], ' %')} vs {fmt(metrics_b['l1_miss_rate'], ' %')}\n"
            f"L2 Miss Rate: {fmt(metrics_a['l2_miss_rate'], ' %')} vs {fmt(metrics_b['l2_miss_rate'], ' %')}\n"
            f"L2 AMAT: {fmt(metrics_a['l2_amat'])} vs {fmt(metrics_b['l2_amat'])}"
        )
        self.compare_result_label.configure(text=text, text_color="#cbd5e1")
        self._draw_graphs(run_a.get("sections", {}), run_b.get("sections", {}))

    def _set_section_values(self, section_labels, stats):
        for key, label in section_labels.items():
            value = stats.get(key, "--")
            label.configure(text=str(value))

    def _set_empty_analysis(self):
        empty = {
            "Total Accesses": "--",
            "Reads": "--",
            "Writes": "--",
            "Cache Hits": "--",
            "Cache Misses": "--",
            "Hit Rate": "--",
            "Miss Rate": "--",
            "AMAT": "--",
        }
        self._set_section_values(self.i_cache_labels, empty)
        self._set_section_values(self.d_cache_labels, empty)
        self._set_section_values(self.l2_cache_labels, empty)
        self.l1_miss_rate_label.configure(text="-- %")
        self.l2_miss_rate_label.configure(text="-- %")
        self.total_time_label.configure(text="--")
        self.comparison_summary_label.configure(
            text="I/D Balance: --   |   D-Write Intensity: --   |   L2 per L1 Miss: --"
        )
        self.compare_result_label.configure(text="Run comparison will appear here.", text_color="#cbd5e1")
        self._clear_graphs_placeholder("Run a simulation to generate performance graphs.")

    def _clear_graphs_placeholder(self, text):
        if self.graph_canvas is not None:
            self.graph_canvas.get_tk_widget().destroy()
            self.graph_canvas = None
        self.graph_placeholder.configure(text=text)
        self.graph_placeholder.grid(row=0, column=0)

    def _draw_graphs(self, sections, compare_sections=None):
        if not MATPLOTLIB_AVAILABLE:
            self._clear_graphs_placeholder("Install matplotlib (pip install matplotlib) to enable graph analytics.")
            return

        levels = ["L1-I", "L1-D", "L2"]
        i_stats = sections.get("Instruction Cache", {})
        d_stats = sections.get("Data Cache", {})
        l2_stats = sections.get("Unified L2 Cache", {})

        accesses = [
            self._safe_num(i_stats.get("Total Accesses")) or 0,
            self._safe_num(d_stats.get("Total Accesses")) or 0,
            self._safe_num(l2_stats.get("Total Accesses")) or 0,
        ]
        hits = [
            self._safe_num(i_stats.get("Cache Hits")) or 0,
            self._safe_num(d_stats.get("Cache Hits")) or 0,
            self._safe_num(l2_stats.get("Cache Hits")) or 0,
        ]
        misses = [
            self._safe_num(i_stats.get("Cache Misses")) or 0,
            self._safe_num(d_stats.get("Cache Misses")) or 0,
            self._safe_num(l2_stats.get("Cache Misses")) or 0,
        ]
        miss_rates = [
            self._safe_num(i_stats.get("Miss Rate")) or 0,
            self._safe_num(d_stats.get("Miss Rate")) or 0,
            self._safe_num(l2_stats.get("Miss Rate")) or 0,
        ]
        amats = [
            self._safe_num(i_stats.get("AMAT")) or 0,
            self._safe_num(d_stats.get("AMAT")) or 0,
            self._safe_num(l2_stats.get("AMAT")) or 0,
        ]

        compare_metrics = None
        if compare_sections is not None:
            ca = compare_sections.get("Instruction Cache", {})
            cb = compare_sections.get("Data Cache", {})
            cc = compare_sections.get("Unified L2 Cache", {})

            a_total = (self._safe_num(ca.get("Total Accesses")) or 0) + (self._safe_num(cb.get("Total Accesses")) or 0)
            a_miss = (self._safe_num(ca.get("Cache Misses")) or 0) + (self._safe_num(cb.get("Cache Misses")) or 0)
            compare_l1 = ((a_miss / a_total) * 100.0) if a_total else 0
            compare_l2 = self._safe_num(cc.get("Miss Rate")) or 0
            compare_amat = self._safe_num(cc.get("AMAT")) or 0

            current_total = accesses[0] + accesses[1]
            current_miss = misses[0] + misses[1]
            current_l1 = ((current_miss / current_total) * 100.0) if current_total else 0
            current_l2 = miss_rates[2]
            current_amat = amats[2]

            compare_metrics = {
                "labels": ["L1 Miss%", "L2 Miss%", "L2 AMAT"],
                "current": [current_l1, current_l2, current_amat],
                "other": [compare_l1, compare_l2, compare_amat],
            }

        figure = Figure(figsize=(8.5, 5.2), dpi=100, facecolor="#0b132b")
        ax1 = figure.add_subplot(221)
        ax2 = figure.add_subplot(222)
        ax3 = figure.add_subplot(223)
        ax4 = figure.add_subplot(224)

        axes = [ax1, ax2, ax3, ax4]
        for ax in axes:
            ax.set_facecolor("#0f172a")
            ax.tick_params(colors="#cbd5e1", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#334155")

        ax1.bar(levels, miss_rates, color=["#38bdf8", "#22c55e", "#f59e0b"])
        ax1.set_title("Miss Rate (%)", color="#e2e8f0", fontsize=10)

        ax2.bar(levels, accesses, color=["#2563eb", "#0ea5e9", "#8b5cf6"])
        ax2.set_title("Total Accesses", color="#e2e8f0", fontsize=10)

        ax3.bar(levels, hits, color="#16a34a", label="Hits")
        ax3.bar(levels, misses, bottom=hits, color="#ef4444", label="Misses")
        ax3.set_title("Hit vs Miss Mix", color="#e2e8f0", fontsize=10)
        ax3.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8)

        if compare_metrics is None:
            ax4.bar(levels, amats, color=["#f97316", "#06b6d4", "#f43f5e"])
            ax4.set_title("AMAT by Level", color="#e2e8f0", fontsize=10)
        else:
            labels = compare_metrics["labels"]
            x_positions = range(len(labels))
            width = 0.36
            current_vals = compare_metrics["current"]
            other_vals = compare_metrics["other"]
            ax4.bar([x - width / 2 for x in x_positions], current_vals, width=width, color="#38bdf8", label="Selected A")
            ax4.bar([x + width / 2 for x in x_positions], other_vals, width=width, color="#f97316", label="Selected B")
            ax4.set_xticks(list(x_positions), labels)
            ax4.set_title("Selected Run Comparison", color="#e2e8f0", fontsize=10)
            ax4.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8)

        for ax in (ax1, ax2, ax4):
            for bar in ax.patches:
                h = bar.get_height()
                ax.annotate(
                    f"{h:.2f}" if isinstance(h, float) else f"{h}",
                    (bar.get_x() + bar.get_width() / 2, h),
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color="#e2e8f0",
                    xytext=(0, 2),
                    textcoords="offset points",
                )

        figure.tight_layout(pad=1.4)

        if self.graph_canvas is not None:
            self.graph_canvas.get_tk_widget().destroy()
        self.graph_placeholder.grid_forget()

        self.graph_canvas = FigureCanvasTkAgg(figure, master=self.graph_host)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _parse_simulator_output(self, output_text):
        sections = {
            "Instruction Cache": {},
            "Data Cache": {},
            "Unified L2 Cache": {},
        }
        current = None
        modified = "--"

        section_headers = {
            "Instruction Cache (I-Cache)": "Instruction Cache",
            "Data Cache (D-Cache)": "Data Cache",
            "Unified L2 Cache": "Unified L2 Cache",
        }

        for raw_line in output_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            for marker, section_name in section_headers.items():
                if marker in line:
                    current = section_name
                    break

            if line.startswith("MODIFIED INSTURCTIONS"):
                modified = line.split(":", 1)[1].strip() if ":" in line else "--"
                continue

            if current and ":" in line:
                key, value = [part.strip() for part in line.split(":", 1)]
                if key in {
                    "Total Accesses",
                    "Reads",
                    "Writes",
                    "Cache Hits",
                    "Cache Misses",
                    "Hit Rate",
                    "Miss Rate",
                    "AMAT",
                }:
                    sections[current][key] = value

        return sections, modified

    def _safe_num(self, value_text):
        match = re.search(r"[-+]?\d*\.?\d+", str(value_text))
        return float(match.group(0)) if match else None

    def _apply_analysis_view_only(self, sections):
        self._set_section_values(self.i_cache_labels, sections.get("Instruction Cache", {}))
        self._set_section_values(self.d_cache_labels, sections.get("Data Cache", {}))
        self._set_section_values(self.l2_cache_labels, sections.get("Unified L2 Cache", {}))

        i_acc = self._safe_num(sections["Instruction Cache"].get("Total Accesses")) or 0
        d_acc = self._safe_num(sections["Data Cache"].get("Total Accesses")) or 0
        i_miss = self._safe_num(sections["Instruction Cache"].get("Cache Misses")) or 0
        d_miss = self._safe_num(sections["Data Cache"].get("Cache Misses")) or 0

        l2_miss_rate = sections["Unified L2 Cache"].get("Miss Rate", "--")
        l2_amat = sections["Unified L2 Cache"].get("AMAT", "--")

        total_l1_acc = i_acc + d_acc
        total_l1_miss = i_miss + d_miss
        if total_l1_acc > 0:
            l1_miss_rate_val = (total_l1_miss / total_l1_acc) * 100.0
            self.l1_miss_rate_label.configure(text=f"{l1_miss_rate_val:.3f} %")
        else:
            self.l1_miss_rate_label.configure(text="-- %")

        if l2_miss_rate == "--":
            self.l2_miss_rate_label.configure(text="-- %")
        else:
            self.l2_miss_rate_label.configure(text=l2_miss_rate if str(l2_miss_rate).endswith("%") else f"{l2_miss_rate} %")

        d_write_intensity_text = "--"
        id_balance_text = "--"
        l2_pressure_text = "--"

        if d_acc > 0:
            d_write_intensity = ((self._safe_num(sections["Data Cache"].get("Writes")) or 0) / d_acc) * 100.0
            d_write_intensity_text = f"{d_write_intensity:.2f} %"

        if d_acc > 0:
            id_balance_text = f"{i_acc / d_acc:.2f} : 1"
        elif i_acc > 0:
            id_balance_text = "INF : 1"

        l2_requests = self._safe_num(sections["Unified L2 Cache"].get("Total Accesses")) or 0
        if total_l1_miss > 0:
            l2_pressure_text = f"{(l2_requests / total_l1_miss):.2f}"

        self.comparison_summary_label.configure(
            text=(
                f"I/D Balance: {id_balance_text}   |   "
                f"D-Write Intensity: {d_write_intensity_text}   |   "
                f"L2 per L1 Miss: {l2_pressure_text}"
            )
        )

        self.total_time_label.configure(text=l2_amat if l2_amat != "--" else "--")
        self._draw_graphs(sections, None)

    def _apply_analysis(self, sections, modified_count, config):
        self._apply_analysis_view_only(sections)

        trace_file = config.get("trace_file", "")
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trace_file": trace_file,
            "trace_summary": self._format_trace_summary(trace_file),
            "config": config,
            "sections": sections,
            "modified": modified_count,
        }
        self.current_run_record = record
        self.history_runs.append(record)
        self._save_history_runs()
        self._refresh_history_controls()

        self._set_run_summary(
            f"Simulation completed successfully. Modified instructions: {modified_count}",
            color="#22c55e",
        )

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select Trace File")
        if filename:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, filename)
            self.validation_label.configure(text="")

    def update_status(self, text, color="gray"):
        self.status_label.configure(text=text, text_color=color)
        if color in ("red", "#ef4444"):
            self.status_pill.configure(text="ERROR", fg_color="#b91c1c")
        elif color in ("#28a745", "#059669", "green"):
            self.status_pill.configure(text="DONE", fg_color="#0f766e")
        elif "running" in text.lower() or "compiling" in text.lower():
            self.status_pill.configure(text="RUNNING", fg_color="#1d4ed8")
        else:
            self.status_pill.configure(text="READY", fg_color="#0f766e")

    def _validate_config(self, config):
        trace_file = config.get("trace_file", "").strip()
        if not trace_file:
            return False, "Please select a trace file before running simulation."
        if not os.path.exists(trace_file):
            return False, "Selected trace file does not exist. Please choose a valid file."

        l1_size = int(config["l1_size"])
        l1_assoc = int(config["l1_assoc"])
        l2_size = int(config["l2_size"])
        l2_assoc = int(config["l2_assoc"])

        if l1_assoc > (l1_size // 64):
            return False, "L1 associativity is too high for selected L1 size."
        if l2_assoc > (l2_size // 64):
            return False, "L2 associativity is too high for selected L2 size."
        if l2_size < l1_size:
            return False, "L2 size should be greater than or equal to L1 size for a practical setup."

        return True, ""

    def start_simulation_thread(self):
        config = {key: var.get() for key, var in self.settings_vars.items()}
        config["trace_file"] = self.file_entry.get().strip()

        is_valid, validation_msg = self._validate_config(config)
        if not is_valid:
            self.validation_label.configure(text=validation_msg)
            self.update_status("Configuration error. Fix highlighted issue and retry.", "#ef4444")
            return

        self.validation_label.configure(text="")
        self._set_run_summary("Preparing simulation run...", color="#93c5fd")
        self._set_empty_analysis()

        self.run_btn.configure(state="disabled", text="Running...")
        self.update_status("Compiling C++ code...", "#1f6aa5")

        threading.Thread(target=self._execute_backend, args=(config,), daemon=True).start()

    def _execute_backend(self, config):
        comp_success, comp_msg = self.simulator.compile_code()

        if comp_success:
            self.after(0, lambda: self.update_status("Compilation successful. Running simulation..."))
            run_success, run_msg = self.simulator.run_simulation(config)

            if run_success:
                sections, modified_count = self._parse_simulator_output(run_msg)
                self.after(0, lambda: self._apply_analysis(sections, modified_count, config))
                self.after(0, lambda: self.update_status("Simulation complete. Results updated.", "#059669"))
            else:
                short_msg = run_msg.splitlines()[0] if run_msg else "Simulation failed"
                self.after(0, lambda: self._set_run_summary(f"Simulation failed: {short_msg}", color="#ef4444"))
                self.after(0, lambda: self.update_status("Simulation failed.", "#ef4444"))
        else:
            short_msg = comp_msg.splitlines()[0] if comp_msg else "Compilation failed"
            self.after(0, lambda: self._set_run_summary(f"Compilation failed: {short_msg}", color="#ef4444"))
            self.after(0, lambda: self.update_status("Compilation failed. Check C++ code.", "#ef4444"))

        self.after(0, lambda: self.run_btn.configure(state="normal", text="Compile & Run Simulation"))