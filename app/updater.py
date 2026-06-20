"""Auto-updater do SERVUS.

Fluxo:
1) check() baixa o manifest JSON e compara com a versao local.
2) Se houver versao mais nova, download_installer() baixa o SetupServus-X.Y.Z.exe.
3) install_and_restart() executa o instalador em modo silencioso e mata o app.
   O Inno Setup, ao terminar, reabre o app via flag RESTARTAPPLICATIONS.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx

from .version import UPDATE_MANIFEST_URL, __version__


@dataclass
class UpdateInfo:
    available: bool
    current: str
    latest: str
    url: str
    notes: str
    error: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.strip().lstrip("v").split(".") if p.isdigit())


def check() -> UpdateInfo:
    """Consulta o manifest e retorna info de atualizacao."""
    cur = __version__
    try:
        r = httpx.get(UPDATE_MANIFEST_URL, timeout=10, follow_redirects=True)
        if r.status_code != 200:
            return UpdateInfo(False, cur, cur, "", "", f"HTTP {r.status_code}")
        m = r.json()
        latest = str(m.get("version", "0.0.0"))
        url = str(m.get("url", ""))
        notes = str(m.get("notes", ""))
        available = _parse_version(latest) > _parse_version(cur)
        return UpdateInfo(available, cur, latest, url, notes)
    except Exception as e:
        return UpdateInfo(False, cur, cur, "", "", str(e))


def download_installer(url: str, on_progress=None) -> Path:
    """Baixa o instalador para %TEMP%\\SetupServus-<v>.exe e retorna o caminho."""
    name = url.rsplit("/", 1)[-1] or "SetupServus.exe"
    dest = Path(tempfile.gettempdir()) / name
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", "0"))
        done = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=64 * 1024):
                f.write(chunk)
                done += len(chunk)
                if on_progress and total:
                    on_progress(done, total)
    return dest


def install_and_restart(installer_path: Path) -> None:
    """Executa o instalador silencioso e relanca o app via batch watcher.

    Problema do /RESTARTAPPLICATIONS: depende de RegisterApplicationRestart
    chamado pelo app antes de fechar - facil de errar. Usamos um .bat
    detachado que: (1) espera o installer encerrar, (2) abre o exe instalado.
    """
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    target_exe = Path(pf) / "SERVUS" / "Servus.exe"
    log_path = Path(tempfile.gettempdir()) / "servus_update.log"

    bat = Path(tempfile.gettempdir()) / "servus_update_relaunch.bat"
    bat_content = (
        '@echo off\r\n'
        'setlocal\r\n'
        f'set "LOG={log_path}"\r\n'
        f'echo [%date% %time%] watcher start >> "%LOG%"\r\n'
        ':wait\r\n'
        f'tasklist /FI "IMAGENAME eq {installer_path.name}" 2>NUL | '
        f'find /I "{installer_path.name}" >NUL\r\n'
        'if not errorlevel 1 (\r\n'
        '    timeout /t 2 /nobreak >NUL\r\n'
        '    goto wait\r\n'
        ')\r\n'
        'timeout /t 2 /nobreak >NUL\r\n'
        f'echo [%date% %time%] installer done, launching >> "%LOG%"\r\n'
        f'start "" "{target_exe}"\r\n'
        f'echo [%date% %time%] launched >> "%LOG%"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )
    bat.write_text(bat_content, encoding="ascii")

    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    # 1) roda o installer (silencioso)
    subprocess.Popen(
        [str(installer_path), "/VERYSILENT", "/SUPPRESSMSGBOXES",
         "/NORESTART", "/CLOSEAPPLICATIONS",
         f"/LOG={Path(tempfile.gettempdir()) / 'servus_inno.log'}"],
        creationflags=flags, close_fds=True,
    )
    # 2) roda o watcher que vai relancar
    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        creationflags=flags, close_fds=True,
    )
    # 3) encerra esta instancia pra liberar arquivos
    threading.Timer(2.0, lambda: os._exit(0)).start()


__all__ = ["UpdateInfo", "check", "download_installer", "install_and_restart"]
