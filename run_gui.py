"""Proxessor GUI Desktop Entrypoint.
Ensures root directory is placed at the front of sys.path and launches the cockpit dashboard.
"""

import os
import sys

# Guarantee repository root is always in Python module lookup path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from src.proxessor.gui.app import launch_gui
    launch_gui()
except Exception as e:
    import traceback
    err_msg = traceback.format_exc()
    log_file = os.path.join(ROOT_DIR, "proxessor_gui_error.log")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(err_msg)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Error launching Proxessor GUI:\n\n{e}\n\nSee {log_file} for full details.", "Proxessor Launch Error", 0x10)
    except Exception:
        pass
    sys.exit(1)
