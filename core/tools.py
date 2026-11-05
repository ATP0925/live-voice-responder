"""
Universal Function Calling & AI Agent Integration Tools
Enables the voice agent to inspect files, execute system commands,
and inject instructions into ANY AI Coding Assistant in real time:
Claude Code, Cursor IDE, OpenAI Codex / Copilot, Google Antigravity, and Windsurf.
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

try:
    import win32gui
    import win32api
    import win32con
    import win32clipboard
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

def read_workspace_file(file_path: str) -> Dict[str, Any]:
    """Reads content of a file within the workspace."""
    p = Path(file_path).resolve()
    if not p.exists():
        return {"error": f"File does not exist: {file_path}"}
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(3000)
        return {"content": content, "size": p.stat().st_size}
    except Exception as e:
        return {"error": str(e)}

def inject_agent_chat(message: str, target_hint: str = "auto") -> Dict[str, Any]:
    """
    Universally injects voice transcription into the active AI Agent's Chat box
    (Claude Code, Cursor, Antigravity, Codex/VS Code, Windsurf) and triggers Enter.
    """
    if not WIN32_AVAILABLE:
        return {"status": "win32_unavailable", "message": message}

    target_hwnd = None
    detected_agent = "Unknown"

    def enum_cb(hwnd, _):
        nonlocal target_hwnd, detected_agent
        if win32gui.IsWindowVisible(hwnd):
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
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_hwnd)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)

            # Copy to clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(message, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            time.sleep(0.05)

            # Paste Ctrl + V
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)

            # Hit ENTER
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
            return {"status": "success", "agent": detected_agent, "injected_text": message}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    return {"status": "no_supported_agent_window_found"}

# Backward-compatible alias
inject_antigravity_chat = inject_agent_chat
