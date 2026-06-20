"""System tray icon do SERVUS."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import pystray
from PIL import Image


def _load_icon() -> Image.Image:
    # tenta achar o icone bundle ou no projeto
    import sys, os
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "assets" / "servus.ico")
    candidates.append(Path(__file__).parent.parent / "assets" / "servus.ico")
    for p in candidates:
        if p.exists():
            try:
                return Image.open(str(p))
            except Exception:
                pass
    # fallback: cria icone simples
    img = Image.new("RGBA", (64, 64), (10, 14, 26, 255))
    return img


class Tray:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle_wake: Callable[[], bool],
        on_quit: Callable[[], None],
        get_wake_state: Callable[[], bool],
    ):
        self.on_show = on_show
        self.on_toggle_wake = on_toggle_wake
        self.on_quit = on_quit
        self.get_wake_state = get_wake_state
        self.icon: pystray.Icon | None = None

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem("Mostrar SERVUS", lambda: self.on_show(), default=True),
            pystray.MenuItem(
                lambda item: f"Sempre escutando: {'ON' if self.get_wake_state() else 'OFF'}",
                lambda: self.on_toggle_wake(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: self._quit()),
        )

    def _quit(self):
        try:
            if self.icon: self.icon.stop()
        except Exception:
            pass
        self.on_quit()

    def run(self):
        def _start():
            self.icon = pystray.Icon("SERVUS", _load_icon(), "SERVUS", self._menu())
            self.icon.run()
        threading.Thread(target=_start, daemon=True).start()

    def stop(self):
        try:
            if self.icon: self.icon.stop()
        except Exception:
            pass
