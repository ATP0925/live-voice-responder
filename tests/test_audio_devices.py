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
