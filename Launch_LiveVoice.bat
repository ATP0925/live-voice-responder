@echo off
title Live Voice Responder - Boss Dual-Way Audio
color 0b
echo ========================================================
echo    🎙️ LIVE VOICE RESPONDER (Hands-Free Duplex Loop)
echo ========================================================
echo Starting Universal Voice Engine for Boss...
echo Speak into your microphone anytime - auto-sends to Antigravity!
echo.
echo [F9 Key] : Global Toggle Mute / Pause Mic (Works anywhere)
echo [Voice]  : Say 'mute mic' or 'pause' to mute hands-free
echo [Enter]  : Say '... enter' at sentence end to auto-press Enter
echo.
python "%~dp0live_voice_cli.py"
pause

