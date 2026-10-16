"""Entry point: python frontend/main.py"""
import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk  # noqa: E402

from app import HRMSApp  # noqa: E402
from core.state import state  # noqa: E402
from ui import theme  # noqa: E402


def main() -> None:
    if sys.platform == "win32":
        try:  # crisp rendering on HiDPI displays
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    state.load_preferences()  # language, theme, accent and scaling chosen on this computer
    ctk.set_appearance_mode(state.theme)
    ctk.set_default_color_theme("blue")
    theme.apply_accent(state.accent)
    theme.load_bundled_fonts()  # Khmer font
    ctk.set_widget_scaling(state.scaling)
    HRMSApp().mainloop()


if __name__ == "__main__":
    main()
