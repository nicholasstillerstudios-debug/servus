"""Wake word detection - OpenWakeWord puro, sem Whisper.

Quando detecta wake, EMITE evento pro JS capturar o comando via Web Speech.
Web Speech em modo burst (5s, nao-continuo) e MUITO mais confiavel que
o modo continuo + nao depende de modelo baixado.
"""

from __future__ import annotations

import os
import queue
import threading
import traceback
from pathlib import Path
from typing import Callable


OWW_MODELS = ["hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy"]
DEFAULT_OWW_MODEL = "hey_jarvis"


def _logcrash(msg: str) -> None:
    try:
        log = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus" / "crash.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def model_ready() -> bool:
    try:
        import openwakeword
        pkg = Path(openwakeword.__file__).parent
        models_path = pkg / "resources" / "models"
        required = ["hey_jarvis_v0.1.onnx", "embedding_model.onnx", "melspectrogram.onnx"]
        return all((models_path / r).exists() for r in required)
    except Exception:
        return False


def download_model(on_progress: Callable[[int, int], None] | None = None) -> bool:
    try:
        import openwakeword
        if on_progress: on_progress(0, 100)
        openwakeword.utils.download_models()
        if on_progress: on_progress(100, 100)
        return True
    except Exception:
        _logcrash(f"oww download fail: {traceback.format_exc()}")
        return False


def has_input_device() -> bool:
    try:
        import sounddevice as sd
        for d in sd.query_devices():
            if d.get("max_input_channels", 0) > 0:
                return True
        return False
    except Exception:
        return False


def available_models() -> list[str]:
    return list(OWW_MODELS)


