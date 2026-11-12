import pytest
from src.proxessor.gui.controller import GUIController

@pytest.fixture
def sample_processes():
    return [
        {
            "pid": 500,
            "ppid": 100,
            "name": "zebra.exe",
            "cpu_percent": 15.5,
            "cpu": 15.5,
            "memory_mb": 256.0,
            "ram": 256.0,
            "priority": "HIGH",
            "prio": "HIGH",
            "threads": 8,
            "affinity": "P-Cores",
            "aff": "P-Cores",
            "status_text": "Restrained (PB)",
            "status": "Restrained (PB)",
            "is_foreground": False,
            "is_restrained": True,
            "is_excluded": False
        },
        {
            "pid": 120,
            "ppid": 0,
            "name": "alpha.exe",
            "cpu_percent": 0.5,
            "cpu": 0.5,
            "memory_mb": 1024.0,
            "ram": 1024.0,
            "priority": "IDLE",
            "prio": "IDLE",
            "threads": 2,
            "affinity": "All Cores",
            "aff": "All Cores",
            "status_text": "Normal",
            "status": "Normal",
            "is_foreground": False,
            "is_restrained": False,
            "is_excluded": False
        },
        {
            "pid": 350,
            "ppid": 120,
            "name": "beta.exe",
            "cpu_percent": 45.0,
            "cpu": 45.0,
            "memory_mb": 50.0,
            "ram": 50.0,
            "priority": "REALTIME",
            "prio": "REALTIME",
            "threads": 16,
            "affinity": "E-Cores",
            "aff": "E-Cores",
            "status_text": "Foreground",
            "status": "Foreground",
            "is_foreground": True,
            "is_restrained": False,
            "is_excluded": False
        },
        {
            "pid": 210,
            "ppid": 120,
            "name": "gamma.exe",
            "cpu_percent": 2.0,
            "cpu": 2.0,
            "memory_mb": 512.0,
            "ram": 512.0,
            "priority": "NORMAL",
            "prio": "NORMAL",
            "threads": 4,
            "affinity": "All Cores",
            "aff": "All Cores",
            "status_text": "Excluded (PB)",
            "status": "Excluded (PB)",
            "is_foreground": False,
            "is_restrained": False,
            "is_excluded": True
        }
    ]

def test_sort_by_pid(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    # Ascending
    asc = ctrl.get_filtered_processes(sort_by="pid", reverse=False)
    assert [p["pid"] for p in asc] == [120, 210, 350, 500]

    # Descending
    desc = ctrl.get_filtered_processes(sort_by="pid", reverse=True)
    assert [p["pid"] for p in desc] == [500, 350, 210, 120]

def test_sort_by_name(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    asc = ctrl.get_filtered_processes(sort_by="name", reverse=False)
    assert [p["name"] for p in asc] == ["alpha.exe", "beta.exe", "gamma.exe", "zebra.exe"]

    desc = ctrl.get_filtered_processes(sort_by="name", reverse=True)
    assert [p["name"] for p in desc] == ["zebra.exe", "gamma.exe", "beta.exe", "alpha.exe"]

def test_sort_by_cpu(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    # Descending using column alias "cpu"
    desc_cpu = ctrl.get_filtered_processes(sort_by="cpu", reverse=True)
    assert [p["pid"] for p in desc_cpu] == [350, 500, 210, 120]

    # Ascending using full name "cpu_percent"
    asc_cpu = ctrl.get_filtered_processes(sort_by="cpu_percent", reverse=False)
    assert [p["pid"] for p in asc_cpu] == [120, 210, 500, 350]

def test_sort_by_ram(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    # Descending using column alias "ram"
    desc_ram = ctrl.get_filtered_processes(sort_by="ram", reverse=True)
    assert [p["pid"] for p in desc_ram] == [120, 210, 500, 350]

    # Ascending using full name "memory_mb"
    asc_ram = ctrl.get_filtered_processes(sort_by="memory_mb", reverse=False)
    assert [p["pid"] for p in asc_ram] == [350, 500, 210, 120]

def test_sort_by_priority_rank(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    # Priority rank: REALTIME (6) > HIGH (5) > NORMAL (3) > IDLE (1)
    desc_prio = ctrl.get_filtered_processes(sort_by="prio", reverse=True)
    assert [p["priority"] for p in desc_prio] == ["REALTIME", "HIGH", "NORMAL", "IDLE"]

    asc_prio = ctrl.get_filtered_processes(sort_by="priority", reverse=False)
    assert [p["priority"] for p in asc_prio] == ["IDLE", "NORMAL", "HIGH", "REALTIME"]

def test_sort_by_threads(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    desc_thr = ctrl.get_filtered_processes(sort_by="threads", reverse=True)
    assert [p["threads"] for p in desc_thr] == [16, 8, 4, 2]

    asc_thr = ctrl.get_filtered_processes(sort_by="threads", reverse=False)
    assert [p["threads"] for p in asc_thr] == [2, 4, 8, 16]

def test_sort_by_status(sample_processes):
    ctrl = GUIController()
    ctrl.cached_processes = sample_processes

    # Status names: "Excluded (PB)", "Foreground", "Normal", "Restrained (PB)"
    asc_st = ctrl.get_filtered_processes(sort_by="status", reverse=False)
    assert [p["status_text"] for p in asc_st] == [
        "Excluded (PB)", "Foreground", "Normal", "Restrained (PB)"
    ]

    desc_st = ctrl.get_filtered_processes(sort_by="status", reverse=True)
    assert [p["status_text"] for p in desc_st] == [
        "Restrained (PB)", "Normal", "Foreground", "Excluded (PB)"
    ]
