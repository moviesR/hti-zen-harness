"""
Brain policy protocol for 2-DOF arm control.

Defines the interface that all arm brains must implement.
"""

from __future__ import annotations

from typing import Protocol, Mapping, Any, Tuple


class ArmBrainPolicy(Protocol):
    """
    Protocol for pluggable arm control policies.

    Brains compute joint torques based on observations.
    Uses structural typing (duck typing) for flexibility.
    """

    def step(
        self,
        obs: Mapping[str, float],
        brain_state: dict[str, Any] | None = None,
    ) -> Tuple[Tuple[float, float], dict[str, Any]]:
        """
        Compute joint torques from observation.

        Args:
            obs: Read-only observation dict containing:
                - theta1, theta2: current joint angles
                - omega1, omega2: current joint velocities
                - x_ee, y_ee: end-effector position
                - x_goal, y_goal: current waypoint goal
                - stage_index: current task stage
            brain_state: Optional mutable state dict for stateful brains

        Returns:
            ((tau1, tau2), new_brain_state): Joint torques and updated state
        """
        ...
