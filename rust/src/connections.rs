//! Network Connections & Sockets Inspector for Proxessor (Inspired by Argus & Netstat)
//! Maps active TCP/UDP endpoints to their owning process PID and process name.

use std::net::Ipv4Addr;
use serde::Serialize;

#[allow(non_snake_case)]
#[repr(C)]
#[derive(Copy, Clone)]
pub struct MIB_TCPROW_OWNER_PID {
    pub dwState: u32,
    pub dwLocalAddr: u32,
    pub dwLocalPort: u32,
    pub dwRemoteAddr: u32,
    pub dwRemotePort: u32,
    pub dwOwningPid: u32,
}

#[allow(non_snake_case)]
#[repr(C)]
#[derive(Copy, Clone)]
pub struct MIB_UDPROW_OWNER_PID {
    pub dwLocalAddr: u32,
    pub dwLocalPort: u32,
    pub dwOwningPid: u32,
}

const AF_INET: u32 = 2;
const TCP_TABLE_OWNER_PID_ALL: u32 = 5;
const UDP_TABLE_OWNER_PID: u32 = 1;

#[link(name = "iphlpapi")]
extern "system" {
    fn GetExtendedTcpTable(
        pTcpTable: *mut core::ffi::c_void,
        pdwSize: *mut u32,
        bOrder: i32,
        ulAf: u32,
        TableClass: u32,
        Reserved: u32,
    ) -> u32;

    fn GetExtendedUdpTable(
        pUdpTable: *mut core::ffi::c_void,
        pdwSize: *mut u32,
        bOrder: i32,
        ulAf: u32,
        TableClass: u32,
        Reserved: u32,
    ) -> u32;
}

#[derive(Debug, Clone, Serialize)]
pub struct NetworkEndpoint {
    pub protocol: String,
    pub local_addr: String,
    pub local_port: u16,
    pub remote_addr: Option<String>,
    pub remote_port: Option<u16>,
    pub state: String,
    pub pid: u32,
}

fn tcp_state_to_str(state: u32) -> &'static str {
    match state {
        1 => "CLOSED",
        2 => "LISTENING",
        3 => "SYN_SENT",
        4 => "SYN_RCVD",
        5 => "ESTABLISHED",
        6 => "FIN_WAIT_1",
        7 => "FIN_WAIT_2",
        8 => "CLOSE_WAIT",
        9 => "CLOSING",
        10 => "LAST_ACK",
        11 => "TIME_WAIT",
        12 => "DELETE_TCB",
        _ => "UNKNOWN",
    }
}

fn decode_port(raw: u32) -> u16 {
    u16::from_be(raw as u16)
}

/// Retrieves all active IPv4 TCP sockets with their owning process PID.
pub fn get_tcp_connections() -> Result<Vec<NetworkEndpoint>, String> {
    let mut size: u32 = 0;
    unsafe {
        let _ = GetExtendedTcpTable(
            std::ptr::null_mut(),
            &mut size,
            0,
            AF_INET,
            TCP_TABLE_OWNER_PID_ALL,
            0,
        );

        if size == 0 {
            return Ok(Vec::new());
        }

        let mut buffer: Vec<u8> = vec![0u8; size as usize];
        let ret = GetExtendedTcpTable(
            buffer.as_mut_ptr() as *mut core::ffi::c_void,
            &mut size,
            0,
            AF_INET,
            TCP_TABLE_OWNER_PID_ALL,
            0,
        );

        if ret != 0 {
            return Err(format!("GetExtendedTcpTable failed with code {ret}"));
        }

        let num_entries = *(buffer.as_ptr() as *const u32) as usize;
        let row_ptr = buffer.as_ptr().add(std::mem::size_of::<u32>()) as *const MIB_TCPROW_OWNER_PID;
        let rows = std::slice::from_raw_parts(row_ptr, num_entries);

        let mut results = Vec::with_capacity(num_entries);
        for row in rows {
            let state_str = tcp_state_to_str(row.dwState);
            let is_listening = row.dwState == 2;

            results.push(NetworkEndpoint {
                protocol: "TCP".to_string(),
                local_addr: Ipv4Addr::from(row.dwLocalAddr.to_ne_bytes()).to_string(),
                local_port: decode_port(row.dwLocalPort),
                remote_addr: if is_listening {
                    None
                } else {
                    Some(Ipv4Addr::from(row.dwRemoteAddr.to_ne_bytes()).to_string())
                },
                remote_port: if is_listening {
                    None
                } else {
                    Some(decode_port(row.dwRemotePort))
                },
                state: state_str.to_string(),
                pid: row.dwOwningPid,
            });
        }

        Ok(results)
    }
}

/// Retrieves all active IPv4 UDP sockets with their owning process PID.
pub fn get_udp_connections() -> Result<Vec<NetworkEndpoint>, String> {
    let mut size: u32 = 0;
    unsafe {
        let _ = GetExtendedUdpTable(
            std::ptr::null_mut(),
            &mut size,
            0,
            AF_INET,
            UDP_TABLE_OWNER_PID,
            0,
        );

        if size == 0 {
            return Ok(Vec::new());
        }

        let mut buffer: Vec<u8> = vec![0u8; size as usize];
        let ret = GetExtendedUdpTable(
            buffer.as_mut_ptr() as *mut core::ffi::c_void,
            &mut size,
            0,
            AF_INET,
            UDP_TABLE_OWNER_PID,
            0,
        );

        if ret != 0 {
            return Err(format!("GetExtendedUdpTable failed with code {ret}"));
        }

        let num_entries = *(buffer.as_ptr() as *const u32) as usize;
        let row_ptr = buffer.as_ptr().add(std::mem::size_of::<u32>()) as *const MIB_UDPROW_OWNER_PID;
        let rows = std::slice::from_raw_parts(row_ptr, num_entries);

        let mut results = Vec::with_capacity(num_entries);
        for row in rows {
            results.push(NetworkEndpoint {
                protocol: "UDP".to_string(),
                local_addr: Ipv4Addr::from(row.dwLocalAddr.to_ne_bytes()).to_string(),
                local_port: decode_port(row.dwLocalPort),
                remote_addr: None,
                remote_port: None,
                state: "LISTENING".to_string(),
                pid: row.dwOwningPid,
            });
        }

        Ok(results)
    }
}

/// Combined list of all TCP and UDP endpoints.
pub fn list_all_connections() -> Vec<NetworkEndpoint> {
    let mut all = get_tcp_connections().unwrap_or_default();
    if let Ok(udp) = get_udp_connections() {
        all.extend(udp);
    }
    all
}
