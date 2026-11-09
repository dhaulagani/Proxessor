# Proxessor System Architecture

## 1. Overview & Architectural Philosophy

**Proxessor** is a high-performance, open-source Windows process governor and thread optimization daemon. It is engineered to deliver 100% of the advanced dynamic optimization features found in commercial utilities like Process Lasso Pro, with zero artificial restrictions, zero licensing paywalls, and zero telemetry.

### Core Architectural Axioms
1. **Decoupled Governor Core**: Optimization runs as a headless, ultra-low-overhead daemon (`Governor Engine`). The user interface (CLI, TUI, or future Web/GUI) attaches via IPC or operates independently. The core daemon consumes `< 0.1%` CPU and `< 15 MB` RAM.
2. **Deterministic Win32 NT Kernel Calls**: Direct integration with Windows kernel APIs (`ntdll.dll`, `kernel32.dll`, `powrprof.dll`, `psapi.dll`) to avoid slow WMI polling overhead.
3. **Multi-Queue Scheduling Protection**: Immediate intervention when thread quantum contention threatens audio rendering (`audiodg.exe`), desktop composition (`dwm.exe`), or user input responsiveness.

---

## 2. High-Level System Architecture Diagram

```
+─────────────────────────────────────────────────────────────+
|                       User Space                            |
|  [ Proxessor CLI / TUI ]       [ JSON / YAML Config Rules ] |
+─────────────┬────────────────────────────────┬──────────────+
              │                                │
              ▼                                ▼
+─────────────────────────────────────────────────────────────+
|               Proxessor Governor Core Daemon                |
|                                                             |
|  +───────────────────────────────────────────────────────+  |
|  |           Process Enumeration & Snapshot Engine       |  |
|  |   (Toolhelp32 / Psapi / GetProcessTimes Differential) |  |
|  +───────────────────────────┬───────────────────────────+  |
|                              │                              |
|         ┌────────────────────┼────────────────────┐         |
|         ▼                    ▼                    ▼         |
|  +─────────────+     +─────────────+     +─────────────+    |
|  |  ProBalance |     |  Foreground |     |   Topology  |    |
|  |  Heuristic  |     |   Booster   |     |   Pinning   |    |
|  +──────┬──────+     +──────┬──────+     +──────┬──────+    |
|         │                   │                   │           |
|         └───────────────────┼───────────────────┘           |
|                             ▼                               |
|  +───────────────────────────────────────────────────────+  |
|  |              Rules & Watchdog Arbiter                 |  |
|  +───────────────────────────┬───────────────────────────+  |
|                              │                              |
|  +───────────────────────────▼───────────────────────────+  |
|  |             Win32 Kernel Enforcement Layer            |  |
|  |  - SetPriorityClass       - SetProcessAffinityMask    |  |
|  |  - NtSetInformationProc   - SetProcessInformation     |  |
|  |    (ProcessIoPriority)      (PowerThrottling / EcoQoS)|  |
|  |  - EmptyWorkingSet        - PowerSetActiveScheme      |  |
|  +───────────────────────────────────────────────────────+  |
+──────────────────────────────┬──────────────────────────────+
                               │
                               ▼
+─────────────────────────────────────────────────────────────+
|                 Windows NT Kernel (Ring 0)                  |
|    [ Scheduler / Thread Quantums / NUMA & Hetero Core ]     |
+─────────────────────────────────────────────────────────────+
```

---

## 3. Subsystem Breakdown

### 3.1. Process Enumeration & Snapshotting
- Periodic sampling loop (default: 1000ms).
- Collects PID, executable name, CPU kernel/user times, thread count, working set size, current priority class, and I/O rates.
- Computes true differential CPU utilization per process over the sampling delta:
  $$\text{CPU}\% = \frac{\Delta\text{KernelTime} + \Delta\text{UserTime}}{\Delta\text{ElapsedTime} \times \text{CoreCount}} \times 100$$

### 3.2. ProBalance (Dynamic Priority Restraint)
- Continually monitors aggregate system load and individual process loads.
- When total CPU exceeds trigger threshold (e.g., 65%) and a background process consumes more than per-process threshold (e.g., 20%), the ProBalance engine dynamically restrains its priority class (e.g. from `NORMAL` to `BELOW_NORMAL`).
- Once CPU contention resolves and the decay duration expires, the process priority is safely restored to its base configuration.

### 3.3. Heterogeneous CPU Topology (P-Cores vs E-Cores / 3D V-Cache)
- Inspects physical core topology using `GetLogicalProcessorInformationEx` (`RelationProcessorCore`).
- Detects Core Efficiency Classes:
  - **Class 0**: Efficient Cores (E-Cores).
  - **Class 1+**: Performance Cores (P-Cores).
- Maps NUMA nodes and cache topologies (e.g. AMD Ryzen 7950X3D / 9950X3D CCD0 with 3D V-Cache vs CCD1 high-frequency).
- Allows explicit or rule-based pinning of gaming processes to P-Cores/V-Cache, and background tasks to E-Cores.

### 3.4. Win32 NT Kernel Subsystems
- **CPU Priority**: Configured via `SetPriorityClass`.
- **I/O Priority**: Configured via `NtSetInformationProcess` using `ProcessIoPriority` (Class 0: Very Low, Class 1: Low, Class 2: Normal, Class 3: High).
- **Memory Priority**: Configured via `SetProcessInformation` (`ProcessMemoryPriority`, 0 to 5).
- **Power Throttling / EcoQoS**: Configured via `PROCESS_POWER_THROTTLING_STATE` with `PROCESS_POWER_THROTTLING_EXECUTION_SPEED`.
- **Working Set Management**: `EmptyWorkingSet` frees unreferenced physical memory pages to standby lists.

---

## 4. Resilience and Safety
- **System Critical Whitelist**: Kernel and critical subsystems (`System`, `csrss.exe`, `dwm.exe`, `lsass.exe`, `audiodg.exe`) are hard-excluded from throttling or termination.
- **Graceful Failure**: If a process terminates or denies access (`ERROR_ACCESS_DENIED`), the governor logs the incident without throwing unhandled exceptions.
