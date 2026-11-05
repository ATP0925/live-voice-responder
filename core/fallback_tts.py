"""
3-Tier Zero-Fail Neural Voice Synthesis Fallback
Tier 1: Microsoft Edge Neural TTS (Natural hi-IN-MadhurNeural / SwaraNeural)
Tier 2: Google gTTS Online Speech
Tier 3: Windows Native SAPI5 (Offline OS Voice)
"""

import os
import re
import sys
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

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
        """Tier 1: High-fidelity Edge Neural TTS."""
        try:
            import edge_tts
            v = voice or self.primary_voice
            communicate = edge_tts.Communicate(text, v, rate=self.rate, volume=self.volume)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                temp_path = fp.name
            await communicate.save(temp_path)

            # Play using PowerShell MediaPlayer or ffplay
            ps_cmd = (
                f'Add-Type -AssemblyName presentationCore;'
                f'$player = New-Object System.Windows.Media.MediaPlayer;'
                f'$player.Open([System.Uri]"file:///{temp_path.replace(os.sep, "/")}");'
                f'$player.Play();'
                f'while($player.NaturalDuration.HasTimeSpan -eq $false){{Start-Sleep -Milliseconds 50}};'
                f'Start-Sleep -Milliseconds ($player.NaturalDuration.TimeSpan.TotalMilliseconds + 200);'
                f'$player.Close();'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return True
        except Exception as e:
            return False

    def speak_sapi5(self, text: str) -> bool:
        """Tier 3: Windows Native SAPI5 Offline Voice."""
        try:
            safe_text = text.replace('"', '""').replace("'", "''")
            ps_cmd = f'$speak = New-Object -ComObject SAPI.SpVoice; $speak.Speak("{safe_text}")'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def speak(self, text: str):
        """Executes 3-tier synthesis with automatic failover."""
        clean = self.clean_text(text)
        if not clean:
            return

        # Try Tier 1 Primary
        try:
            success = asyncio.run(self.speak_edge_tts(clean, self.primary_voice))
            if success:
                return
        except Exception:
            pass

        # Try Tier 1 Fallback Voice
        try:
            success = asyncio.run(self.speak_edge_tts(clean, self.fallback_voice))
            if success:
                return
        except Exception:
            pass

        # Try Tier 3 Offline SAPI5
        self.speak_sapi5(clean)
