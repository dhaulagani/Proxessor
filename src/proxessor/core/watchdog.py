from typing import Dict, List, Optional
import re
import psutil

class WatchdogEngine:
    """Monitors running processes for instance limits, memory hog thresholds, and triggers enforcement actions."""

    def __init__(self, watchdogs_config: List[Dict]):
        self.watchdogs = []
        for wd in watchdogs_config:
            pattern_str = wd.get("pattern", "")
            try:
                compiled = re.compile(pattern_str)
                self.watchdogs.append({
                    "name": wd.get("name", "Watchdog"),
                    "regex": compiled,
                    "max_instances": wd.get("max_instances"),
                    "max_memory_mb": wd.get("max_memory_mb"),
                    "action": wd.get("action", "LOG")
                })
            except re.error:
                continue

    def evaluate(self, process_snapshots: List[Dict]) -> List[Dict]:
        """Evaluates running processes and returns watchdog violation actions."""
        actions = []

        for wd in self.watchdogs:
            matching = [p for p in process_snapshots if wd["regex"].search(p["name"])]

            # Check instance count limits
            max_inst = wd.get("max_instances")
            if max_inst and len(matching) > max_inst:
                # Sort by creation time / PID descending (newest first)
                matching_sorted = sorted(matching, key=lambda x: x.get("create_time", 0.0), reverse=True)
                excess = matching_sorted[:(len(matching) - max_inst)]
                for target in excess:
                    actions.append({
                        "type": "INSTANCE_LIMIT_EXCEEDED",
                        "watchdog_name": wd["name"],
                        "pid": target["pid"],
                        "name": target["name"],
                        "action": wd.get("action", "TERMINATE_NEWEST")
                    })

            # Check memory consumption limits
            max_mem = wd.get("max_memory_mb")
            if max_mem:
                for target in matching:
                    mem_mb = target.get("memory_mb", 0.0)
                    if mem_mb > max_mem:
                        actions.append({
                            "type": "MEMORY_LIMIT_EXCEEDED",
                            "watchdog_name": wd["name"],
                            "pid": target["pid"],
                            "name": target["name"],
                            "memory_mb": mem_mb,
                            "action": wd.get("action", "TRIM_WORKING_SET")
                        })

        return actions
