"""Control band - action selection (50 Hz)

Proposes actions based on observations and semantic advice.
Does NOT apply safety bounds - that's the Shield's job.
"""

from hti_v0_demo.shared_state import SharedState


class ControlBand:
    """Mid-level control band running at 50 Hz.

    Chooses action proposals that may be out of bounds.
    Shield will enforce safety.
    """

    def __init__(self, gain: float = 0.3):
        """Initialize control band.

        Args:
            gain: Proportional gain for position control
        """
        self.gain = gain

    def step(self, state: SharedState) -> None:
        """Compute action proposal based on obs and semantic advice.

        Reads: state.obs, state.semantics_advice
        Writes: state.action_proposed
        MUST NOT write: state.action_final

        Args:
            state: Shared state (modified in-place)
        """
        # TODO v0.2: Use direct dict access state.obs["x"] to fail fast on malformed obs
        x = state.obs.get("x", 0.0)
        x_target = state.obs.get("x_target", 0.0)

        error = x_target - x

        # Simple proportional control
        action = self.gain * error

        # Consider semantic advice for confidence scaling
        if state.semantics_advice.confidence > 0.7:
            # High confidence - use full gain
            pass
        elif state.semantics_advice.confidence < 0.3:
            # Low confidence - reduce aggressiveness
            action *= 0.5

        # Propose action (may be out of bounds - Shield will clip)
        state.action_proposed = action
