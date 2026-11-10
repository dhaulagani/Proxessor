"""System Tray integration for Proxessor.
Manages the Windows notification area icon, tooltip telemetry, and quick-action context menu.
"""

import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item, Menu

def create_default_tray_image(size: int = 64) -> Image.Image:
    """Generates a crisp bespoke tray icon for Proxessor.
    Dark cockpit background with Emerald P logo and Sky-blue accent ring.
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Outer circle / ring (Emerald Accent)
    draw.ellipse([4, 4, size - 5, size - 5], fill=(18, 22, 32, 255), outline=(16, 185, 129, 255), width=3)

    # Inner emblem "P"
    # Vertical stem
    draw.rectangle([20, 16, 26, 48], fill=(248, 250, 252, 255))
    # Top loop
    draw.rounded_rectangle([24, 16, 44, 34], radius=6, fill=(16, 185, 129, 255))
    # Cutout inside loop
    draw.rounded_rectangle([27, 21, 38, 29], radius=3, fill=(18, 22, 32, 255))

    return image

class SystemTrayManager:
    """Manages the lifecycle, background thread, and menu events of the system tray icon."""

    def __init__(
        self,
        on_show: Callable[[], None],
        on_exit: Callable[[], None],
        on_smart_trim: Optional[Callable[[], None]] = None,
        on_power_change: Optional[Callable[[str], None]] = None,
        icon_path: Optional[str] = None
    ):
        self.on_show = on_show
        self.on_exit = on_exit
        self.on_smart_trim = on_smart_trim
        self.on_power_change = on_power_change

        self.image = self._load_or_create_image(icon_path)
        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

    def _load_or_create_image(self, icon_path: Optional[str]) -> Image.Image:
        if icon_path:
            try:
                return Image.open(icon_path)
            except Exception:
                pass
        return create_default_tray_image()

    def _create_menu(self) -> Menu:
        menu_items = [
            item("Open Proxessor", self._handle_show, default=True),
            item("SmartTrim RAM Now", self._handle_trim),
            Menu.SEPARATOR,
            item(
                "Power Plan",
                Menu(
                    item("High Performance", lambda: self._handle_power("HIGH_PERFORMANCE")),
                    item("Balanced", lambda: self._handle_power("BALANCED")),
                    item("Ultimate Performance", lambda: self._handle_power("ULTIMATE_PERFORMANCE")),
                    item("Power Saver", lambda: self._handle_power("POWER_SAVER")),
                )
            ),
            Menu.SEPARATOR,
            item("Exit Proxessor", self._handle_exit)
        ]
        return Menu(*menu_items)

    def start(self):
        """Starts the system tray icon in a dedicated daemon thread."""
        if self.is_running:
            return

        self.is_running = True
        self.icon = pystray.Icon(
            name="Proxessor",
            icon=self.image,
            title="Proxessor Process Governor\nProBalance: Active",
            menu=self._create_menu()
        )

        def runner():
            try:
                self.icon.run()
            except Exception:
                pass

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def stop(self):
        """Removes the system tray icon and terminates the tray thread."""
        self.is_running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def update_tooltip(self, cpu_pct: float, ram_pct: float, restrained_count: int = 0):
        """Updates the hover tooltip text on the tray icon."""
        if not self.icon or not self.is_running:
            return
        status = f"Restraining ({restrained_count})" if restrained_count > 0 else "Active"
        tip = f"Proxessor Governor\nCPU: {cpu_pct:.1f}% | RAM: {ram_pct:.1f}%\nProBalance: {status}"
        try:
            self.icon.title = tip
        except Exception:
            pass

    def notify(self, title: str, message: str):
        """Displays a native Windows toast/balloon notification from the tray icon."""
        if self.icon and self.is_running:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def _handle_show(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _handle_trim(self, icon=None, item=None):
        if self.on_smart_trim:
            self.on_smart_trim()

    def _handle_power(self, plan: str):
        if self.on_power_change:
            self.on_power_change(plan)

    def _handle_exit(self, icon=None, item=None):
        self.stop()
        if self.on_exit:
            self.on_exit()
