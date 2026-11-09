import ctypes
from ctypes import wintypes
import uuid
from typing import Optional, Dict

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

# Standard Windows Power Scheme GUIDs
SCHEME_GUID_MAP = {
    "BALANCED": uuid.UUID("381b4222-f694-41f0-9685-ff5bb260df2e"),
    "HIGH_PERFORMANCE": uuid.UUID("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"),
    "POWER_SAVER": uuid.UUID("a1841308-3541-4fab-bc81-f71556f20b4a"),
    "ULTIMATE_PERFORMANCE": uuid.UUID("e9a42b02-d5df-448d-aa00-03f14749eb61")
}

def uuid_to_guid_struct(u: uuid.UUID) -> GUID:
    """Converts a standard Python UUID object to a Win32 GUID structure."""
    raw = u.bytes_le
    guid = GUID()
    ctypes.memmove(ctypes.byref(guid), raw, 16)
    return guid

class PowerPlanManager:
    """Manages active Windows Power Plans dynamically."""

    def __init__(self):
        try:
            self.powrprof = ctypes.windll.powrprof
        except Exception:
            self.powrprof = None
        self.active_scheme_name: Optional[str] = None

    def set_active_scheme(self, scheme_name: str) -> bool:
        """Sets the active system power plan by friendly name."""
        if not self.powrprof:
            return False

        u = SCHEME_GUID_MAP.get(scheme_name.upper())
        if not u:
            return False

        guid_struct = uuid_to_guid_struct(u)
        try:
            res = self.powrprof.PowerSetActiveScheme(None, ctypes.byref(guid_struct))
            if res == 0:
                self.active_scheme_name = scheme_name.upper()
                return True
            return False
        except Exception:
            return False
