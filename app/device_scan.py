"""Scanner periodico de dispositivos (BLE + Chromecast + HA).

Detecta dispositivos NOVOS (nunca vistos) e notifica callback.
Dispositivos podem ser dispensados pra nao incomodar de novo.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Callable


def _state_file() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    base.mkdir(parents=True, exist_ok=True)
    return base / "device_scan_state.json"


def _load_state() -> dict:
    p = _state_file()
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    return {"seen": [], "dismissed": []}


def _save_state(s: dict) -> None:
    _state_file().write_text(json.dumps(s, indent=2), encoding="utf-8")


def dismiss(key: str) -> None:
    s = _load_state()
    if key not in s["dismissed"]:
        s["dismissed"].append(key)
        _save_state(s)


class DeviceScanner:
    def __init__(
        self,
        on_new_device: Callable[[dict], None],
        interval_min: float = 10.0,
        scan_ble: bool = True,
        scan_cast: bool = True,
    ):
        self.on_new_device = on_new_device
        self.interval = interval_min * 60
        self.scan_ble = scan_ble
        self.scan_cast = scan_cast
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        # primeira scan apos 45s (deixa app iniciar) - depois no intervalo
        if self._stop.wait(45): return
        while not self._stop.is_set():
            try: self._scan_once()
            except Exception: pass
            # dorme em intervalos curtos pra responder a stop()
            for _ in range(int(self.interval / 5)):
                if self._stop.wait(5): return

    def _scan_once(self):
        state = _load_state()
        seen = set(state.get("seen", []))
        dismissed = set(state.get("dismissed", []))
        new_devices = []

        # ----- BLE -----
        if self.scan_ble:
            try:
                from app import bluetooth as bt
                for d in bt.scan(timeout=4.0):
                    key = f"ble:{d.address}"
                    if key in seen or key in dismissed: continue
                    seen.add(key)
                    new_devices.append({
                        "key": key, "type": "bluetooth",
                        "name": d.name, "address": d.address,
                    })
            except Exception:
                pass

        # ----- Chromecast -----
        if self.scan_cast:
            try:
                from app import cast
                for d in cast.list_devices(timeout=4.0):
                    key = f"cast:{d['host']}"
                    if key in seen or key in dismissed: continue
                    seen.add(key)
                    new_devices.append({
                        "key": key, "type": "cast",
                        "name": d["name"], "address": d["host"],
                        "model": d.get("model", ""),
                    })
            except Exception:
                pass

        state["seen"] = list(seen)
        _save_state(state)

        for d in new_devices:
            try: self.on_new_device(d)
            except Exception: pass
