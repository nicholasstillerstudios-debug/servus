"""Captura de tela pra Vision API (Claude/GPT-4o).

Fluxo: usuario aperta Ctrl+Shift+V -> captura tela -> salva em %TEMP% ->
proxima mensagem do usuario inclui essa imagem no prompt do interpreter.
"""

from __future__ import annotations

import base64
import os
import tempfile
import time
from pathlib import Path

try:
    import mss
    HAS_MSS = True
except Exception:
    HAS_MSS = False


def capture_screen() -> Path | None:
    """Captura monitor principal e salva em %TEMP%. Retorna o path."""
    if not HAS_MSS:
        return None
    out = Path(tempfile.gettempdir()) / f"servus_screen_{int(time.time())}.png"
    try:
        with mss.mss() as sct:
            # monitor 1 = monitor principal (monitor 0 = todos)
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            mss.tools.to_png(shot.rgb, shot.size, output=str(out))
        return out
    except Exception:
        return None


def file_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
