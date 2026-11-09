import pytest
from src.proxessor.core.probalance import ProBalanceEngine

@pytest.fixture
def pb_config():
    return {
        "enabled": True,
        "cpu_trigger_threshold_percent": 60.0,
        "per_process_cpu_trigger_percent": 25.0,
        "target_restraint_priority": "BELOW_NORMAL",
        "restraint_duration_seconds": 5.0,
        "recovery_threshold_percent": 40.0,
        "ignore_foreground_process": True,
        "excluded_processes": ["dwm.exe", "audiodg.exe", "System"]
    }

def test_probalance_no_trigger_on_low_system_cpu(pb_config):
    engine = ProBalanceEngine(pb_config)
    processes = [
        {"pid": 100, "name": "heavy_worker.exe", "cpu_percent": 30.0, "priority": "NORMAL"}
    ]
    # System CPU is 40% (below trigger of 60%)
    actions = engine.evaluate(system_cpu_percent=40.0, process_snapshots=processes, foreground_pid=None)
    assert len(actions) == 0
    assert len(engine.restrained_processes) == 0

def test_probalance_triggers_restraint_on_high_cpu(pb_config):
    engine = ProBalanceEngine(pb_config)
    processes = [
        {"pid": 101, "name": "heavy_worker.exe", "cpu_percent": 35.0, "priority": "NORMAL"},
        {"pid": 102, "name": "light_worker.exe", "cpu_percent": 5.0, "priority": "NORMAL"}
    ]
    # System CPU is 75% (above 60%)
    actions = engine.evaluate(system_cpu_percent=75.0, process_snapshots=processes, foreground_pid=None, current_time=100.0)
    assert len(actions) == 1
    act = actions[0]
    assert act["action"] == "RESTRAIN"
    assert act["pid"] == 101
    assert act["target_priority"] == "BELOW_NORMAL"
    assert 101 in engine.restrained_processes

def test_probalance_respects_exclusions_and_foreground(pb_config):
    engine = ProBalanceEngine(pb_config)
    processes = [
        {"pid": 201, "name": "dwm.exe", "cpu_percent": 40.0, "priority": "HIGH"},
        {"pid": 202, "name": "game.exe", "cpu_percent": 50.0, "priority": "HIGH"}
    ]
    # 201 is excluded by name, 202 is the foreground window PID
    actions = engine.evaluate(system_cpu_percent=85.0, process_snapshots=processes, foreground_pid=202, current_time=100.0)
    assert len(actions) == 0
    assert len(engine.restrained_processes) == 0

def test_probalance_restoration_cycle(pb_config):
    engine = ProBalanceEngine(pb_config)
    processes = [
        {"pid": 301, "name": "converter.exe", "cpu_percent": 45.0, "priority": "NORMAL"}
    ]

    # Trigger restraint at t = 1000.0
    actions_1 = engine.evaluate(system_cpu_percent=70.0, process_snapshots=processes, foreground_pid=None, current_time=1000.0)
    assert len(actions_1) == 1
    assert actions_1[0]["action"] == "RESTRAIN"

    # At t = 1002.0 (elapsed 2s < 5s duration), even if system CPU dropped to 20%, restraint remains
    actions_2 = engine.evaluate(system_cpu_percent=20.0, process_snapshots=processes, foreground_pid=None, current_time=1002.0)
    assert len(actions_2) == 0
    assert 301 in engine.restrained_processes

    # At t = 1006.0 (elapsed 6s > 5s duration) AND system CPU is 20% (< 40% recovery), restore occurs
    actions_3 = engine.evaluate(system_cpu_percent=20.0, process_snapshots=processes, foreground_pid=None, current_time=1006.0)
    assert len(actions_3) == 1
    assert actions_3[0]["action"] == "RESTORE"
    assert actions_3[0]["pid"] == 301
    assert actions_3[0]["target_priority"] == "NORMAL"
    assert 301 not in engine.restrained_processes
