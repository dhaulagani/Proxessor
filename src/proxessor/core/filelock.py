"""File Lock Hunter module for Proxessor.
Identifies processes holding open locks or handles on files/directories
using the Windows Restart Manager API (rstrtmgr.dll).
"""

import os
import sys
import ctypes
from ctypes import wintypes
from typing import List, Dict, Optional

# Ctypes structures for Restart Manager
CCH_RM_SESSION_KEY = 32
CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63

class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [
        ("dwProcessId", wintypes.DWORD),
        ("ProcessStartTime", wintypes.FILETIME),
    ]

class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", wintypes.WCHAR * (CCH_RM_MAX_APP_NAME + 1)),
        ("strServiceShortName", wintypes.WCHAR * (CCH_RM_MAX_SVC_NAME + 1)),
        ("ApplicationType", wintypes.DWORD),
        ("AppStatus", wintypes.DWORD),
        ("TSSessionId", wintypes.DWORD),
        ("bRestartable", wintypes.BOOL),
    ]

APP_TYPE_NAMES = {
    1: "MainWindow",
    2: "OtherWindow",
    3: "Service",
    4: "Explorer",
    5: "Console",
    1000: "CriticalSystem",
}

class FileLockHunter:
    """Detects which processes are locking a specified file or directory."""

    def __init__(self):
        try:
            self.rstrtmgr = ctypes.WinDLL("rstrtmgr.dll")
        except Exception:
            self.rstrtmgr = None

    def find_lockers(self, target_path: str) -> List[Dict[str, any]]:
        """Returns list of processes holding a lock on target_path."""
        if not os.path.exists(target_path):
            return []

        # If rstrtmgr dll is loaded, query directly via Win32 API
        if self.rstrtmgr:
            try:
                return self._query_restart_manager(target_path)
            except Exception:
                pass

        # Fallback: invoke native rust proxessor binary if available
        return self._query_native_cli(target_path)

    def _query_restart_manager(self, target_path: str) -> List[Dict[str, any]]:
        abs_path = os.path.abspath(target_path)
        session_handle = wintypes.DWORD()
        session_key = (wintypes.WCHAR * (CCH_RM_SESSION_KEY + 1))()

        res = self.rstrtmgr.RmStartSession(
            ctypes.byref(session_handle),
            wintypes.DWORD(0),
            session_key
        )
        if res != 0:
            return []

        try:
            path_array = (wintypes.LPCWSTR * 1)(abs_path)
            res = self.rstrtmgr.RmRegisterResources(
                session_handle,
                wintypes.UINT(1),
                path_array,
                wintypes.UINT(0),
                None,
                wintypes.UINT(0),
                None
            )
            if res != 0:
                return []

            proc_info_needed = wintypes.DWORD(0)
            proc_info_count = wintypes.DWORD(0)
            reboot_reasons = wintypes.DWORD(0)

            # Sizing call
            res = self.rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(proc_info_needed),
                ctypes.byref(proc_info_count),
                None,
                ctypes.byref(reboot_reasons)
            )

            # 234 is ERROR_MORE_DATA
            if proc_info_needed.value == 0:
                return []

            proc_info_array = (RM_PROCESS_INFO * proc_info_needed.value)()
            proc_info_count.value = proc_info_needed.value

            res = self.rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(proc_info_needed),
                ctypes.byref(proc_info_count),
                proc_info_array,
                ctypes.byref(reboot_reasons)
            )

            if res != 0:
                return []

            results = []
            for i in range(proc_info_count.value):
                item = proc_info_array[i]
                app_name = item.strAppName or "Unknown"
                svc_name = item.strServiceShortName or None
                results.append({
                    "pid": int(item.Process.dwProcessId),
                    "app_name": str(app_name),
                    "service": str(svc_name) if svc_name else None,
                    "kind": APP_TYPE_NAMES.get(item.ApplicationType, "Other"),
                })
            return results

        finally:
            self.rstrtmgr.RmEndSession(session_handle)

    def _query_native_cli(self, target_path: str) -> List[Dict[str, any]]:
        import subprocess
        candidate_paths = [
            "proxessor.exe",
            os.path.join(os.path.dirname(sys.executable), "proxessor.exe"),
            os.path.join(getattr(sys, '_MEIPASS', ''), "proxessor.exe") if getattr(sys, '_MEIPASS', None) else "",
            "rust/target/release/proxessor.exe",
            "rust/target/debug/proxessor.exe",
        ]
        for exe_path in candidate_paths:
            if exe_path and os.path.exists(exe_path):
                try:
                    out = subprocess.check_output([exe_path, "filelock", target_path], text=True, stderr=subprocess.DEVNULL)
                    # Parse output lines
                    results = []
                    lines = out.strip().splitlines()
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 3 and parts[0].isdigit():
                            results.append({
                                "pid": int(parts[0]),
                                "app_name": parts[1],
                                "kind": parts[2],
                                "service": parts[3] if len(parts) > 3 and parts[3] != "-" else None,
                            })
                    return results
                except Exception:
                    pass
        return []
