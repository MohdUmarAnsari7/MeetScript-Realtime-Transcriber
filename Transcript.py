import sys
# Set COM apartment model to STA (Single-Threaded Apartment) before any library loads COM.
# Windows Shell dialogs (like filedialog.askdirectory) REQUIRE STA, otherwise they hang indefinitely.
sys.coinit_flags = 2

import ctypes
try:
    # Explicitly initialize the main thread as STA.
    ctypes.windll.ole32.OleInitialize(None)
except Exception:
    pass

import os
import subprocess
import threading


def set_bypass_execution_policy():
    """Run Set-ExecutionPolicy Bypass silently in the background to prevent policy blockers."""
    def _run():
        try:
            cmd = (
                "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; "
                "Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force"
            )
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
                capture_output=True,
                creationflags=creationflags,
                check=False
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


# Ensure the current directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import customtkinter as ctk
from ui import App


def main():
    set_bypass_execution_policy()
    app_root = ctk.CTk()
    app = App(app_root)
    app_root.mainloop()


if __name__ == "__main__":
    main()
