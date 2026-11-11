"""Proxessor — Windows Native Process Governor & Task Manager.
Engineered with native Windows Win32 styling, high density, and zero AI slop.
"""

import os
import sys
import threading
import time
import ctypes
from typing import Optional, Dict, List

# Instantly hide any attached console window
try:
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)
except Exception:
    pass

# Ensure project root is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.proxessor.gui.controller import GUIController
from src.proxessor.gui.tray import SystemTrayManager

# ---------------------------------------------------------------------------
# Windows 11 Dark Mode Palette Tokens (Native Fluent / Win32 Dense)
# ---------------------------------------------------------------------------
WIN_BG = "#1f1f1f"          # Standard Windows 11 Dark Surface
WIN_SURFACE = "#252526"     # Controls & Panels
WIN_SURFACE_ALT = "#2d2d2d" # Headers & Toolbars
WIN_BORDER = "#333333"      # Subtle separator line
WIN_BORDER_LIGHT = "#3e3e42"# Control border
WIN_TEXT = "#f3f3f3"        # Primary Text
WIN_TEXT_MUTED = "#8e8e8e"  # Secondary / Placeholder Text
WIN_ACCENT = "#0078d4"      # Windows Blue Accent
WIN_SELECT = "#094771"      # Windows List Selection Blue
WIN_SELECT_TEXT = "#ffffff"

# Oscilloscope Graph Palette (Windows Task Manager Classic)
GRAPH_BG = "#121a14"        # Very dark green-tinted charcoal
GRAPH_GRID = "#1b2b1f"      # Subtle gridline
GRAPH_CPU = "#00e676"       # Phosphor Green (1px crisp)
GRAPH_RAM = "#00b0ff"       # Windows Sky Blue (1px crisp)
GRAPH_RESTRAINT = "#ff9100" # Warning Amber (ProBalance action line)

# Fonts: Standard Windows System Typography
FONT_UI = ("Segoe UI", 9)
FONT_UI_BOLD = ("Segoe UI", 9, "bold")
FONT_UI_TITLE = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 9)
FONT_STATUS = ("Segoe UI", 8)


class OscilloscopeStrip(tk.Canvas):
    """Task Manager style scrolling history graph with fine gridlines."""

    def __init__(self, parent, height: int = 44, **kwargs):
        super().__init__(
            parent,
            height=height,
            bg=GRAPH_BG,
            highlightthickness=1,
            highlightbackground=WIN_BORDER,
            **kwargs
        )
        self.bind("<Configure>", lambda e: self.redraw())
        self.cpu_data = [0.0] * 60
        self.ram_data = [0.0] * 60
        self.restraint_data = [0.0] * 60

    def update_history(self, cpu_history: list, ram_history: list, restraint_history: list):
        self.cpu_data = cpu_history[-60:] if len(cpu_history) >= 60 else ([0.0] * (60 - len(cpu_history)) + cpu_history)
        self.ram_data = ram_history[-60:] if len(ram_history) >= 60 else ([0.0] * (60 - len(ram_history)) + ram_history)
        self.restraint_data = restraint_history[-60:] if len(restraint_history) >= 60 else ([0.0] * (60 - len(restraint_history)) + restraint_history)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        # 1. Subtle horizontal gridlines (Task Manager style 25%, 50%, 75%)
        for pct in (0.25, 0.50, 0.75):
            y = int(h - (h * pct))
            self.create_line(0, y, w, y, fill=GRAPH_GRID, width=1)
            self.create_text(w - 24, y - 5, text=f"{int(pct*100)}%", fill="#3b5240", font=("Consolas", 7))

        # Vertical gridlines (every 10 data points)
        step_x = w / 59.0
        for i in range(0, 60, 10):
            x = int(i * step_x)
            self.create_line(x, 0, x, h, fill=GRAPH_GRID, width=1)

        # 2. Draw Plot Series
        def draw_line(data: list, color: str, width: int = 1):
            pts = []
            for i, val in enumerate(data):
                x = i * step_x
                clamped = max(0.0, min(100.0, val))
                y = h - (clamped / 100.0 * (h - 4)) - 2
                pts.extend([x, y])
            if len(pts) >= 4:
                self.create_line(pts, fill=color, width=width)

        draw_line(self.ram_data, GRAPH_RAM, 1)
        draw_line(self.restraint_data, GRAPH_RESTRAINT, 1)
        draw_line(self.cpu_data, GRAPH_CPU, 1)


