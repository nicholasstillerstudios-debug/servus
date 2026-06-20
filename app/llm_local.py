"""Deteccao do Ollama local + listagem de modelos."""

from __future__ import annotations

import httpx


DEFAULT_BASE = "http://localhost:11434"


def status(base: str = DEFAULT_BASE) -> dict:
    try:
        r = httpx.get(f"{base.rstrip('/')}/api/tags", timeout=2)
        if r.status_code != 200:
            return {"running": False, "models": []}
        data = r.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "name": m.get("name", ""),
                "size_gb": round((m.get("size", 0) or 0) / 1e9, 2),
                "modified": m.get("modified_at", ""),
            })
        return {"running": True, "models": models, "base": base}
    except Exception as e:
        return {"running": False, "models": [], "error": str(e)}
