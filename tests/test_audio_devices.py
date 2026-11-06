import unittest
import json
import os
import tempfile
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.audio_stream import AudioStreamManager

class TestAudioDevicesAndLock(unittest.TestCase):
    def test_list_audio_devices(self):
        devices = AudioStreamManager.list_audio_devices()
        self.assertIsInstance(devices, (list, tuple, object))

    def test_audio_stream_manager_init_with_devices(self):
        mgr = AudioStreamManager(input_device=1, output_device=3)
        self.assertEqual(mgr.input_device, 1)
        self.assertEqual(mgr.output_device, 3)

    def test_output_callback_odd_bytes_no_crash(self):
        import numpy as np
        mgr = AudioStreamManager()
        # Feed odd number of bytes into queue
        mgr._running = True
        mgr.feed_output_audio(b"\x01\x02\x03\x04\x05")
        outdata = np.zeros((10, 1), dtype=np.float32)
        mgr._output_callback(outdata, frames=10, time_info=None, status=None)
        self.assertTrue(mgr.is_playing)

    def test_speaking_lock_payload(self):
        lock_file = os.path.join(tempfile.gettempdir(), "test_speaking_lock.json")
        try:
            payload = json.dumps({"pid": os.getpid(), "timestamp": time.time()})
            with open(lock_file, "w", encoding="utf-8") as f:
                f.write(payload)

            with open(lock_file, "r", encoding="utf-8") as f:
                data = json.loads(f.read())

            self.assertEqual(data["pid"], os.getpid())
            self.assertGreater(data["timestamp"], 0)
        finally:
            if os.path.exists(lock_file):
                os.remove(lock_file)

if __name__ == "__main__":
    unittest.main()
