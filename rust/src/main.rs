use std::env;
use std::thread::sleep;
use std::time::Duration;

use proxessor::config::AppConfig;
use proxessor::governor::GovernorEngine;
use proxessor::topology::CPUTopology;
use proxessor::win32::Win32Kernel;

fn print_banner() {
    println!("==================================================");
    println!("     PROXESSOR CORE GOVERNOR (NATIVE RUST)        ");
    println!("==================================================");
}

fn cmd_topology() {
    print_banner();
    let topo = CPUTopology::detect();
    println!("Total Logical Cores : {}", topo.total_logical_cores);
    println!("P-Cores (Perf)      : {} (Indices: {:?})", topo.p_cores.len(), topo.p_cores);
    println!("E-Cores (Eff)       : {} (Indices: {:?})", topo.e_cores.len(), topo.e_cores);
    println!("All Cores Mask      : {:#x}", topo.get_all_cores_mask());
    println!("P-Cores Mask        : {:#x}", topo.get_p_cores_mask());
    println!("E-Cores Mask        : {:#x}", topo.get_e_cores_mask());
    println!("==================================================");
}

fn cmd_status() {
    print_banner();
    let fg = Win32Kernel::get_foreground_pid();
    let ram = Win32Kernel::get_system_ram_percent();
    println!("Foreground PID         : {}", fg.map(|p| p.to_string()).unwrap_or_else(|| "None / Desktop".to_string()));
    println!("System RAM Utilization : {:.1}%", ram);
    println!("==================================================");
}

fn cmd_trim() {
    print_banner();
    println!("Flushing working sets across system processes...");
    let ram_before = Win32Kernel::get_system_ram_percent();
    println!("RAM before trim: {:.1}%", ram_before);
    let (config, resolved_path) = AppConfig::discover_and_load(None);
    println!("Config used    : {}", resolved_path);
    let mut gov = GovernorEngine::new(config);
    let stats = gov.tick(false);
    let ram_after = Win32Kernel::get_system_ram_percent();
    println!("Trimmed {} monitored processes.", stats.monitored_processes);
    println!("RAM after trim: {:.1}%", ram_after);
}

fn cmd_run(custom_config: Option<&str>, dry_run: bool) {
    print_banner();
    let (config, resolved_path) = AppConfig::discover_and_load(custom_config);
    println!("Config   : {}", resolved_path);
    println!("Mode     : {}", if dry_run { "SIMULATED DRY-RUN" } else { "ACTIVE RING-3 KERNEL ENFORCEMENT" });
    println!("Status   : Online (Zero-GC native loop)... Press Ctrl+C to terminate.");
    println!("==================================================");

    let poll_ms = config.engine.poll_interval_ms.max(200);
    let mut gov = GovernorEngine::new(config);

    loop {
        let stats = gov.tick(dry_run);
        print!(
            "\r[TICK] Monitored: {:<3} | RAM: {:>4.1}% | ProBalance: {:<2} | Watchdogs: {:<2} | Blocked: {:<2} | Idle: {:<5}   ",
            stats.monitored_processes, stats.ram_percent, stats.probalance_actions, stats.watchdog_actions, stats.disallowed_kills, if stats.is_idle { "YES" } else { "NO" }
        );
        use std::io::Write;
        std::io::stdout().flush().unwrap();
        sleep(Duration::from_millis(poll_ms));
    }
}

fn cmd_filelock(path: &str) {
    print_banner();
    println!("Target Path : {}", path);
    println!("Scanning for locking processes via Windows Restart Manager...");
    match proxessor::filelock::find_file_lockers(path) {
        Ok(lockers) => {
            if lockers.is_empty() {
                println!("No processes currently hold an open lock on this resource.");
            } else {
                println!("Found {} process(es) locking this path:", lockers.len());
                println!("{:<8} {:<30} {:<15} {:<15}", "PID", "APP NAME", "TYPE", "SERVICE");
                println!("{}", "-".repeat(70));
                for l in lockers {
                    println!(
                        "{:<8} {:<30} {:<15} {:<15}",
                        l.pid,
                        l.app_name,
                        l.app_type,
                        l.service_name.as_deref().unwrap_or("-")
                    );
                }
            }
        }
        Err(e) => {
            eprintln!("Error checking file lock: {}", e);
        }
    }
    println!("==================================================");
}

