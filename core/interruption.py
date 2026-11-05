"""
Turn-Taking, VAD & Barge-In State Machine
Coordinates natural flow and tracks conversation metrics.
"""

import time
from enum import Enum
from typing import Callable, Optional, Dict, Any

class ConversationState(Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"

class InterruptionCoordinator:
    def __init__(self, on_state_change: Optional[Callable[[ConversationState], None]] = None):
        self.state = ConversationState.IDLE
        self.on_state_change = on_state_change
        
        # Metrics
        self.turns_count = 0
        self.interruptions_count = 0
        self.turn_start_time = 0.0
        self.last_speech_time = 0.0
        self.total_latency_ms = 0.0

    def set_state(self, new_state: ConversationState):
        if self.state != new_state:
            prev = self.state
            self.state = new_state
            if self.on_state_change:
                self.on_state_change(new_state)

    def trigger_interruption(self):
        """Called when user starts speaking while agent is speaking."""
        self.interruptions_count += 1
        self.set_state(ConversationState.INTERRUPTED)

    def start_user_turn(self):
        self.turn_start_time = time.time()
        self.set_state(ConversationState.LISTENING)

    def start_processing(self):
        self.set_state(ConversationState.PROCESSING)

    def start_agent_speaking(self):
        if self.turn_start_time > 0:
            latency = (time.time() - self.turn_start_time) * 1000
            self.total_latency_ms += latency
            self.turns_count += 1
        self.set_state(ConversationState.SPEAKING)

    def finish_turn(self):
        self.set_state(ConversationState.IDLE)

    def get_metrics(self) -> Dict[str, Any]:
        avg_latency = (self.total_latency_ms / self.turns_count) if self.turns_count > 0 else 0.0
        return {
            "state": self.state.value,
            "turns_count": self.turns_count,
            "interruptions_count": self.interruptions_count,
            "avg_latency_ms": round(avg_latency, 1)
        }
