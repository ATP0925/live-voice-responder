"""
High-Performance Audio Stream Manager with Instant Barge-In (Interruption) Support
Handles 16kHz PCM input and 24kHz PCM output via sounddevice with zero-crash fallbacks.
"""

import sys
import queue
import threading
import numpy as np
from typing import Optional, Callable

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioStreamManager:
    def __init__(
        self,
        input_rate: int = 16000,
        output_rate: int = 24000,
        chunk_size: int = 1024,
        vad_energy_threshold: float = 0.015,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
        on_interruption: Optional[Callable[[], None]] = None
    ):
        self.input_rate = input_rate
        self.output_rate = output_rate
        self.chunk_size = chunk_size
        self.vad_energy_threshold = vad_energy_threshold
        self.input_device = input_device
        self.output_device = output_device
        self.on_interruption = on_interruption

        self.input_queue: queue.Queue = queue.Queue()
        self.output_queue: queue.Queue = queue.Queue()

        self._is_playing = False
        self._is_recording = False
        self._running = False

        self.input_stream = None
        self.output_stream = None
        self._lock = threading.Lock()

    def _input_callback(self, indata, frames, time_info, status):
        """Processes microphone input frames."""
        pcm_data = indata.copy()
        raw_bytes = (pcm_data * 32767).astype(np.int16).tobytes()
        self.input_queue.put(raw_bytes)

        # Calculate RMS energy for VAD / Interruption
        rms = np.sqrt(np.mean(pcm_data**2)) if len(pcm_data) > 0 else 0.0

        if self._is_playing and rms > self.vad_energy_threshold:
            if self.on_interruption:
                self.on_interruption()
            self.flush_playback()

    def _output_callback(self, outdata, frames, time_info, status):
        """Feeds audio frames to sound card speakers."""
        bytes_needed = frames * 2
        filled = 0
        out_bytes = bytearray()

        while filled < bytes_needed:
            try:
                chunk = self.output_queue.get_nowait()
                if chunk is None:
                    break
                out_bytes.extend(chunk)
                filled = len(out_bytes)
            except queue.Empty:
                break

        if len(out_bytes) >= bytes_needed:
            to_play = out_bytes[:bytes_needed]
            remainder = out_bytes[bytes_needed:]
            if remainder:
                self.output_queue.queue.appendleft(bytes(remainder))
            
            audio_np = np.frombuffer(to_play, dtype=np.int16).astype(np.float32) / 32767.0
            outdata[:, 0] = audio_np
            self._is_playing = True
        elif len(out_bytes) > 0:
            to_play = bytes(out_bytes)
            audio_np = np.frombuffer(to_play, dtype=np.int16).astype(np.float32) / 32767.0
            outdata[:len(audio_np), 0] = audio_np
            outdata[len(audio_np):, 0] = 0.0
            self._is_playing = True
        else:
            outdata.fill(0.0)
            self._is_playing = False

    def start(self):
        """Starts input and output streams."""
        if not SOUNDDEVICE_AVAILABLE:
            print("[AudioStream] sounddevice is not available. Audio hardware streaming disabled.")
            return

        with self._lock:
            if self._running:
                return

            self._running = True
            try:
                self.input_stream = sd.InputStream(
                    samplerate=self.input_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.chunk_size,
                    device=self.input_device,
                    callback=self._input_callback
                )
                self.output_stream = sd.OutputStream(
                    samplerate=self.output_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.chunk_size,
                    device=self.output_device,
                    callback=self._output_callback
                )
                self.input_stream.start()
                self.output_stream.start()
                self._is_recording = True
            except Exception as e:
                print(f"[Audio Hardware Warning]: {e}")
                self._running = False

    def stop(self):
        """Stops all streams cleanly."""
        with self._lock:
            self._running = False
            self._is_recording = False
            self._is_playing = False
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception:
                    pass
                self.input_stream = None
            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception:
                    pass
                self.output_stream = None
            self.flush_playback()

    def feed_output_audio(self, raw_pcm_bytes: bytes):
        """Pushes raw PCM audio bytes to the speaker playback queue."""
        if not self._running:
            return
        self.output_queue.put(raw_pcm_bytes)
        self._is_playing = True

    def flush_playback(self):
        """Instantly flushes output audio queue to silence output on interruption."""
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break
        self._is_playing = False

    def get_input_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Retrieves recorded 16kHz PCM chunk from mic queue."""
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @staticmethod
    def list_audio_devices():
        """Lists all physical/virtual audio devices available in the OS."""
        if not SOUNDDEVICE_AVAILABLE:
            return []
        try:
            return sd.query_devices()
        except Exception as e:
            print(f"[Audio Devices Warning]: {e}")
            return []
