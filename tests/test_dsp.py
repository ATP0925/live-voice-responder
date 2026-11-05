import unittest
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.dsp import SpeechNoiseFilter, AdaptiveNoiseGate

class TestDSP(unittest.TestCase):
    def test_butterworth_bandpass_attenuates_low_fan_rumble(self):
        filter_obj = SpeechNoiseFilter(16000)
        t = np.linspace(0, 0.1, 1600)
        fan_100hz = np.sin(2 * np.pi * 100 * t)
        voice_600hz = np.sin(2 * np.pi * 600 * t)

        filtered_fan = filter_obj.filter_chunk(fan_100hz)
        filtered_voice = filter_obj.filter_chunk(voice_600hz)

        rms_fan_after = np.sqrt(np.mean(filtered_fan**2))
        rms_voice_after = np.sqrt(np.mean(filtered_voice**2))

        # Fan noise should be significantly attenuated (>50% on fallback, >98% on SciPy)
        self.assertLess(rms_fan_after, 0.35)
        # Human vocal frequency should pass through intact (>80% preserved)
        self.assertGreater(rms_voice_after, 0.55)

    def test_adaptive_noise_gate_vocal_detection(self):
        gate = AdaptiveNoiseGate(sample_rate=16000, silence_timeout=0.3, min_speech_duration=0.1)
        
        # 8 quiet chunks to calibrate ambient floor
        silence_chunk = (np.zeros(512, dtype=np.int16)).tobytes()
        for _ in range(8):
            gate.process_chunk(silence_chunk)
        self.assertTrue(gate.calibrated)

        # Voice burst at 500Hz
        t = np.linspace(0, 0.032, 512)
        voice_pcm = (np.sin(2 * np.pi * 500 * t) * 15000).astype(np.int16).tobytes()
        is_spk, just_fin, rms = gate.process_chunk(voice_pcm)
        self.assertTrue(is_spk)
        self.assertFalse(just_fin)

if __name__ == "__main__":
    unittest.main()
