import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import LiveVoiceConfig, PersonaConfig, AudioConfig, ModelConfig

class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = LiveVoiceConfig.load()
        self.assertIsNotNone(cfg.persona)
        self.assertEqual(cfg.persona.callsign, "Boss")
        self.assertEqual(cfg.model.live_model, "gemini-3.1-flash-live-preview")
        self.assertEqual(cfg.audio.input_sample_rate, 16000)
        self.assertEqual(cfg.audio.output_sample_rate, 24000)

    def test_audio_device_indices(self):
        audio_cfg = AudioConfig(input_device_index=1, output_device_index=3)
        self.assertEqual(audio_cfg.input_device_index, 1)
        self.assertEqual(audio_cfg.output_device_index, 3)

if __name__ == "__main__":
    unittest.main()
