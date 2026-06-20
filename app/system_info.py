"""Detecta o que tem instalado no PC do usuario - permite ao LLM se adaptar."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


KNOWN_APPS = {
    "Spotify": [
        r"%APPDATA%\Spotify\Spotify.exe",
        r"%LocalAppData%\Spotify\Spotify.exe",
    ],
    "VLC": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "MPV": [r"C:\Program Files\mpv\mpv.exe"],
    "VS Code": [
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe",
    ],
    "VS Code Insiders": [
        r"C:\Program Files\Microsoft VS Code Insiders\Code - Insiders.exe",
    ],
    "Cursor": [r"%LocalAppData%\Programs\Cursor\Cursor.exe"],
    "Sublime Text": [r"C:\Program Files\Sublime Text\sublime_text.exe"],
    "Notepad++": [r"C:\Program Files\Notepad++\notepad++.exe"],
    "Discord": [
        r"%LocalAppData%\Discord\Update.exe",
        r"%LocalAppData%\DiscordCanary\Update.exe",
    ],
    "Slack": [r"%LocalAppData%\slack\slack.exe"],
    "Steam": [r"C:\Program Files (x86)\Steam\Steam.exe"],
    "Epic Games": [r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe"],
    "OBS": [r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"],
    "Audacity": [r"C:\Program Files\Audacity\Audacity.exe"],
    "Photoshop": [r"C:\Program Files\Adobe"],  # checa pasta
    "Premiere Pro": [r"C:\Program Files\Adobe"],
    "Office Word": [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "Office Excel": [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "PowerToys": [r"C:\Program Files\PowerToys\PowerToys.exe"],
    "Git": [r"C:\Program Files\Git\bin\git.exe"],
    "Docker": [r"C:\Program Files\Docker\Docker\Docker Desktop.exe"],
    "Node.js": [r"C:\Program Files\nodejs\node.exe"],
    "Python (sys)": [r"C:\Python311\python.exe", r"C:\Python312\python.exe"],
    "WSL": [r"C:\Windows\System32\wsl.exe"],
    "Windows Terminal": [r"%LocalAppData%\Microsoft\WindowsApps\wt.exe"],
    "PowerShell 7": [r"C:\Program Files\PowerShell\7\pwsh.exe"],
    "OneDrive": [r"%LocalAppData%\Microsoft\OneDrive\OneDrive.exe"],
}


def detect_apps() -> dict[str, str]:
    found = {}
    for name, paths in KNOWN_APPS.items():
        for p in paths:
            expanded = os.path.expandvars(p)
            if Path(expanded).exists():
                found[name] = expanded
                break
    return found


def system_summary() -> dict:
    """Resumo curto pra injetar no system prompt."""
    try:
        cpu_count = os.cpu_count() or 0
    except Exception:
        cpu_count = 0
    try:
        import psutil
        ram_gb = round(psutil.virtual_memory().total / 1e9)
    except Exception:
        ram_gb = 0
    try:
        import pynvml
        pynvml.nvmlInit()
        gpu_name = "GPU NVIDIA"
        try:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            n = pynvml.nvmlDeviceGetName(h)
            gpu_name = n.decode() if isinstance(n, bytes) else n
        except Exception: pass
        pynvml.nvmlShutdown()
    except Exception:
        gpu_name = ""
    return {
        "os": platform.platform(),
        "user": os.environ.get("USERNAME", ""),
        "home": str(Path.home()),
        "cpu": platform.processor() or f"{cpu_count} cores",
        "ram_gb": ram_gb,
        "gpu": gpu_name,
        "apps": detect_apps(),
    }


def render_for_prompt() -> str:
    s = system_summary()
    apps = s["apps"]
    app_names = list(apps.keys())

    # heuristicas de "preferencia" baseadas no que tem instalado
    media_hints = []
    if "Spotify" in apps:
        media_hints.append(
            "- Para tocar musica: tem **Spotify** instalado. Pode abrir via `subprocess.Popen([r'%s'])` "
            "ou URL search `spotify:search:nome+da+musica`." % apps["Spotify"]
        )
    if "VLC" in apps:
        media_hints.append(
            "- Para tocar video local: use **VLC** (`subprocess.Popen([r'%s', 'caminho/video.mp4'])`)." % apps["VLC"]
        )
    if "Discord" in apps:
        media_hints.append("- **Discord** disponivel - pode abrir/ativar pela URL `discord://`.")

    media_block = "\n".join(media_hints) if media_hints else "(nenhuma preferencia detectada)"

    return f"""

### Ambiente do usuario (DETECTADO)
- OS: {s['os']}
- User: {s['user']} (home: {s['home']})
- CPU: {s['cpu']}  RAM: {s['ram_gb']}GB  GPU: {s['gpu'] or 'sem GPU NVIDIA'}
- Apps instalados: {', '.join(app_names) if app_names else '(scan vazio)'}

ADAPTACOES sugeridas:
{media_block}

Use esse contexto pra escolher a ferramenta certa. Ex: se o usuario quer abrir
codigo e VS Code esta instalado, abre la em vez de Notepad. Se quer tocar musica
e tem Spotify, prefere ele.
"""
