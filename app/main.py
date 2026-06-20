"""
SERVUS Desktop - painel de interacao (texto + voz) com Open Interpreter.

Janela nativa (PyWebView) conversa com o backend Python via
window.pywebview.api. Backend usa Open Interpreter pra executar
comandos no PC e Edge TTS pra falar.
"""

from __future__ import annotations

# ----- FIX URGENTE: corrige streams antes de QUALQUER import pesado -----
import os as _os
import sys as _sys
import traceback as _tb
from pathlib import Path as _Path

# crash log em %APPDATA%\Servus\crash.log
_CRASH_LOG = _Path(_os.environ.get("APPDATA", str(_Path.home()))) / "Servus" / "crash.log"
def _logcrash(msg: str) -> None:
    try:
        _CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def _excepthook(t, v, tb):
    _logcrash("UNCAUGHT: " + "".join(_tb.format_exception(t, v, tb)))
_sys.excepthook = _excepthook
_logcrash(f"=== boot {__name__} ===")

# Corrige streams nulos do modo windowed
for _n in ("stdin", "stdout", "stderr"):
    _mode = "r" if _n == "stdin" else "w"
    for _attr in (_n, f"__{_n}__"):
        if getattr(_sys, _attr, None) is None:
            try:
                setattr(_sys, _attr, open(_os.devnull, _mode, encoding="utf-8"))
                _logcrash(f"streams: fix sys.{_attr}")
            except Exception as _e:
                _logcrash(f"streams: fail sys.{_attr}: {_e}")
_logcrash("streams ok")

# Esconder janelas de console em QUALQUER subprocess que o app spawn.
# Open Interpreter usa Jupyter kernel + executa python/shell - sem isso fica
# piscando janela preta de cmd/powershell na frente do usuario.
if _os.name == "nt":
    import subprocess as _sp
    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen = _sp.Popen.__init__
    def _silent_popen(self, *args, **kwargs):
        cf = kwargs.get("creationflags", 0) or 0
        kwargs["creationflags"] = cf | _CREATE_NO_WINDOW
        try:
            si = kwargs.get("startupinfo") or _sp.STARTUPINFO()
            si.dwFlags |= _sp.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si
        except Exception:
            pass
        return _orig_popen(self, *args, **kwargs)
    _sp.Popen.__init__ = _silent_popen
    _logcrash("subprocess hidden ok")
# -----------------------------------------------------------------------

import asyncio
import base64
import os
import re
import sys
import threading
from pathlib import Path


