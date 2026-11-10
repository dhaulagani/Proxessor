import pytest
from src.proxessor.gui.tray import create_default_tray_image, SystemTrayManager

def test_tray_image_creation():
    img = create_default_tray_image(64)
    assert img is not None
    assert img.size == (64, 64)
    assert img.mode == "RGBA"

def test_tray_manager_initialization():
    called = []
    manager = SystemTrayManager(
        on_show=lambda: called.append("show"),
        on_exit=lambda: called.append("exit"),
        on_smart_trim=lambda: called.append("trim")
    )
    assert manager is not None
    assert manager.is_running is False
    assert manager.image is not None

    menu = manager._create_menu()
    assert menu is not None
