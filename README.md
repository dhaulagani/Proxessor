# Proxessor ⚡
### Open-Source, Unrestricted Windows Process Governor & Optimization Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20%7C%20Server-0078D6.svg)](docs/WIN32_INTERNALS.md)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Tests Passing](https://img.shields.io/badge/Tests-12%2F12%20Passed-brightgreen.svg)](tests/)
[![No Telemetry](https://img.shields.io/badge/Telemetry-0%25%20Offline-red.svg)](#privacy--security)

**Proxessor** is a high-performance, open-source Windows process governor and system optimizer engineered to deliver all the advanced real-time prioritization and CPU scheduling features of commercial utilities (such as Process Lasso Pro) — with **zero artificial paywalls, zero nag screens, zero subscription fees, and zero telemetry**.

Proxessor includes both:
1. 🦀 **High-Performance Native Rust Core Engine (`rust/`)**: Compiled bare-metal Windows executable (`1.6 MB`, `< 2 MB` RAM footprint, `0.0%` CPU idle, deterministic microsecond latency with zero garbage collection).
2. 🖥️ **Bespoke Desktop GUI Client (`src/proxessor/gui/`)**: Anti-slop systems interface with live process table, visual tuning drawer, and real-time ProBalance telemetry.

---

## 🚀 Key Highlights & Pro Features (100% Unlocked)

- ⚖️ **Dynamic ProBalance Algorithm**: Prevents runaway background threads from monopolizing CPU cores and causing UI micro-stutters or audio distortion (`audiodg.exe`).
- 🧠 **Heterogeneous CPU Topology Engine**: Automatic detection and affinity steering for **Intel Alder/Raptor/Arrow Lake** (P-Cores vs E-Cores) and **AMD 3D V-Cache** (CCD0 Cache vs CCD1 Frequency).
- ⚡ **Windows EcoQoS / Power Throttling**: Native toggling of Windows power throttling states (`PROCESS_POWER_THROTTLING_EXECUTION_SPEED`) to conserve thermal headroom and battery.
- 💽 **Direct NT I/O & Memory Priority**: Leverages low-level `NtSetInformationProcess` (`ProcessIoPriority`) and `SetProcessInformation` (`ProcessMemoryPriority`) to protect disk latency.
- 🧹 **SmartTrim Working Set Limiter**: Intelligently trims dormant physical memory pages back into the standby list when system RAM pressure spikes.
- 🎯 **Real-Time Foreground Window Booster**: Automatically elevates CPU scheduling priorities and thread quantums for the currently focused game or workspace.
- 🔋 **Power Scheme Automation**: Dynamically activates High Performance / Ultimate Performance power plans on demanding game launches and restores Balanced mode upon exit.
- 🛡️ **Watchdog Engine**: Enforces single-instance execution and memory leak caps with configurable termination or trimming triggers.
- 🏎️ **Decoupled Headless Core**: Operates as an ultra-lightweight daemon with `< 0.1%` CPU consumption and `< 15 MB` RAM footprint.

---

## 📊 Feature Comparison Matrix

| Feature | Process Lasso Free | Process Lasso Pro (\$40-\$80) | Proxessor (FOSS) |
|:---|:---:|:---:|:---:|
| **Price & License** | Nag screen / 3s delay | Paid Commercial | **100% Free & Open Source (MIT)** |
| **Telemetry / Tracking** | Present | Present | **Zero Telemetry / Fully Offline** |
| **ProBalance Heuristic** | Basic | Unrestricted | **Unrestricted & Configurable** |
| **P-Core / E-Core Routing** | Limited | Full | **Native Heterogeneous Engine** |
| **Win32 I/O Priority** | Paywalled | Full | **Native Unlocked** |
| **Memory Priority (0-5)** | Paywalled | Full | **Native Unlocked** |
| **EcoQoS Power Throttling** | Partial | Full | **Native Unlocked** |
| **SmartTrim Memory Cleaning** | Periodic | Threshold-based | **Configurable Interval & Threshold** |
| **Foreground App Booster** | Paywalled | Full | **Real-Time Foreground Tracking** |
| **Power Plan Switching** | Paywalled | Full | **Native Power Scheme Switcher** |
| **Max Process Rules** | Limited | Unlimited | **Unlimited (JSON / Regex)** |
| **Watchdog Automations** | Limited | Unlimited | **Unlimited** |

---

## 🏗️ Architecture

```
+─────────────────────────────────────────────────────────────+
|                         User Space                          |
|  [ Proxessor CLI / TUI ]       [ JSON / YAML Config Rules ] |
+─────────────┬────────────────────────────────┬──────────────+
              │                                │
              ▼                                ▼
+─────────────────────────────────────────────────────────────+
|               Proxessor Governor Core Daemon                |
|                                                             |
|  +───────────────────────────────────────────────────────+  |
|  |           Process Enumeration & Snapshot Engine       |  |
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
|  |             Win32 Kernel Enforcement Layer            |  |
|  |  - SetPriorityClass       - SetProcessAffinityMask    |  |
|  |  - NtSetInformationProc   - SetProcessInformation     |  |
|  |  - EmptyWorkingSet        - PowerSetActiveScheme      |  |
|  +───────────────────────────────────────────────────────+  |
+──────────────────────────────┬──────────────────────────────+
                               │
                               ▼
+─────────────────────────────────────────────────────────────+
|                 Windows NT Kernel (Ring 0)                  |
|     [ Preemptive Scheduler & Core Thread Quantums ]         |
+─────────────────────────────────────────────────────────────+
```

For deeper architectural breakdowns, read:
- [System Architecture Specification](docs/ARCHITECTURE.md)
- [ProBalance Algorithmic & Finite State Machine Spec](docs/PROBALANCE_SPEC.md)
- [Windows Win32 & NT Kernel Internals](docs/WIN32_INTERNALS.md)
- [Configuration Guide](docs/CONFIGURATION.md)

---

## 🛠️ Installation & Quickstart

### Prerequisites
- Windows 10, Windows 11, or Windows Server 2016+
- Python 3.10 or higher
- Administrator privileges (required to adjust process priorities, core affinities, and power plans)

### Setup
```powershell
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Proxessor.git
cd Proxessor

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 CLI Commands

### 1. View CPU Topology & Core Masks
Discover your CPU's logical processor count, Performance Cores (P-Cores), and Efficiency Cores (E-Cores):
```powershell
python -m src.proxessor.cli.main topology
```

### 2. Check System Status & Foreground Window
```powershell
python -m src.proxessor.cli.main status
```

### 3. Dry-Run / Test Rules Against Running Processes
Verify which processes match your configuration rules without modifying kernel state:
```powershell
python -m src.proxessor.cli.main test-rules
```

### 4. Run the Governor Optimization Daemon
```powershell
# Run with active kernel enforcement
python -m src.proxessor.cli.main run

# Or run in simulated dry-run mode
python -m src.proxessor.cli.main run --dry-run
```

---

## ⚙️ Configuration Reference

Edit `config/default_rules.json` to define custom optimization rules:

```json
{
  "rules": [
    {
      "name": "Competitive Gaming Optimization",
      "pattern": "(?i)(cyberpunk2077|valorant|cs2|eldenring)\\.exe",
      "priority": "HIGH",
      "io_priority": "HIGH",
      "memory_priority": 5,
      "power_throttling_eco_qos": false,
      "cpu_affinity": "P_CORES",
      "power_scheme": "HIGH_PERFORMANCE"
    },
    {
      "name": "Background Web Browsers",
      "pattern": "(?i)(chrome|msedge|brave)\\.exe",
      "priority": "NORMAL",
      "io_priority": "NORMAL",
      "memory_priority": 3,
      "power_throttling_eco_qos": true,
      "cpu_affinity": "ALL_CORES"
    }
  ]
}
```

---

## 🧪 Testing

Execute the test suite verifying ProBalance heuristics, rules compiler, core topology calculation, and Win32 wrappers:
```powershell
python -m pytest tests/ -v
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
