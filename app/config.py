"""Carrega/salva configuracao do SERVUS em %APPDATA%\\Servus\\config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT: dict[str, Any] = {
    "identity": {
        "name": "SERVUS",
        "persona": (
            "Assistente pessoal do Nicholas. Direto, tecnico, leal. "
            "Resolve problemas em vez de descrever. Quando age no PC, "
            "explica brevemente o que fez."
        ),
    },
    "voice": "pt-BR-AntonioNeural",
    "rate": "+5%",
    "pitch": "+0Hz",
    "mood": "neutro",
    "accent": "padrao",
    "model": "auto",  # auto | claude | openai | ollama
    "speed": "balanced",   # fast (Haiku) | balanced (Sonnet, default seguro) | smart (Opus)
    "enabled_skills": [],  # nomes das skills ativas
    "wake_enabled": False,
    "wake_word": "",  # LEGADO - usado so com Web Speech
    "wake_words": [], # usado so com Web Speech (multi-palavras)
    "wake_model_offline": "hey_jarvis",  # modelo OpenWakeWord pre-treinado (hey_jarvis|alexa|hey_mycroft|hey_rhasspy)
    "screen_mode": False,         # anexa screenshot em TODA mensagem (visao continua)
    "auto_scan_enabled": True,    # scanner periodico de dispositivos
    "auto_scan_interval_min": 10, # de quanto em quanto tempo (minutos)
    "browser": "default",         # browser para abrir URLs (default/chrome/edge/firefox/brave/opera)
    "show_code": False,           # mostra blocos de codigo/saida no chat (modo dev)
    "devices": {
        "provider": "none",   # none | home_assistant
        "ha_url": "",
        "ha_token": "",
    },
    "bluetooth": {
        "known": [],  # [{address, name, alias}]
    },
    # Path 3 (performance)
    "stt_engine": "browser",        # browser | whisper_local
    "streaming_tts": True,
    "barge_in": True,
    "wake_offline": False,           # usa Vosk em vez de Web Speech
    "ollama_model": "",              # override do modelo Ollama (vazio = llama3.1)
    # Path 1 (inteligencia)
    "auto_retry": True,              # tenta de novo em erro
    "multi_step_mode": False,        # forca planejamento em etapas
    "rag_folder": "",                # ultima pasta indexada
    "messaging": {
        "telegram": {"token": "", "chat_id": ""},
        "email": {
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "imap_host": "imap.gmail.com", "imap_port": 993,
            "user": "", "password": "",
        },
        "whatsapp": {"webhook_url": "", "webhook_secret": ""},
    },
}

# ---- catalogos ----------------------------------------------------------

VOICES = [
    {"id": "pt-BR-AntonioNeural",            "label": "Antonio (masc)"},
    {"id": "pt-BR-FranciscaNeural",          "label": "Francisca (fem, neutra)"},
    {"id": "pt-BR-ThalitaNeural",            "label": "Thalita (fem, energetica)"},
    {"id": "pt-BR-ThalitaMultilingualNeural","label": "Thalita Multilingual (fem)"},
]

VALID_VOICE_IDS = {v["id"] for v in VOICES}


# Presets pre-configurados (voice + rate + pitch + mood)
# So usam vozes que REALMENTE existem no Edge TTS pt-BR
VOICE_PRESETS = [
    {
        "id": "jarvis", "label": "🤖 JARVIS",
        "description": "Grave, calmo, formal",
        "voice": "pt-BR-AntonioNeural", "rate": "-5%", "pitch": "-20Hz", "mood": "formal",
    },
    {
        "id": "tony_stark", "label": "🦾 Tony Stark",
        "description": "Sarcastico afiado",
        "voice": "pt-BR-AntonioNeural", "rate": "+5%", "pitch": "+0Hz", "mood": "sarcastico",
    },
    {
        "id": "locutor", "label": "📻 Locutor",
        "description": "Voz de radio, grave e cadenciada",
        "voice": "pt-BR-AntonioNeural", "rate": "-8%", "pitch": "-12Hz", "mood": "serio",
    },
    {
        "id": "noir", "label": "🎬 Detetive Noir",
        "description": "Misterioso, voz cavernosa",
        "voice": "pt-BR-AntonioNeural", "rate": "-12%", "pitch": "-30Hz", "mood": "serio",
    },
    {
        "id": "narrador", "label": "📖 Narrador",
        "description": "Ritmo de leitura",
        "voice": "pt-BR-AntonioNeural", "rate": "-3%", "pitch": "+0Hz", "mood": "neutro",
    },
    {
        "id": "coach", "label": "💪 Coach motivacional",
        "description": "Energia alta, agudo",
        "voice": "pt-BR-AntonioNeural", "rate": "+15%", "pitch": "+15Hz", "mood": "motivacional",
    },
    {
        "id": "acolhedora", "label": "🌸 Acolhedora",
        "description": "Calma, feminina",
        "voice": "pt-BR-FranciscaNeural", "rate": "+0%", "pitch": "+0Hz", "mood": "neutro",
    },
    {
        "id": "secretaria", "label": "💼 Secretaria executiva",
        "description": "Profissional, ritmo agil",
        "voice": "pt-BR-FranciscaNeural", "rate": "+10%", "pitch": "+0Hz", "mood": "formal",
    },
    {
        "id": "energetica", "label": "⚡ Energetica",
        "description": "Voz jovem e animada",
        "voice": "pt-BR-ThalitaNeural", "rate": "+8%", "pitch": "+5Hz", "mood": "motivacional",
    },
    {
        "id": "padrao", "label": "⚙ Padrao SERVUS",
        "description": "Voz neutra inicial",
        "voice": "pt-BR-AntonioNeural", "rate": "+5%", "pitch": "+0Hz", "mood": "neutro",
    },
]

MOODS = {
    "neutro":        "Tom neutro e profissional. Sem firulas.",
    "formal":        "Tom formal e cerimonioso. Trate o usuario com cortesia explicita.",
    "brincalhao":    "Tom leve e bem-humorado. Use trocadilhos e ironia branda quando fizer sentido.",
    "sarcastico":    "Tom sarcastico afiado, mas nunca ofensivo. Ironia inteligente, no estilo do Jarvis do Tony Stark.",
    "motivacional":  "Tom encorajador. Reforce vitorias, transforme problemas em proximos passos acionaveis.",
    "serio":         "Tom serio e objetivo. Zero floreios. Vai direto a resposta.",
}

ACCENTS = {
    "padrao":      "Use portugues brasileiro padrao, neutro.",
    "carioca":     "Use sotaque e girias cariocas (Rio de Janeiro): 'mermao', 'caraca', 'sinistro', 'maneiro', 'partiu'.",
    "nordestino":  "Use expressoes nordestinas: 'massa', 'oxe', 'vish', 'eita', 'visse'. Calorosidade no tom.",
    "mineiro":     "Use jeito mineiro: 'uai', 'trem', 'sô', 'cê', com fala acolhedora.",
    "gaucho":      "Use jeito gaucho: 'tche', 'bah', 'guri', 'tri', 'capaz!'.",
    "paulista":    "Use jeito paulistano urbano: direto, 'mano', 'meu', 'beleza', 'tipo assim'.",
    "portugues":   "Use portugues europeu: 'fixe', 'giro', 'estou a fazer', 'pequeno-almoco', 'autocarro'.",
}


def load() -> dict:
    cfg = json.loads(json.dumps(DEFAULT))
    if CONFIG_FILE.exists():
        try:
            # utf-8-sig strip BOM automaticamente (PowerShell Out-File escreve com BOM)
            text = CONFIG_FILE.read_text(encoding="utf-8-sig")
            data = json.loads(text)
            cfg = _merge(DEFAULT, data)
        except Exception as e:
            # log em vez de silenciar - bug grave que estava escondido
            try:
                import traceback
                log = CONFIG_FILE.parent / "crash.log"
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"config.load FAIL (usando DEFAULT): {type(e).__name__}: {e}\n")
                    f.write(traceback.format_exc() + "\n")
            except Exception:
                pass
    # auto-migra voice invalida pra default
    if cfg.get("voice") not in VALID_VOICE_IDS:
        cfg["voice"] = "pt-BR-AntonioNeural"
    return cfg


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = _merge(DEFAULT, cfg)
    CONFIG_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge(base: dict, override: dict) -> dict:
    out = json.loads(json.dumps(base))
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def build_system_message(cfg: dict) -> str:
    name = cfg["identity"]["name"]
    persona = cfg["identity"]["persona"]
    mood = MOODS.get(cfg["mood"], MOODS["neutro"])
    accent = ACCENTS.get(cfg["accent"], ACCENTS["padrao"])
    base = (
        f"Voce e {name}. {persona}\n\n"
        f"Estilo: {mood}\n"
        f"Linguagem: {accent}\n"
        f"Plataforma: Windows. Use Python/Shell/PowerShell para executar tarefas. "
        f"Quando agir, explique em uma frase o que fez."
    )
    if cfg.get("multi_step_mode"):
        base += (
            "\n\nMODO MULTI-ETAPA: Para pedidos complexos, primeiro explique brevemente "
            "seu PLANO em 2-5 passos numerados. So depois execute. Apos cada passo, "
            "informe o resultado antes de seguir. Se algo falhar, ajuste o plano."
        )
    if cfg.get("auto_retry"):
        base += (
            "\n\nAUTO-CORRECAO: Se um comando falhar, NAO desista. Analise o erro, "
            "tente uma abordagem alternativa, e so reporte falha apos 2-3 tentativas."
        )
    return base


SPEED_MODES = [
    {"id": "fast",     "label": "⚡ Rapido (Haiku)",     "model": "claude-haiku-4-5"},
    {"id": "balanced", "label": "⚖ Equilibrado (Sonnet)", "model": "claude-sonnet-4-5"},
    {"id": "smart",    "label": "🧠 Inteligente (Opus)", "model": "claude-opus-4-7"},
]


def catalogs() -> dict:
    return {
        "voices": VOICES,
        "voice_presets": VOICE_PRESETS,
        "speed_modes": SPEED_MODES,
        "moods":  [{"id": k, "label": k.capitalize()} for k in MOODS],
        "accents": [{"id": k, "label": k.capitalize()} for k in ACCENTS],
        "models": [
            {"id": "auto",   "label": "Auto (detecta API key)"},
            {"id": "claude", "label": "Claude (Anthropic)"},
            {"id": "openai", "label": "GPT (OpenAI)"},
            {"id": "ollama", "label": "Ollama (local)"},
        ],
    }
