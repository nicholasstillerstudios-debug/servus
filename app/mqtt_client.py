"""MQTT direto (sem Home Assistant). Para dispositivos Tuya custom, ESP32, etc."""

from __future__ import annotations

import threading
import time

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except Exception:
    HAS_MQTT = False


_client = None
_lock = threading.Lock()


def configure(host: str, port: int = 1883, username: str = "", password: str = "") -> dict:
    global _client
    if not HAS_MQTT:
        return {"ok": False, "error": "paho-mqtt nao disponivel"}
    with _lock:
        try:
            if _client:
                try: _client.disconnect()
                except Exception: pass
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if username:
                c.username_pw_set(username, password)
            c.connect(host, int(port), keepalive=30)
            c.loop_start()
            _client = c
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def publish(topic: str, payload: str, retain: bool = False) -> dict:
    if not _client:
        return {"ok": False, "error": "MQTT nao configurado"}
    try:
        info = _client.publish(topic, payload, retain=retain)
        return {"ok": info.rc == 0, "rc": info.rc}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def render_for_prompt(cfg: dict) -> str:
    m = cfg.get("mqtt") or {}
    if not m.get("host"):
        return ""
    return (
        "\n\n### MQTT\n"
        f"Broker: {m.get('host')}:{m.get('port', 1883)}\n"
        "Use a Api do SERVUS via Python:\n"
        "```python\n"
        "from app.mqtt_client import publish\n"
        "publish('home/luz/sala', 'ON')\n"
        "```\n"
    )
