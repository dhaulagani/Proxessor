use proxessor::config::AppConfig;

#[test]
fn test_embedded_default_config_validity() {
    let cfg = AppConfig::load_embedded();
    assert!(cfg.engine.foreground_boost_enabled);
    assert_eq!(cfg.engine.foreground_boost_priority, "ABOVE_NORMAL");
    assert!(cfg.probalance.enabled);
    assert!(cfg.rules.len() > 0);
    assert!(cfg.disallowed_processes.contains(&"unwanted_crypto_miner.exe".to_string()));
}

#[test]
fn test_discover_and_load_fallback_to_embedded_when_path_invalid() {
    let (cfg, path) = AppConfig::discover_and_load(Some("non_existent_folder/missing.json"));
    // Even if path is invalid, it falls back gracefully without panic
    assert!(cfg.rules.len() > 0);
    println!("Resolved path: {}", path);
}

#[test]
fn test_discover_and_load_auto_discovery() {
    let (cfg, path) = AppConfig::discover_and_load(None);
    assert!(cfg.rules.len() > 0);
    assert!(path.contains("default_rules.json") || path.contains("Embedded"));
}
