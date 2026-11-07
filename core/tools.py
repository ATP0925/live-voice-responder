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
    "Windsurf"
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

def find_agent_window(target_hint: str = "auto") -> tuple[Any, str]:
    """Finds target AI agent window HWND reliably across Windows desktop boundaries."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)

        candidates = []
        current_pid = kernel32.GetCurrentProcessId()
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == current_pid:
                return True

            proc_name = ""
            try:
                import psutil
                proc = psutil.Process(pid.value)
                proc_name = proc.name().lower()
            except Exception:
                pass

            title_lower = title.lower()
            if "live voice responder" in title_lower or "dual-way audio" in title_lower or "neural_speak" in title_lower:
                return True

            if target_hint != "auto":
                if target_hint.lower() in proc_name:
                    candidates.append((0, hwnd, target_hint))
                    return False
                elif target_hint.lower() in title_lower:
                    candidates.append((1, hwnd, target_hint))
                    return False
            else:
                if "antigravity ide" in proc_name or "antigravity" in proc_name:
                    candidates.append((0, hwnd, "Antigravity"))
                elif "antigravity" in title_lower and not ("chrome" in proc_name or "brave" in proc_name or "msedge" in proc_name):
                    candidates.append((1, hwnd, "Antigravity"))
                elif "cursor" in proc_name:
                    candidates.append((2, hwnd, "Cursor"))
                elif "cursor" in title_lower:
                    candidates.append((3, hwnd, "Cursor"))
                elif "code" in proc_name or "vscode" in title_lower or "visual studio code" in title_lower:
                    candidates.append((4, hwnd, "Visual Studio Code"))
                elif "windsurf" in proc_name or "windsurf" in title_lower:
                    candidates.append((5, hwnd, "Windsurf"))
                elif "claude" in proc_name or "claude" in title_lower:
                    candidates.append((6, hwnd, "Claude"))
            return True

        cb_func = WNDENUMPROC(cb)
        if h_desk:
            user32.EnumDesktopWindows(h_desk, cb_func, 0)
        else:
            user32.EnumWindows(cb_func, 0)

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1], candidates[0][2]
    except Exception:
        pass
    return None, "Unknown"


def inject_agent_chat(message: str, target_hint: str = "auto", force_enter: bool = True, auto_focus_chat: bool = True) -> Dict[str, Any]:
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

    target_hwnd, detected_agent = find_agent_window(target_hint)
    if not target_hwnd:
        return {"status": "no_supported_agent_window_found"}

    try:
        import ctypes
        user32 = ctypes.windll.user32

        # 1. Safely restore and focus target window without altering size or pressing ALT
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)

        # SwitchToThisWindow guarantees activation across desktop boundaries
        try:
            user32.AllowSetForegroundWindow(-1)
            user32.SwitchToThisWindow(target_hwnd, True)
            user32.BringWindowToTop(target_hwnd)
            user32.SetForegroundWindow(target_hwnd)
        except Exception:
            pass
        time.sleep(0.08)

        # 2. Focus AI Chat input box for IDEs if auto_focus_chat is enabled
        if auto_focus_chat and detected_agent in ("Antigravity", "Cursor", "Visual Studio Code", "Windsurf"):
            try:
                ctrl_scan = win32api.MapVirtualKey(win32con.VK_CONTROL, 0)
                l_scan = win32api.MapVirtualKey(ord('L'), 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, 0, 0)
                win32api.keybd_event(ord('L'), l_scan, 0, 0)
                time.sleep(0.04)
                win32api.keybd_event(ord('L'), l_scan, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.08)
                # Move cursor to end so existing text is not erased
                end_scan = win32api.MapVirtualKey(win32con.VK_END, 0)
                win32api.keybd_event(win32con.VK_END, end_scan, 0, 0)
                time.sleep(0.02)
                win32api.keybd_event(win32con.VK_END, end_scan, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.04)
            except Exception:
                pass

        clipboard_ok = False
        if clean_message:
            # 3. Copy text to Windows Clipboard with retry loop (resilient against locks)
            for _ in range(10):
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(clean_message, win32clipboard.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    clipboard_ok = True
                    break
                except Exception:
                    try:
                        win32clipboard.CloseClipboard()
                    except Exception:
                        pass
                    time.sleep(0.02)
            time.sleep(0.04)

            # 4. Paste (Ctrl + V) with hardware scancodes only if clipboard was successfully set
            if clipboard_ok:
                ctrl_scan = win32api.MapVirtualKey(win32con.VK_CONTROL, 0)
                v_scan = win32api.MapVirtualKey(ord('V'), 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, 0, 0)
                win32api.keybd_event(ord('V'), v_scan, 0, 0)
                time.sleep(0.03)
                win32api.keybd_event(ord('V'), v_scan, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, ctrl_scan, win32con.KEYEVENTF_KEYUP, 0)
                # Crucial: Allow React/Electron DOM ~160ms to render the pasted text
                time.sleep(0.16)

        # 5. Hit ENTER with hardware scancode (simulates physical Enter key!)
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

# Backward-compatible alias
inject_antigravity_chat = inject_agent_chat
