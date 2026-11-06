import os
import sys
import time
import threading
import subprocess
import webbrowser
from flask import Flask, request, render_template_string
import win32api
import win32con
import win32gui
import win32clipboard
import winsound

app = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antigravity Voice Assistant</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            min-height: 100vh;
            user-select: none;
        }
        .header {
            text-align: center;
            margin-bottom: 8px;
        }
        .header h2 {
            margin: 0;
            font-size: 20px;
            color: #38bdf8;
            letter-spacing: -0.5px;
        }
        .header p {
            margin: 4px 0 0 0;
            font-size: 12px;
            color: #94a3b8;
        }
        .mic-box {
            position: relative;
            margin: 16px 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .mic-btn {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 4px solid #38bdf8;
            background: #1e293b;
            color: #ffffff;
            font-size: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            outline: none;
            box-shadow: 0 4px 20px rgba(56, 189, 248, 0.3);
            transition: all 0.25s ease;
        }
        .mic-btn:hover {
            transform: scale(1.05);
            background: #334155;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.6);
        }
        .mic-btn.active {
            background: #ef4444;
            border-color: #fca5a5;
            animation: pulse-ring 1.3s infinite;
        }
        @keyframes pulse-ring {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 22px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        .status-pill {
            margin-top: 10px;
            font-size: 13px;
            font-weight: 600;
            padding: 4px 14px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.08);
            color: #cbd5e1;
        }
        .transcript-container {
            width: 100%;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 12px;
            min-height: 90px;
            max-height: 120px;
            overflow-y: auto;
            font-size: 14px;
            line-height: 1.5;
            color: #e2e8f0;
            text-align: left;
            margin-bottom: 12px;
            word-break: break-word;
        }
        .transcript-placeholder {
            color: #64748b;
            font-style: italic;
        }
        .btn-row {
            display: flex;
            gap: 8px;
            width: 100%;
            margin-bottom: 10px;
        }
        .action-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .action-btn:active { transform: scale(0.98); }
        .btn-send { background: #10b981; color: #ffffff; }
        .btn-send:hover { opacity: 0.9; }
        .btn-clear { background: #475569; color: #f8fafc; }
        .btn-clear:hover { opacity: 0.9; }
        .options {
            display: flex;
            justify-content: space-between;
            width: 100%;
            font-size: 12px;
            color: #94a3b8;
            padding: 0 4px;
        }
        .options label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .sound-test-btn {
            background: transparent;
            border: 1px solid #475569;
            color: #94a3b8;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            cursor: pointer;
        }
        .sound-test-btn:hover {
            color: #38bdf8;
            border-color: #38bdf8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>🎙️ Antigravity Voice Bar</h2>
        <p>Bolo aur Antigravity Chat me auto-type & enter hoga</p>
    </div>

    <div class="mic-box">
        <button id="micBtn" class="mic-btn" title="Click to Speak">🎙️</button>
        <div id="statusPill" class="status-pill">Ready (Click Mic to Speak)</div>
    </div>

    <div id="transcriptBox" class="transcript-container">
        <span class="transcript-placeholder">Aapki boli gayi aawaz yahan type hogi...</span>
    </div>

    <div class="btn-row">
        <button id="sendBtn" class="action-btn btn-send">🚀 Send to Chat</button>
        <button id="clearBtn" class="action-btn btn-clear">🗑️ Clear</button>
    </div>

    <div class="options">
        <label>
            <input type="checkbox" id="autoSendCheck" checked>
            <span>Auto-send on pause</span>
        </label>
        <select id="langSelect" style="background:#1e293b; color:#cbd5e1; border:1px solid #475569; border-radius:4px; padding:2px 6px;">
            <option value="hi-IN" selected>Hindi / Hinglish</option>
            <option value="en-US">English</option>
        </select>
        <button id="testAudioBtn" class="sound-test-btn">🔊 Sound</button>
    </div>

    <script>
        const micBtn = document.getElementById('micBtn');
        const statusPill = document.getElementById('statusPill');
        const transcriptBox = document.getElementById('transcriptBox');
        const sendBtn = document.getElementById('sendBtn');
        const clearBtn = document.getElementById('clearBtn');
        const autoSendCheck = document.getElementById('autoSendCheck');
        const langSelect = document.getElementById('langSelect');
        const testAudioBtn = document.getElementById('testAudioBtn');

        let isListening = false;
        let recognition = null;
        let finalTranscript = '';
        let silenceTimer = null;

        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRec) {
            statusPill.innerText = "❌ Browser Speech API not available";
            statusPill.style.color = "#ef4444";
        } else {
            recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = langSelect.value;

            recognition.onstart = () => {
                isListening = true;
                micBtn.classList.add('active');
                statusPill.innerText = "🔴 Listening... (Bolo abhi)";
                statusPill.style.color = "#f87171";
            };

            recognition.onresult = (event) => {
                let interim = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += (finalTranscript ? ' ' : '') + event.results[i][0].transcript.trim();
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }
                const display = finalTranscript + (interim ? ' ' + interim : '');
                if (display.trim()) {
                    transcriptBox.innerText = display;
                }

                // If auto-send is checked, reset silence timer to auto-send after 1.8 seconds of pause
                if (autoSendCheck.checked && (finalTranscript.trim() || interim.trim())) {
                    clearTimeout(silenceTimer);
                    silenceTimer = setTimeout(() => {
                        const toSend = finalTranscript.trim() || interim.trim();
                        if (toSend && isListening) {
                            sendChat(toSend);
                            finalTranscript = '';
                        }
                    }, 1800);
                }
            };

            recognition.onerror = (event) => {
                console.warn("Speech error:", event.error);
                if (event.error === 'not-allowed') {
                    statusPill.innerText = "⚠️ Allow Microphone Permission in Browser!";
                    statusPill.style.color = "#f59e0b";
                } else {
                    statusPill.innerText = "⚠️ Error: " + event.error;
                }
            };

            recognition.onend = () => {
                if (isListening) {
                    try { recognition.start(); } catch(e){}
                } else {
                    micBtn.classList.remove('active');
                    statusPill.innerText = "Ready (Click Mic to Speak)";
                    statusPill.style.color = "#cbd5e1";
                }
            };
        }

        function toggleMic() {
            if (!recognition) return;
            if (isListening) {
                isListening = false;
                recognition.stop();
            } else {
                recognition.lang = langSelect.value;
                try {
                    recognition.start();
                } catch(e) {
                    console.error("Start error:", e);
                }
            }
        }

        function sendChat(text) {
            if (!text || !text.trim()) return;
            statusPill.innerText = "🚀 Sending to Antigravity Chat...";
            statusPill.style.color = "#34d399";
            
            fetch('/send_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'text/plain;charset=utf-8' },
                body: text
            })
            .then(() => {
                statusPill.innerText = "✅ Sent to Antigravity Chat!";
                statusPill.style.color = "#34d399";
                setTimeout(() => {
                    if (isListening) {
                        statusPill.innerText = "🔴 Listening... (Bolo abhi)";
                        statusPill.style.color = "#f87171";
                    } else {
                        statusPill.innerText = "Ready (Click Mic to Speak)";
                        statusPill.style.color = "#cbd5e1";
                    }
                }, 1500);
            })
            .catch(err => {
                console.error("Send error:", err);
                statusPill.innerText = "❌ Send error";
            });
        }

        micBtn.addEventListener('click', toggleMic);

        sendBtn.addEventListener('click', () => {
            const current = transcriptBox.innerText;
            if (current && !current.includes('Aapki boli gayi')) {
                sendChat(current.trim());
                finalTranscript = '';
            }
        });

        clearBtn.addEventListener('click', () => {
            finalTranscript = '';
            transcriptBox.innerHTML = '<span class="transcript-placeholder">Aapki boli gayi aawaz yahan type hogi...</span>';
        });

        langSelect.addEventListener('change', () => {
            if (recognition) {
                recognition.lang = langSelect.value;
                if (isListening) {
                    recognition.stop();
                }
            }
        });

        testAudioBtn.addEventListener('click', () => {
            // Audio chime + TTS
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(659.25, ctx.currentTime); // E5
                osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1); // A5
                gain.gain.setValueAtTime(0.2, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.3);

                if (window.speechSynthesis) {
                    const u = new SpeechSynthesisUtterance("Audio bilkul sahi chal raha hai!");
                    u.lang = 'hi-IN';
                    window.speechSynthesis.speak(u);
                }
                statusPill.innerText = "🔊 Sound Played!";
            } catch(e) {}
        });

        // Auto-start listening on launch for immediate hands-free readiness
        window.addEventListener('load', () => {
            setTimeout(() => {
                if (recognition && !isListening) {
                    toggleMic();
                }
            }, 800);
        });
    </script>
