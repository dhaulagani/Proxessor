use proxessor::filelock::find_file_lockers;
use proxessor::connections::list_all_connections;

#[test]
fn test_rust_filelock_on_existing_file() {
    let result = find_file_lockers("Cargo.toml");
    assert!(result.is_ok(), "find_file_lockers should succeed on existing file");
}

#[test]
fn test_rust_filelock_on_nonexistent_file() {
    let result = find_file_lockers("this_file_definitely_does_not_exist_xyz.tmp");
    assert!(result.is_err(), "find_file_lockers should return an error for non-existent path");
}

#[test]
fn test_rust_connections_listing() {
    let conns = list_all_connections();
    assert!(!conns.is_empty(), "Should list at least some active network connections");
    assert!(conns.iter().any(|c| c.protocol == "TCP" || c.protocol == "UDP"));
}
