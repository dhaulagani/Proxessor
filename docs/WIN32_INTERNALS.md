# Windows Win32 & NT Kernel Internals Reference

Proxessor interacts with native Windows operating system APIs to enforce prioritization, core assignment, memory trimming, and power throttling. This document provides the low-level reference for developers and auditors.

---

## 1. Process CPU Priority Classes
Windows provides 6 priority classes via `SetPriorityClass` and `GetPriorityClass` (`kernel32.dll`):

| Priority Class Constant | Hex Value | Base Thread Priority |
|:---|:---:|:---:|
| `IDLE_PRIORITY_CLASS` | `0x00000040` | 4 |
| `BELOW_NORMAL_PRIORITY_CLASS` | `0x00004000` | 6 |
| `NORMAL_PRIORITY_CLASS` | `0x00000020` | 8 |
| `ABOVE_NORMAL_PRIORITY_CLASS` | `0x00008000` | 10 |
| `HIGH_PRIORITY_CLASS` | `0x00000080` | 13 |
| `REALTIME_PRIORITY_CLASS` | `0x00000100` | 24 |

> [!WARNING]
> Setting a non-kernel process to `REALTIME_PRIORITY_CLASS` can starve mouse input, keyboard interrupts, and disk flushing. Proxessor automatically safeguards against accidental real-time escalations.

---

## 2. Process I/O Priority (NT Kernel Undocumented API)
Windows I/O request packets (IRPs) can be prioritized using `NtSetInformationProcess` (`ntdll.dll`):

### C Signature:
```c
typedef enum _PROCESS_INFORMATION_CLASS {
    ProcessIoPriority = 33
} PROCESS_INFORMATION_CLASS;

NTSTATUS NTAPI NtSetInformationProcess(
    HANDLE ProcessHandle,
    PROCESS_INFORMATION_CLASS ProcessInformationClass,
    PVOID ProcessInformation,
    ULONG ProcessInformationLength
);
```

### I/O Priority Values:
- `0`: **Very Low** (Background, zero interference with active reads)
- `1`: **Low**
- `2`: **Normal** (Default for desktop applications)
- `3`: **High** (Prioritized file operations)

---

## 3. Process Memory Priority (Working Set & Page Fault Handling)
Windows 8 / 10 / 11 introduce fine-grained process memory page replacement priority via `SetProcessInformation` (`kernel32.dll`):

```c
typedef struct _MEMORY_PRIORITY_INFORMATION {
    ULONG MemoryPriority; // Values 0 (Lowest) to 5 (Highest / Normal)
} MEMORY_PRIORITY_INFORMATION;

BOOL SetProcessInformation(
    HANDLE hProcess,
    PROCESS_INFORMATION_CLASS ProcessInformationClass, // ProcessMemoryPriority = 4
    LPVOID ProcessInformation,
    DWORD ProcessInformationSize
);
```

---

## 4. Windows Power Throttling & EcoQoS
Starting with Windows 10 Build 16299 and Windows 11:
```c
typedef struct _PROCESS_POWER_THROTTLING_STATE {
    ULONG Version;
    ULONG ControlMask;
    ULONG StateMask;
} PROCESS_POWER_THROTTLING_STATE;

#define PROCESS_POWER_THROTTLING_CURRENT_VERSION 1
#define PROCESS_POWER_THROTTLING_EXECUTION_SPEED 0x1
```

When `ControlMask` and `StateMask` are set to `0x1`, the process enters EcoQoS mode:
- CPU frequency scaling throttles down execution.
- Windows scheduler routes threads to energy-efficient cores (E-Cores).
- Thermal and battery efficiency improves significantly.

---

## 5. Working Set Trimming (`EmptyWorkingSet`)
To release unneeded allocated physical pages back to the operating system's standby list:
```c
BOOL EmptyWorkingSet(
    HANDLE hProcess
);
```
Alternatively:
```c
SetProcessWorkingSetSize(hProcess, (SIZE_T)-1, (SIZE_T)-1);
```

---

## 6. Dynamic Power Scheme Switching
Power schemes can be switched dynamically using `powrprof.dll`:
```c
DWORD PowerSetActiveScheme(
    HKEY UserRootPowerKey,
    const GUID *SchemeGuid
);
```
Common Standard GUIDs:
- **Balanced**: `381b4222-f694-41f0-9685-ff5bb260df2e`
- **High Performance**: `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`
- **Power Saver**: `a1841308-3541-4fab-bc81-f71556f20b4a`
- **Ultimate Performance**: `e9a42b02-d5df-448d-aa00-03f14749eb61`
