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
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import LiveVoiceConfig
from core.fallback_tts import FallbackTTS
from core.tools import inject_agent_chat, parse_spoken_enter

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

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
        self._recording = False
        self._audio_chunks = []
        self._stream = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            with self._lock:
                self._audio_chunks.append(indata.copy())

    def _transcribe_and_inject(self, pcm_bytes: bytes):
        if not pcm_bytes or len(pcm_bytes) < 6000:
            return
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            audio_obj = sr.AudioData(pcm_bytes, self.config.audio.input_sample_rate, 2)
            lang = self.config.persona.language or "en-IN"
            text = recognizer.recognize_google(audio_obj, language=lang).strip()
            if text:
                clean_tx, was_spoken_enter = parse_spoken_enter(text)
                print(f"[Daemon Transcript] Boss: {clean_tx}")
                inject_agent_chat(clean_tx, target_hint=self.config.target_agent, force_enter=True)
        except Exception as e:
            print(f"[Daemon Speech Error]: {e}")

    def on_press(self, key):
        try:
            if key == keyboard.Key.f8 and not self.hotkey_pressed:
                self.hotkey_pressed = True
                self._recording = True
                with self._lock:
                    self._audio_chunks = []
                print("\n[🎙️ F8 Push-to-Talk] Listening... Release F8 to send to Antigravity.")
        except AttributeError:
            pass

    def on_release(self, key):
        if key == keyboard.Key.f8 and self.hotkey_pressed:
            self.hotkey_pressed = False
            self._recording = False
            print("[⚡ F8 Released] Transcribing and sending to chat...")
            with self._lock:
                if self._audio_chunks:
                    audio_np = np.concatenate(self._audio_chunks)
                    pcm_bytes = (audio_np * 32767).astype(np.int16).tobytes()
                    self._audio_chunks = []
                    threading.Thread(target=self._transcribe_and_inject, args=(pcm_bytes,), daemon=True).start()

    def run(self):
        print("="*65)
        print("   🎙️ LIVE VOICE DAEMON (Background Push-to-Talk Service)")
        print("="*65)
        print(f"[*] Callsign: {self.config.persona.callsign}")
        print("[*] Global Hotkey: F8 (Press & Hold to talk, Release to auto-send)")
        print("[*] Service is active in background. Press Ctrl+C to stop.\n")

        self.tts.speak(f"{self.config.persona.callsign}, background push to talk daemon active hai.")

        if SOUNDDEVICE_AVAILABLE:
            self._stream = sd.InputStream(
                samplerate=self.config.audio.input_sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback
            )
            self._stream.start()

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

        if self._stream:
            self._stream.stop()
            self._stream.close()

if __name__ == "__main__":
    daemon = LiveVoiceDaemon()
    daemon.run()

