"""
Universal Live Voice Responder Core Modules
Compatible across Claude Code, Cursor, Codex, Antigravity, and Local AI.
"""

from .config import LiveVoiceConfig, PersonaConfig, AudioConfig, EngineConfig
from .audio_stream import AudioStreamManager
from .interruption import InterruptionCoordinator, ConversationState
from .fallback_tts import FallbackTTS
from .tools import execute_system_command, read_workspace_file, inject_agent_chat, inject_antigravity_chat
from .engine import UniversalLiveVoiceEngine, GeminiLiveEngine

__all__ = [
    "LiveVoiceConfig",
    "PersonaConfig",
    "AudioConfig",
    "EngineConfig",
    "AudioStreamManager",
    "InterruptionCoordinator",
    "ConversationState",
    "FallbackTTS",
    "execute_system_command",
    "read_workspace_file",
    "inject_agent_chat",
    "inject_antigravity_chat",
    "UniversalLiveVoiceEngine",
    "GeminiLiveEngine"
]
