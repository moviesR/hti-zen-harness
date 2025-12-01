"""
Shared state data structures for HTI arm demo.

These structures are passed between time bands within a single tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional


@dataclass
class ArmSemanticsAdvice:
    """
    High-level task advice from Semantics band (10 Hz).

    Tracks current stage in multi-waypoint task and goal position.
    """
    stage_index: int
    x_goal: float
    y_goal: float
    stage_complete: bool = False


@dataclass
class ArmReflexFlags:
    """
    Fast safety flags from Reflex band (100 Hz).

    Detects proximity to joint limits, excessive velocities, and obstacles.
    """
    # Joint limit proximity
    joint1_near_limit: bool
    joint2_near_limit: bool
    joint1_distance_to_limit: float
    joint2_distance_to_limit: float

    # Velocity limits
    joints_too_fast: bool

    # Obstacle detection (stubbed for v0.4)
    near_obstacle: bool
    obstacle_distance: Optional[float] = None


@dataclass
class ArmEventPack:
    """
    Safety intervention event for logging.

    Generated when SafetyShield modifies proposed actions.
    """
    timestamp: float  # seconds
    tick: int
    band: str  # which band generated the event

    # State snapshot
    obs_before: Dict[str, float]

    # Action comparison
    action_proposed: Tuple[float, float]  # (tau1, tau2) before Shield
    action_final: Tuple[float, float]  # (tau1, tau2) after Shield

    # Intervention details
    reason: str
    metadata: Dict[str, float | int | bool] = field(default_factory=dict)


@dataclass
class ArmSharedState:
    """
    Shared state passed between bands in HTI arm demo.

    Updated by each band in strict order:
      Semantics → Control → Reflex → SafetyShield → env.step()
    """

    # Time
    tick: int = 0
    t: float = 0.0  # seconds

    # Environment observation
    obs: Dict[str, float] = field(default_factory=dict)

    # Band outputs
    semantics_advice: Optional[ArmSemanticsAdvice] = None
    reflex_flags: Optional[ArmReflexFlags] = None

    # Actions
    action_proposed: Optional[Tuple[float, float]] = None  # from Control+brain
    action_final: Optional[Tuple[float, float]] = None  # from SafetyShield

    # Brain tracking (v0.5)
    brain_name: str = "unknown"  # which brain produced action_proposed

    # Statistics
    shield_interventions: int = 0
