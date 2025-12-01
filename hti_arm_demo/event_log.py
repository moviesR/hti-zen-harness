"""
Event logging for HTI arm demo.

Writes safety intervention events to JSONL format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from hti_arm_demo.shared_state import ArmEventPack


class EventLogger:
    """
    Simple JSONL logger for safety intervention events.

    Writes events to file and optionally prints to console.
    """

    def __init__(self, filepath: str | Path = "event_log.jsonl", verbose: bool = False):
        """
        Initialize event logger.

        Args:
            filepath: Path to JSONL output file
            verbose: If True, print events to console
        """
        self.filepath = Path(filepath)
        self.verbose = verbose
        self.events: List[ArmEventPack] = []

    def log(self, event: ArmEventPack) -> None:
        """Add event to buffer."""
        self.events.append(event)
        if self.verbose:
            print(f"[Event] tick={event.tick} {event.band}: {event.reason}")

    def flush(self) -> None:
        """Write all buffered events to file."""
        if not self.events:
            return

        with open(self.filepath, "w") as f:
            for event in self.events:
                # Convert event to dict
                event_dict = {
                    "timestamp": event.timestamp,
                    "tick": event.tick,
                    "band": event.band,
                    "obs_before": event.obs_before,
                    "action_proposed": list(event.action_proposed),
                    "action_final": list(event.action_final),
                    "reason": event.reason,
                    "metadata": event.metadata,
                }
                f.write(json.dumps(event_dict) + "\n")

    def clear(self) -> None:
        """Clear event buffer."""
        self.events.clear()
