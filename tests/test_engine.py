import unittest
import math
import threading
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestFallbackTTS(unittest.TestCase):
    def test_clean_text_strips_markdown(self):
        from core.fallback_tts import FallbackTTS
        tts = FallbackTTS()
        result = tts.clean_text("**bold** and `code` and [link](http://example.com)")
        self.assertNotIn("**", result)
        self.assertNotIn("`", result)
        self.assertNotIn("http://", result)

    def test_clean_text_empty(self):
        from core.fallback_tts import FallbackTTS
        tts = FallbackTTS()
        self.assertEqual(tts.clean_text(""), "")


class TestParseSpokenEnter(unittest.TestCase):
    def test_enter_at_end(self):
        from core.tools import parse_spoken_enter
        text, flag = parse_spoken_enter("hello world enter")
        self.assertTrue(flag)
        self.assertEqual(text, "hello world")

    def test_just_enter(self):
        from core.tools import parse_spoken_enter
        text, flag = parse_spoken_enter("enter")
        self.assertTrue(flag)
        # stripped should be empty
        self.assertEqual(text, "")

    def test_no_enter(self):
        from core.tools import parse_spoken_enter
        text, flag = parse_spoken_enter("hello world")
        self.assertFalse(flag)


class TestAudioStreamAndPTT(unittest.TestCase):
    def test_ptt_max_duration_constant(self):
        from core.audio_stream import PTT_MAX_DURATION
        self.assertEqual(PTT_MAX_DURATION, 30.0)

    def test_audio_clipping_prevents_overflow(self):
        from core.audio_stream import AudioStreamManager
        mgr = AudioStreamManager()
        # Feed extreme audio data that exceeds [-1.0, 1.0]
        extreme_indata = np.array([[2.5], [-3.0], [0.5]], dtype=np.float32)
        mgr._input_callback(extreme_indata, frames=3, time_info=None, status=None)
        chunk = mgr.get_input_chunk(timeout=0.1)
        self.assertIsNotNone(chunk)
        arr = np.frombuffer(chunk, dtype=np.int16)
        # Verify clipping: maximum int16 value (32767) and minimum (-32767)
        self.assertEqual(arr[0], 32767)
        self.assertEqual(arr[1], -32767)
        self.assertEqual(arr[2], int(0.5 * 32767))


class TestTerminalHUD(unittest.TestCase):
    def test_nan_and_inf_energy_guarded(self):
        from ui.terminal_hud import TerminalHUD
        hud = TerminalHUD()
        
        # Test NaN
        hud.update_energy(float("nan"))
        self.assertEqual(hud.current_energy, 0.0)
        panel = hud.generate_status_panel()
        self.assertIsNotNone(panel)

        # Test Inf
        hud.update_energy(float("inf"))
        self.assertEqual(hud.current_energy, 0.0)
        panel_inf = hud.generate_status_panel()
        self.assertIsNotNone(panel_inf)

    def test_thread_safe_messages(self):
        from ui.terminal_hud import TerminalHUD
        hud = TerminalHUD()

        def worker(idx):
            for i in range(20):
                hud.add_message(f"Speaker_{idx}", f"msg {i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        messages = hud.get_messages()
        self.assertLessEqual(len(messages), 10)
        # Snapshot in render
        panel = hud.render()
        self.assertIsNotNone(panel)


if __name__ == "__main__":
    unittest.main()
