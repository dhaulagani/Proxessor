import pytest
from src.proxessor.gui.controller import GUIController

def test_gui_controller_initialization():
    controller = GUIController(config_path="config/default_rules.json")
    assert controller is not None
    assert controller.win32 is not None
    assert controller.topology is not None

def test_gui_controller_snapshot_collection():
    controller = GUIController(config_path="config/default_rules.json")
    state = controller.refresh_state()
    assert "system_cpu" in state
    assert "system_ram" in state
    assert "processes" in state
    assert isinstance(state["processes"], list)
    assert len(state["processes"]) > 0

def test_gui_controller_filtering():
    controller = GUIController(config_path="config/default_rules.json")
    controller.refresh_state()
    # Filter with known system process or blank
    filtered_all = controller.get_filtered_processes("")
    assert len(filtered_all) > 0

    filtered_python = controller.get_filtered_processes("python")
    assert all("python" in p["name"].lower() for p in filtered_python)
