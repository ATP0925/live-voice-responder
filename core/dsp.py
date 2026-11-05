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
    """Bandpass filter that strips fan noise (<300Hz) and high hiss (>3400Hz).
    Uses SciPy 4th-order Butterworth when available, or zero-dependency Pure-NumPy highpass fallback.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        if SCIPY_AVAILABLE:
            # 4th order Butterworth bandpass filter
            self.sos = butter(4, [300, 3400], btype='bandpass', fs=sample_rate, output='sos')
        else:
            self.sos = None
            cutoff = 300.0
            RC = 1.0 / (2.0 * np.pi * cutoff)
            dt = 1.0 / sample_rate
            self.alpha = float(RC / (RC + dt))
            self.prev_x = 0.0
            self.prev_y = 0.0

    def filter_chunk(self, pcm_float: np.ndarray) -> np.ndarray:
        if self.sos is not None and len(pcm_float) > 16:
            try:
                return sosfilt(self.sos, pcm_float)
            except Exception:
                pass
        elif len(pcm_float) > 1:
            # Pure NumPy IIR Highpass fallback (removes fan rumble <300Hz)
            y = np.empty_like(pcm_float)
            px = self.prev_x
            py = self.prev_y
            a = self.alpha
            for i in range(len(pcm_float)):
                curr_y = a * (py + pcm_float[i] - px)
                y[i] = curr_y
                px = pcm_float[i]
                py = curr_y
            self.prev_x = px
            self.prev_y = py
            return y
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
        min_speech_duration: float = 0.20,
        max_speech_duration: float = 6.0
    ):
        self.filter = SpeechNoiseFilter(sample_rate=sample_rate)
        self.silence_timeout = silence_timeout
        self.min_speech_duration = min_speech_duration
        self.max_speech_duration = max_speech_duration

        self.ambient_floor = 0.005
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

        # 2. Calibration of initial ambient floor (using lowest 20th percentile to ignore speech)
        if not self.calibrated:
            self.ambient_samples.append(rms)
            if len(self.ambient_samples) >= 8:
                perc = float(np.percentile(self.ambient_samples, 20))
                self.ambient_floor = min(0.010, max(0.002, perc))
                self.calibrated = True
            return False, False, rms

        # 3. Dynamic vocal sensitivity thresholds
        # Speech attack threshold: sensitive to human voice, never locking out user
        attack_thresh = min(0.022, max(0.010, self.ambient_floor * 1.5 + 0.004))
        # Release threshold: detect clean drop to silence
        release_thresh = max(0.005, self.ambient_floor * 1.1 + 0.002)

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
            # Slow leaky update of ambient floor during quiet periods (capped at 0.010)
            self.ambient_floor = min(0.010, 0.98 * self.ambient_floor + 0.02 * rms)

        return self.is_speaking, just_finished, rms

