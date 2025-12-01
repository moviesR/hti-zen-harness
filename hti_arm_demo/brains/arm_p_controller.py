"""
P controller brain with real inverse kinematics for 2-DOF planar arm.

This is the reference brain implementation that demonstrates:
- Semantics provides workspace goals (x_goal, y_goal)
- Control solves IK to find desired joint angles
- Control applies P control in joint space
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Any, Tuple

from .base import ArmBrainPolicy


def inverse_kinematics_2dof(
    x_goal: float,
    y_goal: float,
    L1: float,
    L2: float
) -> Tuple[float, float]:
    """
    Closed-form inverse kinematics for 2-link planar arm.

    Uses standard geometric solution:
    - Law of cosines for elbow angle (theta2)
    - Geometry for shoulder angle (theta1)

    Args:
        x_goal, y_goal: Desired end-effector position in workspace
        L1, L2: Link lengths

    Returns:
        (theta1, theta2): Joint angles to reach goal

    Handles edge cases:
    - Unreachable targets: scaled to workspace boundary
    - Too-close targets: pushed to minimum reach
    - Singularities: numerical clamping
    """
    # Distance from origin to goal
    r_sq = x_goal**2 + y_goal**2
    r = math.sqrt(r_sq)

    # Workspace reachability limits
    max_reach = L1 + L2
    min_reach = abs(L1 - L2)

    # Handle unreachable targets
    if r > max_reach:
        # Scale goal to workspace boundary
        scale = max_reach / r
        x_goal *= scale
        y_goal *= scale
        r = max_reach
        r_sq = r**2
    elif r < min_reach:
        # Push outward to minimum reach
        scale = min_reach / r if r > 1e-6 else 1.0
        x_goal *= scale
        y_goal *= scale
        r = min_reach
        r_sq = r**2

    # Elbow angle via law of cosines
    # cos(theta2) = (r^2 - L1^2 - L2^2) / (2 * L1 * L2)
    cos_theta2 = (r_sq - L1**2 - L2**2) / (2 * L1 * L2)
    cos_theta2 = max(-1.0, min(1.0, cos_theta2))  # numerical safety
    theta2 = math.acos(cos_theta2)

    # Shoulder angle via geometry
    alpha = math.atan2(y_goal, x_goal)  # angle to goal
    beta = math.atan2(
        L2 * math.sin(theta2),
        L1 + L2 * math.cos(theta2)
    )  # angle contribution from elbow
    theta1 = alpha - beta

    return (theta1, theta2)


@dataclass
class ArmPControllerBrain(ArmBrainPolicy):
    """
    Joint-space P controller with inverse kinematics.

    Control flow:
    1. Read workspace goal from Semantics (x_goal, y_goal)
    2. Solve IK to find desired joint angles
    3. Apply P control: tau = gain * (theta_desired - theta_actual)

    This creates meaningful hierarchy:
    - Semantics defines WHAT (task-space waypoints)
    - Control solves HOW (IK + joint control)
    - Reflex/Shield enforce SAFETY (limits)
    """

    gain: float = 5.0
    L1: float = 0.6  # must match env
    L2: float = 0.4

    def step(
        self,
        obs: Mapping[str, float],
        brain_state: dict[str, Any] | None = None,
    ) -> Tuple[Tuple[float, float], dict[str, Any]]:
        """Compute joint torques via IK + P control."""
        if brain_state is None:
            brain_state = {}

        # Read current joint state
        theta1 = obs["theta1"]
        theta2 = obs["theta2"]

        # Read workspace goal from Semantics
        x_goal = obs["x_goal"]
        y_goal = obs["y_goal"]

        # Inverse kinematics: workspace → joints
        theta1_target, theta2_target = inverse_kinematics_2dof(
            x_goal, y_goal, self.L1, self.L2
        )

        # P control in joint space
        tau1 = self.gain * (theta1_target - theta1)
        tau2 = self.gain * (theta2_target - theta2)

        return ((tau1, tau2), brain_state)