class WakeListener:
    """OpenWakeWord puro. Quando detecta, chama on_wake_fire() sem texto.
    O JS captura o comando depois via Web Speech burst.
    """

    def __init__(
        self,
        wake_words: list[str] | str = "",   # compat - ignorado
        on_wake: Callable[[str], None] = None,
        on_error: Callable[[str], None] | None = None,
        wake_model: str = DEFAULT_OWW_MODEL,
        threshold: float = 0.5,
        capture_seconds: float = 5.0,   # compat - ignorado
    ):
        self.wake_model = wake_model if wake_model in OWW_MODELS else DEFAULT_OWW_MODEL
        # on_wake recebera string vazia "" - indica pro JS comecar burst
        self.on_wake = on_wake or (lambda t: None)
        self.on_error = on_error or (lambda m: None)
        self.threshold = threshold
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._paused = False

    def start(self) -> bool:
        if not has_input_device():
            self.on_error("Nenhum microfone detectado")
            return False
        try:
            import openwakeword  # noqa
            import sounddevice as sd  # noqa
            import numpy as np  # noqa
        except Exception as e:
            _logcrash(f"oww imports fail: {e}")
            self.on_error(f"OpenWakeWord indisponivel: {e}")
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_safe, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def _run_safe(self):
        try:
            self._run()
        except Exception as e:
            tb = traceback.format_exc()
            _logcrash(f"oww _run_safe top-level fail:\n{tb}")
            try: self.on_error(f"Wake crashou: {type(e).__name__}: {str(e)[:200]}")
            except Exception: pass

    def _run(self):
        import numpy as np
        import openwakeword
        from openwakeword.model import Model as OwwModel
        import sounddevice as sd

        # 1) garante modelos baixados (no-op se ja tem)
        try: openwakeword.utils.download_models()
        except Exception: pass

        # 2) carrega detector
        try:
            oww = OwwModel(
                wakeword_models=[self.wake_model],
                inference_framework="onnx",
            )
            _logcrash(f"oww loaded: {self.wake_model}")
        except Exception as e:
            _logcrash(f"OwwModel fail: {traceback.format_exc()}")
            self.on_error(f"OpenWakeWord load fail: {e}")
            return

        # 3) prepara stream com fallbacks
        q: queue.Queue = queue.Queue(maxsize=100)

        def cb(indata, frames, time, status):
            try:
                if not q.full(): q.put(bytes(indata))
            except Exception: pass

        device_idx = None
        extra = None
        try:
            for i, ha in enumerate(sd.query_hostapis()):
                if "WASAPI" in (ha.get("name") or ""):
                    di = ha.get("default_input_device", -1)
                    if di is not None and di >= 0: device_idx = di
                    break
            extra = sd.WasapiSettings(exclusive=False)
        except Exception:
            extra = None

        stream = None
        actual_rate = 16000
        need_resample = False

        # cascata: 16k native -> native-rate + resample
        for attempt in [
            {"device": device_idx, "extra_settings": extra},
            {"device": device_idx, "extra_settings": None},
            {"device": None, "extra_settings": None},
        ]:
            try:
                stream = sd.RawInputStream(
                    samplerate=16000, blocksize=1280, dtype="int16",
                    channels=1, callback=cb, **attempt,
                )
                stream.start()
                _logcrash(f"oww stream 16k OK: {attempt}")
                break
            except Exception as e:
                _logcrash(f"oww stream 16k fail {attempt}: {e}")

        if stream is None:
            try:
                info = sd.query_devices(device_idx, kind="input")
                actual_rate = int(info.get("default_samplerate") or 48000)
                need_resample = (actual_rate != 16000)
                blocksize = int(actual_rate * 0.08)
                for attempt in [
                    {"device": device_idx, "extra_settings": None},
                    {"device": None, "extra_settings": None},
                ]:
                    try:
                        stream = sd.RawInputStream(
                            samplerate=actual_rate, blocksize=blocksize,
                            dtype="int16", channels=1, callback=cb, **attempt,
                        )
                        stream.start()
                        _logcrash(f"oww stream {actual_rate}Hz OK (resample={need_resample})")
                        break
                    except Exception as e:
                        _logcrash(f"oww stream {actual_rate}Hz fail: {e}")
            except Exception as e:
                _logcrash(f"oww native rate fail: {e}")

        if stream is None:
            self.on_error("Nao conseguiu abrir mic")
            return

        # resampler se preciso
        resampler = None
        if need_resample:
            try:
                from scipy.signal import resample_poly
                from math import gcd
                g = gcd(16000, actual_rate)
                up = 16000 // g
                down = actual_rate // g
                resampler = lambda a: resample_poly(a, up, down)
            except Exception as e:
                _logcrash(f"resampler fail: {e}")
                self.on_error(f"Resample falhou: {e}")
                try: stream.stop(); stream.close()
                except Exception: pass
                return

        # 4) LOOP - so detecta wake e dispara evento
        last_trigger_time = [0.0]
        DEBOUNCE_SECONDS = 3.0   # nao dispara 2x em <3s

        try:
            while not self._stop.is_set():
                if self._paused:
                    self._stop.wait(0.2)
                    continue

                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                try:
                    audio_np = np.frombuffer(data, dtype=np.int16)
                    if len(audio_np) == 0: continue
                    if resampler is not None:
                        audio_f = audio_np.astype(np.float32)
                        audio_f = resampler(audio_f)
                        audio_np = audio_f.astype(np.int16)
                    if len(audio_np) >= 1280:
                        audio_np = audio_np[:1280]
                    preds = oww.predict(audio_np)
                    conf = preds.get(self.wake_model, 0) or 0
                except Exception as e:
                    _logcrash(f"predict fail: {e}")
                    continue

                if conf < self.threshold:
                    continue

                # debounce
                import time
                now = time.time()
                if now - last_trigger_time[0] < DEBOUNCE_SECONDS:
                    continue
                last_trigger_time[0] = now

                _logcrash(f"WAKE FIRE! conf={conf:.2f}")

                # dispara evento - JS captura comando via Web Speech
                try:
                    self.on_wake("")   # string vazia = "comece a escutar"
                except Exception as e:
                    _logcrash(f"on_wake fail: {e}")

                # reset OWW pra evitar trigger duplo
                try: oww.reset()
                except Exception: pass

                # esvazia queue (audio gravado durante o trigger)
                while not q.empty():
                    try: q.get_nowait()
                    except queue.Empty: break

        finally:
            try: stream.stop(); stream.close()
            except Exception: pass
            _logcrash("oww loop ended")
