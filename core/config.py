"""
Universal Configuration Loader & Validator for Live Voice Responder
Supports multi-provider configuration (Auto, Gemini, OpenAI, Anthropic, Local)
Enterprise Opus 5.5 Architecture
"""

import os
import json
import dataclasses
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
        "You are the Universal Live Voice Executive Partner to Boss (Lead Architect & Executive Commander). "
        "Speak in crisp, natural Hindi/Hinglish with institutional authority, zero sycophancy, "
        "and razor-sharp technical precision. Keep responses to 1-3 spoken sentences unless in-depth "
        "analysis is explicitly requested. Address the user strictly as Boss."
    )

@dataclass
class EngineConfig:
    provider: str = "auto"
    live_model: str = "gemini-3.1-flash-live-preview"
    voice_name: str = "Puck"
    thinking_level: str = "minimal"
    openai_model: str = "gpt-4o-realtime-preview"
    openai_voice: str = "alloy"
    anthropic_model: str = "claude-3-7-sonnet"

ModelConfig = EngineConfig

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
    input_device_index: Optional[int] = None
    output_device_index: Optional[int] = None

@dataclass
class OfflineTTSConfig:
    primary_voice: str = "hi-IN-MadhurNeural"
    fallback_voice: str = "hi-IN-SwaraNeural"
    rate: str = "+0%"
    volume: str = "+0%"

@dataclass
class LiveVoiceConfig:
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    offline_tts: OfflineTTSConfig = field(default_factory=OfflineTTSConfig)
    target_agent: str = "auto"

    # Backward compatibility properties
    @property
    def model(self):
        return self.engine

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
        engine_data = data.get("engine", {}) or data.get("model", {})
        audio_data = data.get("audio", {})
        tts_data = data.get("offline_tts", {})
        agent_data = data.get("agent_bridge", {})

        # Extract nested provider specs if present
        provider = engine_data.get("provider", "auto")
        gemini_cfg = engine_data.get("gemini", {})
        openai_cfg = engine_data.get("openai", {})
        anthropic_cfg = engine_data.get("anthropic", {})

        engine_obj = EngineConfig(
            provider=provider,
            live_model=gemini_cfg.get("model", engine_data.get("live_model", "gemini-3.1-flash-live-preview")),
            voice_name=gemini_cfg.get("voice_name", engine_data.get("voice_name", "Puck")),
            thinking_level=gemini_cfg.get("thinking_level", engine_data.get("thinking_level", "minimal")),
            openai_model=openai_cfg.get("model", "gpt-4o-realtime-preview"),
            openai_voice=openai_cfg.get("voice_name", "alloy"),
            anthropic_model=anthropic_cfg.get("model", "claude-3-7-sonnet")
        )

        def _filter_known(target_cls, raw_data):
            if not isinstance(raw_data, dict):
                return {}
            known_fields = {f.name for f in dataclasses.fields(target_cls)}
            return {k: v for k, v in raw_data.items() if k in known_fields}

        return cls(
            persona=PersonaConfig(**_filter_known(PersonaConfig, persona_data)),
            engine=engine_obj,
            audio=AudioConfig(**_filter_known(AudioConfig, audio_data)),
            offline_tts=OfflineTTSConfig(**_filter_known(OfflineTTSConfig, tts_data)),
            target_agent=data.get("target_agent") or (agent_data.get("target_agent", "auto") if isinstance(agent_data, dict) else "auto")
        )

    def resolve_active_provider(self) -> str:
        """Determines provider based on configuration and available environment keys."""
        if self.engine.provider != "auto":
            return self.engine.provider

        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            return "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        return "local"