fn cmd_connections(filter: Option<&str>) {
    print_banner();
    println!("Enumerating active TCP and UDP sockets...");
    let conns = proxessor::connections::list_all_connections();
    println!("{:<6} {:<22} {:<22} {:<12} {:<8}", "PROTO", "LOCAL ENDPOINT", "REMOTE ENDPOINT", "STATE", "PID");
    println!("{}", "-".repeat(72));

    let mut count = 0;
    for c in conns {
        let local = format!("{}:{}", c.local_addr, c.local_port);
        let remote = match (&c.remote_addr, c.remote_port) {
            (Some(ip), Some(p)) => format!("{}:{}", ip, p),
            _ => "*:*".to_string(),
        };

        if let Some(f) = filter {
            let matches = c.protocol.to_lowercase().contains(&f.to_lowercase())
                || local.contains(f)
                || remote.contains(f)
                || c.pid.to_string() == f;
            if !matches {
                continue;
            }
        }

        println!("{:<6} {:<22} {:<22} {:<12} {:<8}", c.protocol, local, remote, c.state, c.pid);
        count += 1;
    }
    println!("==================================================");
    println!("Total sockets listed: {}", count);
}

fn print_help() {
    print_banner();
    println!("Portable Windows Process Governor & System Optimizer");
    println!("Version : {}", env!("CARGO_PKG_VERSION"));
    println!();
    println!("USAGE:");
    println!("  proxessor.exe [COMMAND] [OPTIONS]");
    println!();
    println!("COMMANDS:");
    println!("  run                Start the active background governor engine (Default)");
    println!("  status             Display current foreground PID & system RAM usage");
    println!("  trim               Flush working sets across monitored processes");
    println!("  topology           Display CPU P/E-Cores & 3D V-Cache affinity masks");
    println!("  filelock <path>    Scan which processes lock a file or folder");
    println!("  connections [f]    Enumerate active network TCP/UDP sockets (optional filter)");
    println!("  help, -h, --help   Show this help message");
    println!("  version, -v        Display version information");
    println!();
    println!("OPTIONS for 'run':");
    println!("  --config <path>    Path to custom JSON configuration file");
    println!("  --dry-run          Run in simulation mode without applying changes");
    println!("==================================================");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let first_arg = args.get(1).map(|s| s.as_str());

    match first_arg {
        None | Some("run") => {
            let dry_run = args.iter().any(|a| a == "--dry-run");
            let config_path = args
                .windows(2)
                .find(|w| w[0] == "--config")
                .map(|w| w[1].as_str());
            cmd_run(config_path, dry_run);
        }
        Some("topology") => cmd_topology(),
        Some("status") => cmd_status(),
        Some("trim") => cmd_trim(),
        Some("filelock") => {
            let path = args.get(2).map(|s| s.as_str()).unwrap_or(".");
            cmd_filelock(path);
        }
        Some("connections") => {
            let filter = args.get(2).map(|s| s.as_str());
            cmd_connections(filter);
        }
        Some("help") | Some("-h") | Some("--help") => {
            print_help();
        }
        Some("version") | Some("-v") | Some("--version") => {
            println!("Proxessor Core v{} (Windows x86_64 Portable)", env!("CARGO_PKG_VERSION"));
        }
        Some(unknown) => {
            if unknown.starts_with("--") {
                let dry_run = args.iter().any(|a| a == "--dry-run");
                let config_path = args
                    .windows(2)
                    .find(|w| w[0] == "--config")
                    .map(|w| w[1].as_str());
                cmd_run(config_path, dry_run);
            } else {
                eprintln!("Unknown command: '{}'", unknown);
                print_help();
                std::process::exit(1);
            }
        }
    }
}
