"""Semantics band - high-level advisor (10 Hz)

ADVISORY ONLY: Cannot set action_proposed or action_final.
"""

from hti_v0_demo.shared_state import SharedState, SemanticsAdvice


class SemanticsBand:
    """High-level advisory band running at 10 Hz.

    Provides strategic hints to lower bands but cannot directly control actions.
    """

    def step(self, state: SharedState) -> None:
        """Compute high-level advice based on current observation.

        Reads: state.obs
        Writes: state.semantics_advice
        MUST NOT write: state.action_proposed, state.action_final

        Args:
            state: Shared state (modified in-place)
        """
        # TODO v0.2: Use direct dict access state.obs["x"] to fail fast on malformed obs
        x = state.obs.get("x", 0.0)
        x_target = state.obs.get("x_target", 0.0)

        error = x_target - x

        # Simple heuristic: suggest direction
        if abs(error) < 0.05:
            # Close to target
            direction_hint = 0
            confidence = 0.9
        elif error > 0:
            # Target is to the right
            direction_hint = 1
            confidence = min(0.5 + abs(error), 1.0)
        else:
            # Target is to the left
            direction_hint = -1
            confidence = min(0.5 + abs(error), 1.0)

        # Update advisory output (NOT action)
        state.semantics_advice = SemanticsAdvice(
            direction_hint=direction_hint,
            confidence=confidence
        )
