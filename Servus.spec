# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para o SERVUS Desktop."""

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas = []
binaries = []
hiddenimports = []

for pkg in ("litellm", "edge_tts", "interpreter", "tiktoken_ext", "tiktoken",
            "inquirer", "readchar", "blessed", "yaspin", "bleak", "winrt",
            "pystray", "PIL", "keyboard", "mss", "paho", "pychromecast",
            "zeroconf", "windows_toasts", "duckduckgo_search", "primp",
            "faster_whisper", "ctranslate2", "onnxruntime", "vosk",
            "sounddevice", "pypdf",
            # 0.5.0+: novos pacotes
            "rapidocr_onnxruntime", "psutil", "pyautogui", "win32",
            "mouse", "slack_sdk", "discord", "twilio",
            "pynvml", "wmi", "yt_dlp",
            # 0.7.1: wake word definitivo
            "openwakeword", "sklearn", "scipy", "narwhals"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[spec] skip {pkg}: {e}")

# Pacotes que chamam importlib.metadata.version() no import (precisam de dist-info)
for pkg in ("readchar", "inquirer", "blessed", "tokentrim", "litellm",
            "anthropic", "openai", "tiktoken", "httpx", "edge_tts"):
    try:
        datas += copy_metadata(pkg)
    except Exception as e:
        print(f"[spec] no metadata {pkg}: {e}")

for mod in ("anthropic", "openai", "google.generativeai", "jupyter_client", "httpx"):
    try:
        hiddenimports += collect_submodules(mod)
    except Exception:
        pass

# UI estatica + icone
datas += [("app/ui", "app/ui")]
datas += [("assets/servus.ico", "assets")]


a = Analysis(
    ['app\\main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['build_assets/rt_fix_streams.py'],
    excludes=[
        'matplotlib.tests', 'numpy.tests',
        'PIL.ImageQt', 'PySide2', 'PySide6', 'PyQt5', 'PyQt6',
        # 'tkinter' e 'unittest' NAO podem ser excluidos:
        # open-interpreter -> jupyter_client -> unittest.mock,
        # e ipykernel chama tkinter em algumas paths.
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Servus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\servus.ico',
    # uac_admin REMOVIDO - quebrava mic do WebView2. SERVUS roda como usuario.
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Servus',
)
