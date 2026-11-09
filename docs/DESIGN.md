# Proxessor Design System Specification (DESIGN.md)

## 1. Visual Atmosphere & Philosophy
- **Density:** Cockpit Dense (8/10). Engineered for real-time systems observability, low latency, and dense information layout.
- **Variance:** Offset Asymmetric (5/10). Structured telemetry header, high-density live process tree, and contextual action drawer.
- **Motion:** Restrained Spring (3/10). Purpose-driven state transitions; zero gratuitous bouncy animations.
- **Target Aesthetic:** Swiss Precision Industrial Terminal meets Modern Windows Fluent Systems Architecture. Zero AI purple glowing gradient cliches. Zero emojis in the production interface.

---

## 2. Color Palette & Functional Calibration

| Color Name | Hex Code | Functional Role |
|:---|:---:|:---|
| **Base Canvas** | `#0b0d11` | Primary background, deep low-glare dark surface |
| **Card Surface** | `#131720` | Secondary component background, table container |
| **Hover Surface** | `#1c2230` | Hovered rows, interactive button states |
| **Border Subtle** | `#242c3d` | Strict structural boundary dividers |
| **Border Active** | `#3b4760` | Focused input border, selected process row |
| **Text Primary** | `#f1f5f9` | High-contrast headers, active process names, PIDs |
| **Text Secondary** | `#94a3b8` | Metadata, thread counts, column labels |
| **Text Muted** | `#64748b` | Timestamps, inactive hints |
| **Accent Optimal** | `#10b981` | Normal status, optimal efficiency, green telemetry |
| **Accent Restrained** | `#f59e0b` | ProBalance active restraint indicator |
| **Accent Critical** | `#ef4444` | High CPU threshold warning, kill process button |

---

## 3. Typographic Architecture
- **Primary Interface Font:** `Segoe UI Variable`, `Segoe UI`, or `Geist Sans` (System sans-serif, track-tight, crisp readability).
- **Telemetry & Numerical Monospace:** `JetBrains Mono`, `Consolas`, or `Cascadia Code` (Mandatory for PIDs, CPU %, RAM MB, Hex Affinity masks, and timestamps).

---

## 4. Component Behaviors & Layout Principles
- **Header Telemetry Bar:** Live gauge readout of System CPU (0-100%), System RAM (0-100%), Monitored Processes count, ProBalance Status badge, and active Windows Power Scheme.
- **Search & Quick-Filter:** Track-typed search input for immediate regex/substring filtering.
- **Process Data Grid:** Dense sortable columns (PID, Name, CPU %, RAM MB, Priority, I/O Priority, Affinity, EcoQoS). Selected row highlighted in `#1c2230` with `#10b981` leading border.
- **Context Action Drawer:** Immediate single-click adjustments:
  - CPU Priority Selector (Realtime, High, Above Normal, Normal, Below Normal, Idle)
  - Core Affinity Selector (All Cores, P-Cores Only, E-Cores Only)
  - I/O Priority Selector (High, Normal, Low, Very Low)
  - Memory Priority Selector (5 to 1)
  - EcoQoS / Power Throttling Toggle
  - Working Set Trim (Flush RAM)
  - Terminate Process
- **ProBalance Live Telemetry Stream:** Monospace terminal log displaying microsecond-accurate kernel interventions.
