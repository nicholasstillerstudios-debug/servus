"""Notificacoes nativas do Windows via windows-toasts."""

from __future__ import annotations


def toast(title: str, body: str) -> None:
    try:
        from windows_toasts import WindowsToaster, Toast
        toaster = WindowsToaster("SERVUS")
        t = Toast()
        t.text_fields = [title, body[:400]]
        toaster.show_toast(t)
    except Exception as e:
        print(f"toast fail: {e}")
