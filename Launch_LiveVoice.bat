@echo off
title Live Voice Responder - Boss Dual-Way Audio
color 0b
echo ========================================================
echo    🎙️ LIVE VOICE RESPONDER (Hands-Free Duplex Loop)
echo ========================================================
echo Starting Universal Voice Engine for Boss...
echo Speak into your microphone anytime - auto-sends to Antigravity!
echo.
echo [F8 Key / Esc]   : Instant Barge-In / Interruption (Stops speech & listens to suggestion)
echo [Voice Command]  : Say 'CROW', 'STOP', or 'SUNO' while assistant speaks to interrupt!
echo [F9 Key]         : Global Toggle Mute / Pause Mic (Works anywhere)
echo [Hands-Free]     : Continuous listening - No pressing Enter in terminal required!
echo [Auto Enter]     : Automatically injects into Antigravity Chat and presses Enter!
echo.

set PY_CMD=python
where python >nul 2>nul
if %errorlevel% neq 0 (
    set PY_CMD=py -3.11
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        set PY_CMD=py -3.14
    )
)

%PY_CMD% "%~dp0live_voice_cli.py" %*
if %errorlevel% neq 0 (
    echo.
    echo [Fallback]: Attempting py -3.11 runner...
    py -3.11 "%~dp0live_voice_cli.py" %*
)
pause
