"""
Live Voice Responder — Opus 5.5 Enterprise Neural Voice Synthesis Engine
Architected for: Boss (Lead Architect & Executive Commander)
Pillars: Zero-Fail Multi-Tier TTS (Edge-TTS -> gTTS -> Windows SAPI5) + Acronym Normalizer
"""

import sys
import os
import re
import subprocess
import asyncio
import tempfile
import json
import uuid
import time
import winsound
from pathlib import Path

# Primary High-Fidelity Indian Neural Voices
PRIMARY_VOICE = os.getenv("ANTIGRAVITY_VOICE", "hi-IN-MadhurNeural")
FALLBACK_VOICE = "hi-IN-SwaraNeural"

# Technical Acronyms to Phonetic Pronunciations
ACRONYM_MAP = {
    r'\bUID\b': 'U-I-D',
    r'\bERP\b': 'E-R-P',
    r'\bHOD\b': 'H-O-D',
    r'\bCIE\b': 'C-I-E',
    r'\bAPI\b': 'A-P-I',
    r'\bAPIs\b': 'A-P-Is',
    r'\bCDP\b': 'C-D-P',
    r'\bPR\b': 'P-R',
    r'\bPRs\b': 'P-Rs',
    r'\bE2E\b': 'End to End',
    r'\bTTS\b': 'T-T-S',
    r'\bDB\b': 'Database',
    r'\bURL\b': 'U-R-L',
    r'\bURLs\b': 'U-R-Ls',
    r'\bCLI\b': 'C-L-I',
    r'\bUI\b': 'U-I',
    r'\bUX\b': 'U-X',
    r'\bSDK\b': 'S-D-K',
    r'\bJWT\b': 'J-W-T',
    r'\bOAuth\b': 'O-Auth',
    r'\bPVPPCOE\b': 'P-V-P-P College',
    r'\bNAAC\b': 'Naac',
    r'\bNBA\b': 'N-B-A',
    r'\bTPO\b': 'T-P-O',
    r'\bSGRC\b': 'S-G-R-C'
}

def sanitize_and_normalize_speech(text: str) -> str:
    """
    Cleans markdown, URLs, links, code snippets and enforces 
    the institutional Boss persona.
    """
    if not text:
        return "Boss, main ready hoon. Agla task batayein."

    # 1. Strip Code Blocks & Inline Code
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)

    # 2. Strip Markdown Links [Label](url) -> Label
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)

    # 3. Strip URLs & File Paths
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'file:///\S+', '', text)
    text = re.sub(r'[A-Za-z]:\\[\w\\\.\-]+', '', text)

    # 4. Strip Metadata Badges and Formatting
    text = re.sub(r'\[.*?Status\].*?(\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?Update\].*?(\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[*_#~>|]', ' ', text)
    text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)

    # 5. Enforce Boss Persona Integrity (Replace any accidental colloquialisms)
    text = re.sub(r'\b(haan\s+bhai|bhai|pratik\s+bhai|dost|yaar|buddy)\b', 'Boss', text, flags=re.IGNORECASE)

    # Ensure respectful Boss prefix if missing
    text_stripped = text.strip()
    if not re.search(r'\bBoss\b', text_stripped, flags=re.IGNORECASE):
        text = f"Boss, {text_stripped}"

    # 6. Expand Technical Acronyms for Natural Speech
    for pattern, replacement in ACRONYM_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 7. Normalize Multiple Spaces and Clean Punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def _synthesize_edge_tts(text: str, voice: str, target_file: str):
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(target_file)

def _synthesize_gtts(text: str, target_file: str, lang: str = "hi"):
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(target_file)

