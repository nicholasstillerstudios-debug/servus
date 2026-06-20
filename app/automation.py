"""Automacao: abrir browser/URL, achar e tocar YouTube, busca de arquivos."""

from __future__ import annotations

import os
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path


# ---- Browser catalog ----------------------------------------------------

BROWSERS = [
    {"id": "default", "label": "Padrao do Windows"},
    {"id": "chrome",  "label": "Google Chrome"},
    {"id": "edge",    "label": "Microsoft Edge"},
    {"id": "firefox", "label": "Mozilla Firefox"},
    {"id": "brave",   "label": "Brave"},
    {"id": "opera",   "label": "Opera"},
]

_BROWSER_PATHS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ],
    "edge": [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "brave": [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
    "opera": [
        os.path.expandvars(r"%LocalAppData%\Programs\Opera\launcher.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\Opera GX\launcher.exe"),
    ],
}


def installed_browsers() -> list[dict]:
    """Retorna so os browsers que existem de fato no sistema."""
    out = [{"id": "default", "label": "Padrao do Windows", "installed": True}]
    for b in BROWSERS[1:]:
        paths = _BROWSER_PATHS.get(b["id"], [])
        exists = any(Path(p).exists() for p in paths)
        out.append({**b, "installed": exists})
    return out


_CHROMIUM_AUTOPLAY_FLAGS = [
    "--autoplay-policy=no-user-gesture-required",
]


def open_url(url: str, browser_id: str = "default", new_window: bool = False,
             autoplay: bool = False) -> dict:
    """Abre URL no browser escolhido. autoplay=True passa flag pra bypassar bloqueio."""
    is_chromium = browser_id in ("chrome", "edge", "brave", "opera")

    if browser_id == "default" or not browser_id:
        try:
            webbrowser.open(url, new=1 if new_window else 0)
            return {"ok": True, "browser": "default"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    for path in _BROWSER_PATHS.get(browser_id, []):
        if Path(path).exists():
            try:
                args = [path]
                if autoplay and is_chromium:
                    args.extend(_CHROMIUM_AUTOPLAY_FLAGS)
                if new_window: args.append("--new-window")
                args.append(url)
                subprocess.Popen(args, close_fds=True)
                return {"ok": True, "browser": browser_id, "path": path}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    # fallback: padrao
    try:
        webbrowser.open(url)
        return {"ok": True, "browser": "default-fallback"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---- YouTube ------------------------------------------------------------

def youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"


def youtube_find_first(query: str) -> dict | None:
    """Usa yt-dlp pra achar o ID do 1o resultado. Retorna {id, title, channel, duration}."""
    try:
        from yt_dlp import YoutubeDL
    except Exception:
        return None
    try:
        opts = {
            "quiet": True, "no_warnings": True, "extract_flat": True,
            "skip_download": True, "default_search": "ytsearch1",
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        entries = info.get("entries") or []
        if not entries: return None
        v = entries[0]
        return {
            "id": v.get("id", ""),
            "title": v.get("title", ""),
            "channel": v.get("uploader") or v.get("channel", ""),
            "duration": v.get("duration", 0),
            "url": f"https://www.youtube.com/watch?v={v.get('id', '')}",
        }
    except Exception:
        return None


def _press_space_delayed(delay: float = 4.5) -> None:
    """Workaround pra autoplay block do Chrome/Edge: pressiona Space depois
    do load (foca o player e da play). Roda em thread separado."""
    import threading
    def go():
        import time
        time.sleep(delay)
        try:
            import pyautogui
            pyautogui.press("space")
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


def youtube_play(query: str, browser_id: str = "default") -> dict:
    """Acha musica/video por query e abre + garante reproducao via Space key."""
    found = youtube_find_first(query)
    if not found:
        return open_url(youtube_search_url(query), browser_id)
    # 1) tenta autoplay flag (funciona em new Chrome/Edge sessions)
    result = open_url(found["url"] + "&autoplay=1",
                      browser_id, new_window=True, autoplay=True)
    # 2) backup garantido: pressiona Space depois do load
    # (foca player + da play - funciona mesmo com autoplay block)
    _press_space_delayed(4.5)
    return {
        **result,
        "title": found["title"],
        "channel": found["channel"],
        "method": "autoplay+space",
    }


# ---- Busca de arquivos --------------------------------------------------

DEFAULT_SEARCH_DIRS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Pictures",
    Path.home() / "Videos",
    Path.home() / "Music",
    Path.home() / "OneDrive",
    Path.home(),  # raiz do user dir
]


def find_files(
    pattern: str,
    search_dirs: list[str] | None = None,
    max_results: int = 30,
    include_dirs: bool = True,
) -> list[dict]:
    """Procura arquivos/pastas por substring (case-insensitive) ou glob simples.

    Ignora pastas pesadas/ocultas (.git, node_modules, venv, etc) pra ser rapido.
    """
    skip_dirs = {
        ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache",
        "AppData", ".npm", ".local", "Temp", "$RECYCLE.BIN",
        ".vscode", ".idea", "dist", "build", ".next",
    }
    needle = pattern.lower().strip()
    if not needle: return []

    is_glob = any(c in pattern for c in "*?[")
    glob_check = None
    if is_glob:
        from fnmatch import fnmatch
        glob_check = lambda n: fnmatch(n.lower(), needle)

    dirs = [Path(d) for d in search_dirs] if search_dirs else DEFAULT_SEARCH_DIRS
    matches: list[dict] = []

    for base in dirs:
        if not base.exists(): continue
        try:
            for root, dirnames, filenames in os.walk(base):
                # remove diretorios a ignorar (in-place pra nao descer)
                dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]

                items = filenames + (dirnames if include_dirs else [])
                for name in items:
                    match = (glob_check(name) if glob_check else (needle in name.lower()))
                    if not match: continue
                    p = Path(root) / name
                    try:
                        st = p.stat()
                        matches.append({
                            "path": str(p),
                            "name": name,
                            "is_dir": p.is_dir(),
                            "size_kb": round(st.st_size / 1024, 1) if p.is_file() else None,
                            "modified": st.st_mtime,
                        })
                    except Exception:
                        matches.append({"path": str(p), "name": name, "is_dir": p.is_dir()})
                    if len(matches) >= max_results: return matches
        except (PermissionError, OSError):
            continue
    return matches


# ---- System prompt ------------------------------------------------------

def render_for_prompt(cfg: dict) -> str:
    browser_id = (cfg.get("browser") or "default")
    return f"""

### Automacao (browser, YouTube, busca de arquivos)

Browser preferido do usuario: **{browser_id}**. SEMPRE use isso ao abrir URLs.

```python
from app.automation import open_url, youtube_play, find_files
BROWSER = "{browser_id}"

# abrir URL no browser preferido
open_url("https://exemplo.com", BROWSER)

# tocar musica/video no YouTube (acha 1o resultado e abre com autoplay)
youtube_play("artista nome da musica", BROWSER)

# buscar arquivos no PC do usuario por nome (case-insensitive ou glob *.pdf)
find_files("relatorio", max_results=10)
find_files("*.pdf", search_dirs=[r"C:\\Users\\nicho\\Documents"])
```

Quando o usuario pedir pra TOCAR musica/video, use `youtube_play` (resolve o video certo).
NAO use pyautogui pra clicar play - o autoplay da URL ja toca direto.
"""
