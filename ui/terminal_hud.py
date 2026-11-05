"""
Terminal HUD Interface for Live Voice Responder
Features Gemini Live Style Dynamic Audio Wave Animation & Real-Time VU Meter.
"""

import sys
import time
import math
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align

console = Console()

WAVE_CHARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
ORB_FRAMES = [
    "[cyan](  ●  )[/cyan]",
    "[bright_cyan]( ◉ ◉ )[/bright_cyan]",
    "[bold cyan](  ◯  )[/bold cyan]",
    "[bright_blue]( ✦ ✦ )[/bright_blue]",
    "[cyan](  ●  )[/cyan]"
]

class TerminalHUD:
    def __init__(self, callsign: str = "Boss"):
        self.callsign = callsign
        self.messages: List[Tuple[str, str, str]] = []
        self.state = "LISTENING"
        self.current_energy = 0.0
        self.peak_energy = 0.0
        self.frame_idx = 0
        self.last_update = time.time()
        self.interruption_count = 0
        self.turns_count = 0
        self.live_display: Live = None

    def add_message(self, speaker: str, text: str):
        timestamp = time.strftime("%H:%M:%S")
        self.messages.append((speaker, text, timestamp))
        if len(self.messages) > 10:
            self.messages.pop(0)

        # Print message into console history
        msg_str = ""
        if speaker == self.callsign or speaker == "Boss":
            msg_str = f"[bold cyan]🎙️ {speaker}:[/bold cyan] [white]{text}[/white]"
        elif speaker == "Agent":
            msg_str = f"[bold green]🤖 Agent:[/bold green] [italic #38bdf8]{text}[/italic #38bdf8]"
        elif speaker == "System":
            msg_str = f"[yellow]⚡ System:[/yellow] {text}"
        else:
            msg_str = f"[{speaker}]: {text}"

        if self.live_display:
            self.live_display.console.print(msg_str)
        else:
            console.print(msg_str)

    def update_state(self, state: str):
        self.state = state

    def update_energy(self, energy: float):
        self.current_energy = energy
        if energy > self.peak_energy:
            self.peak_energy = energy
        else:
            self.peak_energy = max(0.0, self.peak_energy * 0.95)

    def generate_wave_bars(self, num_bars: int = 24) -> Text:
        """Generates dynamic audio equalizer wave based on mic energy & harmonics."""
        t = time.time() * 6.0
        e = min(1.0, self.current_energy * 18.0)  # Sensitivity boost
        text = Text()

        for i in range(num_bars):
            # Harmonic sine wave modulation around center
            center_dist = abs(i - (num_bars / 2)) / (num_bars / 2)
            wave_mod = math.sin(t + i * 0.5) * 0.5 + 0.5
            height = int((e * (1.0 - center_dist * 0.5) * wave_mod) * (len(WAVE_CHARS) - 1))
            height = max(0, min(len(WAVE_CHARS) - 1, height))
            char = WAVE_CHARS[height]

            # Color coding by intensity
            if height >= 7:
                style = "bold red"
            elif height >= 5:
                style = "bold yellow"
            elif height >= 3:
                style = "bold green"
            elif height >= 1:
                style = "bold cyan"
            else:
                style = "dim cyan"

            text.append(char, style=style)
            text.append(" ")

        return text

    def generate_status_panel(self) -> Panel:
        """Renders Gemini Live style glowing status & wave animation widget."""
        self.frame_idx = (self.frame_idx + 1) % len(ORB_FRAMES)
        orb = ORB_FRAMES[self.frame_idx]

        # State badge & color
        if self.state == "MUTED":
            orb = "[bold red]( ✕ ✕ )[/bold red]"
            status_badge = "[bold red]🔇 MIC MUTED / PAUSED (Press F9 to Resume)[/bold red]"
            vu_meter = "[bold red][MUTED][/bold red] -∞dB"
            waveform = Text("— " * 22, style="dim red")
            border_col = "bold red"
            panel_title = f"[bold red]🔇 LIVE VOICE PAUSED[/bold red] [dim]({self.callsign}) — Press F9 to Unmute[/dim]"
        elif self.state == "LISTENING":
            border_col = "cyan" if self.current_energy <= 0.015 else "bright_green"
            panel_title = f"[bold cyan]🎙️ GEMINI LIVE DUPLEX HUD[/bold cyan] [dim]({self.callsign})[/dim]"
            waveform = self.generate_wave_bars(num_bars=22)
            db = int(20 * math.log10(max(1e-5, self.current_energy)))
            meter_filled = min(15, max(0, int((self.current_energy * 50))))
            vu_meter = f"[bold green]{'█' * meter_filled}[/bold green][dim grey]{'░' * (15 - meter_filled)}[/dim grey] {db}dB"
            if self.current_energy > 0.015:
                status_badge = "[bold green]● HEARING YOU (Speaking)[/bold green]"
            else:
                status_badge = "[bold cyan]● LISTENING (Speak anytime | F9 to Mute)[/bold cyan]"
        elif self.state == "PROCESSING":
            border_col = "yellow"
            panel_title = f"[bold cyan]🎙️ GEMINI LIVE DUPLEX HUD[/bold cyan] [dim]({self.callsign})[/dim]"
            waveform = self.generate_wave_bars(num_bars=22)
            db = int(20 * math.log10(max(1e-5, self.current_energy)))
            meter_filled = min(15, max(0, int((self.current_energy * 50))))
            vu_meter = f"[bold green]{'█' * meter_filled}[/bold green][dim grey]{'░' * (15 - meter_filled)}[/dim grey] {db}dB"
            status_badge = "[bold yellow]✦ PROCESSING SPEECH...[/bold yellow]"
        elif self.state == "SPEAKING":
            border_col = "magenta"
            panel_title = f"[bold cyan]🎙️ GEMINI LIVE DUPLEX HUD[/bold cyan] [dim]({self.callsign})[/dim]"
            waveform = self.generate_wave_bars(num_bars=22)
            db = int(20 * math.log10(max(1e-5, self.current_energy)))
            meter_filled = min(15, max(0, int((self.current_energy * 50))))
            vu_meter = f"[bold green]{'█' * meter_filled}[/bold green][dim grey]{'░' * (15 - meter_filled)}[/dim grey] {db}dB"
            status_badge = "[bold magenta]🔊 AGENT SPEAKING...[/bold magenta]"
        elif self.state == "INTERRUPTED":
            border_col = "bold red"
            panel_title = f"[bold cyan]🎙️ GEMINI LIVE DUPLEX HUD[/bold cyan] [dim]({self.callsign})[/dim]"
            waveform = self.generate_wave_bars(num_bars=22)
            db = int(20 * math.log10(max(1e-5, self.current_energy)))
            meter_filled = min(15, max(0, int((self.current_energy * 50))))
            vu_meter = f"[bold green]{'█' * meter_filled}[/bold green][dim grey]{'░' * (15 - meter_filled)}[/dim grey] {db}dB"
            status_badge = "[bold red]🛑 BARGE-IN INTERRUPTED[/bold red]"
        else:
            border_col = "cyan"
            panel_title = f"[bold cyan]🎙️ GEMINI LIVE DUPLEX HUD[/bold cyan] [dim]({self.callsign})[/dim]"
            waveform = self.generate_wave_bars(num_bars=22)
            db = int(20 * math.log10(max(1e-5, self.current_energy)))
            meter_filled = min(15, max(0, int((self.current_energy * 50))))
            vu_meter = f"[bold green]{'█' * meter_filled}[/bold green][dim grey]{'░' * (15 - meter_filled)}[/dim grey] {db}dB"
            status_badge = f"[cyan]{self.state}[/cyan]"

        content = Table.grid(padding=(0, 1))
        content.add_column(justify="center")
        content.add_row(Align.center(f"{orb}  {status_badge}  |  Mic: {vu_meter}"))
        content.add_row(Align.center(waveform))

        return Panel(
            content,
            title=panel_title,
            border_style=border_col,
            padding=(0, 1)
        )

    def render_header(self):
        console.print(Panel.fit(
            f"[bold cyan]🎙️ UNIVERSAL LIVE VOICE MULTIMODAL DUPLEX[/bold cyan] | "
            f"[bold magenta]Lead Architect: {self.callsign}[/bold magenta] | "
            f"[green]Status: {self.state}[/green]\n"
            f"[dim]⚡ F9: Global Mute/Pause · Say 'mute mic' to Pause · Spoken 'Enter'[/dim]",
            border_style="cyan"
        ))
