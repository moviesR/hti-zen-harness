"""Safety Shield - final safety check before environment (100 Hz)

Always runs last in the band ordering. Enforces hard bounds and logs interventions.
"""

from typing import Optional
from hti_v0_demo.shared_state import SharedState
from hti_v0_demo.event_log import EventPack


class SafetyShield:
    """Safety Shield enforcing action bounds.

    Runs at 100 Hz, always last before env.step.
    Clips actions to safe bounds and generates EventPacks on intervention.
    """

    def __init__(self, u_min: float = -0.05, u_max: float = 0.05):
        """Initialize safety shield.

        Args:
            u_min: Minimum allowed action
            u_max: Maximum allowed action

        Raises:
            ValueError: If u_min > u_max (invalid safety bounds)
        """
        if u_min > u_max:
            raise ValueError(f"u_min ({u_min}) must be <= u_max ({u_max})")
        self.u_min = u_min
        self.u_max = u_max

    def apply(self, state: SharedState) -> tuple[float, Optional[EventPack]]:
        """Apply safety bounds to proposed action.

        v0.2 PRECEDENCE (Zen MCP #4):
          1. Sensor mismatch → STOP (action_final = 0.0)
          2. Out of bounds → CLIP
          3. Near boundary → CONSERVATIVE CLIP

        Reads: state.action_proposed, state.obs, state.reflex_flags
        Produces:
          - safe action_final (bounded or stopped)
          - optional EventPack if clipping / override occurred
        Writes: state.action_final

        Args:
            state: Shared state (modified in-place)

        Returns:
            Tuple of (safe_action, optional_event)
        """
        proposed = state.action_proposed if state.action_proposed is not None else 0.0

        # PRECEDENCE 1: Sensor mismatch (Zen MCP #1 - trust ReflexBand flag)
        if state.reflex_flags.sensor_mismatch:
            safe_action = 0.0
            state.action_final = safe_action

            # Zen MCP #5: Generate event even if proposed==0.0
            event = EventPack(
                timestamp=state.t,
                tick=state.tick,
                band="SafetyShield",
                obs_before=state.obs.copy(),
                action_proposed=proposed,
                action_final=safe_action,
                reason="stop_sensor_mismatch",  # v0.2
                metadata={
                    "near_boundary": state.reflex_flags.near_boundary,
                    "too_fast": state.reflex_flags.too_fast,
                    "distance_to_boundary": state.reflex_flags.distance_to_boundary,
                    "sensor_mismatch": state.reflex_flags.sensor_mismatch,
                    "mismatch_magnitude": state.reflex_flags.mismatch_magnitude
                }
            )
            return safe_action, event

        # PRECEDENCE 2: Boundary-aware clipping
        conservative_mode = state.reflex_flags.near_boundary

        # Set bounds (potentially stricter if near boundary)
        if conservative_mode:
            # Be more conservative near boundaries
            u_min_effective = self.u_min * 0.5
            u_max_effective = self.u_max * 0.5
            reason_prefix = "clip_near_boundary"
        else:
            u_min_effective = self.u_min
            u_max_effective = self.u_max
            reason_prefix = "clip_out_of_bounds"

        # Clip to bounds
        safe_action = max(u_min_effective, min(u_max_effective, proposed))

        # Update state
        state.action_final = safe_action

        # Generate event if we intervened
        event = None
        if abs(safe_action - proposed) > 1e-9:  # Intervention occurred
            event = EventPack(
                timestamp=state.t,
                tick=state.tick,
                band="SafetyShield",
                obs_before=state.obs.copy(),
                action_proposed=proposed,
                action_final=safe_action,
                reason=reason_prefix,
                metadata={
                    "near_boundary": state.reflex_flags.near_boundary,
                    "too_fast": state.reflex_flags.too_fast,
                    "distance_to_boundary": state.reflex_flags.distance_to_boundary,
                    "sensor_mismatch": state.reflex_flags.sensor_mismatch,
                    "mismatch_magnitude": state.reflex_flags.mismatch_magnitude
                }
            )

        return safe_action, event
