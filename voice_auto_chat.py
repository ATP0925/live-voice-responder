import os
import sys
import time
import subprocess
import tempfile
import urllib.request
import json
import win32api
import win32con
import win32clipboard

MIC_DEVICE = "Microphone Array (Realtek(R) Audio)"
DEFAULT_LANG = "hi-IN" # Hindi / Hinglish

def record_audio(duration=4):
    """Records audio from user's microphone using ffmpeg."""
    temp_dir = tempfile.gettempdir()
    flac_path = os.path.join(temp_dir, f"mic_input_{os.getpid()}.flac")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "dshow",
        "-i", f"audio={MIC_DEVICE}",
        "-t", str(duration),
        "-ar", "16000",
        "-ac", "1",
        "-loglevel", "quiet",
        flac_path
    ]
    subprocess.run(cmd, check=True)
    return flac_path

def transcribe_audio(flac_path, lang=DEFAULT_LANG):
    """Transcribes FLAC audio using Google Speech-to-Text API."""
    url = f"https://www.google.com/speech-api/v2/recognize?client=chromium&lang={lang}&maxresults=1"
    headers = {"Content-Type": "audio/x-flac; rate=16000"}
    
    with open(flac_path, "rb") as f:
        audio_data = f.read()
        
    req = urllib.request.Request(url, data=audio_data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            # Google returns chunked JSON lines
            for line in content.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if "result" in data and len(data["result"]) > 0:
                        alternatives = data["result"][0].get("alternative", [])
                        if alternatives:
                            return alternatives[0].get("transcript", "").strip()
                except Exception:
                    pass
    except Exception as e:
        print(f"[Error in STT]: {e}")
    finally:
        if os.path.exists(flac_path):
            try:
                os.remove(flac_path)
            except Exception:
                pass
    return None

def paste_and_send(text):
    """Puts transcribed text into clipboard, pastes (Ctrl+V), and hits Enter in focused chat."""
    if not text:
        return
        
    print(f"\n[Transcribed]: {text}")
    print("[Action]: Typing into Antigravity Chat & Auto-Sending (Enter)...")
    
    # 1. Set Windows Clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    time.sleep(0.05)
    
    # 2. Simulate Ctrl + V
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(ord('V'), 0, 0, 0)
    win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)
    
    # 3. Simulate Enter to auto-send
    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
    print("Done! Message sent to Antigravity!\n")

def main():
    print("=" * 60)
    print("  ANTIGRAVITY LIVE VOICE TYPIST & AUTO-SENDER")
    print("=" * 60)
    print(f"[*] Microphone: {MIC_DEVICE}")
    print(f"[*] Language: {DEFAULT_LANG} (Hindi / Hinglish)")
    print("\n[Instructions]:")
    print("1. Click your cursor inside Antigravity Chat input box.")
    print("2. Press ENTER in this console to speak (it will record for 4 seconds).")
    print("3. As soon as you finish speaking, it will auto-type & auto-send!\n")
    print("Press CTRL+C anytime to stop.\n")
    
    while True:
        try:
            input("👉 Press [ENTER] to SPEAK (or Ctrl+C to exit)... ")
            print("🎙️ Listening... (Bolo abhi!)")
            flac_file = record_audio(duration=4)
            print("⏳ Converting speech to text...")
            transcription = transcribe_audio(flac_file)
            
            if transcription:
                paste_and_send(transcription)
            else:
                print("⚠️ Aawaz samajh nahi aayi ya silence tha, dubara koshish karo.")
        except KeyboardInterrupt:
            print("\nExiting voice typist. Goodbye!")
            break
        except Exception as err:
            print(f"[Error]: {err}")
            time.sleep(1)

if __name__ == "__main__":
    main()
