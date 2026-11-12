use serde::Deserialize;

#[derive(Debug, Deserialize, Clone)]
pub struct EngineConfig {
    #[serde(default = "default_poll_interval")]
    pub poll_interval_ms: u64,
    #[serde(default = "default_true")]
    pub foreground_boost_enabled: bool,
    #[serde(default = "default_boost_priority")]
    pub foreground_boost_priority: String,
    #[serde(default = "default_false")]
    pub idle_saver_enabled: bool,
    #[serde(default = "default_idle_saver_threshold")]
    pub idle_saver_threshold_seconds: u64,
    #[serde(default = "default_true")]
    pub smart_trim_enabled: bool,
    #[serde(default = "default_ram_threshold")]
    pub smart_trim_threshold_percent: f32,
    #[serde(default = "default_trim_interval")]
    pub smart_trim_interval_seconds: u64,
}

fn default_false() -> bool { false }
fn default_idle_saver_threshold() -> u64 { 300 }

fn default_boost_priority() -> String {
    "ABOVE_NORMAL".to_string()
}

#[derive(Debug, Deserialize, Clone)]
pub struct ProBalanceConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_cpu_trigger")]
    pub cpu_trigger_threshold_percent: f32,
    #[serde(default = "default_proc_cpu_trigger")]
    pub per_process_cpu_trigger_percent: f32,
    #[serde(default = "default_restraint_priority")]
    pub target_restraint_priority: String,
    #[serde(default = "default_restraint_duration")]
    pub restraint_duration_seconds: u64,
    #[serde(default = "default_recovery_threshold")]
    pub recovery_threshold_percent: f32,
    #[serde(default = "default_true")]
    pub ignore_foreground_process: bool,
    #[serde(default)]
    pub excluded_processes: Vec<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ProcessRule {
    pub name: String,
    pub pattern: String,
    pub priority: Option<String>,
    pub io_priority: Option<String>,
    pub memory_priority: Option<u32>,
    pub power_throttling_eco_qos: Option<bool>,
    pub cpu_affinity: Option<String>,
    pub power_scheme: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct WatchdogRule {
    pub name: String,
    pub pattern: String,
    pub max_instances: Option<usize>,
    pub max_memory_mb: Option<f64>,
    pub action: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct AppConfig {
    pub engine: EngineConfig,
    pub probalance: ProBalanceConfig,
    #[serde(default)]
    pub rules: Vec<ProcessRule>,
    #[serde(default)]
    pub watchdogs: Vec<WatchdogRule>,
    #[serde(default)]
    pub disallowed_processes: Vec<String>,
}

fn default_poll_interval() -> u64 { 1000 }
fn default_true() -> bool { true }
fn default_ram_threshold() -> f32 { 85.0 }
fn default_trim_interval() -> u64 { 300 }
fn default_cpu_trigger() -> f32 { 65.0 }
fn default_proc_cpu_trigger() -> f32 { 20.0 }
fn default_restraint_priority() -> String { "BELOW_NORMAL".to_string() }
fn default_restraint_duration() -> u64 { 10 }
fn default_recovery_threshold() -> f32 { 50.0 }

impl AppConfig {
    pub const EMBEDDED_DEFAULT_CONFIG: &'static str = include_str!("../../config/default_rules.json");

    pub fn load_embedded() -> Self {
        serde_json::from_str(Self::EMBEDDED_DEFAULT_CONFIG)
            .expect("Embedded default configuration must be valid JSON")
    }

    pub fn load_from_file(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: AppConfig = serde_json::from_str(&content)?;
        Ok(config)
    }

    pub fn discover_and_load(custom_path: Option<&str>) -> (Self, String) {
        if let Some(path) = custom_path {
            match Self::load_from_file(path) {
                Ok(cfg) => return (cfg, path.to_string()),
                Err(e) => {
                    eprintln!("Warning: Failed to load specified config '{}': {}. Falling back to auto-discovery...", path, e);
                }
            }
        }

        // 1. Check relative to current executable's folder (essential for portable releases)
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(exe_dir) = exe_path.parent() {
                let candidate1 = exe_dir.join("config").join("default_rules.json");
                if candidate1.exists() {
                    if let Ok(cfg) = Self::load_from_file(&candidate1.to_string_lossy()) {
                        return (cfg, candidate1.to_string_lossy().to_string());
                    }
                }
                let candidate2 = exe_dir.join("default_rules.json");
                if candidate2.exists() {
                    if let Ok(cfg) = Self::load_from_file(&candidate2.to_string_lossy()) {
                        return (cfg, candidate2.to_string_lossy().to_string());
                    }
                }
            }
        }

        // 2. Check relative to current working directory
        let search_paths = [
            "config/default_rules.json",
            "default_rules.json",
            "../config/default_rules.json",
        ];

        for path in search_paths {
            if std::path::Path::new(path).exists() {
                if let Ok(cfg) = Self::load_from_file(path) {
                    return (cfg, path.to_string());
                }
            }
        }

        // 3. Fallback to embedded default configuration
        (Self::load_embedded(), "Embedded Default Rules (Internal)".to_string())
    }
}
