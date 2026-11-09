use proxessor::config::ProBalanceConfig;
use proxessor::probalance::{ProBalanceAction, ProBalanceEngine, ProcessMetric};

fn sample_config() -> ProBalanceConfig {
    ProBalanceConfig {
        enabled: true,
        cpu_trigger_threshold_percent: 60.0,
        per_process_cpu_trigger_percent: 25.0,
        target_restraint_priority: "BELOW_NORMAL".to_string(),
        restraint_duration_seconds: 5,
        recovery_threshold_percent: 40.0,
        ignore_foreground_process: true,
        excluded_processes: vec!["dwm.exe".to_string(), "audiodg.exe".to_string(), "System".to_string()],
    }
}

#[test]
fn test_probalance_restrains_heavy_process() {
    let mut engine = ProBalanceEngine::new(sample_config());
    let processes = vec![
        ProcessMetric {
            pid: 101,
            name: "heavy_task.exe".to_string(),
            cpu_percent: 35.0,
            current_priority: "NORMAL".to_string(),
        },
        ProcessMetric {
            pid: 102,
            name: "light_task.exe".to_string(),
            cpu_percent: 5.0,
            current_priority: "NORMAL".to_string(),
        },
    ];

    // High system CPU (75%)
    let actions = engine.evaluate(75.0, &processes, None);
    assert_eq!(actions.len(), 1);

    if let ProBalanceAction::Restrain { pid, target_priority, .. } = &actions[0] {
        assert_eq!(*pid, 101);
        assert_eq!(target_priority, "BELOW_NORMAL");
    } else {
        panic!("Expected Restrain action");
    }

    assert!(engine.restrained_processes.contains_key(&101));
}

#[test]
fn test_probalance_respects_exclusions() {
    let mut engine = ProBalanceEngine::new(sample_config());
    let processes = vec![
        ProcessMetric {
            pid: 201,
            name: "dwm.exe".to_string(),
            cpu_percent: 45.0,
            current_priority: "HIGH".to_string(),
        },
    ];

    let actions = engine.evaluate(85.0, &processes, None);
    assert_eq!(actions.len(), 0);
    assert!(!engine.restrained_processes.contains_key(&201));
}

#[test]
fn test_probalance_respects_foreground_immunity() {
    let mut engine = ProBalanceEngine::new(sample_config());
    let processes = vec![
        ProcessMetric {
            pid: 301,
            name: "game.exe".to_string(),
            cpu_percent: 50.0,
            current_priority: "HIGH".to_string(),
        },
    ];

    // PID 301 is foreground
    let actions = engine.evaluate(80.0, &processes, Some(301));
    assert_eq!(actions.len(), 0);
    assert!(!engine.restrained_processes.contains_key(&301));
}
