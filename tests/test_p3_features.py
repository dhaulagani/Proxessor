import os
import psutil
import pytest
from src.proxessor.gui.controller import GUIController

def test_tree_hierarchy_building():
    ctrl = GUIController()
    raw_processes = [
        {"pid": 100, "ppid": 0, "name": "explorer.exe"},
        {"pid": 200, "ppid": 100, "name": "cmd.exe"},
        {"pid": 300, "ppid": 200, "name": "python.exe"},
        {"pid": 400, "ppid": 100, "name": "chrome.exe"},
        {"pid": 500, "ppid": 0, "name": "system.exe"}
    ]
    tree = ctrl.build_tree_hierarchy(raw_processes)
    assert len(tree) == 5
    
    # explorer.exe is root
    exp = next(p for p in tree if p["pid"] == 100)
    assert exp["display_name"] == "explorer.exe"

    # cmd.exe is child of explorer
    cmd = next(p for p in tree if p["pid"] == 200)
    assert "├── " in cmd["display_name"] or "└── " in cmd["display_name"]

    # python.exe is grandchild
    py = next(p for p in tree if p["pid"] == 300)
    assert "│   " in py["display_name"] or "    " in py["display_name"]

def test_get_process_modules_current_process():
    ctrl = GUIController()
    cur_pid = os.getpid()
    modules = ctrl.get_process_modules(cur_pid)
    assert len(modules) > 0
    assert any(m["name"].lower().endswith(".dll") for m in modules)

def test_get_process_handles_current_process():
    ctrl = GUIController()
    cur_pid = os.getpid()
    handles = ctrl.get_process_handles(cur_pid)
    # Process might have open files or sockets
    assert isinstance(handles, list)
