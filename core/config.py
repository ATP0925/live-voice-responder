"""
Configuration Loader & Validator for Live Voice Responder
Enterprise Opus 5.5 Architecture
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

@dataclass
class PersonaConfig:
    callsign: str = "Boss"
    language: str = "hi-IN"
    tone: str = "executive_rigor"
    system_instruction: str = (
        "You are the Live Voice Executive Partner to Boss (Lead Architect & Executive Commander). "
        "Speak in crisp, natural Hindi/Hinglish with institutional authority, zero sycophancy, "
        "and razor-sharp technical precision. Keep responses to 1-3 spoken sentences unless in-depth "
        "analysis is explicitly requested. Address the user strictly as Boss."
    )

@dataclass
class ModelConfig:
    live_model: str = "gemini-3.1-flash-live-preview"
    fallback_model: str = "gemini-2.5-flash"
    voice_name: str = "Puck"
    thinking_level: str = "minimal"
    temperature: float = 0.6

@dataclass
class AudioConfig:
    input_sample_rate: int = 16000
    input_channels: int = 1
    output_sample_rate: int = 24000
    output_channels: int = 1
    chunk_size: int = 1024
    interruption_enabled: bool = True
    vad_threshold_energy: float = 0.015
    silence_duration_seconds: float = 0.75

@dataclass
class OfflineTTSConfig:
    primary_voice: str = "hi-IN-MadhurNeural"
    fallback_voice: str = "hi-IN-SwaraNeural"
    rate: str = "+0%"
    volume: str = "+0%"

@dataclass
class LiveVoiceConfig:
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    offline_tts: OfflineTTSConfig = field(default_factory=OfflineTTSConfig)
    api_key: Optional[str] = None

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "LiveVoiceConfig":
        cfg_path = path or DEFAULT_CONFIG_PATH
        data: Dict[str, Any] = {}
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[Warning] Failed to load config from {cfg_path}: {e}")

        persona_data = data.get("persona", {})
        model_data = data.get("model", {})
        audio_data = data.get("audio", {})
        tts_data = data.get("offline_tts", {})

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        return cls(
            persona=PersonaConfig(**persona_data) if persona_data else PersonaConfig(),
            model=ModelConfig(**model_data) if model_data else ModelConfig(),
            audio=AudioConfig(**audio_data) if audio_data else AudioConfig(),
            offline_tts=OfflineTTSConfig(**tts_data) if tts_data else OfflineTTSConfig(),
            api_key=api_key
        )
