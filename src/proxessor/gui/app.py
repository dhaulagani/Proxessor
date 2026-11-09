import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.proxessor.gui.controller import GUIController

# Design System Palette (from docs/DESIGN.md)
COLOR_BG = "#0b0d11"
COLOR_SURFACE = "#131720"
COLOR_SURFACE_HOVER = "#1c2230"
COLOR_BORDER = "#242c3d"
COLOR_BORDER_FOCUS = "#3b4760"
COLOR_TEXT_PRIMARY = "#f1f5f9"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"
COLOR_ACCENT_OPTIMAL = "#10b981"
COLOR_ACCENT_RESTRAINED = "#f59e0b"
COLOR_ACCENT_CRITICAL = "#ef4444"

FONT_SANS = ("Segoe UI", 10)
FONT_SANS_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_MONO = ("Consolas", 10)
FONT_MONO_BOLD = ("Consolas", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)

class ProxessorGUI(tk.Tk):
    """Modern, high-density desktop systems interface for Proxessor."""

    def __init__(self, config_path: str = "config/default_rules.json"):
        super().__init__()
        self.title("Proxessor // Process Governor")
        self.geometry("1100x720")
        self.minsize(960, 600)
        self.configure(bg=COLOR_BG)

        self.controller = GUIController(config_path)
        self.selected_pid: int = None
        self.selected_process_name: str = ""
        self.auto_refresh_active = True
        self.sort_column = "cpu_percent"
        self.sort_descending = True

        self._setup_styles()
        self._build_ui()
        self._start_background_polling()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview styling
        style.configure(
            "Treeview",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT_PRIMARY,
            fieldbackground=COLOR_SURFACE,
            rowheight=26,
            font=FONT_MONO,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_BG,
            foreground=COLOR_TEXT_SECONDARY,
            font=FONT_SANS_BOLD,
            relief="flat",
            padding=6
        )
        style.map(
            "Treeview",
            background=[("selected", COLOR_SURFACE_HOVER)],
            foreground=[("selected", COLOR_TEXT_PRIMARY)]
        )

        # Scrollbar styling
        style.configure(
            "Vertical.TScrollbar",
            background=COLOR_SURFACE,
            troughcolor=COLOR_BG,
            bordercolor=COLOR_BORDER,
            arrowcolor=COLOR_TEXT_SECONDARY,
            relief="flat"
        )

    def _build_ui(self):
        # 1. Header Telemetry Bar
        self.header_frame = tk.Frame(self, bg=COLOR_SURFACE, height=64, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.header_frame.pack(fill=tk.X, padx=12, pady=(12, 6))

        # Title / Status
        title_box = tk.Frame(self.header_frame, bg=COLOR_SURFACE)
        title_box.pack(side=tk.LEFT, padx=16, pady=12)

        lbl_brand = tk.Label(title_box, text="PROXESSOR CORE", font=FONT_TITLE, fg=COLOR_TEXT_PRIMARY, bg=COLOR_SURFACE)
        lbl_brand.pack(anchor=tk.W)
        lbl_sub = tk.Label(title_box, text="Open-Source Dynamic Process Governor", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE)
        lbl_sub.pack(anchor=tk.W)

        # Live Metrics Badges
        metrics_box = tk.Frame(self.header_frame, bg=COLOR_SURFACE)
        metrics_box.pack(side=tk.LEFT, padx=32)

        self.lbl_cpu = tk.Label(metrics_box, text="CPU: --%", font=FONT_MONO_BOLD, fg=COLOR_ACCENT_OPTIMAL, bg=COLOR_SURFACE)
        self.lbl_cpu.pack(side=tk.LEFT, padx=12)

        self.lbl_ram = tk.Label(metrics_box, text="RAM: --%", font=FONT_MONO_BOLD, fg=COLOR_TEXT_PRIMARY, bg=COLOR_SURFACE)
        self.lbl_ram.pack(side=tk.LEFT, padx=12)

        self.lbl_probalance = tk.Label(metrics_box, text="ProBalance: ACTIVE", font=FONT_MONO_BOLD, fg=COLOR_ACCENT_OPTIMAL, bg=COLOR_SURFACE)
        self.lbl_probalance.pack(side=tk.LEFT, padx=12)

        # Global Action Buttons
        actions_box = tk.Frame(self.header_frame, bg=COLOR_SURFACE)
        actions_box.pack(side=tk.RIGHT, padx=16)

        btn_smart_trim = tk.Button(
            actions_box,
            text="FLUSH RAM (SMARTTRIM)",
            font=FONT_SANS_BOLD,
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_SURFACE_HOVER,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_TEXT_PRIMARY,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_smart_trim_clicked
        )
        btn_smart_trim.pack(side=tk.LEFT, padx=6)

        btn_power = tk.Button(
            actions_box,
            text="HIGH PERF MODE",
            font=FONT_SANS_BOLD,
            fg=COLOR_ACCENT_OPTIMAL,
            bg=COLOR_SURFACE_HOVER,
            activebackground=COLOR_BORDER,
            activeforeground=COLOR_ACCENT_OPTIMAL,
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self.controller.change_power_scheme("HIGH_PERFORMANCE")
        )
        btn_power.pack(side=tk.LEFT, padx=6)

        # 2. Main Workspace Split
        main_container = tk.Frame(self, bg=COLOR_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        # Left: Process Grid (70% width)
        left_frame = tk.Frame(main_container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Search Bar
        search_frame = tk.Frame(left_frame, bg=COLOR_SURFACE)
        search_frame.pack(fill=tk.X, padx=12, pady=10)

        lbl_filter = tk.Label(search_frame, text="FILTER:", font=FONT_SANS_BOLD, fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE)
        lbl_filter.pack(side=tk.LEFT, padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._update_process_table())
        entry_search = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=FONT_MONO,
            bg=COLOR_BG,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_ACCENT_OPTIMAL
        )
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Process Table
        table_container = tk.Frame(left_frame, bg=COLOR_SURFACE)
        table_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        cols = ("pid", "name", "cpu", "ram", "priority", "threads", "status")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("pid", text="PID", command=lambda: self._sort_by("pid"))
        self.tree.heading("name", text="PROCESS NAME", command=lambda: self._sort_by("name"))
        self.tree.heading("cpu", text="CPU %", command=lambda: self._sort_by("cpu_percent"))
        self.tree.heading("ram", text="RAM (MB)", command=lambda: self._sort_by("memory_mb"))
        self.tree.heading("priority", text="PRIORITY", command=lambda: self._sort_by("priority"))
        self.tree.heading("threads", text="THREADS", command=lambda: self._sort_by("threads"))
        self.tree.heading("status", text="STATUS")

        self.tree.column("pid", width=65, anchor=tk.E)
        self.tree.column("name", width=220, anchor=tk.W)
        self.tree.column("cpu", width=75, anchor=tk.E)
        self.tree.column("ram", width=85, anchor=tk.E)
        self.tree.column("priority", width=110, anchor=tk.CENTER)
        self.tree.column("threads", width=70, anchor=tk.E)
        self.tree.column("status", width=110, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_process_selected)

        # Right: Tuning Drawer & Logs (30% width)
        right_frame = tk.Frame(main_container, bg=COLOR_BG, width=340)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(6, 0))
        right_frame.pack_propagate(False)

        # Tuning Card
        tuning_card = tk.Frame(right_frame, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        tuning_card.pack(fill=tk.X, pady=(0, 6))

        lbl_drawer = tk.Label(tuning_card, text="PROCESS TUNING ARBITER", font=FONT_SANS_BOLD, fg=COLOR_TEXT_PRIMARY, bg=COLOR_SURFACE)
        lbl_drawer.pack(anchor=tk.W, padx=12, pady=(10, 4))

        self.lbl_selected_info = tk.Label(tuning_card, text="Select a process to tune", font=FONT_MONO, fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE)
        self.lbl_selected_info.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Controls Grid
        ctrl_grid = tk.Frame(tuning_card, bg=COLOR_SURFACE)
        ctrl_grid.pack(fill=tk.X, padx=12, pady=(0, 12))

        # Priority Class
        tk.Label(ctrl_grid, text="CPU Priority:", font=FONT_SMALL, fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.prio_var = tk.StringVar(value="NORMAL")
        self.opt_prio = ttk.Combobox(ctrl_grid, textvariable=self.prio_var, values=["REALTIME", "HIGH", "ABOVE_NORMAL", "NORMAL", "BELOW_NORMAL", "IDLE"], state="readonly", width=14)
        self.opt_prio.grid(row=0, column=1, sticky=tk.E, pady=4)

        # CPU Affinity
        tk.Label(ctrl_grid, text="Core Affinity:", font=FONT_SMALL, fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=1, column=0, sticky=tk.W, pady=4)
        self.affinity_var = tk.StringVar(value="ALL_CORES")
        self.opt_affinity = ttk.Combobox(ctrl_grid, textvariable=self.affinity_var, values=["ALL_CORES", "P_CORES", "E_CORES"], state="readonly", width=14)
        self.opt_affinity.grid(row=1, column=1, sticky=tk.E, pady=4)

        # I/O Priority
        tk.Label(ctrl_grid, text="I/O Priority:", font=FONT_SMALL, fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=2, column=0, sticky=tk.W, pady=4)
        self.io_var = tk.StringVar(value="NORMAL")
        self.opt_io = ttk.Combobox(ctrl_grid, textvariable=self.io_var, values=["HIGH", "NORMAL", "LOW", "VERY_LOW"], state="readonly", width=14)
        self.opt_io.grid(row=2, column=1, sticky=tk.E, pady=4)

        # Drawer Buttons
        btn_box = tk.Frame(tuning_card, bg=COLOR_SURFACE)
        btn_box.pack(fill=tk.X, padx=12, pady=(4, 12))

        btn_apply = tk.Button(
            btn_box,
            text="APPLY OPTIMIZATION",
            font=FONT_SANS_BOLD,
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_SURFACE_HOVER,
            relief="flat",
            padx=8,
            pady=6,
            cursor="hand2",
            command=self._apply_tuning
        )
        btn_apply.pack(fill=tk.X, pady=(0, 4))

        btn_row2 = tk.Frame(btn_box, bg=COLOR_SURFACE)
        btn_row2.pack(fill=tk.X)

        btn_trim_proc = tk.Button(
            btn_row2,
            text="TRIM WORKING SET",
            font=FONT_SMALL,
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_SURFACE_HOVER,
            relief="flat",
            padx=6,
            pady=4,
            cursor="hand2",
            command=self._trim_selected
        )
        btn_trim_proc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_kill = tk.Button(
            btn_row2,
            text="TERMINATE",
            font=FONT_SMALL,
            fg=COLOR_ACCENT_CRITICAL,
            bg=COLOR_SURFACE_HOVER,
            relief="flat",
            padx=6,
            pady=4,
            cursor="hand2",
            command=self._kill_selected
        )
        btn_kill.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # Event Log Card
        log_card = tk.Frame(right_frame, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        log_card.pack(fill=tk.BOTH, expand=True)

        lbl_log = tk.Label(log_card, text="PROBALANCE LIVE TELEMETRY", font=FONT_SANS_BOLD, fg=COLOR_TEXT_PRIMARY, bg=COLOR_SURFACE)
        lbl_log.pack(anchor=tk.W, padx=12, pady=(10, 4))

        self.txt_log = tk.Text(
            log_card,
            bg=COLOR_BG,
            fg=COLOR_TEXT_SECONDARY,
            font=FONT_MONO,
            relief="flat",
            padx=8,
            pady=8,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # 3. Bottom Status Bar
        status_bar = tk.Frame(self, bg=COLOR_SURFACE, height=28, highlightthickness=1, highlightbackground=COLOR_BORDER)
        status_bar.pack(fill=tk.X, padx=12, pady=(6, 12))

        self.lbl_status = tk.Label(status_bar, text="Governor status: ONLINE | All Pro features active", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE)
        self.lbl_status.pack(side=tk.LEFT, padx=12, pady=4)

    def _start_background_polling(self):
        """Launches continuous background worker thread for non-blocking state updates."""
        def poll_loop():
            while self.auto_refresh_active:
                try:
                    state = self.controller.refresh_state()
                    self.after(0, self._render_state, state)
                except Exception:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=poll_loop, daemon=True)
        t.start()

    def _render_state(self, state: dict):
        """Updates UI telemetry and process list on the main Tkinter thread."""
        cpu = state.get("system_cpu", 0.0)
        ram = state.get("system_ram", 0.0)
        restrained = state.get("restrained_count", 0)

        # Update telemetry labels
        self.lbl_cpu.config(text=f"CPU: {cpu:.1f}%", fg=COLOR_ACCENT_CRITICAL if cpu > 75 else COLOR_ACCENT_OPTIMAL)
        self.lbl_ram.config(text=f"RAM: {ram:.1f}%")
        if restrained > 0:
            self.lbl_probalance.config(text=f"ProBalance: RESTRAINING ({restrained})", fg=COLOR_ACCENT_RESTRAINED)
        else:
            self.lbl_probalance.config(text="ProBalance: ACTIVE", fg=COLOR_ACCENT_OPTIMAL)

        self.lbl_status.config(
            text=f"Governor status: ONLINE | Processes: {state.get('processes_count', 0)} | Monitored & Enforced"
        )

        self._update_process_table()
        self._update_log_view()

    def _update_process_table(self):
        query = self.search_var.get()
        procs = self.controller.get_filtered_processes(query, sort_by=self.sort_column, reverse=self.sort_descending)

        # Retain selection
        cur_sel = self.tree.selection()
        selected_iid = cur_sel[0] if cur_sel else None

        # Render top 150 items to keep UI snappy
        self.tree.delete(*self.tree.get_children())
        for p in procs[:150]:
            status_text = "NORMAL"
            if p["is_restrained"]:
                status_text = "RESTRAINED"
            elif p["is_foreground"]:
                status_text = "FOREGROUND"

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

    def _update_log_view(self):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        for line in self.controller.events_log[-15:]:
            self.txt_log.insert(tk.END, line + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def _sort_by(self, col: str):
        if self.sort_column == col:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = col
            self.sort_descending = True
        self._update_process_table()

    def _on_process_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        self.selected_pid = pid

        matching = [p for p in self.controller.cached_processes if p["pid"] == pid]
        if matching:
            target = matching[0]
            self.selected_process_name = target["name"]
            self.lbl_selected_info.config(
                text=f"{target['name']} (PID: {pid})\nCPU: {target['cpu_percent']}% | RAM: {target['memory_mb']} MB",
                fg=COLOR_TEXT_PRIMARY
            )
            self.prio_var.set(target["priority"])

    def _apply_tuning(self):
        if not self.selected_pid:
            messagebox.showinfo("No Selection", "Please select a process from the table first.")
            return

        prio = self.prio_var.get()
        affinity = self.affinity_var.get()
        io_prio = self.io_var.get()

        self.controller.apply_priority(self.selected_pid, prio)
        self.controller.apply_affinity(self.selected_pid, affinity)
        self.controller.apply_io_priority(self.selected_pid, io_prio)

    def _trim_selected(self):
        if self.selected_pid:
            self.controller.trim_process(self.selected_pid)

    def _kill_selected(self):
        if self.selected_pid:
            if messagebox.askyesno("Confirm Terminate", f"Terminate {self.selected_process_name} (PID: {self.selected_pid})?"):
                self.controller.kill_process(self.selected_pid)

    def _on_smart_trim_clicked(self):
        trimmed = self.controller.trim_all()
        messagebox.showinfo("SmartTrim", f"Working set successfully flushed across {trimmed} processes.")

def launch_gui(config_path: str = "config/default_rules.json"):
    app = ProxessorGUI(config_path)
    app.mainloop()

if __name__ == "__main__":
    launch_gui()
