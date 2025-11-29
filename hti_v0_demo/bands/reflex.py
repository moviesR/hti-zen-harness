"""Reflex band - fast safety pre-checks (100 Hz)

Analyzes proposed actions and sets warning flags.
Does NOT modify the action - only provides flags for Shield.
"""

from hti_v0_demo.shared_state import SharedState, ReflexFlags


class ReflexBand:
    """Fast reflex band running at 100 Hz.

    Performs pre-checks on proposed actions and sets flags.
    Does not modify actions directly.
    """

    def __init__(self, boundary_margin: float = 0.1, speed_threshold: float = 0.08):
        """Initialize reflex band.

        Args:
            boundary_margin: Distance from boundary considered "near"
            speed_threshold: Action magnitude considered "too fast"
        """
        self.boundary_margin = boundary_margin
        self.speed_threshold = speed_threshold

    def step(self, state: SharedState) -> None:
        """Check proposed action against current state.

        Reads: state.obs, state.action_proposed
        Writes: state.reflex_flags
        MUST NOT write: state.action_proposed, state.action_final

        Args:
            state: Shared state (modified in-place)
        """
        x = state.obs.get("x", 0.0)
        action = state.action_proposed if state.action_proposed is not None else 0.0

        # Check proximity to boundaries
        dist_to_lower = x - 0.0
        dist_to_upper = 1.0 - x
        distance_to_boundary = min(dist_to_lower, dist_to_upper)

        near_boundary = distance_to_boundary < self.boundary_margin

        # Check if action is too aggressive
        too_fast = abs(action) > self.speed_threshold

        # Update flags (NOT action)
        state.reflex_flags = ReflexFlags(
            near_boundary=near_boundary,
            too_fast=too_fast,
            distance_to_boundary=distance_to_boundary
        )
