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

    def __init__(
        self,
        boundary_margin: float = 0.1,
        speed_threshold: float = 0.08,
        mismatch_threshold: float = 0.05  # v0.2
    ):
        """Initialize reflex band.

        Args:
            boundary_margin: Distance from boundary considered "near"
            speed_threshold: Action magnitude considered "too fast"
            mismatch_threshold: |x_true - x_meas| considered a sensor fault (v0.2)
        """
        self.boundary_margin = boundary_margin
        self.speed_threshold = speed_threshold
        self.mismatch_threshold = mismatch_threshold

    def step(self, state: SharedState) -> None:
        """Check proposed action against current state.

        Reads: state.obs, state.action_proposed
        Writes: state.reflex_flags (COMPLETELY REPLACES previous flags)
        MUST NOT write: state.action_proposed, state.action_final

        Args:
            state: Shared state (modified in-place)
        """
        # v0.2: Use x_true for boundary checks (ground truth), fallback to x
        x_true = state.obs.get("x_true", state.obs.get("x", 0.0))
        x_meas = state.obs.get("x_meas", state.obs.get("x", 0.0))
        action = state.action_proposed if state.action_proposed is not None else 0.0

        # Check proximity to boundaries (using TRUE state)
        # TODO v0.2: Parameterize env bounds instead of hardcoding 0.0/1.0
        dist_to_lower = x_true - 0.0
        dist_to_upper = 1.0 - x_true
        distance_to_boundary = min(dist_to_lower, dist_to_upper)

        near_boundary = distance_to_boundary < self.boundary_margin

        # Check if action is too aggressive
        too_fast = abs(action) > self.speed_threshold

        # v0.2: Sensor mismatch detection
        mismatch_magnitude = abs(x_true - x_meas)
        sensor_mismatch = mismatch_magnitude > self.mismatch_threshold

        # REPLACE flags (stateless - Zen MCP #2)
        state.reflex_flags = ReflexFlags(
            near_boundary=near_boundary,
            too_fast=too_fast,
            distance_to_boundary=distance_to_boundary,
            sensor_mismatch=sensor_mismatch,
            mismatch_magnitude=mismatch_magnitude
        )
