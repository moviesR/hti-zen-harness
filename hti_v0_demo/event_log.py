"""Event logging for HTI v0.1

Logs safety interventions as EventPacks in JSONL format.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class EventPack:
    """Record of a safety intervention by the Shield.

    Attributes:
        timestamp: Simulated time in seconds
        tick: Discrete step counter
        band: Name of the band that generated the event (e.g., "SafetyShield")
        obs_before: Environment observation before intervention
        action_proposed: Action requested by Control
        action_final: Action allowed by Shield
        reason: Why the intervention occurred
        metadata: Additional context (optional)
    """
    timestamp: float
    tick: int
    band: str
    obs_before: dict[str, float]
    action_proposed: float
    action_final: float
    reason: str
    metadata: dict[str, Any]


class EventLogger:
    """Logs EventPacks to JSONL file and provides summary statistics.

    Writes each event immediately (no buffering) to event_log.jsonl.
    Tracks statistics for console summary.
    """

    def __init__(self, log_path: str = "event_log.jsonl"):
        """Initialize the event logger.

        Args:
            log_path: Path to JSONL output file
        """
        self.log_path = Path(log_path)
        self.events: list[EventPack] = []
        self.reason_counts: dict[str, int] = {}

        # Clear log file at start
        if self.log_path.exists():
            self.log_path.unlink()

    def log(self, event: EventPack) -> None:
        """Log an event immediately to JSONL file and update statistics.

        Args:
            event: EventPack to log
        """
        # Store for summary
        self.events.append(event)

        # Update reason counts
        self.reason_counts[event.reason] = self.reason_counts.get(event.reason, 0) + 1

        # Write immediately to JSONL
        with open(self.log_path, 'a') as f:
            json_line = json.dumps(asdict(event))
            f.write(json_line + '\n')

    def dump(self) -> None:
        """Print human-readable summary to console."""
        if not self.events:
            print("\nNo Shield interventions occurred.")
            return

        print(f"\n=== Event Summary ===")
        print(f"Total Shield interventions: {len(self.events)}")

        if self.reason_counts:
            print(f"\nBy reason:")
            for reason, count in sorted(self.reason_counts.items()):
                print(f"  {reason}: {count}")

        # Show first and last events
        first = self.events[0]
        last = self.events[-1]

        print(f"\nFirst event (tick {first.tick}):")
        print(f"  Proposed: {first.action_proposed:.4f} → Final: {first.action_final:.4f} ({first.reason})")

        if len(self.events) > 1:
            print(f"\nLast event (tick {last.tick}):")
            print(f"  Proposed: {last.action_proposed:.4f} → Final: {last.action_final:.4f} ({last.reason})")

        print(f"\nEvent log written to: {self.log_path}")
