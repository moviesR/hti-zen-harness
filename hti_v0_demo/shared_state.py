"""Shared state data structures for HTI v0.1

Contains the core state objects that flow through the time-banded system.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SemanticsAdvice:
    """High-level advisory output from Semantics band.

    Attributes:
        direction_hint: Suggested direction (-1, 0, or +1)
        confidence: Confidence in the suggestion (0.0 to 1.0)
    """
    direction_hint: int = 0
    confidence: float = 0.0


@dataclass
class ReflexFlags:
    """Fast pre-check flags from Reflex band.

    Attributes:
        near_boundary: True if state is near a safety boundary
        too_fast: True if proposed action is too aggressive
        distance_to_boundary: Distance to nearest boundary
    """
    near_boundary: bool = False
    too_fast: bool = False
    distance_to_boundary: float = 0.0


@dataclass
class SharedState:
    """Global state shared across all bands in the HTI system.

    Time is owned by the scheduler:
    - tick: discrete step counter (0, 1, 2, ...)
    - t: simulated time in seconds (t = tick * dt)

    Action flow: Control → Reflex → Shield → Environment
    - action_proposed: What Control wants
    - action_final: What Shield allows (bounded, safe)

    Advisory outputs:
    - semantics_advice: High-level guidance (advisory only)
    - reflex_flags: Fast safety pre-checks

    Observation:
    - obs: Current environment observation
    """
    t: float = 0.0
    tick: int = 0
    obs: dict[str, float] = field(default_factory=dict)

    # Control → Shield action flow
    action_proposed: Optional[float] = None
    action_final: Optional[float] = None

    # Semantics output (advisory)
    semantics_advice: SemanticsAdvice = field(default_factory=SemanticsAdvice)

    # Reflex flags
    reflex_flags: ReflexFlags = field(default_factory=ReflexFlags)
