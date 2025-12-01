"""
2-DOF Planar Arm Environment for HTI v0.4

Simple toy physics simulation with:
- Unit inertia dynamics (α = τ - damping * ω)
- Joint angle and velocity limits
- Multi-stage workspace waypoint reaching task
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple, Dict, Any


# Physical constants
L1 = 0.6  # link 1 length (meters)
L2 = 0.4  # link 2 length (meters)
DT = 0.01  # 100 Hz timestep

# Plant damping - FIXED PARAMETER
# NOTE: This models realistic joint damping in the physical plant.
# HTI's design principle: tune CONTROLLERS for this plant, not vice versa.
# When plugging in different brains (PD, RL, VLA), this stays constant.
DAMPING_COEFF = 0.1  # viscous damping coefficient (fixed plant property)

# Joint limits
THETA_MIN = -math.pi
THETA_MAX = math.pi
OMEGA_MAX = 4.0  # rad/s (symmetric)

# Torque limits
TAU_MAX = 5.0  # max torque magnitude per joint

# Task parameters
WORKSPACE_TOL = 0.03  # distance tolerance for waypoint reach (meters)
MAX_STEPS = 2000  # max ticks per episode

# Workspace waypoints (X, Y coordinates in meters)
WAYPOINTS = [
    (0.7, 0.0),   # A - right
    (0.4, 0.3),   # B - up-right
    (0.3, -0.2),  # C - down-right
]


@dataclass
class ArmState:
    """State of the 2-DOF planar arm."""
    theta1: float  # joint 1 angle [rad]
    theta2: float  # joint 2 angle [rad]
    omega1: float  # joint 1 angular velocity [rad/s]
    omega2: float  # joint 2 angular velocity [rad/s]


def forward_kinematics(theta1: float, theta2: float) -> Tuple[float, float]:
    """
    Compute end-effector position from joint angles.

    Args:
        theta1: Shoulder joint angle (radians)
        theta2: Elbow joint angle (radians)

    Returns:
        (x, y): End-effector position in workspace (meters)
    """
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    y = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)
    return x, y


def step_dynamics(state: ArmState, tau1: float, tau2: float) -> ArmState:
    """
    Integrate arm dynamics for one timestep.

    Uses simple unit-inertia model with velocity damping:
        α = τ - damping * ω

    Args:
        state: Current arm state
        tau1, tau2: Applied joint torques

    Returns:
        New arm state after DT seconds
    """
    # Clamp input torques to limits
    tau1 = max(-TAU_MAX, min(TAU_MAX, tau1))
    tau2 = max(-TAU_MAX, min(TAU_MAX, tau2))

    # Unit inertia: angular acceleration = torque - damping
    alpha1 = tau1 - DAMPING_COEFF * state.omega1
    alpha2 = tau2 - DAMPING_COEFF * state.omega2

    # Integrate velocities
    omega1_next = state.omega1 + DT * alpha1
    omega2_next = state.omega2 + DT * alpha2

    # Clamp angular velocities
    omega1_next = max(-OMEGA_MAX, min(OMEGA_MAX, omega1_next))
    omega2_next = max(-OMEGA_MAX, min(OMEGA_MAX, omega2_next))

    # Integrate positions
    theta1_next = state.theta1 + DT * omega1_next
    theta2_next = state.theta2 + DT * omega2_next

    # Clamp joint angles to limits
    theta1_next = max(THETA_MIN, min(THETA_MAX, theta1_next))
    theta2_next = max(THETA_MIN, min(THETA_MAX, theta2_next))

    return ArmState(
        theta1=theta1_next,
        theta2=theta2_next,
        omega1=omega1_next,
        omega2=omega2_next,
    )


class ToyArmEnv:
    """
    2-DOF planar arm environment with multi-stage waypoint reaching task.

    The arm starts at a default configuration and must sequentially reach
    waypoints A, B, C in workspace coordinates.
    """

    def __init__(self) -> None:
        self.state: ArmState | None = None
        self.current_stage: int = 0  # index into WAYPOINTS
        self.step_count: int = 0

    def reset(self) -> Dict[str, float]:
        """
        Reset environment to initial configuration.

        Returns:
            Observation dict with current state and goal
        """
        # Start with arm somewhat extended
        self.state = ArmState(
            theta1=0.0,
            theta2=0.0,
            omega1=0.0,
            omega2=0.0
        )
        self.current_stage = 0
        self.step_count = 0
        return self._build_obs()

    def _build_obs(self) -> Dict[str, float]:
        """Build observation dictionary from current state."""
        assert self.state is not None, "Environment not initialized"

        # Compute end-effector position
        x_ee, y_ee = forward_kinematics(self.state.theta1, self.state.theta2)

        # Get current goal
        x_goal, y_goal = WAYPOINTS[self.current_stage]

        return {
            "theta1": self.state.theta1,
            "theta2": self.state.theta2,
            "omega1": self.state.omega1,
            "omega2": self.state.omega2,
            "x_ee": x_ee,
            "y_ee": y_ee,
            "x_goal": x_goal,
            "y_goal": y_goal,
            "stage_index": float(self.current_stage),
        }

    def step(
        self, tau1: float, tau2: float
    ) -> Tuple[Dict[str, float], bool, Dict[str, Any]]:
        """
        Apply torques and advance simulation by one timestep.

        Args:
            tau1, tau2: Joint torques (after SafetyShield)

        Returns:
            obs: Observation dict
            done: True if episode complete
            info: Additional information dict
        """
        assert self.state is not None, "Environment not initialized"

        # Integrate dynamics
        self.state = step_dynamics(self.state, tau1, tau2)
        self.step_count += 1

        # Check waypoint reach
        x_ee, y_ee = forward_kinematics(self.state.theta1, self.state.theta2)
        x_goal, y_goal = WAYPOINTS[self.current_stage]

        dx = x_goal - x_ee
        dy = y_goal - y_ee
        dist = math.sqrt(dx * dx + dy * dy)

        info: Dict[str, Any] = {"stage_advanced": False}

        # Check if reached current waypoint
        if dist <= WORKSPACE_TOL:
            if self.current_stage < len(WAYPOINTS) - 1:
                # Advance to next stage
                self.current_stage += 1
                info["stage_advanced"] = True
            else:
                # Final goal reached - success!
                done = True
                obs = self._build_obs()
                info["reason"] = "all_waypoints_reached"
                return obs, done, info

        # Check max steps timeout
        done = self.step_count >= MAX_STEPS
        if done:
            info["reason"] = "max_steps"

        obs = self._build_obs()
        return obs, done, info
