"""
Universal Function Calling & AI Agent Integration Tools
Enables the voice agent to inspect files, execute system commands,
and inject instructions into ANY AI Coding Assistant in real time:
Claude Code, Cursor IDE, OpenAI Codex / Copilot, Google Antigravity, and Windsurf.
Features hardware scancode Enter simulation and spoken 'Enter' voice-trigger detection.
Zero-shrink window handling and no menu activation.
"""

import os
import re
import time
import subprocess
import winsound
from pathlib import Path
from typing import Dict, Any, List

try:
    import win32gui
    import win32api
    import win32con
    import win32clipboard
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

SUPPORTED_AGENT_TITLES: List[str] = [
    "Antigravity",
    "Cursor",
    "Visual Studio Code",
    "Claude",
    "Windsurf",
    "Command Prompt",
    "Windows PowerShell",
    "Terminal"
]

def execute_system_command(command: str) -> Dict[str, Any]:
    """Executes a shell command and returns standard output/error."""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=20
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip()[:1500],
            "stderr": proc.stderr.strip()[:500]
        }
    except Exception as e:
        return {"error": str(e)}

def read_workspace_file(file_path: str, workspace_root: str = None) -> Dict[str, Any]:
    """Reads content of a file within the workspace."""
    p = Path(file_path).resolve()

    # Confine to workspace root if specified
    if workspace_root:
        root = Path(workspace_root).resolve()
        if not str(p).lower().startswith(str(root).lower()):
            return {"error": f"Access denied: path outside workspace root"}

    # Block sensitive system files
    sensitive_patterns = ['.ssh', '.gnupg', '.env', 'id_rsa', '.git/config']
    for pat in sensitive_patterns:
        if pat in str(p).lower():
            return {"error": f"Access denied: sensitive file pattern detected"}

    if not p.exists():
        return {"error": f"File does not exist: {file_path}"}
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(3000)
        return {"content": content, "size": p.stat().st_size}
    except Exception as e:
        return {"error": str(e)}

def parse_spoken_enter(text: str) -> tuple[str, bool]:
    """
    Checks if Boss spoke 'enter', 'send', or 'submit' at the end of the sentence.
    Strips the keyword and returns (clean_text, was_spoken_enter).
    """
    if not text:
        return "", False
    clean = text.strip()
    match = re.search(r'\b(enter|send|submit)\b[.,!?]*$', clean, re.IGNORECASE)
    if match:
        stripped = clean[:match.start()].strip(' ,.!?')
        # If entire text was just the command word, signal enter with empty text
        return stripped, True
    return clean, False

def inject_agent_chat(message: str, target_hint: str = "auto", force_enter: bool = True) -> Dict[str, Any]:
    """
    Universally injects voice transcription into the active AI Agent's Chat box
    (Claude Code, Cursor, Antigravity, Codex/VS Code, Windsurf) and triggers Enter.
    Keeps window geometry intact (no shrinking/unmaximizing) and prevents Alt menu activation.
    """
    if not WIN32_AVAILABLE:
        return {"status": "win32_unavailable", "message": message}

    clean_message, spoken_enter = parse_spoken_enter(message)
    if not clean_message and not (force_enter or spoken_enter):
        return {"status": "empty_message"}

    target_hwnd = None
    detected_agent = "Unknown"
    current_pid = os.getpid()

    def enum_cb(hwnd, _):
        nonlocal target_hwnd, detected_agent
        if win32gui.IsWindowVisible(hwnd):
            # Skip windows belonging to our own process
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == current_pid:
                    return True
            except Exception:
                pass
            title = win32gui.GetWindowText(hwnd)
            for agent_name in SUPPORTED_AGENT_TITLES:
                if target_hint != "auto" and target_hint.lower() in agent_name.lower():
                    if agent_name.lower() in title.lower():
                        target_hwnd = hwnd
                        detected_agent = agent_name
                        return False
                elif agent_name.lower() in title.lower():
                    target_hwnd = hwnd
                    detected_agent = agent_name
                    return False
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    if target_hwnd:
        try:
            # 1. Safely focus target window without altering size or pressing ALT
            curr_fg = win32gui.GetForegroundWindow()
            if curr_fg != target_hwnd:
                # If minimized, restore it; otherwise DO NOT touch window dimensions!
                if win32gui.IsIconic(target_hwnd):
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                except Exception:
                    # Use AttachThreadInput technique as fallback
                    try:
                        import ctypes
                        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                        target_thread = ctypes.windll.user32.GetWindowThreadProcessId(target_hwnd, None)
                        ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, True)
                        win32gui.SetForegroundWindow(target_hwnd)
                        ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, False)
                    except Exception:
                        pass
                time.sleep(0.08)

                # Verify focus was obtained
                if win32gui.GetForegroundWindow() != target_hwnd:
                    return {"status": "focus_failed", "agent": detected_agent}

            if clean_message:
                # 2. Copy text to Windows Clipboard
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(clean_message, win32clipboard.CF_UNICODETEXT)
                finally:
                    try:
                        win32clipboard.CloseClipboard()
                    except Exception:
                        pass
                time.sleep(0.04)

                # 3. Paste (Ctrl + V) with hardware scancodes
                ctrl_scan = win32api.MapVirtualKey(win32con.VK_CONTROL, 0)
                v_scan = win32api.MapVirtualKey(ord('V'), 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, 0, 0)
                win32api.keybd_event(ord('V'), v_scan, 0, 0)
                time.sleep(0.03)
                win32api.keybd_event(ord('V'), v_scan, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, win32con.KEYEVENTF_KEYUP, 0)

                # Crucial: Allow React/Electron DOM ~160ms to render the pasted text
                time.sleep(0.16)

            # 4. Hit ENTER with hardware scancode (simulates physical Enter key!)
            if force_enter or spoken_enter:
                enter_scan = win32api.MapVirtualKey(win32con.VK_RETURN, 0)
                win32api.keybd_event(win32con.VK_RETURN, enter_scan, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(win32con.VK_RETURN, enter_scan, win32con.KEYEVENTF_KEYUP, 0)

            # 5. Acoustic confirmation chime
            try:
                winsound.Beep(1200, 50)
            except Exception:
                pass

            return {
                "status": "success",
                "agent": detected_agent,
                "injected_text": clean_message,
                "voice_enter": spoken_enter or force_enter
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    return {"status": "no_supported_agent_window_found"}

# Backward-compatible alias
inject_antigravity_chat = inject_agent_chat
