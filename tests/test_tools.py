import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.tools import execute_system_command, read_workspace_file

class TestTools(unittest.TestCase):
    def test_execute_command(self):
        res = execute_system_command("Write-Output 'Live Voice Ready'")
        self.assertEqual(res.get("exit_code"), 0)
        self.assertIn("Live Voice Ready", res.get("stdout", ""))

    def test_read_workspace_file(self):
        res = read_workspace_file(str(ROOT / "config.json"))
        self.assertIn("content", res)
        self.assertIn("gemini-3.1-flash-live-preview", res["content"])

if __name__ == "__main__":
    unittest.main()
