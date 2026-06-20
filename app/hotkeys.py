"""Atalhos globais do SERVUS via keyboard library.

- Ctrl+Shift+Espaco  -> mostra/foca a janela
- Alt+Espaco         -> push-to-talk (hold)
- Ctrl+Shift+V       -> captura tela e prepara pra proxima mensagem
"""

from __future__ import annotations

import threading
from typing import Callable

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False


class Hotkeys:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_ptt_start: Callable[[], None],
        on_ptt_end: Callable[[], None],
        on_capture_screen: Callable[[], None],
    ):
        self.on_show = on_show
        self.on_ptt_start = on_ptt_start
        self.on_ptt_end = on_ptt_end
        self.on_capture_screen = on_capture_screen
        self._ptt_active = False

    def start(self):
        if not HAS_KEYBOARD:
            return
        def _go():
            try:
                keyboard.add_hotkey("ctrl+shift+space", self.on_show)
                keyboard.add_hotkey("ctrl+shift+v", self.on_capture_screen)
                # PTT - usa on_press/release
                keyboard.on_press_key("alt", self._ptt_key)
                # alternativa mais robusta: monitora combo Alt+Space
                keyboard.add_hotkey("alt+space", self._ptt_toggle, suppress=False)
            except Exception as e:
                print(f"hotkeys: {e}")
        threading.Thread(target=_go, daemon=True).start()

    def _ptt_key(self, ev):
        # nao usado por padrao - mantem stub
        pass

    def _ptt_toggle(self):
        # cada press de Alt+Space alterna start/stop
        if not self._ptt_active:
            self._ptt_active = True
            self.on_ptt_start()
        else:
            self._ptt_active = False
            self.on_ptt_end()

    def stop(self):
        if HAS_KEYBOARD:
            try: keyboard.unhook_all()
            except Exception: pass
