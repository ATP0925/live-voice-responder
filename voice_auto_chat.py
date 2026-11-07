"""
Antigravity Live Voice Typist & Auto-Sender (Hands-Free Duplex Edition)
No terminal enter key required! Listens continuously with VAD, ignores assistant TTS echo,
and automatically focuses Antigravity Chat, pastes text, and hits Enter!
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tools import inject_agent_chat, find_agent_window
from core.dsp import AdaptiveNoiseGate

LOCK_FILE = os.path.join(tempfile.gettempdir(), "live_voice_agent_speaking.lock")
ABORT_FILE = os.path.join(tempfile.gettempdir(), "live_voice_barge_in.signal")

def is_agent_speaking() -> bool:
    """Checks whether the agent/assistant is currently speaking to prevent feedback echo."""
    if not os.path.exists(LOCK_FILE):
        return False
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        data = json.loads(content) if content.startswith("{") else {"timestamp": float(content or 0)}
        ts = data.get("timestamp", 0)
        return (time.time() - ts) < 12.0
    except Exception:
        return False

def main():
    print("=" * 65)
    print("  🎙️ ANTIGRAVITY HANDS-FREE VOICE TYPIST & AUTO-SENDER")
    print("=" * 65)
    print("[*] Mode         : Hands-Free Continuous Voice Activity Detection")
    print("[*] Interruption : Say 'CROW' or press F8 to interrupt assistant")
    print("[*] Mute/Pause   : Press F9 or say 'mute mic'")
    print("[*] Auto-Send    : Automatically focuses Antigravity and hits Enter!")
    print("=" * 65)

    target_hwnd, agent = find_agent_window("Antigravity")
    if target_hwnd:
        print(f"✅ Antigravity Target Found: HWND {target_hwnd} ({agent})")
    else:
        print("ℹ️ Antigravity will be auto-detected when speech occurs.")

    # Delegate to the master asynchronous engine for zero-lag performance
    from live_voice_cli import cli
    cli()

if __name__ == "__main__":
    main()
