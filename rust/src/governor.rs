use std::collections::HashMap;
use std::time::{Duration, Instant};
use regex::Regex;
use windows_sys::Win32::System::Diagnostics::ToolHelp::*;

use crate::config::{AppConfig, ProcessRule};
use crate::probalance::{ProBalanceAction, ProBalanceEngine, ProcessMetric};
use crate::topology::CPUTopology;
use crate::watchdog::{ProcessItem, WatchdogAction, WatchdogEngine};
use crate::win32::Win32Kernel;

pub struct CompiledRule {
    pub regex: Regex,
    pub rule: ProcessRule,
}

pub struct GovernorEngine {
    pub config: AppConfig,
    pub topology: CPUTopology,
    pub probalance: ProBalanceEngine,
    pub watchdog: WatchdogEngine,
    pub rules: Vec<CompiledRule>,
    pub applied_cache: HashMap<u32, AppliedState>,
    pub last_smart_trim: Instant,
}

#[derive(Default, Clone)]
pub struct AppliedState {
    pub priority: Option<String>,
    pub affinity: Option<usize>,
    pub io_priority: Option<String>,
    pub eco_qos: Option<bool>,
}

pub struct TickStats {
    pub monitored_processes: usize,
    pub probalance_actions: usize,
    pub watchdog_actions: usize,
    pub ram_percent: f32,
}

impl GovernorEngine {
    pub fn new(config: AppConfig) -> Self {
        let topology = CPUTopology::detect();
        let probalance = ProBalanceEngine::new(config.probalance.clone());
        let watchdog = WatchdogEngine::new(&config.watchdogs);

        let mut compiled_rules = Vec::new();
        for r in &config.rules {
            if let Ok(reg) = Regex::new(&r.pattern) {
                compiled_rules.push(CompiledRule {
                    regex: reg,
                    rule: r.clone(),
                });
            }
        }

        Self {
            config,
            topology,
            probalance,
            watchdog,
            rules: compiled_rules,
            applied_cache: HashMap::new(),
            last_smart_trim: Instant::now(),
        }
    }

