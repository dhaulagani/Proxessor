from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ProcessRule:
    name: str
    pattern: str
    priority: Optional[str] = None
    io_priority: Optional[str] = None
    memory_priority: Optional[int] = None
    power_throttling_eco_qos: Optional[bool] = None
    cpu_affinity: Optional[str] = None
    power_scheme: Optional[str] = None

@dataclass
class EngineConfig:
    poll_interval_ms: int = 1000
    foreground_boost_enabled: bool = True
    smart_trim_enabled: bool = True
    smart_trim_threshold_percent: float = 85.0
    smart_trim_interval_seconds: float = 300.0

@dataclass
class ProBalanceConfig:
    enabled: bool = True
    cpu_trigger_threshold_percent: float = 65.0
    per_process_cpu_trigger_percent: float = 20.0
    target_restraint_priority: str = "BELOW_NORMAL"
    restraint_duration_seconds: float = 10.0
    recovery_threshold_percent: float = 50.0
    ignore_foreground_process: bool = True
    excluded_processes: List[str] = field(default_factory=list)
