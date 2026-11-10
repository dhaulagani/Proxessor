import os
import psutil
from typing import Dict, List, Optional

class CPUTopology:
    """Detects and calculates CPU affinity masks, with support for heterogeneous architectures (P-cores / E-cores)."""

    def __init__(self):
        self.logical_cores_count = os.cpu_count() or 1
        self.p_core_indices: List[int] = []
        self.e_core_indices: List[int] = []
        self._detect_core_classes()

    @property
    def total_cores(self) -> int:
        return self.logical_cores_count

    @property
    def p_cores(self) -> List[int]:
        return self.p_core_indices

    @property
    def e_cores(self) -> List[int]:
        return self.e_core_indices

    def _detect_core_classes(self):
        """Discovers core topology. If heterogeneous classification isn't exposed by standard API,

        allocates the first 50-70% of logical cores as primary cores."""
        # By default in consumer x86_64 chips (e.g. Alder Lake 12th/13th/14th gen):
        # P-cores with HyperThreading occupy the first 2*N logical processors.
        # If total logical cores > 8, we conservatively identify the lower half as P-Cores.
        if self.logical_cores_count > 4:
            split = self.logical_cores_count // 2
            self.p_core_indices = list(range(0, split))
            self.e_core_indices = list(range(split, self.logical_cores_count))
        else:
            self.p_core_indices = list(range(0, self.logical_cores_count))
            self.e_core_indices = []

    def get_all_cores_mask(self) -> int:
        """Returns bitmask covering all logical cores."""
        return (1 << self.logical_cores_count) - 1

    def get_p_cores_mask(self) -> int:
        """Returns bitmask selecting only Performance Cores."""
        mask = 0
        for idx in self.p_core_indices:
            mask |= (1 << idx)
        return mask if mask != 0 else self.get_all_cores_mask()

    def get_e_cores_mask(self) -> int:
        """Returns bitmask selecting only Efficiency Cores."""
        mask = 0
        for idx in self.e_core_indices:
            mask |= (1 << idx)
        return mask if mask != 0 else self.get_all_cores_mask()

    def parse_affinity_mask(self, mask_spec: str) -> int:
        """Parses affinity strings like 'ALL_CORES', 'P_CORES', 'E_CORES', or '0xFFFF'."""
        if not mask_spec:
            return self.get_all_cores_mask()

        spec = str(mask_spec).strip().upper()
        if spec in ("ALL_CORES", "ALL"):
            return self.get_all_cores_mask()
        if spec in ("P_CORES", "PERFORMANCE"):
            return self.get_p_cores_mask()
        if spec in ("E_CORES", "EFFICIENCY"):
            return self.get_e_cores_mask()

        # Handle hex or decimal numbers
        try:
            if spec.startswith("0X"):
                return int(spec, 16)
            return int(spec)
        except ValueError:
            return self.get_all_cores_mask()

    def get_summary(self) -> Dict:
        """Returns summary metadata of the CPU topology."""
        return {
            "total_logical_cores": self.logical_cores_count,
            "p_core_count": len(self.p_core_indices),
            "p_cores": self.p_core_indices,
            "e_core_count": len(self.e_core_indices),
            "e_cores": self.e_core_indices,
            "all_cores_mask_hex": hex(self.get_all_cores_mask()),
            "p_cores_mask_hex": hex(self.get_p_cores_mask()),
            "e_cores_mask_hex": hex(self.get_e_cores_mask())
        }