class ProxessorApp(tk.Tk):
    """Native Windows Process Governor and Optimization Utility."""

    def __init__(self, config_path: str = "config/default_rules.json"):
        super().__init__()
        self.title("Proxessor — Process Governor & System Optimization")
        self.geometry("1180x720")
        self.minsize(980, 560)
        self.configure(bg=WIN_BG)

        # Apply Windows 11 Immersive Dark Mode to Win32 Title Bar
        self._apply_windows_dark_theme()

        self.controller = GUIController(config_path)
        self.selected_pid: Optional[int] = None
        self.selected_name: str = ""
        self.sort_col = "cpu_percent"
        self.sort_desc = True
        self.polling_active = True
        self.tray_notified = False

        # State Variables
        self.var_active_only = tk.BooleanVar(value=False)
        self.var_restrained_only = tk.BooleanVar(value=False)
        self.var_tree_view = tk.BooleanVar(value=False)
        self.var_probalance_enabled = tk.BooleanVar(value=True)
        self.var_always_on_top = tk.BooleanVar(value=False)
        self.var_close_to_tray = tk.BooleanVar(value=True)
        self.update_interval_ms = 1000

        self._configure_ttk_styles()
        self._setup_native_menubar()
        self._setup_layout()
        self._setup_context_menu()
        self._start_background_polling()

        # System Tray Integration
        self.tray_manager = SystemTrayManager(
            on_show=self._show_window_from_tray,
            on_exit=self._exit_full_application,
            on_smart_trim=self._on_smart_trim,
            on_power_change=self._on_power_scheme_change
        )
        self.tray_manager.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close_to_tray)

        self.deiconify()
        self.lift()
        self.focus_force()

    def _apply_windows_dark_theme(self):
        """Enables dark title bar on Windows 10/11 via Desktop Window Manager."""
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

    def _configure_ttk_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Treeview (Data grid)
        style.configure(
            "Treeview",
            background=WIN_BG,
            foreground=WIN_TEXT,
            fieldbackground=WIN_BG,
            bordercolor=WIN_BORDER,
            borderwidth=0,
            font=FONT_UI,
            rowheight=21
        )
        style.map(
            "Treeview",
            background=[("selected", WIN_SELECT)],
            foreground=[("selected", WIN_SELECT_TEXT)]
        )

        style.configure(
            "Treeview.Heading",
            background=WIN_SURFACE_ALT,
            foreground=WIN_TEXT,
            relief="flat",
            borderwidth=1,
            font=FONT_UI_BOLD,
            padding=[6, 4]
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#383838")]
        )

        # Notebook (Tabs)
        style.configure(
            "TNotebook",
            background=WIN_BG,
            borderwidth=0,
            tabmargins=[2, 2, 2, 0]
        )
        style.configure(
            "TNotebook.Tab",
            background=WIN_SURFACE,
            foreground=WIN_TEXT_MUTED,
            padding=[12, 4],
            font=FONT_UI,
            borderwidth=1,
            bordercolor=WIN_BORDER
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", WIN_BG), ("active", WIN_SURFACE_ALT)],
            foreground=[("selected", WIN_TEXT), ("active", WIN_TEXT)],
            bordercolor=[("selected", WIN_BORDER)]
        )

        # Standard controls
        style.configure("TFrame", background=WIN_BG)
        style.configure("Surface.TFrame", background=WIN_SURFACE)
        style.configure("TLabel", background=WIN_BG, foreground=WIN_TEXT, font=FONT_UI)
        style.configure("TCheckbutton", background=WIN_SURFACE_ALT, foreground=WIN_TEXT, font=FONT_UI)
        style.configure("TButton", font=FONT_UI, padding=[8, 3])

    def _setup_native_menubar(self):
        """Builds standard Windows native top menu bar."""
        menubar = tk.Menu(self)

        # 1. File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Run New Task...", command=self._run_new_task)
        file_menu.add_separator()
        file_menu.add_command(label="Exit Proxessor", command=self._exit_full_application, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=file_menu)

        # 2. View
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh Now", command=self._force_refresh, accelerator="F5")
        self.bind("<F5>", lambda e: self._force_refresh())
        self.bind("<Control-f>", lambda e: self.entry_filter.focus_set())

        speed_menu = tk.Menu(view_menu, tearoff=0)
        self.speed_var = tk.IntVar(value=1000)
        speed_menu.add_radiobutton(label="High (0.5s)", variable=self.speed_var, value=500, command=self._on_speed_change)
        speed_menu.add_radiobutton(label="Normal (1.0s)", variable=self.speed_var, value=1000, command=self._on_speed_change)
        speed_menu.add_radiobutton(label="Low (2.0s)", variable=self.speed_var, value=2000, command=self._on_speed_change)
        speed_menu.add_radiobutton(label="Paused", variable=self.speed_var, value=0, command=self._on_speed_change)
        view_menu.add_cascade(label="Update Speed", menu=speed_menu)

        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Active Only (>0% CPU)", variable=self.var_active_only, command=self._render_process_table)
        view_menu.add_checkbutton(label="Show Restrained Only", variable=self.var_restrained_only, command=self._render_process_table)
        menubar.add_cascade(label="View", menu=view_menu)

        # 3. Options
        opt_menu = tk.Menu(menubar, tearoff=0)
        opt_menu.add_checkbutton(label="ProBalance Dynamic Restraint Enabled", variable=self.var_probalance_enabled, command=self._toggle_probalance)
        opt_menu.add_checkbutton(label="Always on Top", variable=self.var_always_on_top, command=self._toggle_always_on_top)
        opt_menu.add_separator()
        opt_menu.add_checkbutton(label="Close to System Tray (Minimize)", variable=self.var_close_to_tray)
        menubar.add_cascade(label="Options", menu=opt_menu)

        # 4. Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="SmartTrim RAM (Flush Working Sets)", command=self._on_smart_trim)
        tools_menu.add_separator()
        tools_menu.add_command(label="Windows Task Manager", command=lambda: os.system("start taskmgr.exe"))
        tools_menu.add_command(label="Resource Monitor", command=lambda: os.system("start resmon.exe"))
        tools_menu.add_command(label="Windows Services Management", command=lambda: os.system("start services.msc"))
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # 5. Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About Proxessor...", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _setup_layout(self):
        # 1. Native Toolbar Strip (Tinggi 32px, padat, rapi)
        toolbar = tk.Frame(self, bg=WIN_SURFACE_ALT, height=32, highlightthickness=1, highlightbackground=WIN_BORDER)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        # Filter Box
        lbl_f = tk.Label(toolbar, text="Filter:", bg=WIN_SURFACE_ALT, fg=WIN_TEXT_MUTED, font=FONT_UI)
        lbl_f.pack(side=tk.LEFT, padx=(8, 4), pady=4)

        self.entry_filter = tk.Entry(
            toolbar,
            bg=WIN_BG,
            fg=WIN_TEXT,
            insertbackground=WIN_TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=WIN_BORDER_LIGHT,
            font=FONT_UI,
            width=22
        )
        self.entry_filter.pack(side=tk.LEFT, padx=2, pady=4)
        self.entry_filter.bind("<KeyRelease>", lambda e: self._render_process_table())

        btn_clear = tk.Button(
            toolbar,
            text="×",
            bg=WIN_SURFACE_ALT,
            fg=WIN_TEXT_MUTED,
            relief="flat",
            activebackground=WIN_SURFACE,
            activeforeground=WIN_TEXT,
            font=("Segoe UI", 9, "bold"),
            command=self._clear_filter,
            padx=4,
            pady=0
        )
        btn_clear.pack(side=tk.LEFT, padx=(0, 6))

        # Checkboxes
        chk_act = tk.Checkbutton(
            toolbar,
            text="Active Only",
            variable=self.var_active_only,
            bg=WIN_SURFACE_ALT,
            fg=WIN_TEXT,
            activebackground=WIN_SURFACE_ALT,
            activeforeground=WIN_TEXT,
            selectcolor=WIN_BG,
            font=FONT_UI,
            command=self._render_process_table
        )
        chk_act.pack(side=tk.LEFT, padx=4)

        chk_tree = tk.Checkbutton(
            toolbar,
            text="Tree View",
            variable=self.var_tree_view,
            bg=WIN_SURFACE_ALT,
            fg=WIN_TEXT,
            activebackground=WIN_SURFACE_ALT,
            activeforeground=WIN_TEXT,
            selectcolor=WIN_BG,
            font=FONT_UI,
            command=self._render_process_table
        )
        chk_tree.pack(side=tk.LEFT, padx=4)

        # Separator
        sep1 = tk.Frame(toolbar, width=1, bg=WIN_BORDER, height=20)
        sep1.pack(side=tk.LEFT, padx=8, pady=6)

        # Quick Actions
        btn_trim = tk.Button(
            toolbar,
            text="Flush RAM (SmartTrim)",
            bg=WIN_SURFACE,
            fg=WIN_TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=WIN_BORDER_LIGHT,
            activebackground=WIN_ACCENT,
            activeforeground="#ffffff",
            font=FONT_UI,
            padx=8,
            pady=1,
            command=self._on_smart_trim
        )
        btn_trim.pack(side=tk.LEFT, padx=4)

        # Power Plan Menu
        self.power_var = tk.StringVar(value="HIGH_PERFORMANCE")
        opt_power = ttk.Combobox(
            toolbar,
            textvariable=self.power_var,
            values=["HIGH_PERFORMANCE", "BALANCED", "ULTIMATE_PERFORMANCE", "POWER_SAVER"],
            state="readonly",
            width=20,
            font=FONT_UI
        )
        opt_power.pack(side=tk.LEFT, padx=4)
        opt_power.bind("<<ComboboxSelected>>", lambda e: self._on_power_scheme_change(self.power_var.get()))

        btn_kill = tk.Button(
            toolbar,
            text="End Process (Del)",
            bg="#3b1f1f",
            fg="#ff8888",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#552222",
            activebackground="#772222",
            activeforeground="#ffffff",
            font=FONT_UI,
            padx=8,
            pady=1,
            command=self._on_kill_single
        )
        btn_kill.pack(side=tk.LEFT, padx=4)

        # Right-aligned Live Telemetry Indicators
        self.lbl_telemetry_top = tk.Label(
            toolbar,
            text="CPU: 0.0%  |  RAM: 0.0%  |  ProBalance: Active",
            bg=WIN_SURFACE_ALT,
            fg=WIN_TEXT,
            font=FONT_UI_BOLD
        )
        self.lbl_telemetry_top.pack(side=tk.RIGHT, padx=12)

        # 2. Oscilloscope History Strip (Tinggi 42px Task Manager Style)
        graph_box = tk.Frame(self, bg=WIN_BG, height=44)
        graph_box.pack(fill=tk.X, side=tk.TOP, padx=6, pady=(4, 2))
        graph_box.pack_propagate(False)

        self.graph = OscilloscopeStrip(graph_box, height=42)
        self.graph.pack(fill=tk.BOTH, expand=True)

        # 3. Main Notebook Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 2))

        # Tabs
        self.tab_procs = ttk.Frame(self.notebook)
        self.tab_topology = ttk.Frame(self.notebook)
        self.tab_sockets = ttk.Frame(self.notebook)
        self.tab_filelock = ttk.Frame(self.notebook)
        self.tab_rules = ttk.Frame(self.notebook)
        self.tab_journal = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_procs, text="Processes")
        self.notebook.add(self.tab_topology, text="CPU Topology")
        self.notebook.add(self.tab_sockets, text="Network Sockets")
        self.notebook.add(self.tab_filelock, text="File Lock Hunter")
        self.notebook.add(self.tab_rules, text="Active Rules & Settings")
        self.notebook.add(self.tab_journal, text="Activity Journal")

        self._build_processes_tab()
        self._build_topology_tab()
        self._build_sockets_tab()
        self._build_filelock_tab()
        self._build_rules_tab()
        self._build_journal_tab()

        # 4. Native 3-Section Status Bar (Tinggi 24px)
        status_bar = tk.Frame(self, bg=WIN_SURFACE, height=24, highlightthickness=1, highlightbackground=WIN_BORDER)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.sb_procs = tk.Label(status_bar, text="Processes: 0 | Active: 0", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_STATUS)
        self.sb_procs.pack(side=tk.LEFT, padx=10)

        sep_sb1 = tk.Frame(status_bar, width=1, bg=WIN_BORDER, height=16)
        sep_sb1.pack(side=tk.LEFT, padx=4, pady=4)

        self.sb_metrics = tk.Label(status_bar, text="CPU: 0.0% | RAM: 0.0%", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_STATUS)
        self.sb_metrics.pack(side=tk.LEFT, padx=10)

        sep_sb2 = tk.Frame(status_bar, width=1, bg=WIN_BORDER, height=16)
        sep_sb2.pack(side=tk.LEFT, padx=4, pady=4)

        self.sb_engine = tk.Label(status_bar, text="ProBalance: Active (0 restrained) • Native Ring-3 Engine", bg=WIN_SURFACE, fg=GRAPH_CPU, font=FONT_STATUS)
        self.sb_engine.pack(side=tk.LEFT, padx=10)

    # -----------------------------------------------------------------------
    # TAB 1: PROCESSES
    # -----------------------------------------------------------------------
    def _build_processes_tab(self):
        container = tk.Frame(self.tab_procs, bg=WIN_BG)
        container.pack(fill=tk.BOTH, expand=True)

        columns = ("pid", "name", "cpu", "ram", "prio", "aff", "threads", "status")
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headers = [
            ("pid", "PID", 70, "e"),
            ("name", "Process Name", 250, "w"),
            ("cpu", "CPU %", 75, "e"),
            ("ram", "RAM (MB)", 90, "e"),
            ("prio", "Priority", 110, "center"),
            ("aff", "Affinity", 100, "center"),
            ("threads", "Threads", 65, "e"),
            ("status", "Status", 130, "w")
        ]

        for col_id, title, width, align in headers:
            self.tree.heading(col_id, text=title, command=lambda c=col_id: self._sort_table(c))
            self.tree.column(col_id, width=width, anchor=align)

        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_process_selected)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Delete>", lambda e: self._on_kill_single())
        self.tree.bind("<Double-1>", lambda e: self._on_trim_single())

        # Tag styles for process status highlight
        self.tree.tag_configure("restrained", background="#332014", foreground="#ffb380")
        self.tree.tag_configure("foreground", foreground="#ffffff")
        self.tree.tag_configure("normal", foreground="#cccccc")

    # -----------------------------------------------------------------------
    # TAB 2: CPU TOPOLOGY
    # -----------------------------------------------------------------------
    def _build_topology_tab(self):
        top_bar = tk.Frame(self.tab_topology, bg=WIN_SURFACE, highlightthickness=1, highlightbackground=WIN_BORDER)
        top_bar.pack(fill=tk.X, padx=4, pady=4)

        topo = self.controller.topology
        txt = (
            f"Heterogeneous CPU Architecture: {topo.total_cores} Logical Processors | "
            f"Performance Cores (P-Cores): {len(topo.p_cores)} ({topo.p_cores}) | "
            f"Efficiency Cores (E-Cores): {len(topo.e_cores)} ({topo.e_cores})"
        )
        lbl = tk.Label(top_bar, text=txt, bg=WIN_SURFACE, fg=WIN_ACCENT, font=FONT_UI_BOLD, padx=8, pady=6)
        lbl.pack(side=tk.LEFT)

        canvas_frame = tk.Frame(self.tab_topology, bg=WIN_BG)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.core_widgets = []
        p_set = set(topo.p_cores)

        for i in range(topo.total_cores):
            is_p = i in p_set
            row = i // 4
            col = i % 4
            canvas_frame.grid_columnconfigure(col, weight=1)

            card = tk.Frame(canvas_frame, bg=WIN_SURFACE, highlightthickness=1, highlightbackground=WIN_BORDER)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            tag = "P-Core" if is_p else "E-Core"
            tag_color = GRAPH_CPU if is_p else GRAPH_RAM

            l_title = tk.Label(card, text=f"Core {i}  [{tag}]", bg=WIN_SURFACE, fg=tag_color, font=FONT_UI_BOLD)
            l_title.pack(anchor="w", padx=8, pady=(4, 2))

            pbar = ttk.Progressbar(card, orient="horizontal", mode="determinate", length=180)
            pbar.pack(fill=tk.X, padx=8, pady=2)

            l_pct = tk.Label(card, text="0.0%", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_MONO)
            l_pct.pack(anchor="e", padx=8, pady=(0, 4))

            self.core_widgets.append((pbar, l_pct))

    # -----------------------------------------------------------------------
    # TAB 3: NETWORK SOCKETS
    # -----------------------------------------------------------------------
    def _build_sockets_tab(self):
        toolbar = tk.Frame(self.tab_sockets, bg=WIN_SURFACE_ALT, height=30)
        toolbar.pack(fill=tk.X, padx=4, pady=(4, 2))

        tk.Label(toolbar, text="Filter Socket / Port:", bg=WIN_SURFACE_ALT, fg=WIN_TEXT_MUTED, font=FONT_UI).pack(side=tk.LEFT, padx=(6, 4))

        self.entry_sock_filter = tk.Entry(toolbar, bg=WIN_BG, fg=WIN_TEXT, font=FONT_UI, width=24, highlightthickness=1, highlightbackground=WIN_BORDER_LIGHT)
        self.entry_sock_filter.pack(side=tk.LEFT, padx=2, pady=2)
        self.entry_sock_filter.bind("<KeyRelease>", lambda e: self._refresh_sockets())

        btn_ref = tk.Button(toolbar, text="Refresh", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI, padx=8, pady=1, relief="flat", command=self._refresh_sockets)
        btn_ref.pack(side=tk.LEFT, padx=6)

        btn_kill_s = tk.Button(toolbar, text="Terminate Process", bg="#3b1f1f", fg="#ff8888", font=FONT_UI, padx=8, pady=1, relief="flat", command=self._on_kill_socket_process)
        btn_kill_s.pack(side=tk.LEFT, padx=2)

        self.lbl_sock_count = tk.Label(toolbar, text="Active Sockets: 0", bg=WIN_SURFACE_ALT, fg=WIN_TEXT_MUTED, font=FONT_STATUS)
        self.lbl_sock_count.pack(side=tk.RIGHT, padx=8)

        container = tk.Frame(self.tab_sockets, bg=WIN_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        cols = ("proto", "local", "remote", "state", "name", "pid")
        self.socket_tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")

        self.socket_tree.heading("proto", text="PROTO")
        self.socket_tree.heading("local", text="LOCAL ENDPOINT")
        self.socket_tree.heading("remote", text="REMOTE ENDPOINT")
        self.socket_tree.heading("state", text="STATE")
        self.socket_tree.heading("name", text="PROCESS NAME")
        self.socket_tree.heading("pid", text="PID")

        self.socket_tree.column("proto", width=65, anchor="center")
        self.socket_tree.column("local", width=180, anchor="w")
        self.socket_tree.column("remote", width=180, anchor="w")
        self.socket_tree.column("state", width=110, anchor="center")
        self.socket_tree.column("name", width=180, anchor="w")
        self.socket_tree.column("pid", width=75, anchor="e")

        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.socket_tree.yview)
        self.socket_tree.configure(yscrollcommand=sb.set)
        self.socket_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.after(600, self._refresh_sockets)

    # -----------------------------------------------------------------------
    # TAB 4: FILE LOCK HUNTER
    # -----------------------------------------------------------------------
    def _build_filelock_tab(self):
        top_bar = tk.Frame(self.tab_filelock, bg=WIN_SURFACE_ALT, highlightthickness=1, highlightbackground=WIN_BORDER)
        top_bar.pack(fill=tk.X, padx=4, pady=4)

        tk.Label(top_bar, text="Target File / Directory:", bg=WIN_SURFACE_ALT, fg=WIN_TEXT, font=FONT_UI_BOLD).pack(side=tk.LEFT, padx=(8, 4), pady=4)

        self.entry_lock_path = tk.Entry(top_bar, bg=WIN_BG, fg=WIN_TEXT, font=FONT_MONO, highlightthickness=1, highlightbackground=WIN_BORDER_LIGHT)
        self.entry_lock_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

        btn_bf = tk.Button(top_bar, text="File...", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI, padx=6, relief="flat", command=self._browse_lock_file)
        btn_bf.pack(side=tk.LEFT, padx=2)

        btn_bd = tk.Button(top_bar, text="Folder...", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI, padx=6, relief="flat", command=self._browse_lock_dir)
        btn_bd.pack(side=tk.LEFT, padx=2)

        btn_scan = tk.Button(top_bar, text="Scan Lockers", bg=WIN_ACCENT, fg="#ffffff", font=FONT_UI_BOLD, padx=10, relief="flat", command=self._scan_file_locks)
        btn_scan.pack(side=tk.LEFT, padx=4)

        container = tk.Frame(self.tab_filelock, bg=WIN_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        cols = ("pid", "name", "kind", "service")
        self.lock_tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")
        self.lock_tree.heading("pid", text="PID")
        self.lock_tree.heading("name", text="APPLICATION / PROCESS")
        self.lock_tree.heading("kind", text="TYPE")
        self.lock_tree.heading("service", text="SERVICE NAME")

        self.lock_tree.column("pid", width=80, anchor="e")
        self.lock_tree.column("name", width=280, anchor="w")
        self.lock_tree.column("kind", width=140, anchor="center")
        self.lock_tree.column("service", width=180, anchor="w")

        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.lock_tree.yview)
        self.lock_tree.configure(yscrollcommand=sb.set)
        self.lock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = tk.Frame(self.tab_filelock, bg=WIN_SURFACE)
        bottom.pack(fill=tk.X, padx=4, pady=2)

        self.lbl_lock_status = tk.Label(bottom, text="Ready to scan target path via Windows Restart Manager.", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_STATUS)
        self.lbl_lock_status.pack(side=tk.LEFT, padx=8, pady=4)

        btn_term = tk.Button(bottom, text="Terminate Selected Locker", bg="#3b1f1f", fg="#ff8888", font=FONT_UI_BOLD, padx=8, relief="flat", command=self._on_kill_file_locker)
        btn_term.pack(side=tk.RIGHT, padx=8, pady=4)

    # -----------------------------------------------------------------------
    # TAB 5: ACTIVE RULES & ENGINE SETTINGS
    # -----------------------------------------------------------------------
    def _build_rules_tab(self):
        container = tk.Frame(self.tab_rules, bg=WIN_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left: Sliders
        left_p = tk.LabelFrame(container, text=" ProBalance Governor Parameters ", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI_BOLD, padx=12, pady=10)
        left_p.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=4)

        # 1. System CPU Trigger
        tk.Label(left_p, text="System CPU Trigger Threshold (%):", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI).pack(anchor="w", pady=(4, 2))
        self.scale_cpu = tk.Scale(left_p, from_=30, to=95, orient="horizontal", bg=WIN_SURFACE, fg=WIN_TEXT, highlightthickness=0, length=240)
        self.scale_cpu.set(60)
        self.scale_cpu.pack(anchor="w", pady=(0, 8))

        # 2. Per-Process Trigger
        tk.Label(left_p, text="Per-Process CPU Trigger (%):", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI).pack(anchor="w", pady=(4, 2))
        self.scale_proc_cpu = tk.Scale(left_p, from_=10, to=90, orient="horizontal", bg=WIN_SURFACE, fg=WIN_TEXT, highlightthickness=0, length=240)
        self.scale_proc_cpu.set(25)
        self.scale_proc_cpu.pack(anchor="w", pady=(0, 8))

        # 3. Restraint Duration
        tk.Label(left_p, text="Restraint Duration (Seconds):", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI).pack(anchor="w", pady=(4, 2))
        self.scale_dur = tk.Scale(left_p, from_=1, to=30, orient="horizontal", bg=WIN_SURFACE, fg=WIN_TEXT, highlightthickness=0, length=240)
        self.scale_dur.set(3)
        self.scale_dur.pack(anchor="w", pady=(0, 12))

        btn_save_pb = tk.Button(left_p, text="Save & Apply Governor Parameters", bg=WIN_ACCENT, fg="#ffffff", font=FONT_UI_BOLD, padx=10, pady=4, relief="flat", command=self._save_engine_params)
        btn_save_pb.pack(fill=tk.X, pady=(4, 8))

        # Right: JSON Rules Editor
        right_p = tk.LabelFrame(container, text=" Persistent Rules (config/default_rules.json) ", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI_BOLD, padx=8, pady=6)
        right_p.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=4)

        self.txt_rules = tk.Text(right_p, bg=WIN_BG, fg=WIN_TEXT, insertbackground=WIN_TEXT, font=FONT_MONO, relief="flat", highlightthickness=1, highlightbackground=WIN_BORDER)
        self.txt_rules.pack(fill=tk.BOTH, expand=True)

        self._reload_rules()

    # -----------------------------------------------------------------------
    # TAB 6: ACTIVITY JOURNAL
    # -----------------------------------------------------------------------
    def _build_journal_tab(self):
        container = tk.Frame(self.tab_journal, bg=WIN_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        toolbar = tk.Frame(container, bg=WIN_SURFACE_ALT)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        tk.Label(toolbar, text="Real-Time Engine Audit Stream:", bg=WIN_SURFACE_ALT, fg=WIN_TEXT, font=FONT_UI_BOLD).pack(side=tk.LEFT, padx=8, pady=4)
        btn_clr = tk.Button(toolbar, text="Clear Log", bg=WIN_SURFACE, fg=WIN_TEXT, font=FONT_UI, padx=8, relief="flat", command=self._clear_logs)
        btn_clr.pack(side=tk.RIGHT, padx=6, pady=2)

        self.txt_journal = tk.Text(container, bg=WIN_BG, fg=GRAPH_CPU, insertbackground=WIN_TEXT, font=FONT_MONO, relief="flat", highlightthickness=1, highlightbackground=WIN_BORDER)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.txt_journal.yview)
        self.txt_journal.configure(yscrollcommand=sb.set)

        self.txt_journal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    # -----------------------------------------------------------------------
    # CONTEXT MENU
    # -----------------------------------------------------------------------
    def _setup_context_menu(self):
        self.menu = tk.Menu(self, tearoff=0)

        # Priority Submenu
        prio_sub = tk.Menu(self.menu, tearoff=0)
        for prio in ("REALTIME", "HIGH", "ABOVE_NORMAL", "NORMAL", "BELOW_NORMAL", "IDLE"):
            prio_sub.add_command(label=prio, command=lambda p=prio: self._quick_set_prio(p))
        self.menu.add_cascade(label="Set Priority Class", menu=prio_sub)

        # Affinity Submenu
        aff_sub = tk.Menu(self.menu, tearoff=0)
        aff_sub.add_command(label="All Cores (Default)", command=lambda: self._quick_set_aff("ALL_CORES"))
        aff_sub.add_command(label="P-Cores Only (Performance)", command=lambda: self._quick_set_aff("P_CORES"))
        aff_sub.add_command(label="E-Cores Only (Efficiency)", command=lambda: self._quick_set_aff("E_CORES"))
        aff_sub.add_command(label="Core 0 Only", command=lambda: self._quick_set_aff("0x1"))
        self.menu.add_cascade(label="Set CPU Affinity", menu=aff_sub)

        # I/O Priority
        io_sub = tk.Menu(self.menu, tearoff=0)
        for io_p in ("HIGH", "NORMAL", "LOW", "VERY_LOW"):
            io_sub.add_command(label=io_p, command=lambda ip=io_p: self._quick_set_io(ip))
        self.menu.add_cascade(label="Set I/O Priority", menu=io_sub)

        self.menu.add_separator()
        self.menu.add_command(label="SmartTrim Working Set (RAM)", command=self._on_trim_single)
        self.menu.add_command(label="Toggle ProBalance Exclusion", command=self._on_toggle_exclude)

        self.menu.add_separator()
        self.menu.add_command(label="Inspect Handles & Loaded DLLs...", command=self._open_handles_dlls_inspector)
        self.menu.add_command(label="Open File Location (Explorer)", command=self._open_file_location)
        self.menu.add_command(label="Restart Process", command=self._on_restart_single)
        self.menu.add_command(label="End Process (Del)", command=self._on_kill_single)

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self._on_process_selected(None)
            self.menu.post(event.x_root, event.y_root)

    # -----------------------------------------------------------------------
    # BACKGROUND POLLING & TELEMETRY
    # -----------------------------------------------------------------------
    def _start_background_polling(self):
        def poll():
            while self.polling_active:
                if self.update_interval_ms > 0:
                    try:
                        state = self.controller.refresh_state()
                        if self.winfo_exists():
                            self.after(0, self._render_live_state, state)
                    except Exception:
                        pass
                    time.sleep(self.update_interval_ms / 1000.0)
                else:
                    time.sleep(1.0)

        t = threading.Thread(target=poll, daemon=True)
        t.start()

    def _render_live_state(self, state: dict):
        cpu = state.get("system_cpu", 0.0)
        ram = state.get("system_ram", 0.0)
        restrained = state.get("restrained_count", 0)
        procs_count = state.get("processes_count", 0)

        # Top telemetry indicator
        pb_status = f"Restraining ({restrained})" if restrained > 0 else "Active"
        self.lbl_telemetry_top.configure(
            text=f"CPU: {cpu:.1f}%   |   RAM: {ram:.1f}%   |   ProBalance: {pb_status}"
        )

        # Status Bar
        self.sb_procs.configure(text=f"Processes: {procs_count} | Selected PID: {self.selected_pid or '-'}")
        self.sb_metrics.configure(text=f"CPU Load: {cpu:.1f}% | Memory Load: {ram:.1f}%")
        self.sb_engine.configure(
            text=f"ProBalance: {pb_status} • Native Win32 Ring-3 Governor",
            fg=GRAPH_RESTRAINT if restrained > 0 else GRAPH_CPU
        )

        # Graph update
        self.graph.update_history(
            state.get("cpu_history", []),
            state.get("ram_history", []),
            state.get("restraint_history", [])
        )

        # Per-core load update
        per_core = state.get("per_core_cpu", [])
        if hasattr(self, "core_widgets") and per_core:
            for idx, (pbar, lbl) in enumerate(self.core_widgets):
                if idx < len(per_core):
                    val = per_core[idx]
                    pbar["value"] = val
                    lbl.configure(text=f"{val:.1f}%")

        self._render_process_table()
        self._update_logs_view()

        # Update System Tray tooltip
        if hasattr(self, "tray_manager"):
            self.tray_manager.update_tooltip(cpu, ram, restrained)

    def _render_process_table(self):
        query = self.entry_filter.get().strip() if hasattr(self, "entry_filter") else ""
        active_only = self.var_active_only.get()

        procs = self.controller.get_filtered_processes(
            search_query=query,
            sort_by=self.sort_col,
            reverse=self.sort_desc,
            active_only=active_only
        )

        if self.var_restrained_only.get():
            procs = [p for p in procs if p["is_restrained"]]

        if self.var_tree_view.get():
            procs = self.controller.build_tree_hierarchy(procs)

        cur_sel = self.tree.selection()
        selected_iid = cur_sel[0] if cur_sel else None

        self.tree.delete(*self.tree.get_children())
        for p in procs[:220]:
            tag = "normal"
            status_text = "Normal"
            if p["is_restrained"]:
                status_text = "Restrained (PB)"
                tag = "restrained"
            elif p["is_foreground"]:
                status_text = "Foreground"
                tag = "foreground"
            elif p["is_excluded"]:
                status_text = "Excluded (PB)"

            iid = str(p["pid"])
            display_name = p.get("display_name", p["name"])
            self.tree.insert("", tk.END, iid=iid, tags=(tag,), values=(
                p["pid"],
                display_name,
                f"{p['cpu_percent']:.1f}",
                f"{p['memory_mb']:.1f}",
                p["priority"],
                "All Cores",
                p["threads"],
                status_text
            ))

        if selected_iid and self.tree.exists(selected_iid):
            self.tree.selection_set(selected_iid)

    def _update_logs_view(self):
        if not hasattr(self, "txt_journal"):
            return
        cur_text = self.txt_journal.get("1.0", tk.END).strip()
        lines = self.controller.events_log[-50:]
        new_text = "\n".join(lines)
        if cur_text != new_text:
            self.txt_journal.delete("1.0", tk.END)
            self.txt_journal.insert(tk.END, new_text + "\n")
            self.txt_journal.see(tk.END)

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

    # -----------------------------------------------------------------------
    # ACTIONS & HELPERS
    # -----------------------------------------------------------------------
    def _clear_filter(self):
        self.entry_filter.delete(0, tk.END)
        self._render_process_table()

    def _force_refresh(self):
        state = self.controller.refresh_state()
        self._render_live_state(state)

    def _on_speed_change(self):
        self.update_interval_ms = self.speed_var.get()

    def _toggle_always_on_top(self):
        self.attributes("-topmost", self.var_always_on_top.get())

    def _toggle_probalance(self):
        enabled = self.var_probalance_enabled.get()
        self.controller.probalance.config.enabled = enabled
        self.controller.log_event(f"ProBalance dynamically {'Enabled' if enabled else 'Disabled'}")

    def _quick_set_prio(self, prio: str):
        if self.selected_pid:
            self.controller.apply_priority(self.selected_pid, prio, persistent=True)
            self._force_refresh()

    def _quick_set_aff(self, aff: str):
        if self.selected_pid:
            self.controller.apply_affinity(self.selected_pid, aff, persistent=True)
            self._force_refresh()

    def _quick_set_io(self, io_prio: str):
        if self.selected_pid:
            self.controller.apply_io_priority(self.selected_pid, io_prio, persistent=True)
            self._force_refresh()

    def _on_toggle_exclude(self):
        if self.selected_name:
            self.controller.toggle_probalance_exclusion(self.selected_name)
            self._force_refresh()

    def _on_trim_single(self):
        if self.selected_pid:
            self.controller.trim_process(self.selected_pid)

    def _on_restart_single(self):
        if self.selected_pid:
            self.controller.restart_process(self.selected_pid)

    def _on_kill_single(self):
        if self.selected_pid:
            if messagebox.askyesno("Confirm Terminate", f"Terminate process '{self.selected_name}' (PID: {self.selected_pid})?"):
                self.controller.kill_process(self.selected_pid, force=True)
                self._force_refresh()

    def _open_file_location(self):
        if not self.selected_pid:
            return
        try:
            import psutil
            p = psutil.Process(self.selected_pid)
            path = p.exe()
            if path and os.path.exists(path):
                os.system(f'explorer /select,"{path}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open location: {e}")

    def _open_handles_dlls_inspector(self):
        if not self.selected_pid:
            return
        pid = self.selected_pid
        name = self.selected_name or f"PID {pid}"

        dialog = tk.Toplevel(self)
        dialog.title(f"Process Inspector — {name} (PID: {pid})")
        dialog.geometry("780x520")
        dialog.minsize(640, 400)
        dialog.configure(bg=WIN_BG)
        dialog.transient(self)

        # Apply immersive dark mode
        try:
            hwnd = ctypes.windll.user32.GetParent(dialog.winfo_id()) or dialog.winfo_id()
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

        # Header Info Strip
        hdr = tk.Frame(dialog, bg=WIN_SURFACE_ALT, height=36, highlightthickness=1, highlightbackground=WIN_BORDER)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        tk.Label(hdr, text=f"Target: {name}", bg=WIN_SURFACE_ALT, fg=WIN_TEXT, font=FONT_UI_BOLD).pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(hdr, text=f"PID: {pid}", bg=WIN_SURFACE_ALT, fg=WIN_TEXT_MUTED, font=FONT_MONO).pack(side=tk.LEFT, padx=8, pady=6)

        gdi_cnt, usr_cnt = self.controller.win32.get_process_gui_resources(pid)
        tk.Label(hdr, text=f"GDI Handles: {gdi_cnt}  |  USER Handles: {usr_cnt}", bg=WIN_SURFACE_ALT, fg=WIN_TEXT_MUTED, font=FONT_UI).pack(side=tk.RIGHT, padx=12, pady=6)

        # Notebook (DLLs vs Handles)
        nb = ttk.Notebook(dialog)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tab_dlls = ttk.Frame(nb)
        tab_handles = ttk.Frame(nb)
        nb.add(tab_dlls, text=" Loaded Modules (.DLLs) ")
        nb.add(tab_handles, text=" Open Handles (Files & Sockets) ")

        # --- TAB 1: DLLs ---
        dll_bar = tk.Frame(tab_dlls, bg=WIN_SURFACE, height=30)
        dll_bar.pack(fill=tk.X, side=tk.TOP, padx=4, pady=3)
        tk.Label(dll_bar, text="Filter DLLs:", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_UI).pack(side=tk.LEFT, padx=4)
        dll_filter = tk.Entry(dll_bar, bg=WIN_BG, fg=WIN_TEXT, relief="flat", highlightthickness=1, highlightbackground=WIN_BORDER, font=FONT_UI, width=28)
        dll_filter.pack(side=tk.LEFT, padx=4, pady=2)

        lbl_dll_count = tk.Label(dll_bar, text="", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_UI)
        lbl_dll_count.pack(side=tk.RIGHT, padx=8)

        dll_tree_frame = tk.Frame(tab_dlls, bg=WIN_BG)
        dll_tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        dll_cols = ("name", "path", "rss")
        tree_dll = ttk.Treeview(dll_tree_frame, columns=dll_cols, show="headings", selectmode="browse")
        tree_dll.heading("name", text="MODULE NAME")
        tree_dll.heading("path", text="FULL BASE PATH")
        tree_dll.heading("rss", text="RSS (KB)")
        tree_dll.column("name", width=200, anchor="w")
        tree_dll.column("path", width=460, anchor="w")
        tree_dll.column("rss", width=80, anchor="e")

        sb_dll = ttk.Scrollbar(dll_tree_frame, orient=tk.VERTICAL, command=tree_dll.yview)
        tree_dll.configure(yscrollcommand=sb_dll.set)
        tree_dll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_dll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- TAB 2: Handles ---
        h_bar = tk.Frame(tab_handles, bg=WIN_SURFACE, height=30)
        h_bar.pack(fill=tk.X, side=tk.TOP, padx=4, pady=3)
        tk.Label(h_bar, text="Filter Handles:", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_UI).pack(side=tk.LEFT, padx=4)
        h_filter = tk.Entry(h_bar, bg=WIN_BG, fg=WIN_TEXT, relief="flat", highlightthickness=1, highlightbackground=WIN_BORDER, font=FONT_UI, width=28)
        h_filter.pack(side=tk.LEFT, padx=4, pady=2)

        lbl_h_count = tk.Label(h_bar, text="", bg=WIN_SURFACE, fg=WIN_TEXT_MUTED, font=FONT_UI)
        lbl_h_count.pack(side=tk.RIGHT, padx=8)

        h_tree_frame = tk.Frame(tab_handles, bg=WIN_BG)
        h_tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        h_cols = ("type", "target", "detail")
        tree_h = ttk.Treeview(h_tree_frame, columns=h_cols, show="headings", selectmode="browse")
        tree_h.heading("type", text="TYPE")
        tree_h.heading("target", text="PATH / ENDPOINT")
        tree_h.heading("detail", text="DETAIL / STATUS")
        tree_h.column("type", width=90, anchor="center")
        tree_h.column("target", width=530, anchor="w")
        tree_h.column("detail", width=120, anchor="w")

        sb_h = ttk.Scrollbar(h_tree_frame, orient=tk.VERTICAL, command=tree_h.yview)
        tree_h.configure(yscrollcommand=sb_h.set)
        tree_h.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_h.pack(side=tk.RIGHT, fill=tk.Y)

        raw_modules = self.controller.get_process_modules(pid)
        raw_handles = self.controller.get_process_handles(pid)

        def populate_dlls():
            q = dll_filter.get().strip().lower()
            tree_dll.delete(*tree_dll.get_children())
            filtered = [m for m in raw_modules if (not q or q in m["name"].lower() or q in m["path"].lower())]
            for m in filtered:
                tree_dll.insert("", tk.END, values=(m["name"], m["path"], m["rss_kb"]))
            lbl_dll_count.configure(text=f"Total: {len(filtered)} / {len(raw_modules)} DLLs")

        def populate_handles():
            q = h_filter.get().strip().lower()
            tree_h.delete(*tree_h.get_children())
            filtered = [h for h in raw_handles if (not q or q in h["target"].lower() or q in h["detail"].lower() or q in h["type"].lower())]
            for h in filtered:
                tree_h.insert("", tk.END, values=(h["type"], h["target"], h["detail"]))
            lbl_h_count.configure(text=f"Total: {len(filtered)} / {len(raw_handles)} Handles")

        dll_filter.bind("<KeyRelease>", lambda e: populate_dlls())
        h_filter.bind("<KeyRelease>", lambda e: populate_handles())

        populate_dlls()
        populate_handles()

    def _on_smart_trim(self):
        trimmed = self.controller.trim_all()
        messagebox.showinfo("SmartTrim", f"Working set successfully flushed across {trimmed} monitored processes.")

    def _on_power_scheme_change(self, scheme: str):
        self.controller.change_power_scheme(scheme)

    def _run_new_task(self):
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}", None, 1)
        except Exception:
            pass

    def _show_about_dialog(self):
        msg = (
            "Proxessor 1.0.0 — Native Win32 Process Governor\n\n"
            "An open-source, unrestricted Windows optimization system inspired by Process Lasso.\n"
            "All Pro features unlocked permanently. Zero telemetry. Zero fees.\n\n"
            "Engine: Native Rust Ring-3 Governor Engine\n"
            "UI: Windows 11 Native Fluent Styling\n"
            "https://github.com/dhaulagani/Proxessor"
        )
        messagebox.showinfo("About Proxessor", msg)

    # -----------------------------------------------------------------------
    # SOCKETS & FILE LOCK LOGIC
    # -----------------------------------------------------------------------
    def _refresh_sockets(self):
        query = self.entry_sock_filter.get().strip() if hasattr(self, "entry_sock_filter") else ""
        def fetch():
            conns = self.controller.list_connections(query)
            try:
                if self.winfo_exists():
                    self.after(0, self._render_socket_table, conns)
            except Exception:
                pass
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
        self.lbl_sock_count.configure(text=f"Active Sockets: {len(conns)}")

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
                self._refresh_sockets()
            else:
                messagebox.showerror("Error", f"Could not terminate PID {pid}.")

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
            try:
                if self.winfo_exists():
                    self.after(0, self._render_lockers, lockers, target)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _render_lockers(self, lockers, path):
        self.lock_tree.delete(*self.lock_tree.get_children())
        if not lockers:
            self.lbl_lock_status.configure(text=f"No active locks found for '{path}'. Resource is unlocked.")
            return

        for item in lockers:
            self.lock_tree.insert("", tk.END, values=(
                item.get("pid"),
                item.get("app_name"),
                item.get("kind"),
                item.get("service") or "-"
            ))
        self.lbl_lock_status.configure(text=f"Found {len(lockers)} locking process(es) holding '{path}'!")

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
                self._scan_file_locks()
            else:
                messagebox.showerror("Error", f"Failed to terminate PID {pid}.")

    def _reload_rules(self):
        try:
            import json
            with open(self.controller.config_path, "r", encoding="utf-8") as f:
                content = json.dumps(json.load(f), indent=2)
            self.txt_rules.delete("1.0", tk.END)
            self.txt_rules.insert(tk.END, content)
        except Exception as e:
            self.txt_rules.insert(tk.END, f"Error loading rules: {e}")

    def _save_engine_params(self):
        try:
            import json
            with open(self.controller.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            pb = data.get("probalance", {})
            pb["cpu_trigger_threshold_percent"] = float(int(self.scale_cpu.get()))
            pb["per_process_cpu_trigger_percent"] = float(int(self.scale_proc_cpu.get()))
            pb["restraint_duration_seconds"] = int(self.scale_dur.get())
            data["probalance"] = pb

            with open(self.controller.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.controller.rule_manager.load()
            self.controller.probalance = self.controller.rule_manager.probalance_config
            self._reload_rules()
            messagebox.showinfo("Saved", "ProBalance parameters saved and applied successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save engine parameters: {e}")

    def _clear_logs(self):
        self.controller.events_log.clear()
        self.txt_journal.delete("1.0", tk.END)

    def _on_close_to_tray(self):
        if self.var_close_to_tray.get():
            self.withdraw()
            if not getattr(self, "tray_notified", False):
                self.tray_notified = True
                if hasattr(self, "tray_manager"):
                    self.tray_manager.notify(
                        "Proxessor Minimized to Tray",
                        "Proxessor continues governing processes in background. Double-click tray icon to restore."
                    )
        else:
            self._exit_full_application()

    def _show_window_from_tray(self):
        def restore():
            self.deiconify()
            self.lift()
            self.focus_force()
        self.after(0, restore)

    def _exit_full_application(self):
        self.polling_active = False
        if hasattr(self, "tray_manager"):
            self.tray_manager.stop()
        self.after(50, self.destroy)


def launch_gui(config_path: str = "config/default_rules.json"):
    app = ProxessorApp(config_path)
    app.mainloop()

ProxessorGUI = ProxessorApp

if __name__ == "__main__":
    launch_gui()
