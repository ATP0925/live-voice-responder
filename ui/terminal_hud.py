"""
Terminal HUD Interface for Live Voice Responder
Renders a live status dashboard, VU meter, and real-time conversation ledger.
"""

import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

console = Console()

class TerminalHUD:
    def __init__(self, callsign: str = "Boss"):
        self.callsign = callsign
        self.messages = []
        self.state = "INITIALIZING"
        self.interruption_count = 0
        self.turns_count = 0

    def add_message(self, speaker: str, text: str):
        self.messages.append((speaker, text, time.strftime("%H:%M:%S")))
        if len(self.messages) > 12:
            self.messages.pop(0)

        # Print message cleanly
        if speaker == self.callsign or speaker == "Boss":
            console.print(f"[bold cyan]🎙️ {speaker}:[/bold cyan] [white]{text}[/white]")
        elif speaker == "Agent":
            console.print(f"[bold green]🤖 Agent:[/bold green] [italic #38bdf8]{text}[/italic #38bdf8]")
        elif speaker == "System":
            console.print(f"[yellow]⚡ System:[/yellow] {text}")

    def update_state(self, state: str):
        self.state = state

    def render_header(self):
        console.print(Panel.fit(
            f"[bold cyan]🎙️ GEMINI LIVE MULTIMODAL DUPLEX[/bold cyan] | "
            f"[bold magenta]Lead Architect: {self.callsign}[/bold magenta] | "
            f"[green]Status: {self.state}[/green]\n"
            f"[dim]⚡ Native 24kHz Streaming Audio · Instant Barge-In · Zero Latency[/dim]",
            border_style="cyan"
        ))
