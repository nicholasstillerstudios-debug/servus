"""Hints curtos das ferramentas disponiveis - injeta no system prompt do LLM.

Mantemos SUPER conciso. Tudo bundle, LLM importa quando precisar.
"""


HINTS = """

### Ferramentas Python disponiveis

Estas libs estao instaladas - importa e usa quando o pedido pedir:

- **OCR**: `from rapidocr_onnxruntime import RapidOCR; ocr=RapidOCR(); ocr('arquivo.png')` -> lista (box, texto, score)
- **Sistema (CPU/RAM/disco/processos)**: `import psutil; psutil.cpu_percent(), psutil.virtual_memory()`
- **Automacao mouse/teclado**: `import pyautogui; pyautogui.screenshot(); pyautogui.click(x,y); pyautogui.write('x'); pyautogui.hotkey('ctrl','c')`
- **Windows API**: `import win32api, win32gui` (pywin32)
- **Mouse hook**: `import mouse; mouse.on_click(callback)`
- **Slack**: `from slack_sdk import WebClient; WebClient(token).chat_postMessage(channel='#x', text='oi')`
- **Discord**: `import discord` (precisa bot loop)
- **Twilio (SMS)**: `from twilio.rest import Client; Client(sid,tok).messages.create(to='+55...', from_='+1...', body='oi')`
- **Bluetooth BLE**: `import asyncio; from bleak import BleakClient, BleakScanner`
- **MQTT**: `import paho.mqtt.client as mqtt`
- **Audio TTS**: `edge_tts` (ja em uso pelo SERVUS)
- **Captura tela**: `import mss` (ja usado pra screenshot)
- **HTTP**: `httpx` (preferir sobre requests)
- **PDF**: `pypdf` ou `pymupdf` se instalado

Antes de afirmar que algo nao da, tente. Se a lib nao estiver instalada o erro sera claro - voce pode pedir pro usuario instalar via `uv pip install <pkg>` no ambiente do servus.
"""


def render() -> str:
    return HINTS
