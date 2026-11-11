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
    pub fn load_from_file(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: AppConfig = serde_json::from_str(&content)?;
        Ok(config)
    }
}
