import time
import json
import collections
import psutil
from typing import Dict, List, Optional
from src.proxessor.core.win32_api import Win32ProcessAPI
from src.proxessor.core.cpu_topology import CPUTopology
from src.proxessor.core.power_manager import PowerPlanManager
from src.proxessor.core.probalance import ProBalanceEngine
from src.proxessor.rules.manager import RuleManager
from src.proxessor.rules.schema import ProcessRule
from src.proxessor.core.filelock import FileLockHunter
from src.proxessor.core.connections import SocketInspector

class GUIController:
    """Enterprise-grade GUI controller providing live telemetry history,

    comprehensive process arbitration, and persistent rule management."""

    def __init__(self, config_path: str = "config/default_rules.json"):
        self.config_path = config_path
        self.rule_manager = RuleManager(config_path)
        self.win32 = Win32ProcessAPI()
        self.topology = CPUTopology()
        self.power_manager = PowerPlanManager()
        self.probalance = ProBalanceEngine(self.rule_manager.probalance_config)
        self.file_lock_hunter = FileLockHunter()
        self.socket_inspector = SocketInspector()

        self.cached_processes: List[Dict] = []
        self.system_cpu: float = 0.0
        self.system_ram: float = 0.0
        self.foreground_pid: Optional[int] = None
        self.events_log: List[str] = []

        # Real-time Telemetry History for Graphing (60 data points)
        self.history_len = 60
        self.cpu_history = collections.deque([0.0] * self.history_len, maxlen=self.history_len)
        self.ram_history = collections.deque([0.0] * self.history_len, maxlen=self.history_len)
        self.restraint_history = collections.deque([0.0] * self.history_len, maxlen=self.history_len)

    def log_event(self, message: str):
        """Appends a timestamped log entry to the in-memory event stream."""
        t_str = time.strftime("%H:%M:%S")
        self.events_log.append(f"[{t_str}] {message}")
        if len(self.events_log) > 300:
            self.events_log.pop(0)

    def refresh_state(self) -> Dict:
        """Polls current system metrics, processes, and evaluates ProBalance."""
        self.system_cpu = psutil.cpu_percent(interval=None)
        self.system_ram = self.win32.get_system_ram_percent()
        self.foreground_pid = self.win32.get_foreground_process_id()

        # Update telemetry history
        self.cpu_history.append(self.system_cpu)
        self.ram_history.append(self.system_ram)

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

                is_restrained = (pid in self.probalance.restrained_processes)
                is_excluded = (name.lower() in self.probalance.excluded_names)
                is_fg = (pid == self.foreground_pid)

                proc_list.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": round(cpu_p, 1),
                    "memory_mb": round(mem_mb, 1),
                    "threads": threads,
                    "priority": prio,
                    "is_foreground": is_fg,
                    "is_restrained": is_restrained,
                    "is_excluded": is_excluded
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

        restrained_count = len(self.probalance.restrained_processes)
        self.restraint_history.append(float(restrained_count * 20.0)) # scaled for graph display
        self.cached_processes = proc_list

        return {
            "system_cpu": self.system_cpu,
            "system_ram": self.system_ram,
            "foreground_pid": self.foreground_pid,
            "processes_count": len(proc_list),
            "restrained_count": restrained_count,
            "processes": proc_list,
            "per_core_cpu": psutil.cpu_percent(percpu=True),
            "cpu_history": list(self.cpu_history),
            "ram_history": list(self.ram_history),
            "restraint_history": list(self.restraint_history)
        }

    def get_filtered_processes(
        self,
        search_query: str = "",
        sort_by: str = "cpu_percent",
        reverse: bool = True,
        active_only: bool = False
    ) -> List[Dict]:
        """Filters and sorts the cached process list."""
        query = (search_query or "").strip().lower()

        results = self.cached_processes
        if active_only:
            results = [p for p in results if p["cpu_percent"] > 0.0 or p["is_restrained"] or p["is_foreground"]]

        if query:
            results = [
                p for p in results
                if query in p["name"].lower() or query == str(p["pid"])
            ]

        try:
            return sorted(results, key=lambda x: x.get(sort_by, 0), reverse=reverse)
        except Exception:
            return results

    def apply_priority(self, pid: int, priority_name: str, persistent: bool = False) -> bool:
        """Sets priority class on target PID, optionally persisting rule."""
        ok = self.win32.set_process_priority(pid, priority_name)
        if ok:
            self.log_event(f"User applied PID {pid} Priority -> {priority_name} {'(Saved to Rules)' if persistent else ''}")
            if persistent:
                self._persist_rule_field(pid, "priority", priority_name)
        return ok

    def apply_affinity(self, pid: int, affinity_spec: str, persistent: bool = False) -> bool:
        """Sets affinity mask on target PID, optionally persisting rule."""
        mask = self.topology.parse_affinity_mask(affinity_spec)
        ok = self.win32.set_process_affinity(pid, mask)
        if ok:
            self.log_event(f"User applied PID {pid} Affinity -> {affinity_spec} ({hex(mask)}) {'(Saved to Rules)' if persistent else ''}")
            if persistent:
                self._persist_rule_field(pid, "cpu_affinity", affinity_spec)
        return ok

    def apply_io_priority(self, pid: int, io_priority_str: str, persistent: bool = False) -> bool:
        """Sets I/O priority on target PID, optionally persisting rule."""
        ok = self.win32.set_process_io_priority(pid, io_priority_str)
        if ok:
            self.log_event(f"User applied PID {pid} I/O Priority -> {io_priority_str} {'(Saved to Rules)' if persistent else ''}")
            if persistent:
                self._persist_rule_field(pid, "io_priority", io_priority_str)
        return ok

    def apply_memory_priority(self, pid: int, memory_priority: int, persistent: bool = False) -> bool:
        """Sets Memory Page Replacement Priority (0 to 5) on target PID."""
        ok = self.win32.set_process_memory_priority(pid, memory_priority)
        if ok:
            self.log_event(f"User applied PID {pid} Memory Priority -> {memory_priority} {'(Saved to Rules)' if persistent else ''}")
            if persistent:
                self._persist_rule_field(pid, "memory_priority", memory_priority)
        return ok

    def apply_eco_qos(self, pid: int, enable: bool, persistent: bool = False) -> bool:
        """Toggles EcoQoS (Power Throttling) on target PID."""
        ok = self.win32.set_process_power_throttling(pid, enable)
        if ok:
            self.log_event(f"User toggled PID {pid} EcoQoS -> {enable} {'(Saved to Rules)' if persistent else ''}")
            if persistent:
                self._persist_rule_field(pid, "power_throttling_eco_qos", enable)
        return ok

    def toggle_probalance_exclusion(self, process_name: str) -> bool:
        """Toggles a process into or out of ProBalance exclusion list."""
        name_lower = process_name.lower()
        if name_lower in self.probalance.excluded_names:
            self.probalance.excluded_names.remove(name_lower)
            self.log_event(f"Removed {process_name} from ProBalance Exclusions")
            return False
        else:
            self.probalance.excluded_names.add(name_lower)
            self.log_event(f"Added {process_name} to ProBalance Exclusions")
            return True

    def trim_process(self, pid: int) -> bool:
        """Flushes physical memory working set on target PID."""
        ok = self.win32.trim_process_working_set(pid)
        if ok:
            self.log_event(f"Flushed RAM working set for PID {pid}")
        return ok

    def trim_all(self) -> int:
        """Flushes working set on all monitored processes (SmartTrim)."""
        trimmed = 0
        for p in self.cached_processes:
            if self.win32.trim_process_working_set(p["pid"]):
                trimmed += 1
        self.log_event(f"SmartTrim flushed working sets across {trimmed} processes")
        return trimmed

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """Terminates or force kills target PID."""
        try:
            p = psutil.Process(pid)
            name = p.name()
            if force:
                p.kill()
            else:
                p.terminate()
            self.log_event(f"{'Force Killed' if force else 'Terminated'} PID {pid} ({name})")
            return True
        except Exception:
            return False

    def restart_process(self, pid: int) -> bool:
        """Restarts a process by spawning a new instance then terminating the old one."""
        try:
            p = psutil.Process(pid)
            exe_path = p.exe()
            cmdline = p.cmdline()
            import subprocess
            subprocess.Popen(cmdline if cmdline else [exe_path])
            p.terminate()
            self.log_event(f"Restarted process PID {pid} ({exe_path})")
            return True
        except Exception as e:
            self.log_event(f"Failed to restart PID {pid}: {e}")
            return False

    def change_power_scheme(self, scheme_name: str) -> bool:
        """Switches active Windows power plan."""
        ok = self.power_manager.set_active_scheme(scheme_name)
        if ok:
            self.log_event(f"Active Power Scheme changed to -> {scheme_name}")
        return ok

    def find_file_lockers(self, path: str) -> List[Dict]:
        """Scans path for open locks/handles via Windows Restart Manager."""
        results = self.file_lock_hunter.find_lockers(path)
        self.log_event(f"Scanned locks for '{path}': found {len(results)} process(es)")
        return results

    def list_connections(self, query: str = "") -> List[Dict]:
        """Enumerates active TCP/UDP sockets mapped to processes."""
        conns = self.socket_inspector.list_connections()
        # Associate process names
        pid_name_map = {p["pid"]: p["name"] for p in self.cached_processes}
        for c in conns:
            c["name"] = pid_name_map.get(c["pid"], "System" if c["pid"] == 4 else "Unknown")

        if not query:
            return conns

        q = query.lower()
        return [
            c for c in conns
            if q in c.get("name", "").lower()
            or q in str(c.get("local_port", ""))
            or q in str(c.get("remote_port", ""))
            or q in c.get("local_addr", "").lower()
            or q in str(c.get("remote_addr", "") or "").lower()
            or q in str(c.get("pid", ""))
        ]

    def get_per_core_cpu(self) -> List[float]:
        """Returns per-logical-core CPU usage percentages."""
        return psutil.cpu_percent(percpu=True)

    def _persist_rule_field(self, pid: int, field_name: str, value):
        """Helper to append or update a rule in config/default_rules.json."""
        target = next((p for p in self.cached_processes if p["pid"] == pid), None)
        if not target:
            return

        name = target["name"]
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            rules = data.get("rules", [])
            existing_rule = next((r for r in rules if name.lower() in r.get("pattern", "").lower()), None)
            if existing_rule:
                existing_rule[field_name] = value
            else:
                new_rule = {
                    "name": f"Custom Rule for {name}",
                    "pattern": f"(?i){name}",
                    field_name: value
                }
                rules.append(new_rule)

            data["rules"] = rules
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.rule_manager.load()
            self.log_event(f"Persisted rule '{field_name}: {value}' for {name} in config")
        except Exception as e:
            self.log_event(f"Error persisting rule for {name}: {e}")
