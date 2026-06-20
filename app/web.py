"""Web search via DuckDuckGo (sem chave de API)."""

from __future__ import annotations


def search(query: str, max_results: int = 5) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]
    except Exception as e:
        return [{"title": "Erro na busca", "url": "", "snippet": str(e)}]


def render_for_prompt() -> str:
    return (
        "\n\n### Web search\n"
        "Voce pode buscar na web via DuckDuckGo:\n"
        "```python\n"
        "from app.web import search  # ou: from duckduckgo_search import DDGS\n"
        "results = search('o que e X', max_results=5)\n"
        "for r in results:\n"
        "    print(r['title'], '-', r['url'])\n"
        "```\n"
    )
