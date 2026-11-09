# Proxessor Configuration Guide

Proxessor configuration files are stored in `config/default_rules.json` (or passed via CLI `--config <path>`).

## Configuration Structure

```json
{
  "version": "1.0.0",
  "engine": {
    "poll_interval_ms": 1000,
    "foreground_boost_enabled": true,
    "smart_trim_enabled": true,
    "smart_trim_threshold_percent": 85,
    "smart_trim_interval_seconds": 300
  },
  "probalance": {
    "enabled": true,
    "cpu_trigger_threshold_percent": 65.0,
    "per_process_cpu_trigger_percent": 20.0,
    "target_restraint_priority": "BELOW_NORMAL",
    "restraint_duration_seconds": 10,
    "ignore_foreground_process": true,
    "excluded_processes": [
      "dwm.exe",
      "audiodg.exe",
      "System",
      "explorer.exe"
    ]
  },
  "rules": [
    {
      "name": "Game Mode Ultra",
      "pattern": "(?i)(game_executable)\\.exe",
      "priority": "HIGH",
      "io_priority": "HIGH",
      "memory_priority": 5,
      "power_throttling_eco_qos": false,
      "cpu_affinity": "P_CORES",
      "power_scheme": "HIGH_PERFORMANCE"
    }
  ],
  "watchdogs": [
    {
      "name": "Prevent Duplicate Launcher",
      "pattern": "(?i)(game_launcher)\\.exe",
      "max_instances": 1,
      "action": "TERMINATE_NEWEST"
    }
  ]
}
```

## Field Definitions

### `engine` Block
- `poll_interval_ms`: Frequency of the governor sampling loop in milliseconds (default: `1000`).
- `foreground_boost_enabled`: If `true`, the active focused foreground window receives elevated priority and thread responsiveness.
- `smart_trim_enabled`: If `true`, Proxessor automatically trims working sets when overall system RAM usage exceeds `smart_trim_threshold_percent`.

### `probalance` Block
- `cpu_trigger_threshold_percent`: System CPU usage percentage required before ProBalance activates (e.g. `65.0`).
- `per_process_cpu_trigger_percent`: Minimum CPU percentage consumed by a single process to qualify for restraint (e.g. `20.0`).
- `target_restraint_priority`: Priority class applied while restrained: `BELOW_NORMAL` or `IDLE`.
- `restraint_duration_seconds`: Cooldown timer before attempting to restore original priority.
- `excluded_processes`: Array of process names exempt from restraint.

### `rules` Array
- `name`: Descriptive name for logging.
- `pattern`: Regular expression or exact executable name.
- `priority`: Target CPU priority class (`IDLE`, `BELOW_NORMAL`, `NORMAL`, `ABOVE_NORMAL`, `HIGH`).
- `io_priority`: `VERY_LOW`, `LOW`, `NORMAL`, `HIGH`.
- `memory_priority`: Integer from `1` (lowest) to `5` (highest).
- `power_throttling_eco_qos`: `true` to enable Windows EcoQoS; `false` to disable throttling.
- `cpu_affinity`:
  - `"ALL_CORES"`: All logical processors.
  - `"P_CORES"`: High-performance cores only (Alder Lake, Raptor Lake, Arrow Lake).
  - `"E_CORES"`: Efficiency cores only.
  - `"0x3F"`: Explicit hex bitmask.
- `power_scheme`: Optional power plan trigger (`HIGH_PERFORMANCE`, `BALANCED`, `ULTIMATE_PERFORMANCE`).