</body>
</html>
"""

def focus_antigravity_window():
    """Finds Antigravity IDE window and brings it to foreground with focus."""
    target_hwnd = None
    
    def enum_cb(hwnd, _):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # Antigravity IDE window title contains 'Antigravity' or workspace name
            if "Antigravity" in title or "my collage life" in title:
                target_hwnd = hwnd
                return False
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    if target_hwnd:
        try:
            curr_fg = win32gui.GetForegroundWindow()
            if curr_fg != target_hwnd:
                # If minimized, restore it; otherwise do NOT alter geometry or press ALT!
                if win32gui.IsIconic(target_hwnd):
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                except Exception:
                    pass
            time.sleep(0.08)
            return True
        except Exception as e:
            print(f"[Focus warning]: {e}")
    return False

def paste_and_send(text):
    """Pastes text directly into Antigravity Chat box and hits ENTER."""
    if not text or not text.strip():
        return
    clean_text = text.strip()
    print(f"\n[Voice Captured]: {clean_text}")

    # 1. Bring Antigravity IDE to the front
    focus_antigravity_window()
    time.sleep(0.08)

    # 2. Copy text to Windows Clipboard
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(clean_text, win32clipboard.CF_UNICODETEXT)
    except Exception as e:
        print(f"[Clipboard error]: {e}")
        return
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    # 3. Simulate Ctrl+V to paste
    try:
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)

        # 4. Simulate ENTER to send prompt
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)

        # 5. Play sweet confirmation chime
        try:
            winsound.Beep(1200, 70)
        except Exception:
            pass
        print("✅ Prompt sent to Antigravity Chat successfully!\n")
    except Exception as e:
        print(f"[Keystroke error]: {e}")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/send_chat', methods=['POST'])
def send_chat():
    text = request.get_data(as_text=True)
    if text:
        threading.Thread(target=paste_and_send, args=(text,)).start()
    return "OK", 200

def launch_floating_window():
    time.sleep(1.2)
    url = "http://localhost:5055"
    print(f"[*] Opening Floating Voice Bar: {url}")
    # Launch in Edge or Chrome as a sleek floating app widget
    try:
        subprocess.Popen([
            "msedge",
            f"--app={url}",
            "--window-size=420,520",
            "--window-position=50,50"
        ])
    except Exception:
        webbrowser.open(url)

if __name__ == '__main__':
    print("=" * 60)
    print("      ANTIGRAVITY LIVE VOICE BAR v2.0")
    print("=" * 60)
    print("[*] URL: http://localhost:5055")
    print("[*] Click the BIG 🎙️ button to speak (or enable auto-send).")
    print("[*] Automatically focuses Antigravity Chat & hits ENTER!\n")
    threading.Thread(target=launch_floating_window, daemon=True).start()
    app.run(host='127.0.0.1', port=5055, debug=False)
