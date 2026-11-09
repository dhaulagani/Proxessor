import time
import psutil
from typing import Dict, List, Optional
from src.proxessor.core.win32_api import Win32ProcessAPI
from src.proxessor.core.cpu_topology import CPUTopology
from src.proxessor.core.power_manager import PowerPlanManager
from src.proxessor.core.probalance import ProBalanceEngine
from src.proxessor.rules.manager import RuleManager

class GUIController:
    """Headless state controller that provides real-time telemetry, process lists,

    and Win32 action execution to the desktop GUI."""

    def __init__(self, config_path: str = "config/default_rules.json"):
        self.config_path = config_path
        self.rule_manager = RuleManager(config_path)
        self.win32 = Win32ProcessAPI()
        self.topology = CPUTopology()
        self.power_manager = PowerPlanManager()
        self.probalance = ProBalanceEngine(self.rule_manager.probalance_config)

        self.cached_processes: List[Dict] = []
        self.system_cpu: float = 0.0
        self.system_ram: float = 0.0
        self.foreground_pid: Optional[int] = None
        self.events_log: List[str] = []

    def log_event(self, message: str):
        """Appends a timestamped log entry to the in-memory event stream."""
        t_str = time.strftime("%H:%M:%S")
        self.events_log.append(f"[{t_str}] {message}")
        if len(self.events_log) > 200:
            self.events_log.pop(0)

    def refresh_state(self) -> Dict:
        """Polls current system metrics and processes."""
        self.system_cpu = psutil.cpu_percent(interval=None)
        self.system_ram = self.win32.get_system_ram_percent()
        self.foreground_pid = self.win32.get_foreground_process_id()

        proc_list = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'num_threads']):
            try:
                info = proc.info
                pid = info['pid']
                name = info['name'] or ""
                if pid <= 4 or not name:
                    continue

                mem_mb = (info['memory_info'].rss / (1024 * 1024)) if info.get('memory_info') else 0.0
                cpu_p = info.get('cpu_percent', 0.0) or 0.0
                threads = info.get('num_threads', 1) or 1
                prio = self.win32.get_process_priority(pid) or "NORMAL"

                proc_list.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": round(cpu_p, 1),
                    "memory_mb": round(mem_mb, 1),
                    "threads": threads,
                    "priority": prio,
                    "is_foreground": (pid == self.foreground_pid),
                    "is_restrained": (pid in self.probalance.restrained_processes)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Evaluate ProBalance actions in real-time
        pb_actions = self.probalance.evaluate(
            system_cpu_percent=self.system_cpu,
            process_snapshots=proc_list,
            foreground_pid=self.foreground_pid
        )
        for act in pb_actions:
            if act["action"] == "RESTRAIN":
                self.win32.set_process_priority(act["pid"], act["target_priority"])
                self.log_event(f"ProBalance RESTRAINED PID {act['pid']} ({act['name']}) -> {act['target_priority']}")
            elif act["action"] == "RESTORE":
                self.win32.set_process_priority(act["pid"], act["target_priority"])
                self.log_event(f"ProBalance RESTORED PID {act['pid']} ({act['name']}) -> {act['target_priority']}")

        self.cached_processes = proc_list
        return {
            "system_cpu": self.system_cpu,
            "system_ram": self.system_ram,
            "foreground_pid": self.foreground_pid,
            "processes_count": len(proc_list),
            "restrained_count": len(self.probalance.restrained_processes),
            "processes": proc_list
        }

    def get_filtered_processes(
        self,
        search_query: str = "",
        sort_by: str = "cpu_percent",
        reverse: bool = True
    ) -> List[Dict]:
        """Filters and sorts the cached process list."""
        query = (search_query or "").strip().lower()
        if not query:
            filtered = list(self.cached_processes)
        else:
            filtered = [
                p for p in self.cached_processes
                if query in p["name"].lower() or query == str(p["pid"])
            ]

        try:
            return sorted(filtered, key=lambda x: x.get(sort_by, 0), reverse=reverse)
        except Exception:
            return filtered

    def apply_priority(self, pid: int, priority_name: str) -> bool:
        """Sets priority class on target PID."""
        ok = self.win32.set_process_priority(pid, priority_name)
        if ok:
            self.log_event(f"User set PID {pid} priority -> {priority_name}")
        return ok

    def apply_affinity(self, pid: int, affinity_spec: str) -> bool:
        """Sets affinity mask on target PID."""
        mask = self.topology.parse_affinity_mask(affinity_spec)
        ok = self.win32.set_process_affinity(pid, mask)
        if ok:
            self.log_event(f"User set PID {pid} affinity -> {affinity_spec} ({hex(mask)})")
        return ok

    def apply_io_priority(self, pid: int, io_priority_str: str) -> bool:
        """Sets I/O priority on target PID."""
        ok = self.win32.set_process_io_priority(pid, io_priority_str)
        if ok:
            self.log_event(f"User set PID {pid} I/O priority -> {io_priority_str}")
        return ok

    def apply_eco_qos(self, pid: int, enable: bool) -> bool:
        """Toggles EcoQoS on target PID."""
        ok = self.win32.set_process_power_throttling(pid, enable)
        if ok:
            self.log_event(f"User toggled PID {pid} EcoQoS -> {enable}")
        return ok

    def trim_process(self, pid: int) -> bool:
        """Flushes physical memory working set on target PID."""
        ok = self.win32.trim_process_working_set(pid)
        if ok:
            self.log_event(f"Trimmed working set for PID {pid}")
        return ok

    def trim_all(self) -> int:
        """Flushes working set on all monitored processes (SmartTrim)."""
        trimmed = 0
        for p in self.cached_processes:
            if self.win32.trim_process_working_set(p["pid"]):
                trimmed += 1
        self.log_event(f"SmartTrim flushed RAM across {trimmed} processes")
        return trimmed

    def kill_process(self, pid: int) -> bool:
        """Terminates target PID."""
        try:
            p = psutil.Process(pid)
            p.terminate()
            self.log_event(f"Terminated PID {pid} ({p.name()})")
            return True
        except Exception:
            return False

    def change_power_scheme(self, scheme_name: str) -> bool:
        """Switches active Windows power plan."""
        ok = self.power_manager.set_active_scheme(scheme_name)
        if ok:
            self.log_event(f"System Power Scheme changed to -> {scheme_name}")
        return ok
