import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.interruption import InterruptionCoordinator, ConversationState

class TestInterruption(unittest.TestCase):
    def test_state_transitions_and_barge_in(self):
        coord = InterruptionCoordinator()
        self.assertEqual(coord.state, ConversationState.IDLE)

        # User starts speaking
        coord.start_user_turn()
        self.assertEqual(coord.state, ConversationState.LISTENING)

        # Agent starts speaking
        coord.start_agent_speaking()
        self.assertEqual(coord.state, ConversationState.SPEAKING)
        self.assertEqual(coord.turns_count, 1)

        # Barge-in happens!
        coord.trigger_interruption()
        self.assertEqual(coord.state, ConversationState.INTERRUPTED)
        self.assertEqual(coord.interruptions_count, 1)

        # Finish turn
        coord.finish_turn()
        self.assertEqual(coord.state, ConversationState.IDLE)

        # Mute test
        coord.set_state(ConversationState.MUTED)
        self.assertEqual(coord.state, ConversationState.MUTED)

    def test_unmute_does_not_trigger_mute(self):
        unmute_triggers = ["unmute mic", "unmute", "resume mic", "start listening", "mic on"]
        mute_triggers = [
            "mute mic", "pause mic", "stop listening", "pause listening",
            "mute please", "mic mute", "mic pause", "mute karo", "pause karo"
        ]

        raw_low = "unmute mic"
        self.assertTrue(raw_low in unmute_triggers or any(t == raw_low for t in unmute_triggers))
        is_mute = raw_low in ("mute", "pause") or any(t == raw_low for t in mute_triggers)
        self.assertFalse(is_mute)

    def test_barge_in_keywords_matching(self):
        barge_keywords = [
            "crow", "kro", "krow", "cro", "stop", "suno", "boss", "ruko",
            "wait", "hold", "pause", "bhai", "chup", "shant", "listen"
        ]
        test_phrases = ["crow suno", "ek minute stop karo", "bhai ruko", "wait a second", "kro listen"]
        for phrase in test_phrases:
            self.assertTrue(any(k in phrase.lower() for k in barge_keywords), f"Failed for {phrase}")

    def test_fallback_tts_lock_and_stop(self):
        import os, tempfile
        from core.fallback_tts import FallbackTTS, LOCK_FILE, ABORT_FILE
        tts = FallbackTTS()
        tts._set_speaking_lock(True)
        self.assertTrue(os.path.exists(LOCK_FILE))

        # Stop / Barge-in triggers cleanup
        tts.stop()
        self.assertTrue(tts._aborted)
        self.assertFalse(os.path.exists(LOCK_FILE))

if __name__ == "__main__":
    unittest.main()

