import time
import psutil
from typing import Dict, Set, Optional
from src.proxessor.core.win32_api import Win32ProcessAPI
from src.proxessor.core.cpu_topology import CPUTopology
from src.proxessor.core.power_manager import PowerPlanManager
from src.proxessor.core.probalance import ProBalanceEngine
from src.proxessor.core.watchdog import WatchdogEngine
from src.proxessor.rules.manager import RuleManager

class GovernorEngine:
    """Master background optimization daemon that orchestrates Win32 kernel calls,

    ProBalance heuristics, CPU topology rules, and memory trimming."""

    def __init__(self, config_path: str, dry_run: bool = False):
        self.config_path = config_path
        self.dry_run = dry_run
        self.rule_manager = RuleManager(config_path)
        self.win32 = Win32ProcessAPI()
        self.topology = CPUTopology()
        self.power_manager = PowerPlanManager()
        self.probalance = ProBalanceEngine(self.rule_manager.probalance_config)
        self.watchdog = WatchdogEngine(self.rule_manager.watchdogs)

        # Cache of applied rule configurations per PID to eliminate redundant kernel API calls:
        # pid -> {"priority": str, "affinity": int, "io_priority": str, "eco_qos": bool}
        self.applied_cache: Dict[int, Dict] = {}
        self.last_smart_trim_time = 0.0
        self.current_foreground_pid: Optional[int] = None

    def tick(self):
        """Executes a single optimization and monitoring tick."""
        now = time.time()
        system_cpu = psutil.cpu_percent(interval=None)

        # 1. Track Foreground Window
        if self.rule_manager.engine_config.foreground_boost_enabled:
            fg_pid = self.win32.get_foreground_process_id()
            self.current_foreground_pid = fg_pid

        # 2. Collect Process Snapshots
        snapshots = []
        active_pids = set()

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                p_info = proc.info
                pid = p_info['pid']
                name = p_info['name'] or ""
                active_pids.add(pid)

                # Skip system idle
                if pid <= 4 or not name:
                    continue

                mem_mb = (p_info['memory_info'].rss / (1024 * 1024)) if p_info.get('memory_info') else 0.0
                cpu_p = p_info.get('cpu_percent', 0.0) or 0.0
                create_t = p_info.get('create_time', 0.0) or 0.0

                snapshots.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": cpu_p,
                    "memory_mb": mem_mb,
                    "create_time": create_t,
                    "priority": self.win32.get_process_priority(pid) or "NORMAL"
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Evict dead PIDs from cache
        dead_pids = [p for p in self.applied_cache if p not in active_pids]
        for p in dead_pids:
            del self.applied_cache[p]

        # 3. Apply Persistent Rules
        for snap in snapshots:
            pid = snap["pid"]
            name = snap["name"]
            rule = self.rule_manager.match_rule(name)

            if rule:
                if pid not in self.applied_cache:
                    self.applied_cache[pid] = {}

                cached = self.applied_cache[pid]

                # Priority rule
                if rule.priority and cached.get("priority") != rule.priority:
                    if not self.dry_run:
                        self.win32.set_process_priority(pid, rule.priority)
                    cached["priority"] = rule.priority

                # Affinity rule
                if rule.cpu_affinity:
                    mask = self.topology.parse_affinity_mask(rule.cpu_affinity)
                    if cached.get("affinity") != mask:
                        if not self.dry_run:
                            self.win32.set_process_affinity(pid, mask)
                        cached["affinity"] = mask

                # I/O Priority rule
                if rule.io_priority and cached.get("io_priority") != rule.io_priority:
                    if not self.dry_run:
                        self.win32.set_process_io_priority(pid, rule.io_priority)
                    cached["io_priority"] = rule.io_priority

                # Memory Priority rule
                if rule.memory_priority is not None and cached.get("memory_priority") != rule.memory_priority:
                    if not self.dry_run:
                        self.win32.set_process_memory_priority(pid, rule.memory_priority)
                    cached["memory_priority"] = rule.memory_priority

                # Power Throttling / EcoQoS
                if rule.power_throttling_eco_qos is not None and cached.get("eco_qos") != rule.power_throttling_eco_qos:
                    if not self.dry_run:
                        self.win32.set_process_power_throttling(pid, rule.power_throttling_eco_qos)
                    cached["eco_qos"] = rule.power_throttling_eco_qos

                # Power Scheme Trigger
                if rule.power_scheme and not self.dry_run:
                    self.power_manager.set_active_scheme(rule.power_scheme)

        # 4. ProBalance Dynamic Priority Restraint
        pb_actions = self.probalance.evaluate(
            system_cpu_percent=system_cpu,
            process_snapshots=snapshots,
            foreground_pid=self.current_foreground_pid,
            current_time=now
        )
        for act in pb_actions:
            target_pid = act["pid"]
            target_prio = act["target_priority"]
            if not self.dry_run:
                self.win32.set_process_priority(target_pid, target_prio)

        # 5. Watchdogs
        wd_actions = self.watchdog.evaluate(snapshots)
        for w_act in wd_actions:
            t_pid = w_act["pid"]
            action = w_act["action"]
            if action == "TRIM_WORKING_SET" and not self.dry_run:
                self.win32.trim_process_working_set(t_pid)
            elif action == "TERMINATE_NEWEST" and not self.dry_run:
                try:
                    p = psutil.Process(t_pid)
                    p.terminate()
                except Exception:
                    pass

        # 6. SmartTrim (Working Set Trimming upon System RAM Threshold)
        eng_cfg = self.rule_manager.engine_config
        if eng_cfg.smart_trim_enabled:
            if (now - self.last_smart_trim_time) >= eng_cfg.smart_trim_interval_seconds:
                current_ram = self.win32.get_system_ram_percent()
                if current_ram >= eng_cfg.smart_trim_threshold_percent:
                    if not self.dry_run:
                        for s in snapshots:
                            self.win32.trim_process_working_set(s["pid"])
                    self.last_smart_trim_time = now

        return {
            "timestamp": now,
            "system_cpu": system_cpu,
            "monitored_processes": len(snapshots),
            "probalance_actions": len(pb_actions),
            "watchdog_actions": len(wd_actions)
        }

    def run_forever(self):
        """Starts the persistent governor background loop."""
        poll_sec = max(0.2, self.rule_manager.engine_config.poll_interval_ms / 1000.0)
        try:
            while True:
                self.tick()
                time.sleep(poll_sec)
        except KeyboardInterrupt:
            pass
