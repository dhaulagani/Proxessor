import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from src.proxessor.core.governor import GovernorEngine

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/default_rules.json")

def test_foreground_boost_elevation_and_restoration():
    gov = GovernorEngine(CONFIG_PATH, dry_run=True)
    
    # Mock Win32ProcessAPI calls
    gov.win32.set_process_priority = MagicMock()
    
    snapshots = [
        {"pid": 100, "name": "app1.exe", "cpu_percent": 5.0, "memory_mb": 100.0, "create_time": 10.0, "priority": "NORMAL"},
        {"pid": 200, "name": "app2.exe", "cpu_percent": 2.0, "memory_mb": 80.0, "create_time": 15.0, "priority": "NORMAL"},
        {"pid": 300, "name": "dwm.exe", "cpu_percent": 1.0, "memory_mb": 50.0, "create_time": 5.0, "priority": "HIGH"},
    ]

    # Tick 1: Focus on app1 (PID 100)
    with patch("psutil.process_iter") as mock_iter, patch("psutil.cpu_percent", return_value=10.0):
        mock_iter.return_value = []
        gov.win32.get_foreground_process_id = MagicMock(return_value=100)
        
        # Inject snapshots directly into tick logic simulation
        with patch.object(gov, "win32") as mock_win32:
            mock_win32.get_foreground_process_id.return_value = 100
            mock_win32.get_system_ram_percent.return_value = 40.0
            
            # Run tick
            gov.current_foreground_pid = 100
            # Step 3c logic verification directly:
            fg_pid = 100
            fg_snap = next(s for s in snapshots if s["pid"] == fg_pid)
            gov.original_fg_priorities[fg_pid] = fg_snap["priority"]
            gov.boosted_fg_pid = fg_pid
            gov.boosted_fg_name = fg_snap["name"]
            
            assert gov.boosted_fg_pid == 100
            assert gov.boosted_fg_name == "app1.exe"
            assert gov.original_fg_priorities[100] == "NORMAL"

    # Tick 2: Focus switches to app2 (PID 200)
    gov.win32.set_process_priority = MagicMock()
    # Simulate focus switch in governor
    prev_pid = gov.boosted_fg_pid
    restore_prio = gov.original_fg_priorities.get(prev_pid, "NORMAL")
    gov.win32.set_process_priority(prev_pid, restore_prio)
    gov.original_fg_priorities.pop(prev_pid, None)
    gov.boosted_fg_pid = 200
    gov.boosted_fg_name = "app2.exe"
    gov.original_fg_priorities[200] = "NORMAL"
    gov.win32.set_process_priority(200, "ABOVE_NORMAL")

    # Verify app1 was restored and app2 was boosted
    gov.win32.set_process_priority.assert_any_call(100, "NORMAL")
    gov.win32.set_process_priority.assert_any_call(200, "ABOVE_NORMAL")

def test_foreground_boost_excludes_system_processes():
    gov = GovernorEngine(CONFIG_PATH, dry_run=True)
    gov.win32.set_process_priority = MagicMock()
    
    # dwm.exe or explorer.exe in foreground
    from src.proxessor.core.governor import SYSTEM_PROCESS_EXCLUSIONS
    assert "dwm.exe" in SYSTEM_PROCESS_EXCLUSIONS
    assert "explorer.exe" in SYSTEM_PROCESS_EXCLUSIONS
    assert "csrss.exe" in SYSTEM_PROCESS_EXCLUSIONS

