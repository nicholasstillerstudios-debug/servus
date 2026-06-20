"""Chromecast/DLNA via pychromecast."""

from __future__ import annotations

import threading

try:
    import pychromecast
    HAS_CAST = True
except Exception:
    HAS_CAST = False


def list_devices(timeout: float = 5.0) -> list[dict]:
    if not HAS_CAST:
        return []
    try:
        casts, browser = pychromecast.get_chromecasts(timeout=timeout)
        out = [{"name": c.cast_info.friendly_name, "host": c.cast_info.host, "model": c.cast_info.model_name} for c in casts]
        try: browser.stop_discovery()
        except Exception: pass
        return out
    except Exception:
        return []


def cast_url(device_name: str, url: str, content_type: str = "video/mp4") -> dict:
    if not HAS_CAST:
        return {"ok": False, "error": "pychromecast indisponivel"}
    try:
        casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[device_name])
        if not casts:
            try: browser.stop_discovery()
            except Exception: pass
            return {"ok": False, "error": f"Dispositivo nao encontrado: {device_name}"}
        cc = casts[0]
        cc.wait()
        mc = cc.media_controller
        mc.play_media(url, content_type)
        mc.block_until_active(timeout=10)
        try: browser.stop_discovery()
        except Exception: pass
        return {"ok": True, "device": device_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def render_for_prompt(cfg: dict) -> str:
    return (
        "\n\n### Chromecast / Cast\n"
        "Para listar e casting via app.cast:\n"
        "```python\n"
        "from app.cast import list_devices, cast_url\n"
        "list_devices()\n"
        "cast_url('TV da Sala', 'https://exemplo.com/video.mp4')\n"
        "```\n"
    )
