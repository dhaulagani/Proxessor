import os
import sys
import threading
import time
import ctypes
from typing import Optional, Dict

# 1. Instantly hide any attached console window (solves empty cmd window)
try:
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
except Exception:
    pass

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

from src.proxessor.gui.controller import GUIController

# Design System Tokens (from docs/DESIGN.md)
COLOR_BG = "#0b0d13"
COLOR_CARD = "#121620"
COLOR_CARD_HOVER = "#1a202c"
COLOR_BORDER = "#222a3d"
COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"

COLOR_ACCENT_GREEN = "#10b981"   # Emerald: Optimal / Active
COLOR_ACCENT_BLUE = "#38bdf8"    # Sky: System RAM
COLOR_ACCENT_AMBER = "#f59e0b"   # Amber: ProBalance Restrained
COLOR_ACCENT_RED = "#ef4444"     # Rose: Critical / Kill

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class TelemetryCanvas(tk.Canvas):
    """Bespoke real-time scrolling history graph for CPU, RAM, and ProBalance restraint."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLOR_CARD, highlightthickness=0, **kwargs)
        self.bind("<Configure>", self._on_resize)
        self.cpu_data = [0.0] * 60
        self.ram_data = [0.0] * 60
        self.restraint_data = [0.0] * 60

    def _on_resize(self, event):
        self.redraw()

    def update_history(self, cpu_history, ram_history, restraint_history):
        self.cpu_data = cpu_history[-60:]
        self.ram_data = ram_history[-60:]
        self.restraint_data = restraint_history[-60:]
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        # Grid lines (25%, 50%, 75%)
        for pct in (0.25, 0.50, 0.75):
            y = h - (h * pct)
            self.create_line(0, y, w, y, fill=COLOR_BORDER, dash=(2, 4), width=1)
            self.create_text(w - 28, y - 6, text=f"{int(pct*100)}%", fill=COLOR_TEXT_MUTED, font=("Consolas", 8))

        # Plot curves
        step = w / max(1, len(self.cpu_data) - 1)

        def draw_series(data, color, width=2):
            points = []
            for i, val in enumerate(data):
                x = i * step
                clamped = max(0.0, min(100.0, val))
                y = h - (clamped / 100.0 * (h - 8)) - 4
                points.extend([x, y])
            if len(points) >= 4:
                self.create_line(points, fill=color, width=width, smooth=True)

        draw_series(self.ram_data, COLOR_ACCENT_BLUE, width=1)
        draw_series(self.restraint_data, COLOR_ACCENT_AMBER, width=2)
        draw_series(self.cpu_data, COLOR_ACCENT_GREEN, width=2)


class ProxessorApp(ctk.CTk):
    """Enterprise-grade Process Lasso alternative desktop application."""

    def __init__(self, config_path: str = "config/default_rules.json"):
        super().__init__()
        self.title("Proxessor // Professional Process Governor & Thread Optimizer")
        self.geometry("1240x820")
        self.minsize(1050, 680)
        self.configure(fg_color=COLOR_BG)

        self.controller = GUIController(config_path)
        self.selected_pid: Optional[int] = None
        self.selected_name: str = ""
        self.filter_mode = "all"
        self.sort_col = "cpu_percent"
        self.sort_desc = True
        self.polling_active = True

        self._setup_layout()
        self._setup_context_menu()
        self._start_background_polling()

    def _setup_layout(self):
        # 1. Top Header Bar
        self.header = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        self.header.pack(fill=tk.X, padx=14, pady=(12, 6))

        # Left: Branding
        brand_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        brand_frame.pack(side=tk.LEFT, padx=16, pady=10)

        title_lbl = ctk.CTkLabel(
            brand_frame,
            text="PROXESSOR CORE",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        title_lbl.pack(anchor=tk.W)

        sub_lbl = ctk.CTkLabel(
            brand_frame,
            text="Native Win32 Governor • All Pro Features Unlocked • 0% Telemetry",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        sub_lbl.pack(anchor=tk.W)

        # Center: Telemetry Badges
        metrics_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        metrics_frame.pack(side=tk.LEFT, padx=30)

        self.badge_cpu = ctk.CTkLabel(
            metrics_frame,
            text="CPU: 0.0%",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        self.badge_cpu.pack(side=tk.LEFT, padx=10)

        self.badge_ram = ctk.CTkLabel(
            metrics_frame,
            text="RAM: 0.0%",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.badge_ram.pack(side=tk.LEFT, padx=10)

        self.badge_pb = ctk.CTkLabel(
            metrics_frame,
            text="PROBALANCE: ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=COLOR_ACCENT_GREEN
        )
        self.badge_pb.pack(side=tk.LEFT, padx=10)

        # Right: Quick Global Triggers
        triggers_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        triggers_frame.pack(side=tk.RIGHT, padx=14)

        btn_smart_trim = ctk.CTkButton(
            triggers_frame,
            text="SmartTrim RAM",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            width=120,
            height=32,
            corner_radius=6,
            command=self._on_smart_trim
        )
        btn_smart_trim.pack(side=tk.LEFT, padx=4)

        self.opt_power = ctk.CTkOptionMenu(
            triggers_frame,
            values=["HIGH_PERFORMANCE", "BALANCED", "ULTIMATE_PERFORMANCE", "POWER_SAVER"],
            width=175,
            height=32,
            corner_radius=6,
            fg_color="#1e293b",
            button_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_power_scheme_change
        )
        self.opt_power.set("HIGH_PERFORMANCE")
        self.opt_power.pack(side=tk.LEFT, padx=4)

        # 2. Real-Time Telemetry Graph
        graph_card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        graph_card.pack(fill=tk.X, padx=14, pady=4)

        graph_header = ctk.CTkFrame(graph_card, fg_color="transparent")
        graph_header.pack(fill=tk.X, padx=12, pady=(6, 2))

        lbl_graph_title = ctk.CTkLabel(
            graph_header,
            text="SYSTEM CPU & RESPONSIVENESS HISTORY",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY
        )
        lbl_graph_title.pack(side=tk.LEFT)

        # Legend
        legend_frame = ctk.CTkFrame(graph_header, fg_color="transparent")
        legend_frame.pack(side=tk.RIGHT)

        for text, col in [("CPU Usage", COLOR_ACCENT_GREEN), ("Memory Load", COLOR_ACCENT_BLUE), ("ProBalance Restraint", COLOR_ACCENT_AMBER)]:
            lbl = ctk.CTkLabel(
                legend_frame,
                text=f"● {text}",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=col
            )
            lbl.pack(side=tk.LEFT, padx=8)

        self.graph = TelemetryCanvas(graph_card, height=72)
        self.graph.pack(fill=tk.X, padx=12, pady=(0, 8))

        # 3. Main Split View: Left (Tabs) & Right (Inspector Drawer)
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        # Left: Tabs for Processes, Rules, Engine, Logs
        self.tabs = ctk.CTkTabview(
            main_split,
            fg_color=COLOR_CARD,
            segmented_button_fg_color="#182030",
            segmented_button_selected_color="#2563eb",
            corner_radius=10
        )
        self.tabs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tab_procs = self.tabs.add("All Processes")
        tab_cores = self.tabs.add("Per-Core Load")
        tab_sockets = self.tabs.add("Network Sockets")
        tab_filelock = self.tabs.add("File Lock Hunter")
        tab_rules = self.tabs.add("Active Rules")
        tab_engine = self.tabs.add("Engine Settings")
        tab_logs = self.tabs.add("ProBalance Journal")

        self._build_processes_tab(tab_procs)
        self._build_cores_tab(tab_cores)
        self._build_sockets_tab(tab_sockets)
        self._build_filelock_tab(tab_filelock)
        self._build_rules_tab(tab_rules)
        self._build_engine_tab(tab_engine)
        self._build_logs_tab(tab_logs)

        # Right: Process Tuning Arbiter Drawer
        self._build_tuning_drawer(main_split)

        # 4. Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color=COLOR_CARD, height=26, corner_radius=6)
        self.status_bar.pack(fill=tk.X, padx=14, pady=(4, 8))

        self.lbl_status = ctk.CTkLabel(
            self.status_bar,
            text="Governor: Native Ring-3 Active • Zero-GC • Monitoring 0 processes",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(side=tk.LEFT, padx=12, pady=2)

    def _build_processes_tab(self, parent):
        # Filter & View Bar
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill=tk.X, padx=6, pady=(6, 8))

        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Filter process name or PID...",
            width=260,
            height=32,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_process_table())

        self.filter_seg = ctk.CTkSegmentedButton(
            toolbar,
            values=["All Processes", "Active (>0% CPU)", "Restrained Only"],
            command=self._on_filter_changed,
            height=32,
            fg_color="#1a202c",
            selected_color="#2563eb"
        )
        self.filter_seg.set("All Processes")
        self.filter_seg.pack(side=tk.LEFT)

        # Table with ttk Treeview styled dark
        table_frame = tk.Frame(parent, bg=COLOR_CARD)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        cols = ("pid", "name", "cpu", "ram", "priority", "threads", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("pid", text="PID", command=lambda: self._sort_table("pid"))
        self.tree.heading("name", text="PROCESS NAME", command=lambda: self._sort_table("name"))
        self.tree.heading("cpu", text="CPU %", command=lambda: self._sort_table("cpu_percent"))
        self.tree.heading("ram", text="RAM (MB)", command=lambda: self._sort_table("memory_mb"))
        self.tree.heading("priority", text="PRIORITY", command=lambda: self._sort_table("priority"))
        self.tree.heading("threads", text="THREADS", command=lambda: self._sort_table("threads"))
        self.tree.heading("status", text="STATUS")

        self.tree.column("pid", width=65, anchor=tk.E)
        self.tree.column("name", width=200, anchor=tk.W)
        self.tree.column("cpu", width=75, anchor=tk.E)
        self.tree.column("ram", width=85, anchor=tk.E)
        self.tree.column("priority", width=105, anchor=tk.CENTER)
        self.tree.column("threads", width=65, anchor=tk.E)
        self.tree.column("status", width=110, anchor=tk.CENTER)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=COLOR_CARD,
            foreground=COLOR_TEXT_PRIMARY,
            fieldbackground=COLOR_CARD,
            rowheight=24,
            font=("Consolas", 10),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#161b26",
            foreground=COLOR_TEXT_SECONDARY,
            font=("Segoe UI", 10, "bold"),
            padding=5
        )
        style.map("Treeview", background=[("selected", "#2563eb")])

        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_process_selected)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _build_tuning_drawer(self, parent):
        drawer = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10, width=340, border_width=1, border_color=COLOR_BORDER)
        drawer.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(6, 0))
        drawer.pack_propagate(False)

        lbl_drawer_title = ctk.CTkLabel(
            drawer,
            text="PROCESS TUNING ARBITER",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl_drawer_title.pack(anchor=tk.W, padx=14, pady=(12, 4))

        self.lbl_selected_title = ctk.CTkLabel(
            drawer,
            text="Select a process to tune",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_selected_title.pack(anchor=tk.W, padx=14, pady=(0, 10))

        # Controls Card
        ctrl_box = ctk.CTkFrame(drawer, fg_color="#181e2b", corner_radius=8)
        ctrl_box.pack(fill=tk.X, padx=12, pady=4)

        # Priority Class
        lbl_prio = ctk.CTkLabel(ctrl_box, text="CPU Priority Class:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_SECONDARY)
        lbl_prio.pack(anchor=tk.W, padx=12, pady=(8, 2))

        self.opt_prio = ctk.CTkOptionMenu(
            ctrl_box,
            values=["REALTIME", "HIGH", "ABOVE_NORMAL", "NORMAL", "BELOW_NORMAL", "IDLE"],
            fg_color="#242c3d",
            height=28
        )
        self.opt_prio.set("NORMAL")
        self.opt_prio.pack(fill=tk.X, padx=12, pady=(0, 8))

        # Core Affinity
        lbl_aff = ctk.CTkLabel(ctrl_box, text="CPU Core Affinity:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_SECONDARY)
        lbl_aff.pack(anchor=tk.W, padx=12, pady=(4, 2))

        self.opt_aff = ctk.CTkOptionMenu(
            ctrl_box,
            values=["ALL_CORES", "P_CORES", "E_CORES"],
            fg_color="#242c3d",
            height=28
        )
        self.opt_aff.set("ALL_CORES")
        self.opt_aff.pack(fill=tk.X, padx=12, pady=(0, 8))

        # I/O Priority
        lbl_io = ctk.CTkLabel(ctrl_box, text="I/O Request Priority:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_SECONDARY)
        lbl_io.pack(anchor=tk.W, padx=12, pady=(4, 2))

        self.opt_io = ctk.CTkOptionMenu(
            ctrl_box,
            values=["HIGH", "NORMAL", "LOW", "VERY_LOW"],
            fg_color="#242c3d",
            height=28
        )
        self.opt_io.set("NORMAL")
        self.opt_io.pack(fill=tk.X, padx=12, pady=(0, 8))

        # Persistent Checkbox
        self.chk_persistent = ctk.CTkCheckBox(
            ctrl_box,
            text="Always Remember (Save Rule)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_PRIMARY,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        self.chk_persistent.pack(anchor=tk.W, padx=12, pady=(4, 10))

        # Toggles Card
        toggles_box = ctk.CTkFrame(drawer, fg_color="#181e2b", corner_radius=8)
        toggles_box.pack(fill=tk.X, padx=12, pady=6)

        self.switch_eco = ctk.CTkSwitch(
            toggles_box,
            text="Windows EcoQoS (Power Throttling)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_PRIMARY,
            command=self._on_toggle_eco
        )
        self.switch_eco.pack(anchor=tk.W, padx=12, pady=8)

        self.switch_exclude = ctk.CTkSwitch(
            toggles_box,
            text="Exclude from ProBalance",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_PRIMARY,
            command=self._on_toggle_exclude
        )
        self.switch_exclude.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Action Buttons
        btn_apply = ctk.CTkButton(
            drawer,
            text="APPLY TUNING CHANGES",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=34,
            command=self._on_apply_tuning
        )
        btn_apply.pack(fill=tk.X, padx=12, pady=(8, 4))

        action_row = ctk.CTkFrame(drawer, fg_color="transparent")
        action_row.pack(fill=tk.X, padx=12, pady=4)

        btn_trim = ctk.CTkButton(
            action_row,
            text="Trim RAM",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            width=95,
            height=30,
            command=self._on_trim_single
        )
        btn_trim.pack(side=tk.LEFT, padx=(0, 3))

        btn_restart = ctk.CTkButton(
            action_row,
            text="Restart",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            width=95,
            height=30,
            command=self._on_restart_single
        )
        btn_restart.pack(side=tk.LEFT, padx=3)

        btn_kill = ctk.CTkButton(
            action_row,
            text="Terminate",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#7f1d1d",
            hover_color=COLOR_ACCENT_RED,
            width=95,
            height=30,
            command=self._on_kill_single
        )
        btn_kill.pack(side=tk.RIGHT, padx=(3, 0))

    def _build_rules_tab(self, parent):
        header_f = ctk.CTkFrame(parent, fg_color="transparent")
        header_f.pack(fill=tk.X, padx=12, pady=8)

        lbl = ctk.CTkLabel(
            header_f,
            text="AUTOMATION RULES ENGINE (Matches Process Lasso Pro)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        lbl.pack(side=tk.LEFT)

        btn_reload = ctk.CTkButton(
            header_f,
            text="Reload from JSON",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=130,
            height=28,
            command=self._reload_rules
        )
        btn_reload.pack(side=tk.RIGHT)

        self.rules_box = ctk.CTkTextbox(
            parent,
            fg_color=COLOR_BG,
            text_color=COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8
        )
        self.rules_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self._reload_rules()

    def _build_engine_tab(self, parent):
        scroll_f = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_f.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # ProBalance Settings Card
        pb_card = ctk.CTkFrame(scroll_f, fg_color=COLOR_CARD, corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        pb_card.pack(fill=tk.X, pady=6)

        ctk.CTkLabel(pb_card, text="PROBALANCE HEURISTIC PARAMETERS", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor=tk.W, padx=14, pady=(10, 6))

        # CPU Trigger Slider
        self.slider_cpu = self._create_slider_row(pb_card, "System CPU Trigger Threshold (%):", 65, 30, 95)
        self.slider_proc_cpu = self._create_slider_row(pb_card, "Per-Process CPU Trigger (%):", 20, 5, 60)
        self.slider_duration = self._create_slider_row(pb_card, "Restraint Duration Cooldown (seconds):", 10, 2, 60)

        btn_save_engine = ctk.CTkButton(
            pb_card,
            text="Save Parameters to Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            height=30,
            command=self._save_engine_params
        )
        btn_save_engine.pack(anchor=tk.W, padx=14, pady=(10, 14))

    def _create_slider_row(self, parent, label_text, default_val, min_val, max_val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, padx=14, pady=4)

        lbl = ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_SECONDARY, width=280, anchor="w")
        lbl.pack(side=tk.LEFT)

        val_lbl = ctk.CTkLabel(row, text=str(default_val), font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), width=40)
        val_lbl.pack(side=tk.RIGHT)

        slider = ctk.CTkSlider(
            row,
            from_=min_val,
            to=max_val,
            number_of_steps=(max_val - min_val),
            command=lambda v: val_lbl.configure(text=str(int(v)))
        )
        slider.set(default_val)
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
        return slider

    def _build_logs_tab(self, parent):
        self.txt_journal = ctk.CTkTextbox(
            parent,
            fg_color=COLOR_BG,
            text_color=COLOR_TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8
        )
        self.txt_journal.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

    def _setup_context_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg=COLOR_TEXT_PRIMARY, activebackground="#2563eb", activeforeground=COLOR_TEXT_PRIMARY)
        self.menu.add_command(label="Priority -> HIGH", command=lambda: self._quick_set_prio("HIGH"))
        self.menu.add_command(label="Priority -> ABOVE_NORMAL", command=lambda: self._quick_set_prio("ABOVE_NORMAL"))
        self.menu.add_command(label="Priority -> NORMAL", command=lambda: self._quick_set_prio("NORMAL"))
        self.menu.add_command(label="Priority -> BELOW_NORMAL", command=lambda: self._quick_set_prio("BELOW_NORMAL"))
        self.menu.add_separator()
        self.menu.add_command(label="Affinity -> P-Cores Only", command=lambda: self._quick_set_aff("P_CORES"))
        self.menu.add_command(label="Affinity -> All Cores", command=lambda: self._quick_set_aff("ALL_CORES"))
        self.menu.add_separator()
        self.menu.add_command(label="Trim RAM Working Set", command=self._on_trim_single)
        self.menu.add_command(label="Toggle ProBalance Exclusion", command=self._on_toggle_exclude)
        self.menu.add_separator()
        self.menu.add_command(label="Restart Process", command=self._on_restart_single)
        self.menu.add_command(label="Terminate Process", command=self._on_kill_single)

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self._on_process_selected(None)
            self.menu.post(event.x_root, event.y_root)

    def _start_background_polling(self):
        def poll_loop():
            while self.polling_active:
                try:
                    state = self.controller.refresh_state()
                    self.after(0, self._render_live_state, state)
                except Exception:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()

    def _render_live_state(self, state: dict):
        cpu = state.get("system_cpu", 0.0)
        ram = state.get("system_ram", 0.0)
        restrained = state.get("restrained_count", 0)

        self.badge_cpu.configure(
            text=f"CPU: {cpu:.1f}%",
            text_color=COLOR_ACCENT_RED if cpu > 75 else COLOR_ACCENT_GREEN
        )
        self.badge_ram.configure(text=f"RAM: {ram:.1f}%")

        if restrained > 0:
            self.badge_pb.configure(text=f"PROBALANCE: RESTRAINING ({restrained})", text_color=COLOR_ACCENT_AMBER)
        else:
            self.badge_pb.configure(text="PROBALANCE: ACTIVE", text_color=COLOR_ACCENT_GREEN)

        self.lbl_status.configure(
            text=f"Governor: Native Ring-3 Active • Zero-GC • Monitored Processes: {state.get('processes_count', 0)} | System Responsive"
        )

        # Update real-time canvas graph
        self.graph.update_history(
            state.get("cpu_history", []),
            state.get("ram_history", []),
            state.get("restraint_history", [])
        )

        # Update per-core load indicators
        per_core = state.get("per_core_cpu", [])
        if hasattr(self, "core_widgets") and per_core:
            for idx, (pbar, lbl) in enumerate(self.core_widgets):
                if idx < len(per_core):
                    val = per_core[idx]
                    pbar.set(val / 100.0)
                    lbl.configure(text=f"{val:.1f}%")

        self._render_process_table()
        self._update_logs_view()

    def _render_process_table(self):
        query = self.search_entry.get()
        active_only = (self.filter_mode == "active")

        procs = self.controller.get_filtered_processes(
            search_query=query,
            sort_by=self.sort_col,
            reverse=self.sort_desc,
            active_only=active_only
        )

        if self.filter_mode == "restrained":
            procs = [p for p in procs if p["is_restrained"]]

        cur_sel = self.tree.selection()
        selected_iid = cur_sel[0] if cur_sel else None

        self.tree.delete(*self.tree.get_children())
        for p in procs[:180]:
            status_text = "NORMAL"
            if p["is_restrained"]:
                status_text = "[RESTRAINED]"
            elif p["is_foreground"]:
                status_text = "[FOREGROUND]"
            elif p["is_excluded"]:
                status_text = "[EXCLUDED]"

            iid = str(p["pid"])
            self.tree.insert("", tk.END, iid=iid, values=(
                p["pid"],
                p["name"],
                f"{p['cpu_percent']:.1f}",
                f"{p['memory_mb']:.1f}",
                p["priority"],
                p["threads"],
                status_text
            ))

        if selected_iid and self.tree.exists(selected_iid):
            self.tree.selection_set(selected_iid)

    def _update_logs_view(self):
        self.txt_journal.delete("1.0", tk.END)
        for line in self.controller.events_log[-40:]:
            self.txt_journal.insert(tk.END, line + "\n")
        self.txt_journal.see(tk.END)

    def _on_filter_changed(self, value):
        if value == "Active (>0% CPU)":
            self.filter_mode = "active"
        elif value == "Restrained Only":
            self.filter_mode = "restrained"
        else:
            self.filter_mode = "all"
        self._render_process_table()

    def _sort_table(self, col: str):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True
        self._render_process_table()

    def _on_process_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        self.selected_pid = pid

        target = next((p for p in self.controller.cached_processes if p["pid"] == pid), None)
        if target:
            self.selected_name = target["name"]
            self.lbl_selected_title.configure(
                text=f"{target['name']} (PID: {pid})\nCPU: {target['cpu_percent']}% | RAM: {target['memory_mb']} MB | Threads: {target['threads']}",
                text_color=COLOR_TEXT_PRIMARY
            )
            self.opt_prio.set(target["priority"])
            self.switch_exclude.select() if target["is_excluded"] else self.switch_exclude.deselect()

    def _on_apply_tuning(self):
        if not self.selected_pid:
            messagebox.showinfo("No Selection", "Please select a process from the table first.")
            return

        prio = self.opt_prio.get()
        affinity = self.opt_aff.get()
        io_prio = self.opt_io.get()
        persistent = bool(self.chk_persistent.get())

        self.controller.apply_priority(self.selected_pid, prio, persistent=persistent)
        self.controller.apply_affinity(self.selected_pid, affinity, persistent=persistent)
        self.controller.apply_io_priority(self.selected_pid, io_prio, persistent=persistent)
        messagebox.showinfo("Proxessor", f"Successfully applied tuning to PID {self.selected_pid} ({self.selected_name})!")

    def _quick_set_prio(self, prio):
        if self.selected_pid:
            self.controller.apply_priority(self.selected_pid, prio)

    def _quick_set_aff(self, aff):
        if self.selected_pid:
            self.controller.apply_affinity(self.selected_pid, aff)

    def _on_toggle_eco(self):
        if self.selected_pid:
            enable = bool(self.switch_eco.get())
            self.controller.apply_eco_qos(self.selected_pid, enable)

    def _on_toggle_exclude(self):
        if self.selected_name:
            self.controller.toggle_probalance_exclusion(self.selected_name)

    def _on_trim_single(self):
        if self.selected_pid:
            self.controller.trim_process(self.selected_pid)

    def _on_restart_single(self):
        if self.selected_pid:
            self.controller.restart_process(self.selected_pid)

    def _on_kill_single(self):
        if self.selected_pid:
            if messagebox.askyesno("Confirm Terminate", f"Terminate {self.selected_name} (PID: {self.selected_pid})?"):
                self.controller.kill_process(self.selected_pid, force=True)

    def _on_smart_trim(self):
        trimmed = self.controller.trim_all()
        messagebox.showinfo("SmartTrim", f"Working set successfully flushed across {trimmed} monitored processes.")

    def _on_power_scheme_change(self, scheme):
        self.controller.change_power_scheme(scheme)

    def _reload_rules(self):
        try:
            import json
            with open(self.controller.config_path, "r", encoding="utf-8") as f:
                content = json.dumps(json.load(f), indent=2)
            self.rules_box.delete("1.0", tk.END)
            self.rules_box.insert(tk.END, content)
        except Exception as e:
            self.rules_box.insert(tk.END, f"Error loading rules: {e}")

    def _build_cores_tab(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill=tk.X, padx=12, pady=(8, 4))

        topo = self.controller.topology
        info_txt = (
            f"Heterogeneous CPU Topology: {topo.total_cores} Logical Cores | "
            f"P-Cores (Perf): {len(topo.p_cores)} ({topo.p_cores}) | "
            f"E-Cores (Eff): {len(topo.e_cores)} ({topo.e_cores})"
        )
        lbl_info = ctk.CTkLabel(
            header,
            text=info_txt,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        lbl_info.pack(side=tk.LEFT)

        self.cores_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLOR_BG, corner_radius=8)
        self.cores_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.core_widgets = []
        p_set = set(topo.p_cores)

        # 4 columns grid
        for i in range(topo.total_cores):
            is_p = i in p_set
            card = ctk.CTkFrame(self.cores_scroll, fg_color=COLOR_CARD, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
            row = i // 4
            col = i % 4
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.cores_scroll.grid_columnconfigure(col, weight=1)

            tag = "P-Core" if is_p else "E-Core"
            tag_col = COLOR_ACCENT_GREEN if is_p else COLOR_ACCENT_BLUE

            lbl_title = ctk.CTkLabel(
                card,
                text=f"Core {i} [{tag}]",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=tag_col
            )
            lbl_title.pack(anchor="w", padx=8, pady=(4, 2))

            pbar = ctk.CTkProgressBar(card, height=10, corner_radius=4, progress_color=tag_col, fg_color="#1e293b")
            pbar.pack(fill=tk.X, padx=8, pady=2)
            pbar.set(0.0)

            lbl_val = ctk.CTkLabel(
                card,
                text="0.0%",
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=COLOR_TEXT_SECONDARY
            )
            lbl_val.pack(anchor="e", padx=8, pady=(0, 4))

            self.core_widgets.append((pbar, lbl_val))

    def _build_sockets_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.socket_filter = ctk.CTkEntry(
            toolbar,
            placeholder_text="Filter port (e.g. 80, 443, 8080), IP, or process...",
            width=320,
            height=32,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER
        )
        self.socket_filter.pack(side=tk.LEFT, padx=(0, 8))
        self.socket_filter.bind("<KeyRelease>", lambda e: self._refresh_sockets())

        btn_refresh = ctk.CTkButton(
            toolbar,
            text="Refresh Sockets",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            width=120,
            height=32,
            command=self._refresh_sockets
        )
        btn_refresh.pack(side=tk.LEFT, padx=4)

        btn_kill_sock = ctk.CTkButton(
            toolbar,
            text="Terminate Socket PID",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#7f1d1d",
            hover_color=COLOR_ACCENT_RED,
            width=140,
            height=32,
            command=self._on_kill_socket_process
        )
        btn_kill_sock.pack(side=tk.LEFT, padx=4)

        table_frame = tk.Frame(parent, bg=COLOR_CARD)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        columns = ("proto", "local", "remote", "state", "name", "pid")
        self.socket_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.socket_tree.heading("proto", text="PROTO")
        self.socket_tree.heading("local", text="LOCAL ENDPOINT")
        self.socket_tree.heading("remote", text="REMOTE ENDPOINT")
        self.socket_tree.heading("state", text="STATE")
        self.socket_tree.heading("name", text="PROCESS NAME")
        self.socket_tree.heading("pid", text="PID")

        self.socket_tree.column("proto", width=70, anchor="center")
        self.socket_tree.column("local", width=180, anchor="w")
        self.socket_tree.column("remote", width=180, anchor="w")
        self.socket_tree.column("state", width=110, anchor="center")
        self.socket_tree.column("name", width=180, anchor="w")
        self.socket_tree.column("pid", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.socket_tree.yview)
        self.socket_tree.configure(yscrollcommand=scrollbar.set)
        self.socket_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_socket_status = ctk.CTkLabel(
            parent,
            text="Active Endpoints: 0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_socket_status.pack(anchor="w", padx=12, pady=(0, 6))
        self.after(500, self._refresh_sockets)

    def _refresh_sockets(self):
        query = self.socket_filter.get().strip() if hasattr(self, "socket_filter") else ""
        def fetch():
            conns = self.controller.list_connections(query)
            self.after(0, self._render_socket_table, conns)
        threading.Thread(target=fetch, daemon=True).start()

    def _render_socket_table(self, conns):
        self.socket_tree.delete(*self.socket_tree.get_children())
        for c in conns:
            local = f"{c.get('local_addr')}:{c.get('local_port')}"
            remote = f"{c.get('remote_addr')}:{c.get('remote_port')}" if c.get('remote_addr') else "*:*"
            self.socket_tree.insert("", tk.END, values=(
                c.get("proto", "TCP"),
                local,
                remote,
                c.get("state", "UNKNOWN"),
                c.get("name", "Unknown"),
                c.get("pid", 0)
            ))
        self.lbl_socket_status.configure(text=f"Active Endpoints Listed: {len(conns)}")

    def _on_kill_socket_process(self):
        selected = self.socket_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a network connection from the table first.")
            return
        vals = self.socket_tree.item(selected[0], "values")
        pid = int(vals[5])
        name = vals[4]
        if messagebox.askyesno("Confirm Terminate", f"Terminate process '{name}' (PID {pid}) holding this socket?"):
            ok = self.controller.terminate_process(pid)
            if ok:
                messagebox.showinfo("Terminated", f"Successfully terminated {name} (PID {pid}).")
                self._refresh_sockets()
            else:
                messagebox.showerror("Error", f"Could not terminate PID {pid}.")

    def _build_filelock_tab(self, parent):
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=10, pady=(8, 4))

        lbl_desc = ctk.CTkLabel(
            top_bar,
            text="Inspect which processes are locking a file or folder (Windows Restart Manager)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_SECONDARY
        )
        lbl_desc.pack(anchor="w", pady=(0, 4))

        input_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        input_row.pack(fill=tk.X)

        self.entry_lock_path = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter absolute path to file or folder...",
            height=32,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER
        )
        self.entry_lock_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_browse_f = ctk.CTkButton(
            input_row,
            text="File...",
            width=65,
            height=32,
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            command=self._browse_lock_file
        )
        btn_browse_f.pack(side=tk.LEFT, padx=3)

        btn_browse_d = ctk.CTkButton(
            input_row,
            text="Folder...",
            width=70,
            height=32,
            fg_color="#1e293b",
            hover_color=COLOR_CARD_HOVER,
            command=self._browse_lock_dir
        )
        btn_browse_d.pack(side=tk.LEFT, padx=3)

        btn_scan = ctk.CTkButton(
            input_row,
            text="Scan Lockers",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=110,
            height=32,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._scan_file_locks
        )
        btn_scan.pack(side=tk.LEFT, padx=(3, 0))

        table_frame = tk.Frame(parent, bg=COLOR_CARD)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        columns = ("pid", "name", "kind", "service")
        self.lock_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.lock_tree.heading("pid", text="PID")
        self.lock_tree.heading("name", text="PROCESS NAME / APP")
        self.lock_tree.heading("kind", text="APPLICATION TYPE")
        self.lock_tree.heading("service", text="SERVICE NAME")

        self.lock_tree.column("pid", width=80, anchor="center")
        self.lock_tree.column("name", width=260, anchor="w")
        self.lock_tree.column("kind", width=150, anchor="center")
        self.lock_tree.column("service", width=180, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.lock_tree.yview)
        self.lock_tree.configure(yscrollcommand=scrollbar.set)
        self.lock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_bar = ctk.CTkFrame(parent, fg_color="transparent")
        bottom_bar.pack(fill=tk.X, padx=10, pady=(2, 8))

        self.lbl_lock_status = ctk.CTkLabel(
            bottom_bar,
            text="Status: Ready to scan target resource.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_lock_status.pack(side=tk.LEFT)

        btn_kill_locker = ctk.CTkButton(
            bottom_bar,
            text="Terminate Selected Locker",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#7f1d1d",
            hover_color=COLOR_ACCENT_RED,
            height=30,
            command=self._on_kill_file_locker
        )
        btn_kill_locker.pack(side=tk.RIGHT)

    def _browse_lock_file(self):
        fn = filedialog.askopenfilename(title="Select File to Inspect Locks")
        if fn:
            self.entry_lock_path.delete(0, tk.END)
            self.entry_lock_path.insert(0, fn)
            self._scan_file_locks()

    def _browse_lock_dir(self):
        d = filedialog.askdirectory(title="Select Folder to Inspect Locks")
        if d:
            self.entry_lock_path.delete(0, tk.END)
            self.entry_lock_path.insert(0, d)
            self._scan_file_locks()

    def _scan_file_locks(self):
        target = self.entry_lock_path.get().strip()
        if not target:
            messagebox.showinfo("Path Required", "Please specify or browse a file or directory path.")
            return

        self.lbl_lock_status.configure(text=f"Scanning '{target}' via Restart Manager...")
        def run():
            lockers = self.controller.find_file_lockers(target)
            self.after(0, self._render_lockers, lockers, target)
        threading.Thread(target=run, daemon=True).start()

    def _render_lockers(self, lockers, path):
        self.lock_tree.delete(*self.lock_tree.get_children())
        if not lockers:
            self.lbl_lock_status.configure(
                text=f"No active locks found for '{path}'. Resource is unlocked.",
                text_color=COLOR_ACCENT_GREEN
            )
            return

        for item in lockers:
            self.lock_tree.insert("", tk.END, values=(
                item.get("pid"),
                item.get("app_name"),
                item.get("kind"),
                item.get("service") or "-"
            ))
        self.lbl_lock_status.configure(
            text=f"Found {len(lockers)} locking process(es) holding '{path}'!",
            text_color=COLOR_ACCENT_AMBER
        )

    def _on_kill_file_locker(self):
        selected = self.lock_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a locking process from the table first.")
            return
        vals = self.lock_tree.item(selected[0], "values")
        pid = int(vals[0])
        name = vals[1]
        if messagebox.askyesno("Confirm Terminate", f"Terminate locker process '{name}' (PID {pid})?"):
            ok = self.controller.terminate_process(pid)
            if ok:
                messagebox.showinfo("Unlocked", f"Successfully terminated locker {name} (PID {pid}).")
                self._scan_file_locks()
            else:
                messagebox.showerror("Error", f"Failed to terminate PID {pid}.")

    def _save_engine_params(self):
        try:
            import json
            with open(self.controller.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            pb = data.get("probalance", {})
            pb["cpu_trigger_threshold_percent"] = float(int(self.slider_cpu.get()))
            pb["per_process_cpu_trigger_percent"] = float(int(self.slider_proc_cpu.get()))
            pb["restraint_duration_seconds"] = int(self.slider_duration.get())
            data["probalance"] = pb

            with open(self.controller.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.controller.rule_manager.load()
            self.controller.probalance = self.controller.rule_manager.probalance_config
            messagebox.showinfo("Saved", "ProBalance parameters saved and applied successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save engine parameters: {e}")

def launch_gui(config_path: str = "config/default_rules.json"):
    app = ProxessorApp(config_path)
    app.mainloop()

ProxessorGUI = ProxessorApp

if __name__ == "__main__":
    launch_gui()
