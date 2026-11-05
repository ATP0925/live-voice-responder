"""
Digital Signal Processing (DSP) & Adaptive Noise Gate for Live Voice Responder
Eliminates laptop fan hum, AC rumble, and ambient room noise using a 4th-order
Butterworth vocal bandpass filter (300Hz - 3400Hz) and dual-threshold hysteresis.
"""

import time
import numpy as np
from typing import Tuple

try:
    from scipy.signal import butter, sosfilt
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class SpeechNoiseFilter:
    """Bandpass filter that strips fan noise (<300Hz) and high hiss (>3400Hz)."""
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        if SCIPY_AVAILABLE:
            # 4th order Butterworth bandpass filter
            self.sos = butter(4, [300, 3400], btype='bandpass', fs=sample_rate, output='sos')
        else:
            self.sos = None

    def filter_chunk(self, pcm_float: np.ndarray) -> np.ndarray:
        if self.sos is not None and len(pcm_float) > 16:
            try:
                return sosfilt(self.sos, pcm_float)
            except Exception:
                pass
        return pcm_float


class AdaptiveNoiseGate:
    """
    Dual-threshold hysteresis noise gate with rolling ambient noise baseline.
    Prevents background hum from hanging the silence detector.
    """
    def __init__(
        self,
        sample_rate: int = 16000,
        silence_timeout: float = 0.45,
        min_speech_duration: float = 0.35,
        max_speech_duration: float = 6.0
    ):
        self.filter = SpeechNoiseFilter(sample_rate=sample_rate)
        self.silence_timeout = silence_timeout
        self.min_speech_duration = min_speech_duration
        self.max_speech_duration = max_speech_duration

        self.ambient_floor = 0.008
        self.calibrated = False
        self.ambient_samples = []

        self.is_speaking = False
        self.speech_start_time = 0.0
        self.last_voice_time = 0.0

    def process_chunk(self, raw_chunk: bytes) -> Tuple[bool, bool, float]:
        """
        Processes a 16kHz PCM chunk.
        Returns: (is_currently_speaking, speech_just_finished, filtered_rms)
        """
        if not raw_chunk:
            return self.is_speaking, False, 0.0

        pcm_raw = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32767.0
        # 1. Strip fan hum and room rumble
        pcm_filtered = self.filter.filter_chunk(pcm_raw)
        rms = float(np.sqrt(np.mean(pcm_filtered**2))) if len(pcm_filtered) > 0 else 0.0

        now = time.time()

        # 2. Calibration of initial ambient floor
        if not self.calibrated:
            self.ambient_samples.append(rms)
            if len(self.ambient_samples) >= 10:
                self.ambient_floor = max(0.004, float(np.mean(self.ambient_samples)))
                self.calibrated = True
            return False, False, rms

        # 3. Dual-threshold hysteresis
        # Attack threshold requires clear human vocal energy above ambient floor
        attack_thresh = max(0.018, self.ambient_floor * 2.6 + 0.010)
        # Release threshold for silence drop
        release_thresh = max(0.010, self.ambient_floor * 1.4 + 0.004)

        just_finished = False

        if rms > attack_thresh:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_start_time = now
            self.last_voice_time = now
        elif self.is_speaking:
            # Below release threshold -> silence counting
            if rms < release_thresh:
                silence_elapsed = now - self.last_voice_time
                total_duration = now - self.speech_start_time

                # Check if Boss finished speaking (pause >= silence_timeout or max duration exceeded)
                if silence_elapsed >= self.silence_timeout or total_duration >= self.max_speech_duration:
                    self.is_speaking = False
                    if total_duration >= self.min_speech_duration:
                        just_finished = True
        else:
            # Slow leaky update of ambient floor during quiet periods
            self.ambient_floor = 0.98 * self.ambient_floor + 0.02 * rms

        return self.is_speaking, just_finished, rms
