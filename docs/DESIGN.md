# Proxessor Design System Specification (DESIGN.md)

## 1. Visual Atmosphere & Philosophy (Anti-AI-Slop & Native Windows)
- **Design Philosophy:** Windows 11 Native Fluent / Classic Win32 Task Manager & Process Lasso Parity.
- **Strict Anti-Slop Policy:**
  - Zero rounded floating pill cards or oversized web mockups.
  - Zero bloated neon gradients or Figma crypto dashboard templates.
  - 100% Native Windows typography (`Segoe UI` 9pt for UI labels/lists, `Consolas` 9pt for numeric telemetry).
  - High information density (21px row height) allowing 30+ processes to be viewed simultaneously.
  - Real Windows Native Top Menu Bar (`File`, `Edit`, `View`, `Options`, `Tools`, `Help`) with standard Windows accelerators.
  - Windows 11 Immersive Dark Mode title bar integration (`DwmSetWindowAttribute`).

---

## 2. Color Palette & Functional Calibration (Windows 11 Dark Mode)

| Color Name | Hex Code | Functional Role |
|:---|:---:|:---|
| **Window Background** | `#1f1f1f` | Windows 11 standard dark canvas |
| **Control / Surface** | `#252526` | Panel containers, tabs, comboboxes |
| **Header & Toolbars** | `#2d2d2d` | Win32 ListView headers, toolbars |
| **Border Subtle** | `#333333` | 1px clean separator lines |
| **Border Control** | `#3e3e42` | Input box & button borders |
| **Text Primary** | `#f3f3f3` | High-contrast process names, primary labels |
| **Text Secondary / Muted**| `#8e8e8e` | Status bar, column labels, timestamps |
| **Windows Accent Blue** | `#0078d4` | Active power scheme, primary action highlights |
| **List Selection** | `#094771` | Windows Task Manager blue selection bar |
| **Oscilloscope Background**| `#121a14` | Very dark phosphor-green tinted background |
| **Oscilloscope Grid** | `#1b2b1f` | 25%/50%/75% subtle gridlines |
| **CPU Telemetry** | `#00e676` | Task manager phosphor green (1px crisp line) |
| **RAM Telemetry** | `#00b0ff` | Windows sky blue (1px crisp line) |
| **Restraint Telemetry** | `#ff9100` | Amber restraint activity indicator |

---

## 3. Typographic Architecture
- **Interface Font:** `Segoe UI` (9pt regular for body/treeview, 9pt bold for headers/badges, 8pt for status bar).
- **Telemetry & Numerical Monospace:** `Consolas` (9pt for PIDs, CPU %, RAM MB, Thread counts, IP sockets, and logs).

---

## 4. Layout Architecture
1. **Windows Native Menu Bar:**
   - `File`: Run New Task, Exit
   - `View`: Refresh Now (F5), Update Speed (0.5s, 1s, 2s, Paused), Show Active Only, Show Restrained Only
   - `Options`: ProBalance Enabled, Always on Top, Close to System Tray
   - `Tools`: SmartTrim System RAM, Task Manager, Resource Monitor, Windows Services
   - `Help`: About Proxessor
2. **Compact Toolbar Strip (32px):**
   - Filter entry + clear button (`×`)
   - `[ ] Active Only` & `[ ] Restrained Only` checkbuttons
   - `[ Flush RAM (SmartTrim) ]` button
   - `Power Plan: [ High Performance ▼ ]` combobox
   - `[ End Process (Del) ]` button
   - Right-aligned summary: `CPU: X.X% | RAM: X.X% | ProBalance: Active`
3. **Oscilloscope History Strip (42px):**
   - Compact Task Manager performance graph strip showing real-time 60-second scrolling CPU load, RAM load, and ProBalance restraint lines.
4. **Native Notebook Tabs:**
   - `Processes`: Dense 8-column ListView with sorting and right-click Win32 context menu.
   - `CPU Topology`: Heterogeneous architecture inspector (P-Cores vs E-Cores real-time meters).
   - `Network Sockets`: TCP/UDP endpoints mapped to process PIDs with terminate action.
   - `File Lock Hunter`: Restart Manager unlocked files inspector with browse dialogs.
   - `Active Rules & Settings`: Persistent rules editor & live ProBalance threshold sliders.
   - `Activity Journal`: Real-time audit log stream.
5. **3-Section Native Status Bar (24px):**
   - Section 1: Process count and selected PID.
   - Section 2: Real-time CPU and RAM utilization.
   - Section 3: ProBalance restraint status and engine indicator.
