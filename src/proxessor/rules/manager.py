import json
import re
from typing import List, Optional, Tuple, Dict
from src.proxessor.rules.schema import ProcessRule, EngineConfig, ProBalanceConfig

class RuleManager:
    """Loads and compiles process optimization rules."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.engine_config = EngineConfig()
        self.probalance_config = {}
        self.rules: List[Tuple[re.Pattern, ProcessRule]] = []
        self.watchdogs: List[Dict] = []
        self.disallowed_patterns: List[re.Pattern] = []
        self.load()

    def _resolve_config_path(self, path: str) -> str:
        import os
        import sys
        if os.path.exists(path):
            return path
        candidates = [
            os.path.join(os.path.dirname(sys.executable), path),
            os.path.join(os.path.dirname(sys.executable), "config", "default_rules.json"),
            os.path.join(os.path.dirname(sys.executable), "default_rules.json"),
            os.path.join(getattr(sys, "_MEIPASS", ""), path) if getattr(sys, "_MEIPASS", None) else "",
            os.path.join(getattr(sys, "_MEIPASS", ""), "config", "default_rules.json") if getattr(sys, "_MEIPASS", None) else "",
            os.path.join(os.getcwd(), "config", "default_rules.json"),
            os.path.join(os.getcwd(), "default_rules.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "default_rules.json")
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return path

    def load(self):
        """Reads configuration JSON file and compiles patterns."""
        resolved = self._resolve_config_path(self.config_path)
        with open(resolved, "r", encoding="utf-8") as f:
            data = json.load(f)

        engine_data = data.get("engine", {})
        self.engine_config = EngineConfig(
            poll_interval_ms=engine_data.get("poll_interval_ms", 1000),
            foreground_boost_enabled=engine_data.get("foreground_boost_enabled", True),
            foreground_boost_priority=engine_data.get("foreground_boost_priority", "ABOVE_NORMAL"),
            idle_saver_enabled=engine_data.get("idle_saver_enabled", False),
            idle_saver_threshold_seconds=engine_data.get("idle_saver_threshold_seconds", 300.0),
            smart_trim_enabled=engine_data.get("smart_trim_enabled", True),
            smart_trim_threshold_percent=engine_data.get("smart_trim_threshold_percent", 85.0),
            smart_trim_interval_seconds=engine_data.get("smart_trim_interval_seconds", 300.0)
        )

        self.probalance_config = data.get("probalance", {})
        self.watchdogs = data.get("watchdogs", [])
        
        # Compile disallowed process patterns
        self.disallowed_patterns = []
        for dis in data.get("disallowed_processes", []):
            try:
                # If regex pattern provided, compile as-is; otherwise case-insensitive exact name match
                pat = dis if (dis.startswith("(?i)") or "\\" in dis or "*" in dis) else f"(?i)^{re.escape(dis)}$"
                self.disallowed_patterns.append(re.compile(pat))
            except re.error:
                continue

        self.rules = []
        for r_dict in data.get("rules", []):
            rule_obj = ProcessRule(
                name=r_dict.get("name", "Unnamed Rule"),
                pattern=r_dict.get("pattern", ""),
                priority=r_dict.get("priority"),
                io_priority=r_dict.get("io_priority"),
                memory_priority=r_dict.get("memory_priority"),
                power_throttling_eco_qos=r_dict.get("power_throttling_eco_qos"),
                cpu_affinity=r_dict.get("cpu_affinity"),
                power_scheme=r_dict.get("power_scheme")
            )
            try:
                compiled = re.compile(rule_obj.pattern)
                self.rules.append((compiled, rule_obj))
            except re.error:
                continue

    def match_rule(self, process_name: str) -> Optional[ProcessRule]:
        """Finds the first matching rule for a given process name."""
        for pattern, rule in self.rules:
            if pattern.search(process_name):
                return rule
        return None

    def is_disallowed(self, process_name: str) -> bool:
        """Checks if a process name matches any disallowed process pattern."""
        for pattern in self.disallowed_patterns:
            if pattern.search(process_name):
                return True
        return False
