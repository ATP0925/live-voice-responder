"""
Gemini Live Multimodal Voice Engine (Full Duplex WebSocket Streaming)
Enterprise Opus 5.5 Level Rigor
Supports Gemini 3.1 Flash Live, native 24kHz audio, instant interruption (barge-in),
input/output real-time transcription, and live function calling.
"""

import os
import sys
import asyncio
import threading
from typing import Optional, Callable
from .config import LiveVoiceConfig
from .audio_stream import AudioStreamManager
from .interruption import InterruptionCoordinator, ConversationState
from .fallback_tts import FallbackTTS
from .tools import execute_system_command, read_workspace_file, inject_antigravity_chat

class GeminiLiveEngine:
    def __init__(
        self,
        config: Optional[LiveVoiceConfig] = None,
        on_transcript: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[ConversationState], None]] = None
    ):
        self.config = config or LiveVoiceConfig.load()
        self.on_transcript = on_transcript
        self.on_state_change = on_state_change

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

    async def _audio_send_loop(self, session):
        """Continuously streams 16kHz PCM audio from microphone to Gemini Live."""
        from google.genai import types

        while self._running:
            chunk = self.audio_mgr.get_input_chunk(timeout=0.05)
            if chunk and len(chunk) > 0:
                try:
                    await session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )
                except Exception as e:
                    if self._running:
                        pass
            await asyncio.sleep(0.01)

    async def _audio_receive_loop(self, session):
        """Receives streaming audio chunks, transcripts, and interruption signals."""
        try:
            async for response in session.receive():
                if not self._running:
                    break

                server_content = getattr(response, "server_content", None)
                if not server_content:
                    # Check for tool call
                    tool_call = getattr(response, "tool_call", None)
                    if tool_call:
                        await self._handle_tool_call(session, tool_call)
                    continue

                # 1. Handle Interruption Signal from Gemini
                if getattr(server_content, "interrupted", False):
                    self._handle_barge_in()
                    continue

                # 2. Handle Realtime Input Transcription (Boss's voice)
                input_tx = getattr(server_content, "input_transcription", None)
                if input_tx and hasattr(input_tx, "text") and input_tx.text:
                    tx_text = input_tx.text.strip()
                    if tx_text:
                        self.coordinator.start_user_turn()
                        if self.on_transcript:
                            self.on_transcript("Boss", tx_text)

                # 3. Handle Realtime Output Transcription (Agent's voice)
                output_tx = getattr(server_content, "output_transcription", None)
                if output_tx and hasattr(output_tx, "text") and output_tx.text:
                    tx_text = output_tx.text.strip()
                    if tx_text:
                        if self.on_transcript:
                            self.on_transcript("Agent", tx_text)

                # 4. Handle Streaming Audio Output (24kHz PCM)
                model_turn = getattr(server_content, "model_turn", None)
                if model_turn:
                    self.coordinator.start_agent_speaking()
                    for part in getattr(model_turn, "parts", []):
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            self.audio_mgr.feed_output_audio(inline.data)

                # 5. Turn Complete
                if getattr(server_content, "turn_complete", False):
                    self.coordinator.finish_turn()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._running:
                print(f"[Live Error]: {e}")

    async def _handle_tool_call(self, session, tool_call):
        """Executes live tools and sends tool response back to Gemini."""
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
            elif name == "inject_antigravity_chat":
                msg = args.get("message", "")
                result = inject_antigravity_chat(msg)

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
        """Connects to Gemini Multimodal Live API and begins duplex conversation."""
        api_key = self.config.api_key
        if not api_key:
            print("\n" + "="*65)
            print("  ⚠️  GEMINI_API_KEY IS NOT SET IN ENVIRONMENT")
            print("="*65)
            print("Please set your Gemini API key in powershell:")
            print("  $env:GEMINI_API_KEY='your-gemini-api-key'")
            print("Or pass it inside config.json.")
            print("\nStarting local fail-safe voice mode for Boss...\n")
            self.fallback_tts.speak(
                "Boss, Gemini API Key detect nahi hui. Main local neural mode me active hoon."
            )
            return

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Tools definition for live duplex function calling
        tools_def = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="execute_system_command",
                    description="Run PowerShell or terminal command for Boss.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "command": types.Schema(type="STRING", description="The command to execute.")
                        },
                        required=["command"]
                    )
                ),
                types.FunctionDeclaration(
                    name="read_workspace_file",
                    description="Read contents of any workspace file.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "file_path": types.Schema(type="STRING", description="Path of file to read.")
                        },
                        required=["file_path"]
                    )
                ),
                types.FunctionDeclaration(
                    name="inject_antigravity_chat",
                    description="Paste message into Antigravity IDE Chat box and press Enter.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "message": types.Schema(type="STRING", description="The prompt or instruction to send to Antigravity.")
                        },
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
                        voice_name=self.config.model.voice_name
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
        print(f"\n[Live Voice Engine] Connecting to {self.config.model.live_model}...")

        try:
            async with client.aio.live.connect(
                model=self.config.model.live_model,
                config=live_config
            ) as session:
                self._session = session
                print("✅ [Live Voice Engine] Connected! Dual-way conversation is LIVE.")
                print("👉 Bolna shuru kijiye Boss (Barge-in active: bolte hi AI ruk jayega).\n")

                # Concurrent send and receive loops
                send_task = asyncio.create_task(self._audio_send_loop(session))
                receive_task = asyncio.create_task(self._audio_receive_loop(session))

                await asyncio.gather(send_task, receive_task)

        except Exception as e:
            print(f"[Connection Error]: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stops the live engine and releases audio hardware."""
        self._running = False
        self.audio_mgr.stop()
        self.coordinator.finish_turn()
        print("[Live Voice Engine] Disconnected cleanly.")