    pub fn tick(&mut self, dry_run: bool) -> TickStats {
        let foreground_pid = if self.config.engine.foreground_boost_enabled {
            Win32Kernel::get_foreground_pid()
        } else {
            None
        };

        let ram_percent = Win32Kernel::get_system_ram_percent();

        // Enumerate running processes via Toolhelp32
        let snapshots = self.enumerate_system_processes();

        // 1. Evaluate Persistent Rules
        for snap in &snapshots {
            let matched_rule = self.match_rule(&snap.name).cloned();

            if let Some(rule) = matched_rule {
                let entry = self.applied_cache.entry(snap.pid).or_default();

                if let Some(ref prio) = rule.priority {
                    if entry.priority.as_ref() != Some(prio) {
                        if !dry_run {
                            Win32Kernel::set_process_priority(snap.pid, prio);
                        }
                        entry.priority = Some(prio.clone());
                    }
                }

                if let Some(ref aff_spec) = rule.cpu_affinity {
                    let mask = self.topology.parse_affinity(aff_spec);
                    if entry.affinity != Some(mask) {
                        if !dry_run {
                            Win32Kernel::set_process_affinity(snap.pid, mask);
                        }
                        entry.affinity = Some(mask);
                    }
                }

                if let Some(ref io_prio) = rule.io_priority {
                    if entry.io_priority.as_ref() != Some(io_prio) {
                        if !dry_run {
                            Win32Kernel::set_process_io_priority(snap.pid, io_prio);
                        }
                        entry.io_priority = Some(io_prio.clone());
                    }
                }

                if let Some(eco_qos) = rule.power_throttling_eco_qos {
                    if entry.eco_qos != Some(eco_qos) {
                        if !dry_run {
                            Win32Kernel::set_process_eco_qos(snap.pid, eco_qos);
                        }
                        entry.eco_qos = Some(eco_qos);
                    }
                }

                if let Some(ref scheme) = rule.power_scheme {
                    if !dry_run {
                        Win32Kernel::set_active_power_scheme(scheme);
                    }
                }
            }
        }

        // 2. Evaluate ProBalance Heuristic
        let metrics: Vec<ProcessMetric> = snapshots
            .iter()
            .map(|s| ProcessMetric {
                pid: s.pid,
                name: s.name.clone(),
                cpu_percent: s.cpu_percent,
                current_priority: "NORMAL".to_string(),
            })
            .collect();

        let avg_cpu: f32 = metrics.iter().map(|m| m.cpu_percent).sum::<f32>().min(100.0);

        let pb_actions = self.probalance.evaluate(avg_cpu, &metrics, foreground_pid);
        for act in &pb_actions {
            match act {
                ProBalanceAction::Restrain { pid, target_priority, .. } => {
                    if !dry_run {
                        Win32Kernel::set_process_priority(*pid, target_priority);
                    }
                }
                ProBalanceAction::Restore { pid, target_priority, .. } => {
                    if !dry_run {
                        Win32Kernel::set_process_priority(*pid, target_priority);
                    }
                }
            }
        }

        // 3. Evaluate Watchdogs
        let wd_items: Vec<ProcessItem> = snapshots
            .iter()
            .map(|s| ProcessItem {
                pid: s.pid,
                name: s.name.clone(),
                memory_mb: s.memory_mb,
            })
            .collect();

        let wd_actions = self.watchdog.evaluate(&wd_items);
        for w_act in &wd_actions {
            match w_act {
                WatchdogAction::TrimWorkingSet { pid, .. } => {
                    if !dry_run {
                        Win32Kernel::trim_process_working_set(*pid);
                    }
                }
                WatchdogAction::Terminate { pid, .. } => {
                    if !dry_run {
                        unsafe {
                            let h = windows_sys::Win32::System::Threading::OpenProcess(
                                windows_sys::Win32::System::Threading::PROCESS_TERMINATE,
                                0,
                                *pid,
                            );
                            if !h.is_null() {
                                windows_sys::Win32::System::Threading::TerminateProcess(h, 1);
                                windows_sys::Win32::Foundation::CloseHandle(h);
                            }
                        }
                    }
                }
            }
        }

        // 4. SmartTrim (Working Set Trimming on High RAM Pressure)
        let eng = &self.config.engine;
        if eng.smart_trim_enabled {
            let cooldown = Duration::from_secs(eng.smart_trim_interval_seconds);
            if self.last_smart_trim.elapsed() >= cooldown
                && ram_percent >= eng.smart_trim_threshold_percent
            {
                if !dry_run {
                    for s in &snapshots {
                        Win32Kernel::trim_process_working_set(s.pid);
                    }
                }
                self.last_smart_trim = Instant::now();
            }
        }

        TickStats {
            monitored_processes: snapshots.len(),
            probalance_actions: pb_actions.len(),
            watchdog_actions: wd_actions.len(),
            ram_percent,
        }
    }

    fn match_rule(&self, process_name: &str) -> Option<&ProcessRule> {
        for cr in &self.rules {
            if cr.regex.is_match(process_name) {
                return Some(&cr.rule);
            }
        }
        None
    }

    fn enumerate_system_processes(&self) -> Vec<RawProcessSnapshot> {
        let mut results = Vec::new();
        unsafe {
            let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
            if snapshot.is_null() {
                return results;
            }

            let mut entry = PROCESSENTRY32 {
                dwSize: std::mem::size_of::<PROCESSENTRY32>() as u32,
                cntUsage: 0,
                th32ProcessID: 0,
                th32DefaultHeapID: 0,
                th32ModuleID: 0,
                cntThreads: 0,
                th32ParentProcessID: 0,
                pcPriClassBase: 0,
                dwFlags: 0,
                szExeFile: [0; 260],
            };

            if Process32First(snapshot, &mut entry) != 0 {
                loop {
                    if entry.th32ProcessID > 4 {
                        let name_len = entry
                            .szExeFile
                            .iter()
                            .position(|&c| c == 0)
                            .unwrap_or(entry.szExeFile.len());
                        let name_bytes: Vec<u8> = entry.szExeFile[..name_len]
                            .iter()
                            .map(|&c| c as u8)
                            .collect();
                        let name = String::from_utf8_lossy(&name_bytes).to_string();

                        results.push(RawProcessSnapshot {
                            pid: entry.th32ProcessID,
                            name,
                            cpu_percent: 0.0,
                            memory_mb: 25.0,
                            threads: entry.cntThreads,
                        });
                    }

                    if Process32Next(snapshot, &mut entry) == 0 {
                        break;
                    }
                }
            }

            windows_sys::Win32::Foundation::CloseHandle(snapshot);
        }

        results
    }
}

pub struct RawProcessSnapshot {
    pub pid: u32,
    pub name: String,
    pub cpu_percent: f32,
    pub memory_mb: f64,
    pub threads: u32,
}
