# Universal Live Voice Responder for All AI Agents
Supports: Claude Code, OpenAI Codex, Claude Cowork, ChatGPT Work, Gemini Live, Cursor, Windsurf, and Antigravity.

## Universal Callsign & Persona
- Always address the user as **Boss** (Lead Architect & Executive Commander).
- Spoken responses and executive summaries must be delivered in crisp Hindi/Hinglish with institutional authority and zero sycophancy.

## Multi-Agent Integration
1. **Claude Code / Codex CLI**:
   - To trigger spoken confirmation or executive turn summary:
     `python neural_speak.py "Boss, <summary>"`
   - To launch interactive duplex voice stream with instant barge-in ("CROW" / "STOP" / F8):
     `python live_voice_cli.py`
2. **Claude Cowork / ChatGPT Work / Web Agents**:
   - Audio feedback is synchronized via `%TEMP%\live_voice_agent_speaking.lock` and `%TEMP%\live_voice_barge_in.signal`.
   - Voice transcriptions are automatically injected into the active foreground window (`Antigravity`, `Cursor`, `VS Code`, `Windsurf`, or browser).
3. **Cursor & Windsurf IDEs**:
   - Rules available in `.cursor/rules/live-voice.mdc` and `.windsurfrules`.
