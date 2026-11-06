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
import argparse
from pathlib import Path
from rich.live import Live
from rich.console import Console
from rich.table import Table

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import LiveVoiceConfig
from core.engine import UniversalLiveVoiceEngine
from core.audio_stream import AudioStreamManager
from core.interruption import ConversationState
from ui.terminal_hud import TerminalHUD

hud = TerminalHUD(callsign="Boss")
console = Console()

def on_transcript_received(speaker: str, text: str):
    hud.add_message(speaker, text)

def on_state_changed(state: ConversationState):
    hud.update_state(state.value)

def on_energy_received(energy: float):
    hud.update_energy(energy)

def print_audio_devices():
    """Prints a clean, formatted table of all audio hardware devices."""
    devices = AudioStreamManager.list_audio_devices()
    if not devices:
        console.print("[yellow]No audio devices found or sounddevice unavailable.[/yellow]")
        return

    table = Table(title="🎙️ SYSTEM AUDIO HARDWARE DEVICES", header_style="bold cyan")
    table.add_column("Index", justify="right", style="bold green", width=6)
    table.add_column("Device Name", style="white")
    table.add_column("Inputs", justify="center", style="cyan", width=8)
    table.add_column("Outputs", justify="center", style="magenta", width=8)
    table.add_column("Default Rate", justify="right", style="yellow", width=14)

    for idx, dev in enumerate(devices):
        name = dev.get("name", "Unknown")
        max_in = dev.get("max_input_channels", 0)
        max_out = dev.get("max_output_channels", 0)
        samplerate = f"{int(dev.get('default_samplerate', 0))} Hz"
        
        # Highlight input devices (microphones/headsets)
        row_style = "bold white" if max_in > 0 else "dim"
        table.add_row(str(idx), name, str(max_in), str(max_out), samplerate, style=row_style)

    console.print(table)
    console.print("\n[dim]Usage: Launch with --device <Index> to target specific headset or phone mic.[/dim]\n")

def parse_args():
    parser = argparse.ArgumentParser(description="Live Voice Responder Duplex CLI for Boss")
    parser.add_argument("--list-devices", action="store_true", help="List all sound input/output devices and exit")
    parser.add_argument("--device", type=int, default=None, help="Input microphone device index")
    parser.add_argument("--output-device", type=int, default=None, help="Speaker output device index")
    parser.add_argument("--agent", type=str, default=None, help="Target agent (antigravity, claude, cursor, codex)")
    parser.add_argument("--lang", type=str, default=None, help="Speech recognition language (e.g. en-IN, hi-IN, en-US)")
    parser.add_argument("--mute", action="store_true", help="Start in muted/paused state")
    return parser.parse_args()

async def main():
    args = parse_args()
    if args.list_devices:
        print_audio_devices()
        return

    config = LiveVoiceConfig.load()
    if args.device is not None:
        config.audio.input_device_index = args.device
    if args.output_device is not None:
        config.audio.output_device_index = args.output_device
    if args.agent:
        config.target_agent = args.agent
    if args.lang:
        config.persona.language = args.lang

    hud.callsign = config.persona.callsign
    hud.render_header()

    engine = UniversalLiveVoiceEngine(
        config=config,
        on_transcript=on_transcript_received,
        on_state_change=on_state_changed,
        on_energy=on_energy_received
    )

    if args.mute:
        engine.is_muted = True

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