def _play_audio_file(mp3_path: str, wav_path: str) -> bool:
    """
    Tries multiple native audio playback routes on Windows:
    1. ffmpeg conversion -> winsound (Native WinMM)
    2. ffplay (quiet, auto-exit)
    3. PowerShell System.Media.SoundPlayer
    """
    # Route 1: Convert to WAV and play via Windows native winmm
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", mp3_path,
            "-ar", "24000",
            "-ac", "1",
            "-loglevel", "quiet",
            wav_path
        ], check=True, capture_output=True)
        if os.path.exists(wav_path):
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)
            return True
    except Exception:
        pass

    # Route 2: ffplay direct MP3 playback
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", mp3_path],
            check=True, capture_output=True
        )
        return True
    except Exception:
        pass

    # Route 3: PowerShell SoundPlayer on WAV
    if os.path.exists(wav_path):
        try:
            subprocess.run([
                "powershell", "-NoProfile", "-Command",
                f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync()"
            ], check=True, capture_output=True)
            return True
        except Exception:
            pass

    # Route 4: Windows Media Player COM (plays MP3 natively without ffmpeg)
    try:
        ps_cmd = (
            f'$player = New-Object -ComObject WMPlayer.OCX;'
            f'$player.URL = "{mp3_path.replace(chr(92), "/")}";'
            f'$player.controls.play();'
            f'Start-Sleep -Milliseconds 500;'
            f'while($player.playState -eq 3){{Start-Sleep -Milliseconds 100}};'
            f'$player.close();'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            check=True, capture_output=True, timeout=30
        )
        return True
    except Exception:
        pass

    return False

def _speak_offline_sapi5(text: str):
    """
    Zero-network offline fallback using Windows SAPI5 Speech Synthesizer.
    Guarantees the agent is NEVER muted even during complete network severance.
    """
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.Volume = 100
    $synth.Rate = 0
    $synth.Speak('{text.replace("'", "''")}')
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[SAPI5 Offline Speech Error]: {e}", file=sys.stderr)
        return False

LOCK_FILE = os.path.join(tempfile.gettempdir(), "live_voice_agent_speaking.lock")

def _set_speaking_lock(active: bool):
    try:
        if active:
            payload = json.dumps({"pid": os.getpid(), "timestamp": time.time()})
            with open(LOCK_FILE, "w", encoding="utf-8") as f:
                f.write(payload)
        else:
            time.sleep(0.65)  # Generous grace period for room acoustic reverb dampening
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
    except Exception:
        pass

def speak_neural(raw_text: str):
    cleaned = sanitize_and_normalize_speech(raw_text)
    if not cleaned:
        return

    _set_speaking_lock(True)
    try:
        session_id = uuid.uuid4().hex[:8]
        temp_dir = tempfile.gettempdir()
        mp3_path = os.path.join(temp_dir, f"antigravity_voice_{session_id}.mp3")
        wav_path = os.path.join(temp_dir, f"antigravity_voice_{session_id}.wav")

        # Tier 1: High-Fidelity Edge TTS Neural
        try:
            asyncio.run(_synthesize_edge_tts(cleaned, PRIMARY_VOICE, mp3_path))
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 500:
                if _play_audio_file(mp3_path, wav_path):
                    return
        except Exception as edge_err:
            print(f"[Tier 1 Edge-TTS notice]: {edge_err}. Cascading to Tier 2...", file=sys.stderr)

        # Tier 2: Resilient Google gTTS Fallback
        try:
            _synthesize_gtts(cleaned, mp3_path, lang="hi")
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 500:
                if _play_audio_file(mp3_path, wav_path):
                    return
        except Exception as gtts_err:
            print(f"[Tier 2 gTTS notice]: {gtts_err}. Cascading to Tier 3...", file=sys.stderr)

        # Tier 3: Zero-Network Native Windows SAPI5 Offline Engine
        print("[Tier 3 Active]: Executing zero-network SAPI5 offline synthesis.", file=sys.stderr)
        _speak_offline_sapi5(cleaned)
    finally:
        _set_speaking_lock(False)
        # Clean up temp files safely
        for p in (mp3_path, wav_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        input_text = "Boss, live voice responder poori tarah upgrade aur verified ho chuka hai."
    speak_neural(input_text)
