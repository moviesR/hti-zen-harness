"""
Control Band - Brain adapter layer (50 Hz)

Responsibilities:
- Translate SharedState → brain observations
- Delegate action computation to pluggable brain
- Manage brain internal state
- Write proposed actions

Reads: state.obs
Writes: state.action_proposed
"""

from __future__ import annotations

from typing import Any, Mapping

from hti_arm_demo.shared_state import ArmSharedState
from hti_arm_demo.brains.base import ArmBrainPolicy


class ControlBand:
    """
    Brain-agnostic control band.

    Runs at 50 Hz (every 2 ticks).
    """

    def __init__(self, brain: ArmBrainPolicy, brain_name: str = "unknown") -> None:
        """
        Initialize with pluggable brain.

        Args:
            brain: Any object implementing ArmBrainPolicy protocol
            brain_name: Name for tracking in EventPack metadata (v0.5)
        """
        self._brain = brain
        self._brain_name = brain_name
        self._brain_state: dict[str, Any] = {}
        self._initialized: bool = False

    def reset_episode(self) -> None:
        """
        Called by scheduler after env.reset().

        Initializes brain state for new episode.
        """
        self._brain_state.clear()
        self._initialized = True

    def _build_brain_obs(self, obs: Mapping[str, float]) -> Mapping[str, float]:
        """
        Anti-corruption layer: SharedState → brain observation.

        For v0.4, pass through directly. Future versions may add filtering.
        """
        return obs

    def step(self, state: ArmSharedState) -> None:
        """
        Compute action proposal using brain.

        Reads: state.obs
        Writes: state.action_proposed
        """
        if not self._initialized:
            raise RuntimeError(
                "ControlBand.step() called before reset_episode(). "
                "Scheduler must call reset_episode() after env.reset()."
            )

        # Translate observation
        obs_view = self._build_brain_obs(state.obs)

        # Delegate to brain
        (tau1, tau2), new_state = self._brain.step(obs_view, self._brain_state)
        self._brain_state = new_state

        # Write proposed action and brain name (v0.5)
        state.action_proposed = (tau1, tau2)
        state.brain_name = self._brain_name
