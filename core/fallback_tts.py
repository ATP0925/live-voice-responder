"""
3-Tier Zero-Fail Neural Voice Synthesis Fallback
Tier 1: Microsoft Edge Neural TTS (Natural hi-IN-MadhurNeural / SwaraNeural)
Tier 2: Google gTTS Online Speech
Tier 3: Windows Native SAPI5 (Offline OS Voice)
"""

import os
import re
import sys
import time
import json
import asyncio
import threading
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

LOCK_FILE = os.path.join(tempfile.gettempdir(), "live_voice_agent_speaking.lock")
ABORT_FILE = os.path.join(tempfile.gettempdir(), "live_voice_barge_in.signal")

class FallbackTTS:
    def __init__(
        self,
        primary_voice: str = "hi-IN-MadhurNeural",
        fallback_voice: str = "hi-IN-SwaraNeural",
        rate: str = "+0%",
        volume: str = "+0%"
    ):
        self.primary_voice = primary_voice
        self.fallback_voice = fallback_voice
        self.rate = rate
        self.volume = volume
        self._current_proc = None
        self._aborted = False

    def _set_speaking_lock(self, active: bool):
        """Signals to audio engine that assistant is speaking (echo cancellation)."""
        try:
            if active:
                if os.path.exists(ABORT_FILE):
                    try:
                        os.remove(ABORT_FILE)
                    except Exception:
                        pass
                self._aborted = False
                payload = json.dumps({"pid": os.getpid(), "timestamp": time.time()})
                with open(LOCK_FILE, "w", encoding="utf-8") as f:
                    f.write(payload)
            else:
                if not self._aborted:
                    time.sleep(0.40)  # Grace period for room acoustic reverb dampening
                if os.path.exists(LOCK_FILE):
                    try:
                        os.remove(LOCK_FILE)
                    except Exception:
                        pass
        except Exception:
            pass

    def stop(self):
        """Immediately interrupts playback and kills any running speech process (barge-in)."""
        self._aborted = True
        if self._current_proc:
            try:
                self._current_proc.terminate()
                self._current_proc.kill()
            except Exception:
                pass
            self._current_proc = None
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    def _run_playable_process(self, cmd: list) -> bool:
        """Runs playback process while monitoring for instant user barge-in."""
        if self._aborted or os.path.exists(ABORT_FILE):
            return False
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._current_proc = proc
            while proc.poll() is None:
                if self._aborted or os.path.exists(ABORT_FILE):
                    proc.terminate()
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    self._current_proc = None
                    return False
                time.sleep(0.04)
            self._current_proc = None
            return proc.returncode == 0
        except Exception:
            self._current_proc = None
            return False

    @staticmethod
    def clean_text(text: str) -> str:
        """Strips markdown, emojis, URLs and code blocks for clean speech."""
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`.*?`', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[*_#~>]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def speak_edge_tts(self, text: str, voice: Optional[str] = None) -> bool:
        """Tier 1: High-fidelity Edge Neural TTS with barge-in support."""
        if self._aborted or os.path.exists(ABORT_FILE):
            return False
        try:
            import edge_tts
            v = voice or self.primary_voice
            communicate = edge_tts.Communicate(text, v, rate=self.rate, volume=self.volume)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_path = fp.name
            await communicate.save(temp_path)

            if self._aborted or os.path.exists(ABORT_FILE):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                return False

            # Play using PowerShell MediaPlayer
            ps_cmd = (
                f'Add-Type -AssemblyName presentationCore;'
                f'$player = New-Object System.Windows.Media.MediaPlayer;'
                f'$player.Open([System.Uri]"file:///{temp_path.replace(os.sep, "/")}");'
                f'$player.Play();'
                f'$timeout = 0;'
                f'while($player.NaturalDuration.HasTimeSpan -eq $false -and $timeout -lt 60){{Start-Sleep -Milliseconds 50; $timeout++}};'
                f'if($player.NaturalDuration.HasTimeSpan){{'
                f'  $total = $player.NaturalDuration.TimeSpan.TotalMilliseconds;'
                f'  while($player.Position.TotalMilliseconds -lt $total){{Start-Sleep -Milliseconds 60}};'
                f'}} else {{'
                f'  Start-Sleep -Milliseconds 3000;'
                f'}};'
                f'$player.Close();'
            )
            success = self._run_playable_process(["powershell", "-NoProfile", "-Command", ps_cmd])
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return success
        except Exception:
            return False

    def speak_sapi5(self, text: str) -> bool:
        """Tier 3: Windows Native SAPI5 Offline Voice with barge-in support."""
        if self._aborted or os.path.exists(ABORT_FILE):
            return False
        try:
            safe_text = text.replace('"', '""').replace("'", "''")
            ps_cmd = f'$speak = New-Object -ComObject SAPI.SpVoice; $speak.Speak("{safe_text}")'
            return self._run_playable_process(["powershell", "-NoProfile", "-Command", ps_cmd])
        except Exception:
            return False

    def speak(self, text: str):
        """Executes 3-tier synthesis with automatic failover and echo-cancellation lock."""
        clean = self.clean_text(text)
        if not clean:
            return

        self._set_speaking_lock(True)
        try:
            # Try Tier 1 Primary
            try:
                success = self._run_async_tts(clean, self.primary_voice)
                if success or self._aborted:
                    return
            except Exception:
                pass

            # Try Tier 1 Fallback Voice
            try:
                success = self._run_async_tts(clean, self.fallback_voice)
                if success or self._aborted:
                    return
            except Exception:
                pass

            # Try Tier 3 Offline SAPI5
            self.speak_sapi5(clean)
        finally:
            self._set_speaking_lock(False)

    def _run_async_tts(self, text: str, voice: str) -> bool:
        """Runs async TTS in a dedicated event loop thread to avoid nested asyncio.run() crashes."""
        result = [False]
        def _worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result[0] = loop.run_until_complete(self.speak_edge_tts(text, voice))
            finally:
                loop.close()
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=20)
        return result[0]

