"""Memoria de longo prazo - fatos persistentes injetados no system prompt."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _file() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    base.mkdir(parents=True, exist_ok=True)
    return base / "memory.json"


def _load() -> list[dict]:
    p = _file()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    _file().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_facts() -> list[dict]:
    return _load()


def add_fact(text: str, category: str = "geral") -> dict:
    items = _load()
    new_id = (max((f.get("id", 0) for f in items), default=0) + 1) if items else 1
    item = {"id": new_id, "text": text.strip(), "category": category}
    items.append(item)
    _save(items)
    return item


def remove_fact(fact_id: int) -> None:
    items = [f for f in _load() if f.get("id") != fact_id]
    _save(items)


def render_for_prompt() -> str:
    facts = _load()
    if not facts:
        return ""
    by_cat: dict[str, list[str]] = {}
    for f in facts:
        by_cat.setdefault(f.get("category") or "geral", []).append(f.get("text", ""))
    lines = ["", "### Memoria persistente (fatos sobre o usuario)"]
    for cat in sorted(by_cat):
        lines.append(f"\n**{cat}**")
        for t in by_cat[cat]:
            lines.append(f"- {t}")
    return "\n".join(lines)
