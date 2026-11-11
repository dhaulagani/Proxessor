use proxessor::config::{AppConfig, EngineConfig, ProBalanceConfig, ProcessRule};
use proxessor::governor::GovernorEngine;

#[test]
fn test_rust_foreground_boost_state() {
    let config = AppConfig {
        engine: EngineConfig {
            poll_interval_ms: 1000,
            foreground_boost_enabled: true,
            foreground_boost_priority: "ABOVE_NORMAL".to_string(),
            idle_saver_enabled: false,
            idle_saver_threshold_seconds: 300,
            smart_trim_enabled: false,
            smart_trim_threshold_percent: 85.0,
            smart_trim_interval_seconds: 300,
        },
        probalance: ProBalanceConfig {
            enabled: true,
            cpu_trigger_threshold_percent: 65.0,
            per_process_cpu_trigger_percent: 20.0,
            target_restraint_priority: "BELOW_NORMAL".to_string(),
            restraint_duration_seconds: 10,
            recovery_threshold_percent: 50.0,
            ignore_foreground_process: true,
            excluded_processes: vec!["dwm.exe".to_string()],
        },
        rules: vec![ProcessRule {
            name: "Game Boost".to_string(),
            pattern: "(?i)game\\.exe".to_string(),
            priority: Some("HIGH".to_string()),
            io_priority: None,
            memory_priority: None,
            power_throttling_eco_qos: None,
            cpu_affinity: None,
            power_scheme: Some("HIGH_PERFORMANCE".to_string()),
        }],
        watchdogs: vec![],
        disallowed_processes: vec!["unwanted_miner.exe".to_string()],
    };

    let mut gov = GovernorEngine::new(config);
    assert!(gov.config.engine.foreground_boost_enabled);
    assert_eq!(gov.config.engine.foreground_boost_priority, "ABOVE_NORMAL");
    assert!(gov.boosted_fg_pid.is_none());
    assert!(gov.active_power_scheme_target.is_none());

    // Execute dry-run tick
    let stats = gov.tick(true);
    assert!(stats.ram_percent >= 0.0);
}

#[test]
fn test_rust_disallowed_processes_enforcement() {
    let config = AppConfig {
        engine: EngineConfig {
            poll_interval_ms: 1000,
            foreground_boost_enabled: false,
            foreground_boost_priority: "ABOVE_NORMAL".to_string(),
            idle_saver_enabled: true,
            idle_saver_threshold_seconds: 300,
            smart_trim_enabled: false,
            smart_trim_threshold_percent: 85.0,
            smart_trim_interval_seconds: 300,
        },
        probalance: ProBalanceConfig {
            enabled: false,
            cpu_trigger_threshold_percent: 65.0,
            per_process_cpu_trigger_percent: 20.0,
            target_restraint_priority: "BELOW_NORMAL".to_string(),
            restraint_duration_seconds: 10,
            recovery_threshold_percent: 50.0,
            ignore_foreground_process: true,
            excluded_processes: vec![],
        },
        rules: vec![],
        watchdogs: vec![],
        disallowed_processes: vec!["banned_malware.exe".to_string()],
    };

    let gov = GovernorEngine::new(config);
    assert_eq!(gov.disallowed_patterns.len(), 1);
    assert!(gov.disallowed_patterns[0].is_match("banned_malware.exe"));
    assert!(gov.disallowed_patterns[0].is_match("BANNED_MALWARE.EXE"));
    assert!(!gov.disallowed_patterns[0].is_match("safe_app.exe"));
}
