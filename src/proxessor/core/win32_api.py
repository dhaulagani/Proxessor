import ctypes
from ctypes import wintypes
import psutil
from typing import Optional, Tuple

# Windows Constants
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_QUOTA = 0x0100

# Priority Class Map
PRIORITY_MAP = {
    "IDLE": 0x00000040,
    "BELOW_NORMAL": 0x00004000,
    "NORMAL": 0x00000020,
    "ABOVE_NORMAL": 0x00008000,
    "HIGH": 0x00000080,
    "REALTIME": 0x00000100
}

REVERSE_PRIORITY_MAP = {v: k for k, v in PRIORITY_MAP.items()}

# IO Priority Constants (NtSetInformationProcess)
# ProcessIoPriority = 33
PROCESS_IO_PRIORITY_CLASS = 33
IO_PRIORITY_MAP = {
    "VERY_LOW": 0,
    "LOW": 1,
    "NORMAL": 2,
    "HIGH": 3
}

# Memory Priority (SetProcessInformation)
# ProcessMemoryPriority = 4
PROCESS_MEMORY_PRIORITY = 4

# Power Throttling (EcoQoS)
# ProcessPowerThrottling = 0x1
PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1

class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.ULONG),
        ("ControlMask", wintypes.ULONG),
        ("StateMask", wintypes.ULONG)
    ]

class MEMORY_PRIORITY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("MemoryPriority", wintypes.ULONG)
    ]

class Win32ProcessAPI:
    """Wrapper for low-level Windows NT kernel process optimization APIs."""

    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.user32 = ctypes.windll.user32
        self.psapi = ctypes.windll.psapi
        self.ntdll = ctypes.windll.ntdll

    def get_foreground_process_id(self) -> Optional[int]:
        """Returns the PID owning the currently focused foreground window."""
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value if pid.value != 0 else None
        except Exception:
            return None

    def set_process_priority(self, pid: int, priority_name: str) -> bool:
        """Sets the Win32 CPU priority class for a process."""
        priority_val = PRIORITY_MAP.get(priority_name.upper())
        if priority_val is None:
            return False

        h_process = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not h_process:
            return False

        try:
            res = self.kernel32.SetPriorityClass(h_process, priority_val)
            return bool(res)
        finally:
            self.kernel32.CloseHandle(h_process)

    def get_process_priority(self, pid: int) -> Optional[str]:
        """Gets the Win32 CPU priority class name for a process."""
        h_process = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_process:
            return None
        try:
            val = self.kernel32.GetPriorityClass(h_process)
            return REVERSE_PRIORITY_MAP.get(val, "UNKNOWN")
        finally:
            self.kernel32.CloseHandle(h_process)

    def set_process_affinity(self, pid: int, affinity_mask: int) -> bool:
        """Sets the CPU affinity bitmask for a process."""
        h_process = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not h_process:
            return False
        try:
            mask_ptr = ctypes.c_size_t(affinity_mask)
            res = self.kernel32.SetProcessAffinityMask(h_process, mask_ptr)
            return bool(res)
        finally:
            self.kernel32.CloseHandle(h_process)

    def set_process_io_priority(self, pid: int, io_priority_str: str) -> bool:
        """Sets I/O Priority via NtSetInformationProcess."""
        prio_val = IO_PRIORITY_MAP.get(io_priority_str.upper())
        if prio_val is None:
            return False

        h_process = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not h_process:
            return False

        try:
            io_val = wintypes.ULONG(prio_val)
            status = self.ntdll.NtSetInformationProcess(
                h_process,
                PROCESS_IO_PRIORITY_CLASS,
                ctypes.byref(io_val),
                ctypes.sizeof(io_val)
            )
            return status == 0
        finally:
            self.kernel32.CloseHandle(h_process)

    def set_process_memory_priority(self, pid: int, memory_priority: int) -> bool:
        """Sets memory page replacement priority (0 to 5) via SetProcessInformation."""
        if not (0 <= memory_priority <= 5):
            return False

        h_process = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not h_process:
            return False

        try:
            mem_info = MEMORY_PRIORITY_INFORMATION(MemoryPriority=memory_priority)
            res = self.kernel32.SetProcessInformation(
                h_process,
                PROCESS_MEMORY_PRIORITY,
                ctypes.byref(mem_info),
                ctypes.sizeof(mem_info)
            )
            return bool(res)
        except Exception:
            return False
        finally:
            self.kernel32.CloseHandle(h_process)

    def set_process_power_throttling(self, pid: int, enable_eco_qos: bool) -> bool:
        """Enables or disables Windows EcoQoS / Power Throttling."""
        h_process = self.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
        if not h_process:
            return False

        try:
            state = PROCESS_POWER_THROTTLING_STATE()
            state.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
            state.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            state.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED if enable_eco_qos else 0

            # ProcessPowerThrottling is index 0x1 in PROCESS_INFORMATION_CLASS enum
            res = self.kernel32.SetProcessInformation(
                h_process,
                1,
                ctypes.byref(state),
                ctypes.sizeof(state)
            )
            return bool(res)
        except Exception:
            return False
        finally:
            self.kernel32.CloseHandle(h_process)

    def trim_process_working_set(self, pid: int) -> bool:
        """Trims unreferenced physical pages from the process working set."""
        h_process = self.kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not h_process:
            return False
        try:
            res = self.psapi.EmptyWorkingSet(h_process)
            return bool(res)
        finally:
            self.kernel32.CloseHandle(h_process)

    def get_system_ram_percent(self) -> float:
        """Returns the current system RAM utilization percentage."""
        return psutil.virtual_memory().percent

    def get_system_idle_seconds(self) -> float:
        """Returns the number of seconds since the last user keyboard or mouse input."""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        lii = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
        if self.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = self.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
        return 0.0

    def get_process_gui_resources(self, pid: int) -> Tuple[int, int]:
        """Returns (gdi_objects_count, user_objects_count) allocated by process."""
        h_process = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_process:
            return (0, 0)
        try:
            gdi = self.user32.GetGuiResources(h_process, 0)
            usr = self.user32.GetGuiResources(h_process, 1)
            return (int(gdi), int(usr))
        finally:
            self.kernel32.CloseHandle(h_process)
