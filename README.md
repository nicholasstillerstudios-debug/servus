# SERVUS

Assistente pessoal desktop com voz para Windows.

- Painel HUD estilo JARVIS (PyWebView + WebView2)
- Wake word offline (OpenWakeWord, ~95% acuracia)
- TTS pt-BR via Edge TTS (4 vozes neurais)
- LLM via Open Interpreter + Claude/OpenAI/Ollama
- Auto-update via GitHub Releases
- Integrações: Home Assistant, MQTT, Bluetooth (BLE), Chromecast, Email, Telegram, WhatsApp bridge, RAG local, system monitor, YouTube, OCR

## Stack

- Python 3.12 + PyInstaller (packaging)
- PyWebView + WebView2 (UI nativa)
- edge-tts (síntese de voz)
- openwakeword + sounddevice (wake detection)
- Open Interpreter (executor de código)
- Inno Setup (instalador Windows)

## Setup local de dev

```powershell
# clone
git clone https://github.com/nicholasstillerstudios-debug/servus.git
cd servus

# venv
uv venv --python 3.12 .venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

# rodar
python app\main.py
```

## Build do instalador

```powershell
# bump versao em app/version.py
# build PyInstaller
python -m PyInstaller --noconfirm --clean Servus.spec

# Inno Setup (precisa do Inno Setup 6 instalado)
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DAppVersion=0.7.2" installer\Servus.iss

# saida em release\SetupServus-X.Y.Z.exe
```

## Auto-update

Releases são publicadas em [servus-updates](https://github.com/nicholasstillerstudios-debug/servus-updates).

O app consulta `latest.json` e oferece update quando há versão nova.

## Estrutura

```
app/
  main.py           # backend principal (PyWebView + Api)
  config.py         # config schema + load/save
  wake.py           # OpenWakeWord detector
  automation.py     # browser + YouTube + file search
  sys_monitor.py    # CPU/RAM/GPU/temp
  device_scan.py    # auto-scan BLE/Chromecast
  messaging.py      # Email/Telegram/WhatsApp
  rag.py            # RAG local (embeddings + retrieval)
  history.py        # SQLite de conversas
  memory.py         # fatos persistentes
  bluetooth.py      # BLE scan via bleak
  devices.py        # Home Assistant client
  mqtt_client.py    # MQTT publish
  cast.py           # Chromecast
  vision.py         # captura tela
  notify.py         # Windows toasts
  web.py            # DuckDuckGo
  tools_hints.py    # hints de libs pro LLM
  system_info.py    # detecta apps instalados
  stt.py            # Whisper local (opcional)
  llm_local.py      # Ollama detect
  updater.py        # auto-update
  tray.py           # system tray
  hotkeys.py        # global hotkeys
  ui/               # HTML/CSS/JS
  version.py        # versao unica
assets/
  servus.ico
installer/
  Servus.iss        # Inno Setup
Servus.spec         # PyInstaller config
release.ps1         # pipeline de release
servus.ps1          # launcher dev
```

## Licença

MIT
