import argparse
import sys
import os
import json
import time

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.proxessor.core.governor import GovernorEngine
from src.proxessor.core.cpu_topology import CPUTopology
from src.proxessor.rules.manager import RuleManager
from src.proxessor.core.win32_api import Win32ProcessAPI

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../../config/default_rules.json")

def cmd_topology(args):
    """Displays CPU topology including P-cores, E-cores, and calculated bitmasks."""
    topo = CPUTopology()
    summary = topo.get_summary()
    print("==================================================")
    print("              PROXESSOR CPU TOPOLOGY              ")
    print("==================================================")
    print(f"Total Logical Cores : {summary['total_logical_cores']}")
    print(f"P-Cores (Perf)      : {summary['p_core_count']} cores (Indices: {summary['p_cores']})")
    print(f"E-Cores (Eff)       : {summary['e_core_count']} cores (Indices: {summary['e_cores']})")
    print(f"All Cores Mask      : {summary['all_cores_mask_hex']}")
    print(f"P-Cores Mask        : {summary['p_cores_mask_hex']}")
    print(f"E-Cores Mask        : {summary['e_cores_mask_hex']}")
    print("==================================================")

def cmd_status(args):
    """Shows current system state and foreground process."""
    win32 = Win32ProcessAPI()
    fg_pid = win32.get_foreground_process_id()
    ram_usage = win32.get_system_ram_percent()
    print("==================================================")
    print("               PROXESSOR SYSTEM STATUS            ")
    print("==================================================")
    print(f"Foreground Process PID : {fg_pid if fg_pid else 'None / Desktop'}")
    print(f"System RAM Utilization : {ram_usage:.1f}%")
    print("==================================================")

def cmd_test_rules(args):
    """Tests compiled rules against currently running processes."""
    cfg_path = args.config or DEFAULT_CONFIG_PATH
    rm = RuleManager(cfg_path)
    print(f"Loaded {len(rm.rules)} rule(s) and {len(rm.watchdogs)} watchdog(s) from {cfg_path}\n")

    import psutil
    matches = 0
    for p in psutil.process_iter(['pid', 'name']):
        try:
            name = p.info['name']
            if not name:
                continue
            rule = rm.match_rule(name)
            if rule:
                matches += 1
                print(f"[MATCH] PID {p.info['pid']:<6} | {name:<25} -> Rule: '{rule.name}' (Priority: {rule.priority}, Affinity: {rule.cpu_affinity})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    print(f"\nTotal Matching Processes: {matches}")

def cmd_run(args):
    """Launches the persistent Governor optimization daemon."""
    cfg_path = args.config or DEFAULT_CONFIG_PATH
    dry_run = args.dry_run

    print("==================================================")
    print("   PROXESSOR - Open Source Process Governor       ")
    print("==================================================")
    print(f"Config   : {cfg_path}")
    print(f"Mode     : {'DRY RUN (Simulated)' if dry_run else 'ACTIVE KERNEL ENFORCEMENT'}")
    print("Status   : Running... Press Ctrl+C to stop.")
    print("==================================================")

    gov = GovernorEngine(cfg_path, dry_run=dry_run)
    poll_sec = max(0.5, gov.rule_manager.engine_config.poll_interval_ms / 1000.0)

    try:
        while True:
            stats = gov.tick()
            sys.stdout.write(
                f"\r[TICK] Monitored: {stats['monitored_processes']} | Sys CPU: {stats['system_cpu']:4.1f}% | Restraints: {stats['probalance_actions']} | Watchdogs: {stats['watchdog_actions']}   "
            )
            sys.stdout.flush()
            time.sleep(poll_sec)
    except KeyboardInterrupt:
        print("\n[PROXESSOR] Daemon terminated cleanly by user.")

def main():
    parser = argparse.ArgumentParser(description="Proxessor: Open-source Windows Process Governor")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Start the background governor daemon")
    run_parser.add_argument("--config", type=str, default=None, help="Path to custom rules JSON config")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate actions without altering system state")
    run_parser.set_defaults(func=cmd_run)

    # Topology command
    topo_parser = subparsers.add_parser("topology", help="Display CPU architecture & core masks")
    topo_parser.set_defaults(func=cmd_topology)

    # Status command
    status_parser = subparsers.add_parser("status", help="Display active foreground & memory metrics")
    status_parser.set_defaults(func=cmd_status)

    # Test rules command
    test_parser = subparsers.add_parser("test-rules", help="Test rules against running processes")
    test_parser.add_argument("--config", type=str, default=None, help="Path to custom rules JSON config")
    test_parser.set_defaults(func=cmd_test_rules)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)

if __name__ == "__main__":
    main()
