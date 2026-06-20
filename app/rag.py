"""RAG simples sobre uma pasta de documentos.

Pipeline:
1. Index: percorre pasta -> chunks (~800 tokens) -> embedding -> SQLite
2. Query: embed pergunta -> cosine sim com todos os chunks -> top-K
3. Inject: top-K na proxima mensagem do usuario

Embeddings: tenta Ollama nomic-embed-text (local, gratis). Fallback Anthropic.
Modelos sao baixados/pagos sob demanda - nada bundlado.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path

import httpx


def _db_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    base.mkdir(parents=True, exist_ok=True)
    return base / "rag.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()))
    c.execute("""CREATE TABLE IF NOT EXISTS chunks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        path TEXT NOT NULL,
        chunk_idx INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding TEXT NOT NULL,
        indexed_at REAL NOT NULL
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")
    return c


# ---- embeddings ---------------------------------------------------------

def _embed_ollama(texts: list[str]) -> list[list[float]] | None:
    try:
        out = []
        for t in texts:
            r = httpx.post("http://localhost:11434/api/embeddings",
                           json={"model": "nomic-embed-text", "prompt": t}, timeout=20)
            r.raise_for_status()
            out.append(r.json()["embedding"])
        return out
    except Exception:
        return None


def _embed_openai(texts: list[str]) -> list[list[float]] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key: return None
    try:
        r = httpx.post("https://api.openai.com/v1/embeddings",
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": "text-embedding-3-small", "input": texts},
                       timeout=30)
        r.raise_for_status()
        return [d["embedding"] for d in r.json()["data"]]
    except Exception:
        return None


def embed(texts: list[str]) -> tuple[list[list[float]] | None, str]:
    """Retorna embeddings + nome do provider usado."""
    e = _embed_ollama(texts)
    if e: return e, "ollama:nomic-embed-text"
    e = _embed_openai(texts)
    if e: return e, "openai:text-embedding-3-small"
    return None, "none"


def has_embedder() -> dict:
    if _embed_ollama(["test"]) is not None:
        return {"ok": True, "provider": "ollama:nomic-embed-text"}
    if os.environ.get("OPENAI_API_KEY"):
        return {"ok": True, "provider": "openai:text-embedding-3-small"}
    return {"ok": False, "provider": ""}


# ---- chunking -----------------------------------------------------------

CHUNK_SIZE = 800   # caracteres
CHUNK_OVERLAP = 150


def _read_file(path: Path) -> str:
    """Le texto de arquivos comuns. PDF requer extra - fallback pra ignorar."""
    try:
        if path.suffix.lower() in (".txt", ".md", ".py", ".js", ".ts", ".html",
                                    ".css", ".json", ".yaml", ".yml", ".csv",
                                    ".sql", ".log", ".ini", ".toml"):
            return path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".pdf":
            try:
                import pypdf
                r = pypdf.PdfReader(str(path))
                return "\n".join(p.extract_text() or "" for p in r.pages)
            except Exception:
                return ""
        return ""
    except Exception:
        return ""


def _chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ---- index / query ------------------------------------------------------

def index_folder(folder: str, source: str = "") -> dict:
    folder_p = Path(folder)
    if not folder_p.exists():
        return {"ok": False, "error": "Pasta nao existe"}
    source = source or folder_p.name

    files = []
    for ext in ("*.txt", "*.md", "*.pdf", "*.py", "*.js", "*.ts", "*.html",
                "*.css", "*.json", "*.yaml", "*.yml", "*.csv", "*.sql"):
        files.extend(folder_p.rglob(ext))
    files = [f for f in files if f.stat().st_size < 5_000_000]  # max 5MB por arquivo

    all_chunks = []  # (path, chunk_idx, content)
    for f in files[:200]:  # limite seguranca
        txt = _read_file(f)
        if not txt or len(txt) < 100: continue
        for ci, c in enumerate(_chunk_text(txt)):
            all_chunks.append((str(f), ci, c))

    if not all_chunks:
        return {"ok": False, "error": "Nenhum conteudo legivel"}

    # remove o source antigo
    with _conn() as c:
        c.execute("DELETE FROM chunks WHERE source=?", (source,))

    # embedding em batches
    BATCH = 32
    total = len(all_chunks)
    indexed = 0
    provider = ""
    with _conn() as c:
        for b in range(0, total, BATCH):
            batch = all_chunks[b:b + BATCH]
            texts = [x[2] for x in batch]
            embs, provider = embed(texts)
            if not embs:
                return {"ok": False, "error": "Sem embedder (Ollama ou OPENAI_API_KEY)"}
            for (path, ci, content), emb in zip(batch, embs):
                c.execute(
                    "INSERT INTO chunks(source, path, chunk_idx, content, embedding, indexed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (source, path, ci, content, json.dumps(emb), time.time()),
                )
            indexed += len(batch)
        c.commit()

    return {"ok": True, "indexed": indexed, "files": len(files), "provider": provider}


def list_sources() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT source, COUNT(*), MAX(indexed_at) FROM chunks GROUP BY source"
        ).fetchall()
    return [{"source": r[0], "chunks": r[1], "indexed_at": r[2]} for r in rows]


def remove_source(source: str) -> dict:
    with _conn() as c:
        c.execute("DELETE FROM chunks WHERE source=?", (source,))
        c.commit()
    return {"ok": True}


def _cosine(a: list[float], b: list[float]) -> float:
    s = 0.0; na = 0.0; nb = 0.0
    for x, y in zip(a, b):
        s += x * y; na += x * x; nb += y * y
    if na == 0 or nb == 0: return 0
    return s / ((na ** 0.5) * (nb ** 0.5))


def query(question: str, top_k: int = 5) -> list[dict]:
    embs, _ = embed([question])
    if not embs: return []
    qv = embs[0]
    with _conn() as c:
        rows = c.execute("SELECT path, content, embedding FROM chunks").fetchall()
    scored = []
    for path, content, emb_json in rows:
        emb = json.loads(emb_json)
        scored.append((_cosine(qv, emb), path, content))
    scored.sort(reverse=True)
    return [{"path": p, "snippet": c[:600], "score": round(s, 3)} for s, p, c in scored[:top_k]]


def render_for_prompt() -> str:
    sources = list_sources()
    if not sources:
        return ""
    names = ", ".join(s["source"] for s in sources)
    return (
        "\n\n### Conhecimento local (RAG)\n"
        f"Voce tem acesso a documentos indexados em: {names}.\n"
        "Para consultar use o codigo abaixo:\n"
        "```python\n"
        "from app.rag import query\n"
        "results = query('o que diz sobre X', top_k=5)\n"
        "for r in results:\n"
        "    print(r['path'], r['snippet'])\n"
        "```\n"
    )
