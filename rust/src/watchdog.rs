use regex::Regex;
use crate::config::WatchdogRule;

pub struct CompiledWatchdog {
    pub name: String,
    pub regex: Regex,
    pub max_instances: Option<usize>,
    pub max_memory_mb: Option<f64>,
    pub action: String,
}

pub struct WatchdogEngine {
    pub rules: Vec<CompiledWatchdog>,
}

pub struct ProcessItem {
    pub pid: u32,
    pub name: String,
    pub memory_mb: f64,
}

pub enum WatchdogAction {
    TrimWorkingSet { pid: u32, name: String, watchdog_name: String },
    Terminate { pid: u32, name: String, watchdog_name: String },
}

impl WatchdogEngine {
    pub fn new(rules: &[WatchdogRule]) -> Self {
        let mut compiled = Vec::new();
        for r in rules {
            if let Ok(reg) = Regex::new(&r.pattern) {
                compiled.push(CompiledWatchdog {
                    name: r.name.clone(),
                    regex: reg,
                    max_instances: r.max_instances,
                    max_memory_mb: r.max_memory_mb,
                    action: r.action.clone().unwrap_or_else(|| "LOG".to_string()),
                });
            }
        }
        Self { rules: compiled }
    }

    pub fn evaluate(&self, processes: &[ProcessItem]) -> Vec<WatchdogAction> {
        let mut actions = Vec::new();

        for wd in &self.rules {
            let matching: Vec<&ProcessItem> = processes
                .iter()
                .filter(|p| wd.regex.is_match(&p.name))
                .collect();

            // Check instance count limit
            if let Some(max_inst) = wd.max_instances {
                if matching.len() > max_inst {
                    // Newest/highest PIDs first
                    let excess = matching.len() - max_inst;
                    for target in matching.iter().rev().take(excess) {
                        actions.push(WatchdogAction::Terminate {
                            pid: target.pid,
                            name: target.name.clone(),
                            watchdog_name: wd.name.clone(),
                        });
                    }
                }
            }

            // Check memory cap limit
            if let Some(max_mem) = wd.max_memory_mb {
                for target in matching {
                    if target.memory_mb > max_mem {
                        actions.push(WatchdogAction::TrimWorkingSet {
                            pid: target.pid,
                            name: target.name.clone(),
                            watchdog_name: wd.name.clone(),
                        });
                    }
                }
            }
        }

        actions
    }
}
