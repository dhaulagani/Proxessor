"""Network Sockets & Connection Inspector module for Proxessor.
Enumerates active TCP and UDP endpoints and associates them with process PIDs.
"""

import os
import sys
import socket
import struct
import ctypes
from ctypes import wintypes
from typing import List, Dict, Optional

class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]

class MIB_UDPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    ]

TCP_STATE_MAP = {
    1: "CLOSED",
    2: "LISTENING",
    3: "SYN_SENT",
    4: "SYN_RCVD",
    5: "ESTABLISHED",
    6: "FIN_WAIT_1",
    7: "FIN_WAIT_2",
    8: "CLOSE_WAIT",
    9: "CLOSING",
    10: "LAST_ACK",
    11: "TIME_WAIT",
    12: "DELETE_TCB",
}

AF_INET = 2
TCP_TABLE_OWNER_PID_ALL = 5
UDP_TABLE_OWNER_PID = 1

def _decode_ip(addr_int: int) -> str:
    return socket.inet_ntoa(struct.pack("<L", addr_int))

def _decode_port(port_int: int) -> int:
    return socket.ntohs(port_int & 0xFFFF)

class SocketInspector:
    """Inspects TCP and UDP network sockets mapped to process PIDs."""

    def __init__(self):
        try:
            self.iphlpapi = ctypes.WinDLL("iphlpapi.dll")
        except Exception:
            self.iphlpapi = None

    def list_connections(self) -> List[Dict[str, any]]:
        """Returns combined list of active TCP and UDP endpoints."""
        if self.iphlpapi:
            try:
                results = self._get_tcp_connections()
                results.extend(self._get_udp_connections())
                return results
            except Exception:
                pass

        return self._query_native_cli()

    def _get_tcp_connections(self) -> List[Dict[str, any]]:
        size = wintypes.DWORD(0)
        self.iphlpapi.GetExtendedTcpTable(None, ctypes.byref(size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)
        if size.value == 0:
            return []

        buf = ctypes.create_string_buffer(size.value)
        ret = self.iphlpapi.GetExtendedTcpTable(buf, ctypes.byref(size), False, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0)
        if ret != 0:
            return []

        num_entries = struct.unpack_from("<L", buf.raw, 0)[0]
        offset = struct.calcsize("<L")
        row_size = ctypes.sizeof(MIB_TCPROW_OWNER_PID)

        results = []
        for _ in range(num_entries):
            row = MIB_TCPROW_OWNER_PID.from_buffer_copy(buf.raw[offset:offset + row_size])
            offset += row_size
            is_listening = row.dwState == 2
            results.append({
                "proto": "TCP",
                "local_addr": _decode_ip(row.dwLocalAddr),
                "local_port": _decode_port(row.dwLocalPort),
                "remote_addr": None if is_listening else _decode_ip(row.dwRemoteAddr),
                "remote_port": None if is_listening else _decode_port(row.dwRemotePort),
                "state": TCP_STATE_MAP.get(row.dwState, "UNKNOWN"),
                "pid": int(row.dwOwningPid),
            })
        return results

    def _get_udp_connections(self) -> List[Dict[str, any]]:
        size = wintypes.DWORD(0)
        self.iphlpapi.GetExtendedUdpTable(None, ctypes.byref(size), False, AF_INET, UDP_TABLE_OWNER_PID, 0)
        if size.value == 0:
            return []

        buf = ctypes.create_string_buffer(size.value)
        ret = self.iphlpapi.GetExtendedUdpTable(buf, ctypes.byref(size), False, AF_INET, UDP_TABLE_OWNER_PID, 0)
        if ret != 0:
            return []

        num_entries = struct.unpack_from("<L", buf.raw, 0)[0]
        offset = struct.calcsize("<L")
        row_size = ctypes.sizeof(MIB_UDPROW_OWNER_PID)

        results = []
        for _ in range(num_entries):
            row = MIB_UDPROW_OWNER_PID.from_buffer_copy(buf.raw[offset:offset + row_size])
            offset += row_size
            results.append({
                "proto": "UDP",
                "local_addr": _decode_ip(row.dwLocalAddr),
                "local_port": _decode_port(row.dwLocalPort),
                "remote_addr": None,
                "remote_port": None,
                "state": "LISTENING",
                "pid": int(row.dwOwningPid),
            })
        return results

    def _query_native_cli(self) -> List[Dict[str, any]]:
        import subprocess
        for exe_path in ["proxessor.exe", "rust/target/release/proxessor.exe", "rust/target/debug/proxessor.exe"]:
            if os.path.exists(exe_path):
                try:
                    out = subprocess.check_output([exe_path, "connections"], text=True, stderr=subprocess.DEVNULL)
                    results = []
                    for line in out.strip().splitlines():
                        parts = line.split()
                        if len(parts) >= 5 and parts[0] in ("TCP", "UDP") and parts[-1].isdigit():
                            local = parts[1].split(":")
                            remote = parts[2].split(":")
                            results.append({
                                "proto": parts[0],
                                "local_addr": local[0] if len(local) > 0 else "0.0.0.0",
                                "local_port": int(local[1]) if len(local) > 1 and local[1].isdigit() else 0,
                                "remote_addr": remote[0] if len(remote) > 0 and remote[0] != "*" else None,
                                "remote_port": int(remote[1]) if len(remote) > 1 and remote[1].isdigit() else None,
                                "state": parts[3],
                                "pid": int(parts[-1]),
                            })
                    return results
                except Exception:
                    pass
        return []