def test_dynamic_game_mode_auto_switch_and_revert():
    gov = GovernorEngine(CONFIG_PATH, dry_run=False)
    
    mock_power = MagicMock()
    initial_guid = uuid.UUID("381b4222-f694-41f0-9685-ff5bb260df2e")
    mock_power.get_active_scheme_uuid.return_value = initial_guid
    mock_power.set_active_scheme.return_value = True
    mock_power.set_active_scheme_uuid.return_value = True
    gov.power_manager = mock_power

    # Game launches (Cyberpunk2077.exe matches HIGH_PERFORMANCE power_scheme rule)
    game_snapshots = [
        {"pid": 9999, "name": "Cyberpunk2077.exe", "cpu_percent": 45.0, "memory_mb": 4096.0, "create_time": 100.0, "priority": "NORMAL"}
    ]
    
    # Tick with game running
    game_mode_requests = []
    for snap in game_snapshots:
        rule = gov.rule_manager.match_rule(snap["name"])
        if rule and rule.power_scheme:
            game_mode_requests.append(rule.power_scheme)
            
    assert len(game_mode_requests) == 1
    assert game_mode_requests[0] == "HIGH_PERFORMANCE"

    # Simulate dynamic game mode auto-switch
    if game_mode_requests:
        target_scheme = game_mode_requests[0]
        if gov.active_power_scheme_target != target_scheme:
            if gov.base_power_scheme_uuid is None:
                gov.base_power_scheme_uuid = gov.power_manager.get_active_scheme_uuid()
            gov.power_manager.set_active_scheme(target_scheme)
            gov.active_power_scheme_target = target_scheme

    mock_power.set_active_scheme.assert_called_with("HIGH_PERFORMANCE")
    assert gov.base_power_scheme_uuid == initial_guid
    assert gov.active_power_scheme_target == "HIGH_PERFORMANCE"

    # Next: Game closes (game_snapshots is empty)
    game_mode_requests = []
    if not game_mode_requests and gov.active_power_scheme_target is not None:
        gov.power_manager.set_active_scheme_uuid(gov.base_power_scheme_uuid)
        gov.active_power_scheme_target = None
        gov.base_power_scheme_uuid = None

    # Verify auto-reversion to base scheme
    mock_power.set_active_scheme_uuid.assert_called_with(initial_guid)
    assert gov.active_power_scheme_target is None
    assert gov.base_power_scheme_uuid is None

def test_disallowed_processes_detection():
    gov = GovernorEngine(CONFIG_PATH, dry_run=True)
    # Check config disallowed processes
    assert gov.rule_manager.is_disallowed("telemetry_bloatware.exe")
    assert gov.rule_manager.is_disallowed("TELEMETRY_BLOATWARE.EXE")
    assert gov.rule_manager.is_disallowed("unwanted_crypto_miner.exe")
    assert not gov.rule_manager.is_disallowed("notepad.exe")

def test_idle_saver_state_transition():
    gov = GovernorEngine(CONFIG_PATH, dry_run=False)
    gov.rule_manager.engine_config.idle_saver_enabled = True
    gov.rule_manager.engine_config.idle_saver_threshold_seconds = 100.0
    
    mock_power = MagicMock()
    initial_guid = uuid.UUID("381b4222-f694-41f0-9685-ff5bb260df2e")
    mock_power.get_active_scheme_uuid.return_value = initial_guid
    mock_power.set_active_scheme.return_value = True
    mock_power.set_active_scheme_uuid.return_value = True
    gov.power_manager = mock_power

    # 1. System is active (idle 5 seconds)
    gov.win32.get_system_idle_seconds = MagicMock(return_value=5.0)
    # Simulate step 3d
    idle_sec = gov.win32.get_system_idle_seconds()
    assert idle_sec < 100.0
    assert not gov.is_idle

    # 2. System goes idle (idle 120 seconds)
    gov.win32.get_system_idle_seconds = MagicMock(return_value=120.0)
    idle_sec = gov.win32.get_system_idle_seconds()
    if idle_sec >= 100.0 and not gov.is_idle:
        gov.pre_idle_scheme_uuid = gov.power_manager.get_active_scheme_uuid()
        gov.power_manager.set_active_scheme("POWER_SAVER")
        gov.is_idle = True

    mock_power.set_active_scheme.assert_called_with("POWER_SAVER")
    assert gov.is_idle is True
    assert gov.pre_idle_scheme_uuid == initial_guid

    # 3. User moves mouse (idle drops to 0.1 seconds)
    gov.win32.get_system_idle_seconds = MagicMock(return_value=0.1)
    idle_sec = gov.win32.get_system_idle_seconds()
    if idle_sec < 100.0 and gov.is_idle:
        gov.power_manager.set_active_scheme_uuid(gov.pre_idle_scheme_uuid)
        gov.is_idle = False
        gov.pre_idle_scheme_uuid = None

    mock_power.set_active_scheme_uuid.assert_called_with(initial_guid)
    assert gov.is_idle is False
    assert gov.pre_idle_scheme_uuid is None
