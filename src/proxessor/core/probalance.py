import time
from typing import Dict, List, Optional, Set

class ProBalanceEngine:
    """Implements the ProBalance dynamic priority restraint heuristic."""

    def __init__(self, config: Dict):
        self.enabled = config.get("enabled", True)
        self.cpu_trigger_threshold = float(config.get("cpu_trigger_threshold_percent", 65.0))
        self.per_process_cpu_trigger = float(config.get("per_process_cpu_trigger_percent", 20.0))
        self.target_restraint_priority = config.get("target_restraint_priority", "BELOW_NORMAL")
        self.restraint_duration = float(config.get("restraint_duration_seconds", 10.0))
        self.recovery_threshold = float(config.get("recovery_threshold_percent", 50.0))
        self.ignore_foreground = config.get("ignore_foreground_process", True)

        raw_exclusions = config.get("excluded_processes", [])
        self.excluded_names: Set[str] = {x.lower() for x in raw_exclusions}

        # Track currently restrained processes:
        # pid -> {"name": str, "base_priority": str, "restrained_timestamp": float}
        self.restrained_processes: Dict[int, Dict] = {}

    def is_eligible_for_restraint(
        self,
        pid: int,
        name: str,
        current_priority: str,
        foreground_pid: Optional[int]
    ) -> bool:
        """Determines if a process is eligible to be dynamically restrained."""
        if not self.enabled:
            return False

        if name.lower() in self.excluded_names:
            return False

        if self.ignore_foreground and foreground_pid is not None and pid == foreground_pid:
            return False

        # If already at or below target restraint priority, do not restrain further
        if current_priority in ("BELOW_NORMAL", "IDLE"):
            return False

        return True

    def evaluate(
        self,
        system_cpu_percent: float,
        process_snapshots: List[Dict],
        foreground_pid: Optional[int],
        current_time: Optional[float] = None
    ) -> List[Dict]:
        """Evaluates system & process loads and returns restraint or restoration actions.

        Each process in process_snapshots has: {'pid': int, 'name': str, 'cpu_percent': float, 'priority': str}
        """
        if not self.enabled:
            return []

        now = current_time if current_time is not None else time.time()
        actions = []
        active_pids = {p["pid"] for p in process_snapshots}

        # 1. Clean up stale/terminated restrained processes
        stale_pids = [pid for pid in self.restrained_processes if pid not in active_pids]
        for pid in stale_pids:
            del self.restrained_processes[pid]

        # 2. Check Restorations
        for pid, info in list(self.restrained_processes.items()):
            time_elapsed = now - info["restrained_timestamp"]
            # Restore if cooldown has elapsed AND system load is below recovery threshold
            if time_elapsed >= self.restraint_duration and system_cpu_percent < self.recovery_threshold:
                actions.append({
                    "action": "RESTORE",
                    "pid": pid,
                    "name": info["name"],
                    "target_priority": info["base_priority"]
                })
                del self.restrained_processes[pid]

        # 3. Check Restraints if System CPU exceeds trigger threshold
        if system_cpu_percent >= self.cpu_trigger_threshold:
            for p in process_snapshots:
                pid = p["pid"]
                name = p["name"]
                cpu_p = p.get("cpu_percent", 0.0)
                cur_prio = p.get("priority", "NORMAL")

                # If already restrained, skip
                if pid in self.restrained_processes:
                    continue

                if cpu_p >= self.per_process_cpu_trigger:
                    if self.is_eligible_for_restraint(pid, name, cur_prio, foreground_pid):
                        actions.append({
                            "action": "RESTRAIN",
                            "pid": pid,
                            "name": name,
                            "target_priority": self.target_restraint_priority,
                            "base_priority": cur_prio
                        })
                        self.restrained_processes[pid] = {
                            "name": name,
                            "base_priority": cur_prio,
                            "restrained_timestamp": now
                        }

        return actions
