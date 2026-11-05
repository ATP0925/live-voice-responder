#!/usr/bin/env python3
"""
Live Voice Daemon — Background Voice Service for Antigravity & OS
Supports Global Push-To-Talk Hotkey and Continuous VAD Listening
"""

import sys
import os
import time
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import LiveVoiceConfig
from core.fallback_tts import FallbackTTS
from core.tools import inject_antigravity_chat

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

class LiveVoiceDaemon:
    def __init__(self):
        self.config = LiveVoiceConfig.load()
        self.tts = FallbackTTS()
        self.is_active = True
        self.hotkey_pressed = False

    def on_press(self, key):
        try:
            # F8 or Insert as default global toggle
            if key == keyboard.Key.f8:
                self.hotkey_pressed = True
                print("\n[Hotkey] F8 Pressed — Listening for Boss...")
        except AttributeError:
            pass

    def on_release(self, key):
        if key == keyboard.Key.f8:
            self.hotkey_pressed = False
            print("[Hotkey] F8 Released — Processing audio...")

    def run(self):
        print("="*65)
        print("   🎙️ LIVE VOICE DAEMON (Background Service)")
        print("="*65)
        print(f"[*] Callsign: {self.config.persona.callsign}")
        print("[*] Global Hotkey: F8 (Press & Hold to talk to Antigravity)")
        print("[*] Service is active in background. Press Ctrl+C to stop.\n")

        self.tts.speak(f"{self.config.persona.callsign}, background voice daemon active hai.")

        if PYNPUT_AVAILABLE:
            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                try:
                    listener.join()
                except KeyboardInterrupt:
                    print("\nDaemon stopped.")
        else:
            print("[Warning] pynput not installed. Running simple sleep loop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nDaemon stopped.")

if __name__ == "__main__":
    daemon = LiveVoiceDaemon()
    daemon.run()