def _clean_for_tts(text: str) -> str:
    """Remove markdown/code/links pra a voz nao falar 'asterisco asterisco'."""
    # blocos de codigo ```...```
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # codigo inline `xxx`
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # negrito/italico
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    # links markdown [texto](url) -> texto
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # urls cruas
    text = re.sub(r"https?://\S+", "link", text)
    # headings
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # marcadores de lista
    text = re.sub(r"^[\-\*\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # tabelas markdown (linhas com |)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
    # quebras duplas viram pausa
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", " ", text)
    # caracteres soltos
    text = re.sub(r"[`~>#]", "", text)
    # multiplos espacos
    text = re.sub(r"\s+", " ", text).strip()
    return text

_logcrash("stdlib ok")
try:
    import edge_tts
    _logcrash("edge_tts ok")
except Exception as _e:
    _logcrash("edge_tts FAIL: " + _tb.format_exc()); raise
try:
    import webview
    _logcrash("webview ok")
except Exception as _e:
    _logcrash("webview FAIL: " + _tb.format_exc()); raise
try:
    from interpreter import interpreter
    _logcrash("interpreter ok")
except Exception as _e:
    _logcrash("interpreter FAIL: " + _tb.format_exc()); raise

# permite import tanto via 'python app/main.py' quanto 'python -m app.main'
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import config as cfgmod  # noqa: E402
from app import updater as upd    # noqa: E402
from app import devices as devmod  # noqa: E402
from app import bluetooth as btmod  # noqa: E402
from app import history as hist    # noqa: E402
from app import memory as memmod   # noqa: E402
from app import vision as vismod   # noqa: E402
from app import notify as notifmod  # noqa: E402
from app import web as webmod      # noqa: E402
from app import mqtt_client as mqttmod  # noqa: E402
from app import cast as castmod    # noqa: E402
from app import context_mgr as ctxmgr  # noqa: E402
from app import llm_local as llmlocal  # noqa: E402
from app import stt as sttmod      # noqa: E402
from app import wake as wakemod    # noqa: E402
from app import rag as ragmod      # noqa: E402
from app import messaging as msgmod  # noqa: E402
from app import tools_hints as tools_hintsmod  # noqa: E402
from app import sys_monitor as sysmon  # noqa: E402
from app import device_scan as dscan   # noqa: E402
from app import automation as automod  # noqa: E402
from app import system_info as sysinfo  # noqa: E402
from app.version import __version__, APP_NAME, APP_MUTEX  # noqa: E402

# quando empacotado pelo PyInstaller, datas vao pra sys._MEIPASS
if getattr(sys, "frozen", False):
    UI_DIR = Path(sys._MEIPASS) / "app" / "ui"
else:
    UI_DIR = Path(__file__).parent / "ui"
INDEX = UI_DIR / "index.html"
_logcrash(f"UI_DIR={UI_DIR} exists={INDEX.exists()}")


# --- aplicacao da config no interpreter ----------------------------------

_SPEED_MODEL_MAP = {
    "fast":     "claude-haiku-4-5-20251001",
    "balanced": "claude-sonnet-4-5",
    "smart":    "claude-opus-4-1-20250805",
}


def apply_config(cfg: dict) -> None:
    """Aplica modelo + system_message ao interpreter global."""
    model_pref = cfg.get("model", "auto")
    speed = cfg.get("speed", "balanced")  # PADRAO MUDOU pra Sonnet (mais confiavel)
    claude_model = _SPEED_MODEL_MAP.get(speed, "claude-sonnet-4-5")

    def pick():
        has_a = bool(os.environ.get("ANTHROPIC_API_KEY"))
        has_o = bool(os.environ.get("OPENAI_API_KEY"))
        if model_pref == "claude" or (model_pref == "auto" and has_a):
            return claude_model, None
        if model_pref == "openai" or (model_pref == "auto" and has_o):
            return "gpt-4o-mini" if speed == "fast" else "gpt-4o", None
        return "ollama/llama3.1", "http://localhost:11434"

    model, api_base = pick()
    interpreter.llm.model = model
    if api_base:
        interpreter.llm.api_base = api_base
    interpreter.auto_run = True
    interpreter.llm.context_window = 16000
    base = cfgmod.build_system_message(cfg)
    devmod.apply_env(cfg)
    devices_text = devmod.render_for_prompt(cfg)
    bt_text = btmod.render_for_prompt(cfg)
    mem_text = memmod.render_for_prompt()
    mqtt_text = mqttmod.render_for_prompt(cfg)
    web_text = webmod.render_for_prompt()
    cast_text = castmod.render_for_prompt(cfg)
    rag_text = ragmod.render_for_prompt()
    msg_text = msgmod.render_for_prompt(cfg)
    tools_text = tools_hintsmod.render()
    hw_text = sysmon.render_for_prompt()
    auto_text = automod.render_for_prompt(cfg)
    sysinfo_text = sysinfo.render_for_prompt()
    # Junta so as secoes nao-vazias (system prompt menor = resposta mais rapida)
    # Reforco de raciocinio (logica) - vem no inicio pro modelo ler primeiro
    reasoning = (
        "\n\n### Raciocinio\n"
        "Antes de responder qualquer pergunta nao-trivial:\n"
        "1. Identifique o que o usuario REALMENTE quer (intencao).\n"
        "2. Cheque se voce tem todas as informacoes (se nao, pergunte ou descubra).\n"
        "3. Se for tarefa multi-etapa, divida em passos numerados.\n"
        "4. Use as ferramentas disponiveis (browser, file_search, hardware, automation) "
        "EM VEZ de dar respostas genericas.\n"
        "5. Confirme cada passo com o resultado real (nao alucine).\n"
    )
    parts = [base, reasoning, sysinfo_text, devices_text, bt_text, mem_text, mqtt_text,
             web_text, cast_text, rag_text, msg_text, tools_text, hw_text, auto_text]
    interpreter.system_message = "".join(p for p in parts if p)


class Api:
    """Bridge Python <-> JS (window.pywebview.api)."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self.cfg = cfgmod.load()
        apply_config(self.cfg)
        self.conv_id = hist.new_conversation()
        self._pending_image: Path | None = None
        self._vosk_listener = None  # WakeListener instance

    def bind(self, window: webview.Window) -> None:
        self._window = window

    # ---- config --------------------------------------------------------
    def get_config(self) -> dict:
        return self.cfg

    def get_catalogs(self) -> dict:
        return cfgmod.catalogs()

    def save_config(self, new_cfg: dict) -> dict:
        cfgmod.save(new_cfg)
        self.cfg = cfgmod.load()
        apply_config(self.cfg)
        interpreter.messages = []  # reseta pra aplicar nova persona
        # Reinicia Vosk se necessario (config nova pode ter mudado wake_words ou wake_offline)
        try:
            if self._vosk_listener:
                self._vosk_listener.stop()
                self._vosk_listener = None
            if self.cfg.get("wake_enabled") and self.cfg.get("wake_offline"):
                self.start_vosk_wake()
        except Exception: pass
        if self._window:
            try:
                self._window.set_title(self.cfg["identity"]["name"])
            except Exception:
                pass
        return {"ok": True, "config": self.cfg}

    # ---- chat ----------------------------------------------------------
    def chat(self, message: str) -> dict:
        threading.Thread(target=self._run_chat, args=(message,), daemon=True).start()
        return {"ok": True}

    def _run_chat(self, message: str) -> None:
        try: hist.add_message(self.conv_id, "user", message)
        except Exception: pass

        # ----- INTERCEPT: comandos de controle por voz -------------------
        # Frases que o usuario diz pra desligar/ligar a escuta - resposta DIRETA
        # sem precisar consultar o LLM (mais rapido e mais confiavel)
        msg_norm = message.lower().strip()
        wake_off_phrases = [
            "para de escutar", "pare de escutar", "para de ouvir",
            "fica quieto", "fique quieto", "shh", "silencio",
            "desativar microfone", "desliga o microfone", "desliga mic",
            "para de me ouvir", "desativa wake", "desativa escuta",
        ]
        wake_on_phrases = [
            "comeca a escutar", "volta a escutar", "ativa escuta",
            "ativa microfone", "liga o microfone", "modo wake",
        ]
        for p in wake_off_phrases:
            if p in msg_norm:
                self.cfg["wake_enabled"] = False
                try: cfgmod.save(self.cfg)
                except Exception: pass
                try: self.stop_vosk_wake()
                except Exception: pass
                self._emit("wake_toggled", "0")
                resp = "Ok, parei de escutar. Pra ativar de novo, abre o app ou liga em Configuracoes > Voz."
                self._emit("token", resp); self._emit("done", resp)
                try: hist.add_message(self.conv_id, "assistant", resp)
                except Exception: pass
                self._speak(_clean_for_tts(resp))
                return
        for p in wake_on_phrases:
            if p in msg_norm:
                self.cfg["wake_enabled"] = True
                try: cfgmod.save(self.cfg)
                except Exception: pass
                if self.cfg.get("wake_offline"):
                    try: self.start_vosk_wake()
                    except Exception: pass
                self._emit("wake_toggled", "1")
                resp = "Escutando. Fala a palavra-gatilho que eu respondo."
                self._emit("token", resp); self._emit("done", resp)
                try: hist.add_message(self.conv_id, "assistant", resp)
                except Exception: pass
                self._speak(_clean_for_tts(resp))
                return

        # Screen mode: anexa screenshot a CADA mensagem
        if self.cfg.get("screen_mode") and not self._pending_image:
            try:
                p = vismod.capture_screen()
                if p: self._pending_image = p
            except Exception: pass

        img_path = self._pending_image
        self._pending_image = None
        if img_path and img_path.exists():
            try:
                interpreter.messages.extend([{
                    "role": "user", "type": "image",
                    "format": "path", "content": str(img_path),
                }])
            except Exception: pass

        # auto-compress se contexto crescer muito (Path 1)
        try: ctxmgr.maybe_compress(interpreter)
        except Exception: pass

        buf = []
        sentence_buf = ""  # streaming TTS - acumula ate fim de frase
        spoken_idx = 0
        attempted_fallback = False

        def flush_sentence(force=False):
            """Procura fim de frase no buffer e fala o que ja esta pronto."""
            nonlocal sentence_buf
            if not sentence_buf.strip(): return
            text = sentence_buf
            if force:
                self._speak(_clean_for_tts(text))
                sentence_buf = ""
                return
            # ultimo "." "!" "?" "\n" - fala ate ali
            m = list(re.finditer(r"[.!?\n](?:\s|$)", text))
            if not m: return
            cut = m[-1].end()
            to_speak = text[:cut]
            sentence_buf = text[cut:]
            cleaned = _clean_for_tts(to_speak)
            if cleaned: self._speak(cleaned)

        try:
            for chunk in interpreter.chat(message, stream=True, display=False):
                ctype = chunk.get("type")
                content = chunk.get("content", "")
                if not content: continue
                if ctype == "message":
                    buf.append(content)
                    sentence_buf += content
                    self._emit("token", content)
                    # threshold maior - fala mais natural (chunks pequenos sao robotico)
                    if len(sentence_buf) > 60:
                        flush_sentence(force=False)
                elif ctype == "code":
                    self._emit("code", content)
                elif ctype == "console":
                    self._emit("console", content)
        except Exception as e:
            err = str(e)
            # log completo no crash.log com stacktrace
            try:
                import traceback as _tb_mod
                _logcrash(f"chat fail model={interpreter.llm.model}: {_tb_mod.format_exc()}")
            except Exception: pass

            # Auto-fallback: se o modelo nao existe / 404 / NotFound, troca pra Sonnet 4.5
            err_low = err.lower()
            model_err = any(s in err_low for s in (
                "model_not_found", "404", "notfound", "invalid model",
                "model:", "does not exist"
            ))
            if model_err and interpreter.llm.model != "claude-sonnet-4-5":
                self._emit("token", f"\n[Modelo {interpreter.llm.model} indisponivel - tentando Sonnet 4.5]\n")
                interpreter.llm.model = "claude-sonnet-4-5"
                try:
                    self._run_chat(message)
                    return
                except Exception: pass

            self._emit("error", err[:400])
            return

        # fala o resto que sobrou
        flush_sentence(force=True)

        full = "".join(buf).strip()
        self._emit("done", full)
        if full:
            try: hist.add_message(self.conv_id, "assistant", full)
            except Exception: pass
            try:
                if self._window and not self._window.shown:
                    notifmod.toast(self.cfg["identity"]["name"], full[:200])
            except Exception: pass

    # ---- TTS -----------------------------------------------------------
    def speak(self, text: str) -> dict:
        self._speak(text)
        return {"ok": True}

    def preview_voice(self, voice_id: str) -> dict:
        sample = f"Ola, eu sou o {self.cfg['identity']['name']}. Pronto para servir."
        threading.Thread(
            target=self._tts_worker, args=(sample, voice_id), daemon=True
        ).start()
        return {"ok": True}

    def _speak(self, text: str) -> None:
        # Para Vosk antes do TTS pra mic ficar livre
        # (evita Vosk capturar a propria voz do SERVUS)
        if self._vosk_listener:
            try: self._vosk_listener.stop()
            except Exception: pass
            # marca pra retomar depois do TTS terminar
            self._vosk_was_active = True
        threading.Thread(target=self._tts_worker, args=(text,), daemon=True).start()

    def _resume_vosk_after_tts(self):
        if getattr(self, "_vosk_was_active", False):
            self._vosk_was_active = False
            self._vosk_listener = None
            try: self.start_vosk_wake()
            except Exception: pass

    def _tts_worker(self, text: str, voice: str | None = None) -> None:
        v = voice or self.cfg.get("voice") or "pt-BR-AntonioNeural"
        try:
            audio_b64 = asyncio.run(self._synth(text, v))
            if audio_b64:
                self._emit("audio", audio_b64)
            else:
                _logcrash(f"TTS empty audio voice={v} text_len={len(text)}")
                self._emit("error", f"TTS sem audio (voz: {v}). Tente outra voz.")
        except Exception as e:
            _logcrash(f"TTS fail voice={v}: {type(e).__name__}: {e}")
            self._emit("error", f"TTS falhou (voz: {v}). {type(e).__name__}: {str(e)[:120]}")
        finally:
            # depois que a sintese termina, reativa Vosk se estava ativo
            threading.Timer(0.8, self._resume_vosk_after_tts).start()

    async def _synth(self, text: str, voice: str) -> str:
        rate = self.cfg.get("rate", "+0%")
        pitch = self.cfg.get("pitch", "+0Hz")
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        chunks: list[bytes] = []
        async for ev in comm.stream():
            if ev["type"] == "audio":
                chunks.append(ev["data"])
        return base64.b64encode(b"".join(chunks)).decode("ascii")

    # ---- historico -----------------------------------------------------
    def list_history(self) -> dict:
        return {"items": hist.list_conversations(limit=50)}

    def load_history(self, conv_id: int) -> dict:
        return {"messages": hist.get_messages(int(conv_id))}

    def new_conversation(self) -> dict:
        interpreter.messages = []
        self.conv_id = hist.new_conversation()
        return {"ok": True, "conv_id": self.conv_id}

    def delete_conversation(self, conv_id: int) -> dict:
        try: hist.delete_conversation(int(conv_id))
        except Exception: pass
        return {"ok": True}

    # ---- memoria de longo prazo ----------------------------------------
    def list_facts(self) -> dict:
        return {"facts": memmod.list_facts()}

    def add_fact(self, text: str, category: str = "geral") -> dict:
        f = memmod.add_fact(text, category)
        apply_config(self.cfg)
        return {"ok": True, "fact": f}

    def remove_fact(self, fact_id: int) -> dict:
        memmod.remove_fact(int(fact_id))
        apply_config(self.cfg)
        return {"ok": True}

    # ---- vision (captura tela) -----------------------------------------
    def prepare_screen(self) -> dict:
        p = vismod.capture_screen()
        if not p:
            return {"ok": False, "error": "Captura falhou"}
        self._pending_image = p
        self._emit("screen_captured", str(p))
        return {"ok": True, "path": str(p)}

    # ---- web search ----------------------------------------------------
    def web_search(self, query: str, max_results: int = 5) -> dict:
        return {"results": webmod.search(query, max_results)}

    # ---- MQTT ----------------------------------------------------------
    def configure_mqtt(self, host: str, port: int = 1883, user: str = "", password: str = "") -> dict:
        m = self.cfg.setdefault("mqtt", {})
        m.update({"host": host, "port": int(port), "user": user, "password": password})
        cfgmod.save(self.cfg)
        r = mqttmod.configure(host, int(port), user, password)
        apply_config(self.cfg)
        return r

    def mqtt_publish(self, topic: str, payload: str, retain: bool = False) -> dict:
        return mqttmod.publish(topic, payload, retain)

    # ---- Cast ----------------------------------------------------------
    def cast_list(self) -> dict:
        return {"devices": castmod.list_devices()}

    def cast_url(self, device: str, url: str, content_type: str = "video/mp4") -> dict:
        return castmod.cast_url(device, url, content_type)

    # ---- compact mode / window -----------------------------------------
    def toggle_compact(self, enabled: bool) -> dict:
        if not self._window: return {"ok": False}
        try:
            if enabled:
                self._window.resize(300, 320)
                self._window.on_top = True
            else:
                self._window.resize(620, 860)
                self._window.on_top = False
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def show_window(self) -> dict:
        if not self._window: return {"ok": False}
        try:
            self._window.show()
            self._window.restore()
        except Exception: pass
        return {"ok": True}

    def hide_window(self) -> dict:
        if not self._window: return {"ok": False}
        try: self._window.hide()
        except Exception: pass
        return {"ok": True}

    # ---- drop de arquivo -----------------------------------------------
    def file_dropped(self, path: str) -> dict:
        """UI chama isso quando usuario solta arquivo. Marca como imagem pendente."""
        p = Path(path)
        if not p.exists(): return {"ok": False}
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            self._pending_image = p
            return {"ok": True, "kind": "image"}
        # outros tipos: injeta como texto na proxima msg
        return {"ok": True, "kind": "file", "path": str(p)}

    # ---- Vosk wake listener (offline) ----------------------------------
    def _wake_words_effective(self) -> list[str]:
        words = list(self.cfg.get("wake_words") or [])
        single = self.cfg.get("wake_word") or ""
        if single and single not in words:
            words.append(single)
        if not words:
            name = (self.cfg.get("identity") or {}).get("name") or "servus"
            words.append(name)
        return words

    def start_vosk_wake(self) -> dict:
        """Inicia listener Vosk (chamado pela UI ao ligar wake_offline)."""
        if self._vosk_listener:
            return {"ok": True, "already": True}
        if not wakemod.model_ready():
            return {"ok": False, "error": "Modelo Vosk nao baixado"}

        def on_wake(after_text: str):
            if after_text:
                self._emit("wake_triggered", after_text)
            else:
                self._emit("wake_listening_followup", "")

        def on_wake_error(msg: str):
            # erro visivel no chat + para o listener
            self._emit("error", f"Wake: {msg}")
            self._emit("wake_engine", "stopped")
            self._vosk_listener = None

        wake_model = self.cfg.get("wake_model_offline") or "hey_jarvis"
        listener = wakemod.WakeListener(
            wake_words=self._wake_words_effective(),  # back-compat
            on_wake=on_wake,
            on_error=on_wake_error,
            wake_model=wake_model,
        )
        if listener.start():
            self._vosk_listener = listener
            self._emit("wake_engine", f"oww:{wake_model}")
            return {"ok": True, "model": wake_model}
        return {"ok": False, "error": "Falha ao iniciar wake listener - cheque crash.log"}

    def stop_vosk_wake(self) -> dict:
        if self._vosk_listener:
            self._vosk_listener.stop()
            self._vosk_listener = None
            self._emit("wake_engine", "stopped")
        return {"ok": True}

    # ---- Automacao (browser + YouTube + arquivos) ----------------------
    def browsers(self) -> dict:
        return {"items": automod.installed_browsers()}

    def open_url(self, url: str) -> dict:
        return automod.open_url(url, self.cfg.get("browser", "default"))

    def youtube_play(self, query: str) -> dict:
        def worker():
            r = automod.youtube_play(query, self.cfg.get("browser", "default"))
            if r.get("ok"):
                msg = f"Tocando: {r.get('title','')} - {r.get('channel','')}".strip()
                self._emit("token", msg)
                self._emit("done", msg)
            else:
                self._emit("error", f"YouTube: {r.get('error','falhou')}")
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def find_files(self, pattern: str, max_results: int = 30) -> dict:
        return {"items": automod.find_files(pattern, max_results=max_results)}

    # ---- Hardware monitor ----------------------------------------------
    def hw_stats(self) -> dict:
        return sysmon.all_stats()

    # ---- Auto-scan dispositivos ----------------------------------------
    def scan_now(self) -> dict:
        """Forca um scan imediato (ignora cache de 'seen')."""
        results = {"bluetooth": [], "cast": []}
        try:
            results["bluetooth"] = [d.to_dict() for d in btmod.scan(timeout=5)]
        except Exception: pass
        try:
            results["cast"] = castmod.list_devices(timeout=5)
        except Exception: pass
        return results

    def dismiss_device(self, key: str) -> dict:
        dscan.dismiss(key)
        return {"ok": True}

    # ---- Messaging Hub -------------------------------------------------
    def msg_save_config(self, channel: str, data: dict) -> dict:
        m = self.cfg.setdefault("messaging", {})
        m[channel] = data
        cfgmod.save(self.cfg)
        apply_config(self.cfg)
        return {"ok": True}

    def msg_telegram_send(self, text: str, chat_id: str = "") -> dict:
        return msgmod.telegram_send(self.cfg, text, chat_id or None)

    def msg_telegram_inbox(self, limit: int = 10) -> dict:
        return {"items": msgmod.telegram_get_updates(self.cfg, limit)}

    def msg_email_send(self, to: str, subject: str, body: str) -> dict:
        return msgmod.email_send(self.cfg, to, subject, body)

    def msg_email_inbox(self, limit: int = 10, unseen_only: bool = False) -> dict:
        return {"items": msgmod.email_read(self.cfg, limit, unseen_only=unseen_only)}

    def msg_whatsapp_send(self, to: str, text: str) -> dict:
        return msgmod.whatsapp_send(self.cfg, to, text)

    def contacts_list(self) -> dict:
        return {"items": msgmod.list_contacts()}

    def contacts_add(self, name: str, phone: str = "", email: str = "", telegram: str = "") -> dict:
        c = msgmod.add_contact(name, phone, email, telegram)
        apply_config(self.cfg)
        return {"ok": True, "contact": c}

    def contacts_remove(self, contact_id: int) -> dict:
        msgmod.remove_contact(int(contact_id))
        apply_config(self.cfg)
        return {"ok": True}

    def templates_list(self) -> dict:
        return {"items": msgmod.list_templates()}

    def templates_add(self, name: str, text: str) -> dict:
        t = msgmod.add_template(name, text)
        apply_config(self.cfg)
        return {"ok": True, "template": t}

    def templates_remove(self, tpl_id: int) -> dict:
        msgmod.remove_template(int(tpl_id))
        apply_config(self.cfg)
        return {"ok": True}

    # ---- RAG -----------------------------------------------------------
    def rag_status(self) -> dict:
        return {"sources": ragmod.list_sources(), "embedder": ragmod.has_embedder()}

    def rag_index(self, folder: str) -> dict:
        def worker():
            self._emit("rag_status", f"Indexando {folder}...")
            r = ragmod.index_folder(folder)
            self.cfg["rag_folder"] = folder
            cfgmod.save(self.cfg)
            apply_config(self.cfg)
            if r.get("ok"):
                self._emit("rag_status", f"OK: {r['indexed']} chunks ({r['provider']})")
            else:
                self._emit("rag_status", f"Erro: {r.get('error')}")
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def rag_remove(self, source: str) -> dict:
        return ragmod.remove_source(source)

    def rag_query(self, q: str, top_k: int = 5) -> dict:
        return {"results": ragmod.query(q, top_k)}

    # ---- STT (Whisper local) -------------------------------------------
    def transcribe(self, audio_b64: str) -> dict:
        return {"text": sttmod.transcribe_b64(audio_b64)}

    # ---- Wake offline (Vosk) -------------------------------------------
    def vosk_status(self) -> dict:
        return {"ready": wakemod.model_ready()}

    def vosk_download(self) -> dict:
        def worker():
            self._emit("vosk_progress", "0")
            def prog(d, t):
                if t: self._emit("vosk_progress", str(int(d * 100 / t)))
            ok = wakemod.download_model(on_progress=prog)
            self._emit("vosk_progress", "done" if ok else "error")
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    # ---- Ollama --------------------------------------------------------
    def ollama_status(self) -> dict:
        return llmlocal.status()

    # ---- bluetooth -----------------------------------------------------
    def ble_scan(self) -> dict:
        try:
            devs = btmod.scan(timeout=6.0)
            return {"devices": [d.to_dict() for d in devs]}
        except Exception as e:
            return {"devices": [], "error": str(e)}

    def ble_remember(self, address: str, name: str, alias: str = "") -> dict:
        bt = self.cfg.setdefault("bluetooth", {"known": []})
        bt.setdefault("known", [])
        if not any(d.get("address") == address for d in bt["known"]):
            bt["known"].append({"address": address, "name": name, "alias": alias})
            cfgmod.save(self.cfg)
            apply_config(self.cfg)
        return {"ok": True, "known": bt["known"]}

    def ble_forget(self, address: str) -> dict:
        bt = self.cfg.setdefault("bluetooth", {"known": []})
        bt["known"] = [d for d in bt.get("known", []) if d.get("address") != address]
        cfgmod.save(self.cfg)
        apply_config(self.cfg)
        return {"ok": True, "known": bt["known"]}

    # ---- dispositivos --------------------------------------------------
    def test_devices(self, url: str, token: str) -> dict:
        return devmod.test_connection(url, token).to_dict()

    def list_devices(self) -> dict:
        dev = self.cfg.get("devices") or {}
        if dev.get("provider") != "home_assistant":
            return {"entities": []}
        return {"entities": devmod.list_entities(dev.get("ha_url", ""), dev.get("ha_token", ""))}

    # ---- update --------------------------------------------------------
    def app_info(self) -> dict:
        return {"name": APP_NAME, "version": __version__}

    def check_update(self) -> dict:
        return upd.check().to_dict()

    def install_update(self, url: str) -> dict:
        def worker():
            try:
                path = upd.download_installer(url, on_progress=lambda d, t: self._emit(
                    "update_progress", f"{int(d * 100 / t)}"
                ))
                self._emit("update_ready", str(path))
                upd.install_and_restart(path)
            except Exception as e:
                self._emit("error", f"Update: {e}")
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    # ---- util ----------------------------------------------------------
    def reset(self) -> dict:
        interpreter.messages = []
        return {"ok": True}

    def _emit(self, kind: str, payload) -> None:
        if not self._window:
            return
        try:
            payload = str(payload) if not isinstance(payload, str) else payload
            safe = (
                payload.replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("$", "\\$")
            )
            self._window.evaluate_js(
                f"window.servusStream && window.servusStream('{kind}', `{safe}`)"
            )
        except Exception as e:
            _logcrash(f"_emit fail kind={kind} type={type(payload).__name__}: {e}")


def _toggle_wake_via_tray(api) -> bool:
    cur = bool(api.cfg.get("wake_enabled"))
    api.cfg["wake_enabled"] = not cur
    cfgmod.save(api.cfg)
    apply_config(api.cfg)
    api._emit("wake_toggled", "1" if api.cfg["wake_enabled"] else "0")
    return api.cfg["wake_enabled"]


def _create_app_mutex():
    """Cria mutex global pro Inno Setup detectar instancia rodando."""
    try:
        import ctypes
        ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX)
    except Exception:
        pass


def main() -> None:
    _create_app_mutex()
    api = Api()

    # auto-check de update em background (silencioso)
    def auto_check():
        info = upd.check()
        if info.available and api._window:
            api._emit("update_available", f"{info.latest}|{info.url}|{info.notes}")

    threading.Timer(3.0, auto_check).start()

    # Inicia Vosk wake se config pediu (depois da janela existir)
    def start_vosk_if_configured():
        we = api.cfg.get("wake_enabled")
        wo = api.cfg.get("wake_offline")
        _logcrash(f"wake auto-check: wake_enabled={we} wake_offline={wo}")
        if we and wo:
            try:
                r = api.start_vosk_wake()
                _logcrash(f"wake auto-start result: {r}")
            except Exception as e:
                _logcrash(f"wake auto-start EXCEPTION: {type(e).__name__}: {e}")
    threading.Timer(5.0, start_vosk_if_configured).start()

    # Scanner periodico de dispositivos
    if api.cfg.get("auto_scan_enabled", True):
        def on_new_device(d):
            api._emit("device_found", f"{d['key']}|{d['type']}|{d['name']}|{d.get('address','')}")
        scanner = dscan.DeviceScanner(
            on_new_device=on_new_device,
            interval_min=api.cfg.get("auto_scan_interval_min", 10),
        )
        scanner.start()

    # System tray
    try:
        from app.tray import Tray
        tray = Tray(
            on_show=lambda: api.show_window(),
            on_toggle_wake=lambda: _toggle_wake_via_tray(api),
            on_quit=lambda: os._exit(0),
            get_wake_state=lambda: bool(api.cfg.get("wake_enabled")),
        )
        tray.run()
    except Exception as e:
        print(f"tray: {e}")

    # Hotkeys globais
    try:
        from app.hotkeys import Hotkeys
        hk = Hotkeys(
            on_show=lambda: api.show_window(),
            on_ptt_start=lambda: api._emit("ptt_start", ""),
            on_ptt_end=lambda: api._emit("ptt_end", ""),
            on_capture_screen=lambda: api.prepare_screen(),
        )
        hk.start()
    except Exception as e:
        print(f"hotkeys: {e}")

    window = webview.create_window(
        title=api.cfg["identity"]["name"],
        url=str(INDEX),
        js_api=api,
        width=760,            # mais largo - painel nao espreme
        height=920,
        min_size=(600, 700),
        background_color="#0a0e1a",
        resizable=True,
    )

    # Auto-concede mic/camera no WebView2 (sem prompt)
    def _grant_perms(uri, allow):
        return True  # mic + camera + tudo necessario
    try:
        window.events.permission_request += _grant_perms  # type: ignore
    except Exception:
        pass
    api.bind(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
