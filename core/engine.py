"""
Universal Full-Duplex Multimodal Live Voice Engine
Compatible with Claude Code, Cursor, OpenAI Codex, Google Antigravity, and Local AI.
Features auto-failover: Gemini Multimodal Live API (when key present) OR
Universal Zero-Config Speech-to-Text with direct Antigravity Chat auto-injection.
"""

import os
import sys
import time
import asyncio
import threading
import tempfile
import urllib.request
import json
import numpy as np
from typing import Optional, Callable
from .config import LiveVoiceConfig
from .audio_stream import AudioStreamManager
from .interruption import InterruptionCoordinator, ConversationState
from .fallback_tts import FallbackTTS
from .tools import execute_system_command, read_workspace_file, inject_agent_chat

class UniversalLiveVoiceEngine:
    def __init__(
        self,
        config: Optional[LiveVoiceConfig] = None,
        on_transcript: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[ConversationState], None]] = None,
        on_energy: Optional[Callable[[float], None]] = None
    ):
        self.config = config or LiveVoiceConfig.load()
        self.on_transcript = on_transcript
        self.on_state_change = on_state_change
        self.on_energy = on_energy

        self.coordinator = InterruptionCoordinator(on_state_change=self._handle_state_change)
        self.audio_mgr = AudioStreamManager(
            input_rate=self.config.audio.input_sample_rate,
            output_rate=self.config.audio.output_sample_rate,
            chunk_size=self.config.audio.chunk_size,
            vad_energy_threshold=self.config.audio.vad_threshold_energy,
            on_interruption=self._handle_barge_in
        )
        self.fallback_tts = FallbackTTS(
            primary_voice=self.config.offline_tts.primary_voice,
            fallback_voice=self.config.offline_tts.fallback_voice
        )

        self._running = False
        self._session = None

    def _handle_state_change(self, state: ConversationState):
        if self.on_state_change:
            self.on_state_change(state)

    def _handle_barge_in(self):
        """Called immediately when user speaks while audio is playing."""
        self.coordinator.trigger_interruption()
        self.audio_mgr.flush_playback()

    async def _gemini_audio_send_loop(self, session):
        from google.genai import types
        while self._running:
            chunk = self.audio_mgr.get_input_chunk(timeout=0.05)
            if chunk and len(chunk) > 0:
                pcm_arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0
                rms = np.sqrt(np.mean(pcm_arr**2)) if len(pcm_arr) > 0 else 0.0
                if self.on_energy:
                    self.on_energy(rms)
                try:
                    await session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )
                except Exception:
                    pass
            await asyncio.sleep(0.01)

    async def _gemini_audio_receive_loop(self, session):
        try:
            async for response in session.receive():
                if not self._running:
                    break

                server_content = getattr(response, "server_content", None)
                if not server_content:
                    tool_call = getattr(response, "tool_call", None)
                    if tool_call:
                        await self._handle_gemini_tool_call(session, tool_call)
                    continue

                if getattr(server_content, "interrupted", False):
                    self._handle_barge_in()
                    continue

                # User transcript (English letters)
                input_tx = getattr(server_content, "input_transcription", None)
                if input_tx and hasattr(input_tx, "text") and input_tx.text:
                    tx_text = input_tx.text.strip()
                    if tx_text:
                        self.coordinator.start_user_turn()
                        if self.on_transcript:
                            self.on_transcript("Boss", tx_text)
                        inject_agent_chat(tx_text, target_hint=self.config.target_agent)

                # Agent transcript
                output_tx = getattr(server_content, "output_transcription", None)
                if output_tx and hasattr(output_tx, "text") and output_tx.text:
                    tx_text = output_tx.text.strip()
                    if tx_text:
                        if self.on_transcript:
                            self.on_transcript("Agent", tx_text)

                # Output streaming audio
                model_turn = getattr(server_content, "model_turn", None)
                if model_turn:
                    self.coordinator.start_agent_speaking()
                    for part in getattr(model_turn, "parts", []):
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            self.audio_mgr.feed_output_audio(inline.data)

                if getattr(server_content, "turn_complete", False):
                    self.coordinator.finish_turn()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._running:
                print(f"[Streaming Error]: {e}")

    async def _handle_gemini_tool_call(self, session, tool_call):
        from google.genai import types
        function_calls = getattr(tool_call, "function_calls", [])
        function_responses = []

        for fc in function_calls:
            name = getattr(fc, "name", "")
            args = getattr(fc, "args", {}) or {}
            call_id = getattr(fc, "id", "")

            result = {}
            if name == "execute_system_command":
                cmd = args.get("command", "")
                result = execute_system_command(cmd)
            elif name == "read_workspace_file":
                fp = args.get("file_path", "")
                result = read_workspace_file(fp)
            elif name in ("inject_agent_chat", "inject_antigravity_chat"):
                msg = args.get("message", "")
                result = inject_agent_chat(msg, target_hint=self.config.target_agent)

            function_responses.append(
                types.FunctionResponse(
                    id=call_id,
                    name=name,
                    response=result
                )
            )

        if function_responses:
            await session.send_tool_response(function_responses=function_responses)

    async def start(self):
        """Dispatches to Gemini Live if key is present, otherwise runs Universal STT Listener."""
        provider = self.config.resolve_active_provider()
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

        if provider == "gemini" and has_gemini_key:
            print("\n[Live Voice Engine] Provider: [bold cyan]GEMINI 3.1 FLASH LIVE (Native Audio)[/bold cyan]")
            await self._start_gemini_duplex()
        else:
            print("\n[Live Voice Engine] Provider: [bold cyan]UNIVERSAL HANDS-FREE STT (English Letters Mode)[/bold cyan]")
            await self._start_universal_listener()

    async def _start_gemini_duplex(self):
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)

        tools_def = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="execute_system_command",
                    description="Run PowerShell or terminal command for Boss.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={"command": types.Schema(type="STRING", description="Command to execute.")},
                        required=["command"]
                    )
                ),
                types.FunctionDeclaration(
                    name="read_workspace_file",
                    description="Read contents of any workspace file.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={"file_path": types.Schema(type="STRING", description="File path.")},
                        required=["file_path"]
                    )
                ),
                types.FunctionDeclaration(
                    name="inject_agent_chat",
                    description="Inject message into Claude Code, Cursor, Codex, or Antigravity Chat.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={"message": types.Schema(type="STRING", description="Text to send.")},
                        required=["message"]
                    )
                )
            ])
        ]

        live_config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.config.engine.voice_name
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.config.persona.system_instruction)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            tools=tools_def
        )

        self._running = True
        self.audio_mgr.start()
        print(f"Connecting to {self.config.engine.live_model}...")

        try:
            async with client.aio.live.connect(
                model=self.config.engine.live_model,
                config=live_config
            ) as session:
                self._session = session
                print("✅ Duplex Voice Stream Active. Speak naturally Boss!\n")
                send_task = asyncio.create_task(self._gemini_audio_send_loop(session))
                receive_task = asyncio.create_task(self._gemini_audio_receive_loop(session))
                await asyncio.gather(send_task, receive_task)
        finally:
            self.stop()

    def _transcribe_raw_pcm(self, pcm_bytes: bytes) -> Optional[str]:
        """Transcribes PCM bytes into clean English letters via Google Speech Recognition."""
        if not pcm_bytes or len(pcm_bytes) < 8000:
            return None
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            audio_obj = sr.AudioData(pcm_bytes, self.config.audio.input_sample_rate, 2)
            # Use en-IN for English letters transcription (Hinglish/Indian English in Latin script)
            lang = self.config.persona.language or "en-IN"
            text = recognizer.recognize_google(audio_obj, language=lang)
            return text.strip() if text else None
        except Exception:
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                audio_obj = sr.AudioData(pcm_bytes, self.config.audio.input_sample_rate, 2)
                return recognizer.recognize_google(audio_obj, language="en-US").strip()
            except Exception:
                return None

    async def _start_universal_listener(self):
        """Continuous Hands-Free VAD with Dynamic Ambient Calibration & Instant English Text Output."""
        self._running = True
        self.audio_mgr.start()
        print("🎙️ [Mic Active - English Letters] Bolo Boss! Aapke words turant English letters me aayenge.\n")
        self.fallback_tts.speak(f"{self.config.persona.callsign}, listening mode active hai.")

        silence_threshold = self.config.audio.silence_duration_seconds
        audio_buffer = bytearray()
        speaking = False
        last_voice_time = 0.0
        ambient_samples = []
        speech_threshold = self.config.audio.vad_threshold_energy
        calibrated = False

        try:
            while self._running:
                chunk = self.audio_mgr.get_input_chunk(timeout=0.06)
                if not chunk or len(chunk) == 0:
                    await asyncio.sleep(0.01)
                    continue

                pcm_arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0
                rms = np.sqrt(np.mean(pcm_arr**2)) if len(pcm_arr) > 0 else 0.0
                if self.on_energy:
                    self.on_energy(rms)

                # Ambient noise floor calibration (first 10 chunks)
                if not calibrated:
                    ambient_samples.append(rms)
                    if len(ambient_samples) >= 10:
                        avg_ambient = float(np.mean(ambient_samples))
                        speech_threshold = max(0.020, avg_ambient * 2.2)
                        calibrated = True
                    continue

                now = time.time()
                if rms > speech_threshold:
                    if not speaking:
                        speaking = True
                        self.coordinator.start_user_turn()
                        audio_buffer.clear()
                    last_voice_time = now
                    audio_buffer.extend(chunk)
                elif speaking:
                    audio_buffer.extend(chunk)
                    silence_duration = now - last_voice_time

                    # End of speech: silence threshold reached or max phrase 6s
                    if silence_duration >= silence_threshold or len(audio_buffer) >= (16000 * 2 * 6):
                        speaking = False
                        self.coordinator.start_processing()
                        captured = bytes(audio_buffer)
                        audio_buffer.clear()

                        if len(captured) >= 12000:  # At least ~0.4s
                            loop = asyncio.get_running_loop()
                            text = await loop.run_in_executor(None, self._transcribe_raw_pcm, captured)
                            if text and text.strip():
                                clean_tx = text.strip()
                                # 1. Display on terminal in English letters!
                                if self.on_transcript:
                                    self.on_transcript("Boss", clean_tx)

                                # 2. Immediately inject into Antigravity Chat
                                inject_agent_chat(clean_tx, target_hint=self.config.target_agent)

                        self.coordinator.finish_turn()

                await asyncio.sleep(0.005)
        finally:
            self.stop()

    def stop(self):
        self._running = False
        self.audio_mgr.stop()
        self.coordinator.finish_turn()
        print("[Live Voice Engine] Stopped cleanly.")

GeminiLiveEngine = UniversalLiveVoiceEngine
