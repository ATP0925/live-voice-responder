#!/usr/bin/env python3
"""
Universal Live Voice Responder — Full Duplex Multimodal CLI
Featuring Gemini Live Style Dynamic Voice Wave & Glowing Status Visualizer
Command Center for Boss (Lead Architect & Executive Commander)
"""

import sys
import os
import signal
import asyncio
from pathlib import Path
from rich.live import Live

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import LiveVoiceConfig
from core.engine import UniversalLiveVoiceEngine
from core.interruption import ConversationState
from ui.terminal_hud import TerminalHUD

hud = TerminalHUD(callsign="Boss")

def on_transcript_received(speaker: str, text: str):
    hud.add_message(speaker, text)

def on_state_changed(state: ConversationState):
    hud.update_state(state.value)

def on_energy_received(energy: float):
    hud.update_energy(energy)

async def main():
    config = LiveVoiceConfig.load()
    hud.callsign = config.persona.callsign
    hud.render_header()

    engine = UniversalLiveVoiceEngine(
        config=config,
        on_transcript=on_transcript_received,
        on_state_change=on_state_changed,
        on_energy=on_energy_received
    )

    # Launch Dynamic 15 FPS Live Waveform Visualizer
    with Live(hud.generate_status_panel(), refresh_per_second=15, auto_refresh=True) as live:
        hud.live_display = live

        async def visualizer_loop():
            try:
                while True:
                    live.update(hud.generate_status_panel())
                    await asyncio.sleep(0.06)
            except asyncio.CancelledError:
                pass

        render_task = asyncio.create_task(visualizer_loop())

        def shutdown():
            render_task.cancel()
            engine.stop()

        try:
            await engine.start()
        except KeyboardInterrupt:
            shutdown()
        except Exception as e:
            hud.add_message("System", f"Error: {e}")
            shutdown()
        finally:
            render_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting Live Voice Responder. Goodbye Boss!")
