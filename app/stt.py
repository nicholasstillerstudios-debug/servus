"""Speech-to-text local via faster-whisper. Modelo baixa na 1a vez."""

from __future__ import annotations

import base64
import io
import os
import tempfile
from pathlib import Path

_model = None


def models_dir() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus" / "models"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_model(size: str = "tiny"):
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    cache = models_dir() / f"whisper-{size}"
    try:
        _model = WhisperModel(
            size, device="cpu", compute_type="int8",
            download_root=str(cache),
        )
        return _model
    except Exception as e:
        print(f"whisper load fail: {e}")
        return None


def transcribe_b64(audio_b64: str, language: str = "pt") -> str:
    """Recebe audio webm/ogg/wav em base64, retorna texto."""
    model = _load_model()
    if model is None:
        return ""
    try:
        data = base64.b64decode(audio_b64)
        # salva em arquivo temporario - faster-whisper aceita path direto
        tmp = Path(tempfile.gettempdir()) / "servus_stt.webm"
        tmp.write_bytes(data)
        segs, info = model.transcribe(str(tmp), language=language, beam_size=1, vad_filter=True)
        text = " ".join(s.text for s in segs).strip()
        try: tmp.unlink()
        except Exception: pass
        return text
    except Exception as e:
        print(f"transcribe fail: {e}")
        return ""
