use std::ffi::c_void;
use std::mem::size_of;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::System::Threading::*;
use windows_sys::Win32::System::ProcessStatus::*;
use windows_sys::Win32::System::SystemInformation::*;
use windows_sys::Win32::System::LibraryLoader::*;
use windows_sys::Win32::UI::WindowsAndMessaging::*;

// NT Undocumented Process Information Class for I/O Priority
const PROCESS_IO_PRIORITY_CLASS: u32 = 33;
const PROCESS_MEMORY_PRIORITY: u32 = 4;
const PROCESS_POWER_THROTTLING: u32 = 1;

const PROCESS_POWER_THROTTLING_CURRENT_VERSION: u32 = 1;
const PROCESS_POWER_THROTTLING_EXECUTION_SPEED: u32 = 0x1;

#[repr(C)]
struct ProcessPowerThrottlingState {
    version: u32,
    control_mask: u32,
    state_mask: u32,
}

#[repr(C)]
struct MemoryPriorityInformation {
    memory_priority: u32,
}

type NtSetInformationProcessFn = unsafe extern "system" fn(
    process_handle: HANDLE,
    process_information_class: u32,
    process_information: *const c_void,
    process_information_length: u32,
) -> i32;

type PowerSetActiveSchemeFn = unsafe extern "system" fn(
    user_root_power_key: *mut c_void,
    scheme_guid: *const windows_sys::core::GUID,
) -> u32;

pub struct Win32Kernel;

impl Win32Kernel {
    pub fn get_foreground_pid() -> Option<u32> {
        unsafe {
            let hwnd = GetForegroundWindow();
            if hwnd.is_null() {
                return None;
            }
            let mut pid = 0u32;
            GetWindowThreadProcessId(hwnd, &mut pid);
            if pid != 0 { Some(pid) } else { None }
        }
    }

    pub fn set_process_priority(pid: u32, priority: &str) -> bool {
        let flag = match priority.to_uppercase().as_str() {
            "IDLE" => IDLE_PRIORITY_CLASS,
            "BELOW_NORMAL" => BELOW_NORMAL_PRIORITY_CLASS,
            "NORMAL" => NORMAL_PRIORITY_CLASS,
            "ABOVE_NORMAL" => ABOVE_NORMAL_PRIORITY_CLASS,
            "HIGH" => HIGH_PRIORITY_CLASS,
            "REALTIME" => REALTIME_PRIORITY_CLASS,
            _ => return false,
        };

        unsafe {
            let handle = OpenProcess(PROCESS_SET_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }
            let ok = SetPriorityClass(handle, flag);
            CloseHandle(handle);
            ok != 0
        }
    }

    pub fn set_process_affinity(pid: u32, mask: usize) -> bool {
        unsafe {
            let handle = OpenProcess(PROCESS_SET_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }
            let ok = SetProcessAffinityMask(handle, mask);
            CloseHandle(handle);
            ok != 0
        }
    }

    pub fn set_process_io_priority(pid: u32, io_prio: &str) -> bool {
        let val: u32 = match io_prio.to_uppercase().as_str() {
            "VERY_LOW" => 0,
            "LOW" => 1,
            "NORMAL" => 2,
            "HIGH" => 3,
            _ => return false,
        };

        unsafe {
            let handle = OpenProcess(PROCESS_SET_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }

            let ntdll = GetModuleHandleA(b"ntdll.dll\0".as_ptr());
            if ntdll.is_null() {
                CloseHandle(handle);
                return false;
            }

            let proc = GetProcAddress(ntdll, b"NtSetInformationProcess\0".as_ptr());
            if proc.is_none() {
                CloseHandle(handle);
                return false;
            }

            let nt_set_info: NtSetInformationProcessFn = std::mem::transmute(proc.unwrap());
            let status = nt_set_info(
                handle,
                PROCESS_IO_PRIORITY_CLASS,
                &val as *const u32 as *const c_void,
                size_of::<u32>() as u32,
            );

            CloseHandle(handle);
            status == 0
        }
    }

