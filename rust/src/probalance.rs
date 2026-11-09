use std::collections::{HashMap, HashSet};
use std::time::Instant;
use crate::config::ProBalanceConfig;

pub struct RestrainedInfo {
    pub name: String,
    pub base_priority: String,
    pub restrained_at: Instant,
}

pub struct ProBalanceEngine {
    pub config: ProBalanceConfig,
    pub excluded_names: HashSet<String>,
    pub restrained_processes: HashMap<u32, RestrainedInfo>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum ProBalanceAction {
    Restrain { pid: u32, name: String, target_priority: String, base_priority: String },
    Restore { pid: u32, name: String, target_priority: String },
}

pub struct ProcessMetric {
    pub pid: u32,
    pub name: String,
    pub cpu_percent: f32,
    pub current_priority: String,
}

impl ProBalanceEngine {
    pub fn new(config: ProBalanceConfig) -> Self {
        let excluded: HashSet<String> = config
            .excluded_processes
            .iter()
            .map(|s| s.to_lowercase())
            .collect();

        Self {
            config,
            excluded_names: excluded,
            restrained_processes: HashMap::new(),
        }
    }

    pub fn evaluate(
        &mut self,
        system_cpu_percent: f32,
        processes: &[ProcessMetric],
        foreground_pid: Option<u32>,
    ) -> Vec<ProBalanceAction> {
        if !self.config.enabled {
            return Vec::new();
        }

        let mut actions = Vec::new();
        let now = Instant::now();
        let active_pids: HashSet<u32> = processes.iter().map(|p| p.pid).collect();

        // 1. Purge dead processes
        self.restrained_processes.retain(|pid, _| active_pids.contains(pid));

        // 2. Check for restorations
        let cooldown = std::time::Duration::from_secs(self.config.restraint_duration_seconds);
        let mut restored_pids = Vec::new();

        for (&pid, info) in &self.restrained_processes {
            if now.duration_since(info.restrained_at) >= cooldown
                && system_cpu_percent < self.config.recovery_threshold_percent
            {
                actions.push(ProBalanceAction::Restore {
                    pid,
                    name: info.name.clone(),
                    target_priority: info.base_priority.clone(),
                });
                restored_pids.push(pid);
            }
        }

        for pid in restored_pids {
            self.restrained_processes.remove(&pid);
        }

        // 3. Check for restraints if system CPU exceeds trigger threshold
        if system_cpu_percent >= self.config.cpu_trigger_threshold_percent {
            for proc in processes {
                if self.restrained_processes.contains_key(&proc.pid) {
                    continue;
                }

                if proc.cpu_percent >= self.config.per_process_cpu_trigger_percent {
                    // Check exclusions
                    if self.excluded_names.contains(&proc.name.to_lowercase()) {
                        continue;
                    }

                    // Check foreground immunity
                    if self.config.ignore_foreground_process && Some(proc.pid) == foreground_pid {
                        continue;
                    }

                    // Avoid restraining processes already at or below target
                    if proc.current_priority == "BELOW_NORMAL" || proc.current_priority == "IDLE" {
                        continue;
                    }

                    actions.push(ProBalanceAction::Restrain {
                        pid: proc.pid,
                        name: proc.name.clone(),
                        target_priority: self.config.target_restraint_priority.clone(),
                        base_priority: proc.current_priority.clone(),
                    });

                    self.restrained_processes.insert(
                        proc.pid,
                        RestrainedInfo {
                            name: proc.name.clone(),
                            base_priority: proc.current_priority.clone(),
                            restrained_at: now,
                        },
                    );
                }
            }
        }

        actions
    }
}
