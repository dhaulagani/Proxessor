//! File Lock Hunter for Proxessor (Dynamic Load of rstrtmgr.dll)
//! Identifies processes holding locks on files/directories via Windows Restart Manager.

#![allow(non_snake_case)]

use std::path::Path;
use serde::Serialize;
use windows_sys::Win32::System::LibraryLoader::{GetProcAddress, LoadLibraryA};

#[allow(non_snake_case)]
#[repr(C)]
#[derive(Copy, Clone)]
pub struct RM_UNIQUE_PROCESS {
    pub dwProcessId: u32,
    pub ProcessStartTime: windows_sys::Win32::Foundation::FILETIME,
}

pub const CCH_RM_SESSION_KEY: usize = 32;
pub const CCH_RM_MAX_APP_NAME: usize = 255;
pub const CCH_RM_MAX_SVC_NAME: usize = 63;

#[allow(non_snake_case)]
#[repr(C)]
#[derive(Copy, Clone)]
pub struct RM_PROCESS_INFO {
    pub Process: RM_UNIQUE_PROCESS,
    pub strAppName: [u16; CCH_RM_MAX_APP_NAME + 1],
    pub strServiceShortName: [u16; CCH_RM_MAX_SVC_NAME + 1],
    pub ApplicationType: u32,
    pub AppStatus: u32,
    pub TSSessionId: u32,
    pub bRestartable: i32,
}

type FnRmStartSession = unsafe extern "system" fn(
    pSessionHandle: *mut u32,
    dwSessionFlags: u32,
    strSessionKey: *mut u16,
) -> u32;

type FnRmRegisterResources = unsafe extern "system" fn(
    dwSessionHandle: u32,
    nFiles: u32,
    rgsFileNames: *const *const u16,
    nApplications: u32,
    rgApplications: *const RM_UNIQUE_PROCESS,
    nServices: u32,
    rgsServiceNames: *const *const u16,
) -> u32;

type FnRmGetList = unsafe extern "system" fn(
    dwSessionHandle: u32,
    pnProcInfoNeeded: *mut u32,
    pnProcInfo: *mut u32,
    rgAffectedApps: *mut RM_PROCESS_INFO,
    lpdwRebootReasons: *mut u32,
) -> u32;

type FnRmEndSession = unsafe extern "system" fn(dwSessionHandle: u32) -> u32;

struct RmApi {
    start_session: FnRmStartSession,
    register_resources: FnRmRegisterResources,
    get_list: FnRmGetList,
    end_session: FnRmEndSession,
}

