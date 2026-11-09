import pytest
import os
from src.proxessor.rules.manager import RuleManager
from src.proxessor.core.watchdog import WatchdogEngine

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/default_rules.json")

def test_rule_manager_loads():
    rm = RuleManager(CONFIG_PATH)
    assert len(rm.rules) > 0
    assert rm.engine_config.poll_interval_ms >= 500
    assert rm.probalance_config.get("enabled") is True

def test_rule_matching():
    rm = RuleManager(CONFIG_PATH)

    # Test gaming rule match
    game_rule = rm.match_rule("Cyberpunk2077.exe")
    assert game_rule is not None
    assert game_rule.priority == "HIGH"
    assert game_rule.cpu_affinity == "P_CORES"

    # Test browser rule match
    browser_rule = rm.match_rule("chrome.exe")
    assert browser_rule is not None
    assert browser_rule.power_throttling_eco_qos is True

    # Test unknown app
    no_rule = rm.match_rule("notepad.exe")
    assert no_rule is None

def test_watchdog_instance_limit():
    watchdogs_config = [
        {
            "name": "Limit Spotify",
            "pattern": "(?i)spotify\\.exe",
            "max_instances": 1,
            "action": "TERMINATE_NEWEST"
        }
    ]
    wd = WatchdogEngine(watchdogs_config)
    processes = [
        {"pid": 10, "name": "spotify.exe", "create_time": 100.0},
        {"pid": 11, "name": "spotify.exe", "create_time": 120.0}
    ]
    actions = wd.evaluate(processes)
    assert len(actions) == 1
    assert actions[0]["pid"] == 11
    assert actions[0]["action"] == "TERMINATE_NEWEST"
