"""Messaging Hub - Email, Telegram, WhatsApp, Webhook.

Tudo via stdlib + httpx (sem deps novas).
"""

from __future__ import annotations

import email
import email.header
import email.message
import imaplib
import json
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx


# ---- contatos & templates -----------------------------------------------

def _data_file(name: str) -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    base.mkdir(parents=True, exist_ok=True)
    return base / name


def _load_json(name: str) -> list:
    p = _data_file(name)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_json(name: str, data: list) -> None:
    _data_file(name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_contacts() -> list[dict]:
    return _load_json("contacts.json")


def add_contact(name: str, phone: str = "", email_addr: str = "", telegram: str = "") -> dict:
    items = list_contacts()
    new_id = max((c.get("id", 0) for c in items), default=0) + 1
    item = {"id": new_id, "name": name.strip(),
            "phone": phone.strip(), "email": email_addr.strip(), "telegram": telegram.strip()}
    items.append(item)
    _save_json("contacts.json", items)
    return item


def remove_contact(contact_id: int) -> None:
    items = [c for c in list_contacts() if c.get("id") != contact_id]
    _save_json("contacts.json", items)


def resolve_contact(name: str) -> dict | None:
    needle = name.lower().strip()
    for c in list_contacts():
        if c.get("name", "").lower() == needle:
            return c
    # parcial
    for c in list_contacts():
        if needle in c.get("name", "").lower():
            return c
    return None


def list_templates() -> list[dict]:
    return _load_json("templates.json")


def add_template(name: str, text: str) -> dict:
    items = list_templates()
    new_id = max((t.get("id", 0) for t in items), default=0) + 1
    item = {"id": new_id, "name": name.strip(), "text": text.strip()}
    items.append(item)
    _save_json("templates.json", items)
    return item


def remove_template(tpl_id: int) -> None:
    items = [t for t in list_templates() if t.get("id") != tpl_id]
    _save_json("templates.json", items)


# ---- Telegram -----------------------------------------------------------

def telegram_send(cfg: dict, text: str, chat_id: str | None = None) -> dict:
    tg = (cfg.get("messaging") or {}).get("telegram") or {}
    token = tg.get("token") or ""
    target = chat_id or tg.get("chat_id") or ""
    if not token or not target:
        return {"ok": False, "error": "Token ou chat_id ausente"}
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": target, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return {"ok": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def telegram_get_updates(cfg: dict, limit: int = 10) -> list[dict]:
    tg = (cfg.get("messaging") or {}).get("telegram") or {}
    token = tg.get("token") or ""
    if not token:
        return []
    try:
        r = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15)
        if r.status_code != 200:
            return []
        result = r.json().get("result", [])
        out = []
        for u in result[-limit:]:
            msg = u.get("message") or u.get("edited_message") or {}
            out.append({
                "from": (msg.get("from") or {}).get("first_name", "?"),
                "chat_id": (msg.get("chat") or {}).get("id"),
                "text": msg.get("text", ""),
                "date": msg.get("date"),
            })
        return out
    except Exception:
        return []


# ---- Email --------------------------------------------------------------

def email_send(cfg: dict, to: str, subject: str, body: str, html: bool = False) -> dict:
    e = (cfg.get("messaging") or {}).get("email") or {}
    host = e.get("smtp_host") or ""
    port = int(e.get("smtp_port") or 587)
    user = e.get("user") or ""
    pwd = e.get("password") or ""
    if not host or not user or not pwd:
        return {"ok": False, "error": "Configuracao SMTP incompleta"}

    msg = MIMEMultipart("alternative") if html else email.message.EmailMessage()
    if html:
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.set_content(body)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
        return {"ok": True}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


def email_read(cfg: dict, limit: int = 10, folder: str = "INBOX",
               unseen_only: bool = False) -> list[dict]:
    e = (cfg.get("messaging") or {}).get("email") or {}
    host = e.get("imap_host") or ""
    port = int(e.get("imap_port") or 993)
    user = e.get("user") or ""
    pwd = e.get("password") or ""
    if not host or not user or not pwd:
        return []

    out = []
    try:
        with imaplib.IMAP4_SSL(host, port) as m:
            m.login(user, pwd)
            m.select(folder)
            crit = "UNSEEN" if unseen_only else "ALL"
            typ, data = m.search(None, crit)
            if typ != "OK":
                return []
            ids = data[0].split()[-limit:]
            for i in reversed(ids):
                typ, msg_data = m.fetch(i, "(RFC822)")
                if typ != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subj_raw = msg.get("Subject", "")
                try:
                    subj_dec = email.header.decode_header(subj_raw)
                    subj = "".join(
                        (s.decode(enc or "utf-8", errors="ignore") if isinstance(s, bytes) else s)
                        for s, enc in subj_dec
                    )
                except Exception:
                    subj = subj_raw
                # corpo
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                            except Exception:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except Exception:
                        body = str(msg.get_payload())
                out.append({
                    "from": msg.get("From", ""),
                    "subject": subj,
                    "date": msg.get("Date", ""),
                    "snippet": body[:300].strip(),
                })
    except Exception as ex:
        return [{"error": str(ex)}]
    return out


# ---- WhatsApp (bridge para bot existente) -------------------------------

def whatsapp_send(cfg: dict, to: str, text: str) -> dict:
    """POST ao webhook do bot do usuario (compativel com Baileys-style)."""
    wa = (cfg.get("messaging") or {}).get("whatsapp") or {}
    url = wa.get("webhook_url") or ""
    secret = wa.get("webhook_secret") or ""
    if not url:
        return {"ok": False, "error": "Webhook URL nao configurada"}
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Webhook-Secret"] = secret
    try:
        r = httpx.post(url, headers=headers,
                       json={"to": to, "text": text}, timeout=20)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code,
                "body": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---- Webhook generico ---------------------------------------------------

def webhook_post(url: str, payload: dict, headers: dict | None = None) -> dict:
    try:
        r = httpx.post(url, json=payload, headers=headers or {}, timeout=15)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code,
                "body": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---- Injetado no system prompt do LLM -----------------------------------

def render_for_prompt(cfg: dict) -> str:
    m = (cfg.get("messaging") or {})
    channels = []
    if (m.get("telegram") or {}).get("token"): channels.append("Telegram")
    if (m.get("email") or {}).get("user"): channels.append("Email")
    if (m.get("whatsapp") or {}).get("webhook_url"): channels.append("WhatsApp")
    if not channels:
        return ""

    contacts = list_contacts()
    templates = list_templates()
    contact_str = "\n".join(
        f"- {c['name']}: phone={c.get('phone','')}, email={c.get('email','')}, tg={c.get('telegram','')}"
        for c in contacts[:20]
    ) or "(nenhum)"
    tpl_str = "\n".join(f"- {t['name']}: {t['text'][:80]}..." for t in templates[:10]) or "(nenhum)"

    return f"""

### Messaging Hub
Canais ativos: {', '.join(channels)}

Para enviar/ler use:
```python
from app.messaging import (
    telegram_send, telegram_get_updates,
    email_send, email_read,
    whatsapp_send, resolve_contact, list_templates,
)
# para resolver contato por nome:
c = resolve_contact("Pedro")
if c:
    whatsapp_send(cfg, c["phone"], "ola Pedro!")
    email_send(cfg, c["email"], "assunto", "corpo")
# ler emails:
inbox = email_read(cfg, limit=10, unseen_only=True)
# ultimas msgs do Telegram bot:
ups = telegram_get_updates(cfg, limit=10)
```

Contatos:
{contact_str}

Templates:
{tpl_str}
"""
