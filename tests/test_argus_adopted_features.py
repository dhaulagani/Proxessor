import os
import pytest
from src.proxessor.core.filelock import FileLockHunter
from src.proxessor.core.connections import SocketInspector
from src.proxessor.gui.controller import GUIController

def test_filelock_hunter_initialization():
    hunter = FileLockHunter()
    assert hunter is not None
    # Test on existing file
    results = hunter.find_lockers(__file__)
    assert isinstance(results, list)

def test_socket_inspector_listing():
    inspector = SocketInspector()
    assert inspector is not None
    conns = inspector.list_connections()
    assert isinstance(conns, list)
    assert len(conns) > 0

    first = conns[0]
    assert "proto" in first
    assert "local_addr" in first
    assert "local_port" in first
    assert "pid" in first
    assert first["proto"] in ("TCP", "UDP")

def test_gui_controller_integrated_argus_features():
    controller = GUIController(config_path="config/default_rules.json")
    controller.refresh_state()

    # Per-core load
    per_core = controller.get_per_core_cpu()
    assert isinstance(per_core, list)
    assert len(per_core) > 0

    # Socket listing with mapped process names
    sockets = controller.list_connections()
    assert isinstance(sockets, list)
    assert len(sockets) > 0
    assert "name" in sockets[0]

    # File lock query
    locks = controller.find_file_lockers("Cargo.toml")
    assert isinstance(locks, list)
