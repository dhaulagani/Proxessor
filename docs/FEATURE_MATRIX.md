# Feature Matrix: Proxessor vs. Process Lasso

| Feature Category | Feature Description | Process Lasso Free | Process Lasso Pro | Proxessor (FOSS) |
|:---|:---|:---:|:---:|:---:|
| **Licensing** | Cost & Activation | Free (Nag screens, 3-second delay) | Paid License (\$40 - \$80) | **100% Free & Open Source (MIT)** |
| **Telemetry / Tracking** | Background phone-home checks | Present | Present | **Zero Telemetry / Offline Native** |
| **ProBalance** | Dynamic Priority Restraint under CPU load | Basic | Unrestricted | **Fully Unrestricted (Customizable)** |
| **Dynamic Priority Rules** | Persistent priority overrides | Limited | Unlimited | **Unlimited (JSON / Regex Engine)** |
| **CPU Affinity Rules** | Pinning processes to specific cores | Limited | Unlimited | **Unlimited & Heterogeneous Aware** |
| **Intel P-Core / E-Core** | Heterogeneous Alder/Raptor/Arrow Lake pinning | Limited | Full | **Native P-Core / E-Core Engine** |
| **AMD 3D V-Cache** | CCD0 (V-Cache) vs CCD1 (Freq) pinning | Limited | Full | **Native Dual-CCD NUMA Engine** |
| **I/O Priority** | Win32 `NtSetInformationProcess` I/O priority | Locked behind Pro | Full | **Native Unlocked** |
| **Memory Priority** | Page replacement priority (0-5) | Locked behind Pro | Full | **Native Unlocked** |
| **EcoQoS / Power Throttling** | Windows Power Throttling API integration | Partial | Full | **Native Unlocked** |
| **SmartTrim / Working Set** | RAM working set cache trimming | Periodic | Threshold-based | **Threshold + Interval Engine** |
| **Foreground Booster** | Prioritizing focused application window | Locked behind Pro | Full | **Real-Time Dynamic Booster** |
| **Power Plan Automation** | Switch power scheme on game/app launch | Locked behind Pro | Full | **Native Power Scheme Switcher** |
| **Instance Watchdog** | Disallow multiple instances / kill hogs | Locked behind Pro | Full | **Configurable Watchdog Daemon** |
| **Core Architecture** | Decoupled Background Governor Daemon | Yes | Yes | **Headless Daemon + CLI / API** |
| **Auditability & Safety** | Open Source Codebase | Closed Source | Closed Source | **100% Auditable Python/Win32** |
