"""
Aggressive P controller brain for testing safety interventions.

Uses higher gain than the baseline controller to trigger more
Shield interventions and demonstrate safety system effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any, Tuple

from .base import ArmBrainPolicy
from .arm_p_controller import inverse_kinematics_2dof


@dataclass
class ArmAggressiveControllerBrain(ArmBrainPolicy):
    """
    High-gain P controller to stress-test safety system.

    Same structure as ArmPControllerBrain but with:
    - Higher gain (more aggressive control)
    - This triggers more Shield interventions
    """

    gain: float = 12.0  # 2.4x higher than baseline
    L1: float = 0.6  # must match env
    L2: float = 0.4

    def step(
        self,
        obs: Mapping[str, float],
        brain_state: dict[str, Any] | None = None,
    ) -> Tuple[Tuple[float, float], dict[str, Any]]:
        """Compute joint torques via IK + aggressive P control."""
        if brain_state is None:
            brain_state = {}

        # Read current state
        theta1 = obs["theta1"]
        theta2 = obs["theta2"]

        # Read workspace goal
        x_goal = obs["x_goal"]
        y_goal = obs["y_goal"]

        # Inverse kinematics
        theta1_target, theta2_target = inverse_kinematics_2dof(
            x_goal, y_goal, self.L1, self.L2
        )

        # Aggressive P control
        tau1 = self.gain * (theta1_target - theta1)
        tau2 = self.gain * (theta2_target - theta2)

        return ((tau1, tau2), brain_state)
