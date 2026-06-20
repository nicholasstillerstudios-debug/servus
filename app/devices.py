"""Integracao com dispositivos eletronicos (Home Assistant por enquanto).

O Home Assistant cobre milhares de dispositivos (Tuya, Hue, Sonos, TVs,
fechaduras, ACs, persianas, etc). Aqui:
- Validamos credenciais
- Listamos entidades controlaveis
- Geramos o trecho de system prompt que ensina o LLM a aciona-las
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


# Dominios que valem a pena expor ao LLM (controlaveis)
USEFUL_DOMAINS = {
    "light", "switch", "cover", "climate", "media_player",
    "fan", "lock", "scene", "script", "input_boolean",
    "vacuum", "humidifier", "siren", "button",
}


@dataclass
class HAStatus:
    ok: bool
    version: str = ""
    error: str = ""
    entity_count: int = 0
    sample: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


def _client(url: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=url.rstrip("/"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=8,
    )


def test_connection(url: str, token: str) -> HAStatus:
    if not url or not token:
        return HAStatus(ok=False, error="URL ou token vazios")
    try:
        with _client(url, token) as c:
            r = c.get("/api/")
            r.raise_for_status()
            info = r.json()
            r2 = c.get("/api/states")
            r2.raise_for_status()
            states = r2.json()
        useful = [s for s in states if s.get("entity_id", "").split(".")[0] in USEFUL_DOMAINS]
        sample = []
        for s in useful[:6]:
            name = s.get("attributes", {}).get("friendly_name", s.get("entity_id"))
            sample.append(f"{s.get('entity_id')} ({name})")
        return HAStatus(
            ok=True,
            version=str(info.get("version", "?")),
            entity_count=len(useful),
            sample=sample,
        )
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code}"
        if e.response.status_code == 401:
            msg += " (token invalido)"
        return HAStatus(ok=False, error=msg)
    except Exception as e:
        return HAStatus(ok=False, error=str(e))


def list_entities(url: str, token: str) -> list[dict]:
    """Retorna entidades controlaveis com {entity_id, name, state, domain}."""
    try:
        with _client(url, token) as c:
            r = c.get("/api/states")
            r.raise_for_status()
            states = r.json()
    except Exception:
        return []
    out = []
    for s in states:
        eid = s.get("entity_id", "")
        dom = eid.split(".")[0]
        if dom not in USEFUL_DOMAINS:
            continue
        out.append({
            "entity_id": eid,
            "domain": dom,
            "name": s.get("attributes", {}).get("friendly_name", eid),
            "state": s.get("state", ""),
        })
    return sorted(out, key=lambda e: (e["domain"], e["name"]))


def apply_env(cfg: dict) -> None:
    """Expoe URL e token via env vars (pra Open Interpreter ler sem expor no prompt)."""
    dev = cfg.get("devices") or {}
    if dev.get("provider") == "home_assistant" and dev.get("ha_url") and dev.get("ha_token"):
        os.environ["HA_URL"] = dev["ha_url"]
        os.environ["HA_TOKEN"] = dev["ha_token"]
    else:
        os.environ.pop("HA_URL", None)
        os.environ.pop("HA_TOKEN", None)


def render_for_prompt(cfg: dict, max_entities: int = 60) -> str:
    """Trecho a injetar no system_message com entidades + helper de codigo."""
    dev = cfg.get("devices") or {}
    if dev.get("provider") != "home_assistant":
        return ""
    url = dev.get("ha_url", "")
    tok = dev.get("ha_token", "")
    if not url or not tok:
        return ""

    entities = list_entities(url, tok)
    if not entities:
        return ""

    # agrupa por dominio
    by_dom: dict[str, list[dict]] = {}
    for e in entities[:max_entities]:
        by_dom.setdefault(e["domain"], []).append(e)

    lines = ["", "### Dispositivos (Home Assistant)"]
    lines.append(
        "Voce pode controlar os dispositivos abaixo. URL e token estao em "
        "os.environ['HA_URL'] e os.environ['HA_TOKEN']. Para acionar:"
    )
    lines.append("```python")
    lines.append("import httpx, os")
    lines.append("def ha(service, entity, **data):")
    lines.append("    domain, svc = service.split('/')")
    lines.append("    r = httpx.post(")
    lines.append("        f\"{os.environ['HA_URL']}/api/services/{domain}/{svc}\",")
    lines.append("        headers={'Authorization': f\"Bearer {os.environ['HA_TOKEN']}\"},")
    lines.append("        json={'entity_id': entity, **data}, timeout=10)")
    lines.append("    return r.json()")
    lines.append("# exemplos:")
    lines.append("# ha('light/turn_on', 'light.sala', brightness=200)")
    lines.append("# ha('switch/turn_off', 'switch.tomada')")
    lines.append("# ha('cover/open_cover', 'cover.persiana')")
    lines.append("# ha('climate/set_temperature', 'climate.ar', temperature=22)")
    lines.append("```")
    lines.append("")
    lines.append("Entidades disponiveis (use o entity_id exato):")
    for dom in sorted(by_dom):
        lines.append(f"\n**{dom}**")
        for e in by_dom[dom]:
            lines.append(f"- `{e['entity_id']}` - {e['name']} (estado: {e['state']})")

    if len(entities) > max_entities:
        lines.append(f"\n_... mais {len(entities) - max_entities} entidades (filtradas para economizar contexto)_")

    return "\n".join(lines)


__all__ = ["HAStatus", "test_connection", "list_entities", "apply_env", "render_for_prompt"]