    pub fn set_process_memory_priority(pid: u32, priority_level: u32) -> bool {
        if priority_level > 5 {
            return false;
        }

        unsafe {
            let handle = OpenProcess(PROCESS_SET_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }

            let info = MemoryPriorityInformation {
                memory_priority: priority_level,
            };

            let ok = SetProcessInformation(
                handle,
                PROCESS_MEMORY_PRIORITY as _,
                &info as *const _ as *const c_void,
                size_of::<MemoryPriorityInformation>() as u32,
            );

            CloseHandle(handle);
            ok != 0
        }
    }

    pub fn set_process_eco_qos(pid: u32, enable: bool) -> bool {
        unsafe {
            let handle = OpenProcess(PROCESS_SET_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }

            let mut state = ProcessPowerThrottlingState {
                version: PROCESS_POWER_THROTTLING_CURRENT_VERSION,
                control_mask: PROCESS_POWER_THROTTLING_EXECUTION_SPEED,
                state_mask: if enable { PROCESS_POWER_THROTTLING_EXECUTION_SPEED } else { 0 },
            };

            let ok = SetProcessInformation(
                handle,
                PROCESS_POWER_THROTTLING as _,
                &mut state as *mut _ as *mut c_void,
                size_of::<ProcessPowerThrottlingState>() as u32,
            );

            CloseHandle(handle);
            ok != 0
        }
    }

    pub fn trim_process_working_set(pid: u32) -> bool {
        unsafe {
            let handle = OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, 0, pid);
            if handle.is_null() {
                return false;
            }
            let ok = EmptyWorkingSet(handle);
            CloseHandle(handle);
            ok != 0
        }
    }

    pub fn get_system_ram_percent() -> f32 {
        unsafe {
            let mut mem_stat = MEMORYSTATUSEX {
                dwLength: size_of::<MEMORYSTATUSEX>() as u32,
                dwMemoryLoad: 0,
                ullTotalPhys: 0,
                ullAvailPhys: 0,
                ullTotalPageFile: 0,
                ullAvailPageFile: 0,
                ullTotalVirtual: 0,
                ullAvailVirtual: 0,
                ullAvailExtendedVirtual: 0,
            };
            if GlobalMemoryStatusEx(&mut mem_stat) != 0 {
                mem_stat.dwMemoryLoad as f32
            } else {
                0.0
            }
        }
    }

    pub fn set_active_power_scheme(scheme_name: &str) -> bool {
        let guid_str = match scheme_name.to_uppercase().as_str() {
            "BALANCED" => "381b4222-f694-41f0-9685-ff5bb260df2e",
            "HIGH_PERFORMANCE" => "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "POWER_SAVER" => "a1841308-3541-4fab-bc81-f71556f20b4a",
            "ULTIMATE_PERFORMANCE" => "e9a42b02-d5df-448d-aa00-03f14749eb61",
            _ => return false,
        };

        if let Ok(guid) = parse_guid(guid_str) {
            unsafe {
                let powrprof = LoadLibraryA(b"powrprof.dll\0".as_ptr());
                if powrprof.is_null() {
                    return false;
                }
                let proc = GetProcAddress(powrprof, b"PowerSetActiveScheme\0".as_ptr());
                if proc.is_none() {
                    FreeLibrary(powrprof);
                    return false;
                }
                let power_fn: PowerSetActiveSchemeFn = std::mem::transmute(proc.unwrap());
                let res = power_fn(std::ptr::null_mut(), &guid);
                FreeLibrary(powrprof);
                res == 0
            }
        } else {
            false
        }
    }
}

fn parse_guid(s: &str) -> Result<windows_sys::core::GUID, ()> {
    let clean = s.replace('-', "");
    if clean.len() != 32 {
        return Err(());
    }

    let d1 = u32::from_str_radix(&clean[0..8], 16).map_err(|_| ())?;
    let d2 = u16::from_str_radix(&clean[8..12], 16).map_err(|_| ())?;
    let d3 = u16::from_str_radix(&clean[12..16], 16).map_err(|_| ())?;

    let mut d4 = [0u8; 8];
    for i in 0..8 {
        d4[i] = u8::from_str_radix(&clean[16 + i * 2..18 + i * 2], 16).map_err(|_| ())?;
    }

    Ok(windows_sys::core::GUID {
        data1: d1,
        data2: d2,
        data3: d3,
        data4: d4,
    })
}
