"""Auto-compressao de contexto quando a conversa fica muito longa.

Quando o numero de mensagens (ou tokens estimados) passa do limite, condensa
as mensagens antigas em um resumo e mantem so as ultimas N.
"""

from __future__ import annotations

# Limiar simples por mensagens (mais robusto que estimativa de tokens)
MAX_MESSAGES = 30
KEEP_RECENT = 10


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def maybe_compress(interpreter) -> bool:
    msgs = getattr(interpreter, "messages", None) or []
    if len(msgs) <= MAX_MESSAGES:
        return False

    # divide: antigas (compactar) + recentes (manter)
    old = msgs[:-KEEP_RECENT]
    recent = msgs[-KEEP_RECENT:]

    # so resume se ha conteudo de message (nao so code/console)
    text_parts = []
    for m in old:
        if not isinstance(m, dict): continue
        if m.get("type") == "message" and m.get("content"):
            role = m.get("role", "?")
            text_parts.append(f"{role}: {m['content'][:500]}")
    if not text_parts:
        return False

    raw = "\n".join(text_parts)
    if _est_tokens(raw) < 1500:
        return False

    # Tenta resumir via o proprio interpreter (modelo configurado)
    try:
        summary = _summarize(interpreter, raw)
    except Exception:
        # fallback: trunca textualmente
        summary = raw[:2000] + "\n[...resto removido por contexto]"

    interpreter.messages = [
        {
            "role": "user", "type": "message",
            "content": f"[Resumo das mensagens anteriores]: {summary}",
        }
    ] + recent
    return True


def _summarize(interpreter, text: str) -> str:
    """Chama LiteLLM diretamente pra evitar mexer com o estado do interpreter."""
    import litellm
    model = interpreter.llm.model
    prompt = (
        "Resuma a conversa abaixo em ate 8 bullets curtos. "
        "Foque em: decisoes tomadas, fatos descobertos, tarefas em andamento, "
        "preferencias do usuario. Em portugues.\n\n" + text[:8000]
    )
    r = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.2,
    )
    return r["choices"][0]["message"]["content"].strip()
