<p align="center">
  <h1 align="center">🎙️ Live Voice Responder</h1>
  <p align="center"><strong>Enterprise Full-Duplex Multimodal Voice Coordination Engine</strong></p>
  <p align="center">Powered by Google Gemini 3.1 Flash Live (Native Audio), Bidirectional WebSocket Streaming, Instant Barge-In (Interruption), and 3-Tier Neural TTS Fail-Safe for Antigravity, Claude Code, and Cursor.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/architecture-Gemini%20Live%20Duplex-38bdf8?style=flat-square" alt="Duplex">
  <img src="https://img.shields.io/badge/tests-4%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/python-3.11+-informational?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/latency-%3C400ms-success?style=flat-square" alt="Latency">
</p>

---

## 🌟 Overview

**Live Voice Responder** bridges the gap between text-only coding prompts and real-time bidirectional vocal pair programming. Modeled directly on Google Gemini's Multimodal Live API, it eliminates awkward typing, pauses, and batch delays.

### Core Capabilities:
1. **⚡ True Full-Duplex Audio:** Continuous 16kHz PCM streaming from microphone and 24kHz raw PCM output streaming to speakers simultaneously over a single persistent WebSocket.
2. **🛑 Instant Barge-In (Interruption Handling):** When you speak while the AI is talking, the speaker buffer is instantly flushed within milliseconds, and the model pivots to your new instruction without hesitation.
3. **🧠 Native Multimodal Voice:** Understands subtle acoustic nuances, tone, pauses, and speech inflection directly without intermediate Speech-to-Text conversion delays.
4. **👑 Institutional Boss Persona:** Calibrated strictly for executive architectural collaboration—razor-sharp Hindi/Hinglish brevity, zero sycophancy, and high technical depth.
5. **🛡️ 3-Tier Zero-Fail Fallback:** If internet or API quotas drop, it seamlessly falls back to Edge-TTS Neural -> Google gTTS -> Windows SAPI5 to ensure 100% voice availability.
6. **🔌 Antigravity Chat Bridge:** Injects spoken commands directly into Antigravity IDE Chat box (`Ctrl+V` + `Enter`) automatically.

---

## 📐 Architecture & Flow

```mermaid
sequenceDiagram
    autonumber
    actor Boss as 🎙️ Boss (Human)
    participant Client as 🎧 Live Voice Client (SoundDevice)
    participant LiveEngine as ⚡ Gemini Live WebSocket (Duplex)
    participant Model as 🤖 Gemini 3.1 Flash Live (Native Audio)

    Note over Boss,Model: Persistent Full-Duplex WebSocket Active
    Boss->>Client: "Suno, CampusNotify ka login code check karo..."
    Client->>LiveEngine: Continuous PCM Audio Chunks (16kHz)
    LiveEngine->>Model: Streaming Realtime Audio
    Model-->>LiveEngine: Streaming PCM Audio Chunks (24kHz) + Realtime Transcript
    LiveEngine-->>Client: Direct Speaker Stream (Latency < 400ms)
    Client-->>Boss: 🔊 AI Speaks Natural Response

    Note over Boss,Client: ⚡ Instant Barge-In (Interruption)
    Boss->>Client: "Ruko, pehle backend DB schema dikhao!"
    Client->>Client: 🛑 Audio Queue Flush (<50ms)
    Client->>LiveEngine: New Audio Chunks + VAD Trigger
    LiveEngine->>Model: Signal: 'interrupted: true'
    Model-->>LiveEngine: AI cancels previous response & immediately pivots
    LiveEngine-->>Client: New Audio Stream
    Client-->>Boss: 🔊 "Samajh gaya Boss, pehle DB schema dekhte hain..."
```

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/ATP0925/live-voice-responder.git
cd live-voice-responder
pip install -r requirements.txt
```

### 2. Set Your Gemini API Key
```powershell
$env:GEMINI_API_KEY="your-gemini-api-key"
```

### 3. Launch Interactive Terminal HUD (Realtime Duplex Mode)
```powershell
python live_voice_cli.py
```

### 4. Or Run Silent Background Daemon (Global F8 Push-to-Talk)
```powershell
python live_voice_daemon.py
```

---

## ⚙️ Configuration (`config.json`)

Customize persona, voices, and audio buffer sensitivity:

```json
{
  "version": "2.0.0",
  "persona": {
    "callsign": "Boss",
    "language": "hi-IN",
    "tone": "executive_rigor"
  },
  "model": {
    "live_model": "gemini-3.1-flash-live-preview",
    "voice_name": "Puck",
    "thinking_level": "minimal"
  },
  "audio": {
    "input_sample_rate": 16000,
    "output_sample_rate": 24000,
    "interruption_enabled": true,
    "vad_threshold_energy": 0.015,
    "silence_duration_seconds": 0.75
  }
}
```

---

## 🧪 Testing

Execute test suite verifying configuration, interruption handling, and tool execution:
```bash
python -m unittest discover -s tests
```

---

## 🤝 License

Licensed under the [MIT License](LICENSE). Architected for Boss & Antigravity.