impl RmApi {
    fn load() -> Option<Self> {
        unsafe {
            let h_mod = LoadLibraryA(b"rstrtmgr.dll\0".as_ptr());
            if h_mod.is_null() {
                return None;
            }

            let p_start = GetProcAddress(h_mod, b"RmStartSession\0".as_ptr())?;
            let p_reg = GetProcAddress(h_mod, b"RmRegisterResources\0".as_ptr())?;
            let p_get = GetProcAddress(h_mod, b"RmGetList\0".as_ptr())?;
            let p_end = GetProcAddress(h_mod, b"RmEndSession\0".as_ptr())?;

            Some(Self {
                start_session: std::mem::transmute(p_start),
                register_resources: std::mem::transmute(p_reg),
                get_list: std::mem::transmute(p_get),
                end_session: std::mem::transmute(p_end),
            })
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct FileLocker {
    pub pid: u32,
    pub app_name: String,
    pub service_name: Option<String>,
    pub app_type: String,
}

fn u16_to_string(slice: &[u16]) -> String {
    let len = slice.iter().position(|&c| c == 0).unwrap_or(slice.len());
    String::from_utf16_lossy(&slice[..len])
}

fn app_type_to_str(t: u32) -> &'static str {
    match t {
        1 => "MainWindow",
        2 => "OtherWindow",
        3 => "Service",
        4 => "Explorer",
        5 => "Console",
        1000 => "CriticalSystem",
        _ => "Other",
    }
}

/// Find all processes that currently have a lock or open handle on the specified file or folder.
pub fn find_file_lockers<P: AsRef<Path>>(target_path: P) -> Result<Vec<FileLocker>, String> {
    let p = target_path.as_ref();
    if !p.exists() {
        return Err(format!("Path does not exist: {}", p.display()));
    }

    let rm = RmApi::load().ok_or_else(|| "Failed to load rstrtmgr.dll from System32".to_string())?;

    let abs_path = std::fs::canonicalize(p)
        .map_err(|e| format!("Failed to canonicalize path: {e}"))?;
    let path_str = abs_path.to_string_lossy().to_string();
    let clean_path = path_str.strip_prefix(r"\\?\").unwrap_or(&path_str);

    let wide_path: Vec<u16> = clean_path.encode_utf16().chain(std::iter::once(0)).collect();
    let mut session_handle: u32 = 0;
    let mut session_key = [0u16; CCH_RM_SESSION_KEY + 1];

    unsafe {
        let err = (rm.start_session)(&mut session_handle, 0, session_key.as_mut_ptr());
        if err != 0 {
            return Err(format!("RmStartSession failed with Win32 error code {err}"));
        }
    }

    struct SessionGuard<'a>(&'a RmApi, u32);
    impl<'a> Drop for SessionGuard<'a> {
        fn drop(&mut self) {
            unsafe {
                let _ = (self.0.end_session)(self.1);
            }
        }
    }
    let _guard = SessionGuard(&rm, session_handle);

    let path_ptr = wide_path.as_ptr();
    let file_ptrs = [path_ptr];

    unsafe {
        let err = (rm.register_resources)(
            session_handle,
            1,
            file_ptrs.as_ptr(),
            0,
            std::ptr::null(),
            0,
            std::ptr::null(),
        );
        if err != 0 {
            return Err(format!("RmRegisterResources failed with error {err}"));
        }

        let mut n_proc_info_needed: u32 = 0;
        let mut n_proc_info: u32 = 0;
        let mut reboot_reasons: u32 = 0;

        let err = (rm.get_list)(
            session_handle,
            &mut n_proc_info_needed,
            &mut n_proc_info,
            std::ptr::null_mut(),
            &mut reboot_reasons,
        );

        if err != 0 && err != 234 {
            return Err(format!("RmGetList sizing call failed with error {err}"));
        }

        if n_proc_info_needed == 0 {
            return Ok(Vec::new());
        }

        let mut proc_info: Vec<RM_PROCESS_INFO> = vec![
            RM_PROCESS_INFO {
                Process: RM_UNIQUE_PROCESS {
                    dwProcessId: 0,
                    ProcessStartTime: windows_sys::Win32::Foundation::FILETIME {
                        dwLowDateTime: 0,
                        dwHighDateTime: 0,
                    },
                },
                strAppName: [0; CCH_RM_MAX_APP_NAME + 1],
                strServiceShortName: [0; CCH_RM_MAX_SVC_NAME + 1],
                ApplicationType: 0,
                AppStatus: 0,
                TSSessionId: 0,
                bRestartable: 0,
            };
            n_proc_info_needed as usize
        ];

        n_proc_info = n_proc_info_needed;
        let err = (rm.get_list)(
            session_handle,
            &mut n_proc_info_needed,
            &mut n_proc_info,
            proc_info.as_mut_ptr(),
            &mut reboot_reasons,
        );

        if err != 0 {
            return Err(format!("RmGetList failed with error {err}"));
        }

        let mut results = Vec::with_capacity(n_proc_info as usize);
        for item in proc_info.iter().take(n_proc_info as usize) {
            let app_name = u16_to_string(&item.strAppName);
            let svc_name = u16_to_string(&item.strServiceShortName);
            let service_name = if svc_name.trim().is_empty() {
                None
            } else {
                Some(svc_name)
            };

            results.push(FileLocker {
                pid: item.Process.dwProcessId,
                app_name: if app_name.is_empty() { "Unknown".to_string() } else { app_name },
                service_name,
                app_type: app_type_to_str(item.ApplicationType).to_string(),
            });
        }

        Ok(results)
    }
}
