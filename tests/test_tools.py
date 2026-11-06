import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.tools import execute_system_command, read_workspace_file, parse_spoken_enter

class TestTools(unittest.TestCase):
    def test_parse_spoken_enter(self):
        text1, enter1 = parse_spoken_enter("deploy to staging enter")
        self.assertEqual(text1, "deploy to staging")
        self.assertTrue(enter1)

        text2, enter2 = parse_spoken_enter("check status")
        self.assertEqual(text2, "check status")
        self.assertFalse(enter2)

        text3, enter3 = parse_spoken_enter("enter")
        self.assertEqual(text3, "")
        self.assertTrue(enter3)

    def test_execute_command(self):
        res = execute_system_command("Write-Output 'Live Voice Ready'")
        self.assertEqual(res.get("exit_code"), 0)
        self.assertIn("Live Voice Ready", res.get("stdout", ""))

    def test_read_workspace_file(self):
        res = read_workspace_file(str(ROOT / "config.json"))
        self.assertIn("content", res)
        self.assertIn("gemini-3.1-flash-live-preview", res["content"])

    def test_read_workspace_file_confinement_and_sensitive_patterns(self):
        # Sensitive pattern block
        res = read_workspace_file("some/path/.env")
        self.assertIn("error", res)
        self.assertIn("Access denied", res["error"])

        # Outside workspace root
        res2 = read_workspace_file(str(ROOT / "config.json"), workspace_root=str(ROOT / "core"))
        self.assertIn("error", res2)
        self.assertIn("Access denied", res2["error"])

if __name__ == "__main__":
    unittest.main()

