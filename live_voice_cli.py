#!/usr/bin/env python3
"""
Live Voice Responder — Gemini Live Multimodal Full Duplex CLI
Command Center for Boss (Lead Architect & Executive Commander)
"""

import sys
import os
import signal
import asyncio
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import LiveVoiceConfig
from core.engine import GeminiLiveEngine
from core.interruption import ConversationState
from ui.terminal_hud import TerminalHUD

hud = TerminalHUD(callsign="Boss")

def on_transcript_received(speaker: str, text: str):
    hud.add_message(speaker, text)

def on_state_changed(state: ConversationState):
    hud.update_state(state.value)

async def main():
    config = LiveVoiceConfig.load()
    hud.callsign = config.persona.callsign
    hud.render_header()

    engine = GeminiLiveEngine(
        config=config,
        on_transcript=on_transcript_received,
        on_state_change=on_state_changed
    )

    loop = asyncio.get_running_loop()

    # Handle graceful exit
    def shutdown():
        print("\n[Shutdown] Stopping Live Voice Engine...")
        engine.stop()

    try:
        await engine.start()
    except KeyboardInterrupt:
        shutdown()
    except Exception as e:
        print(f"\n[Fatal Error]: {e}")
        shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting Live Voice Responder. Goodbye Boss!")
