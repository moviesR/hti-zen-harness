"""
Reflex Band - Fast safety sensing (100 Hz)

Responsibilities:
- Detect proximity to joint limits
- Detect excessive joint velocities
- Flag potential safety issues

Reads: state.obs
Writes: state.reflex_flags
"""

from __future__ import annotations

from hti_arm_demo.shared_state import ArmSharedState, ArmReflexFlags
from hti_arm_demo.env import THETA_MIN, THETA_MAX, OMEGA_MAX


# Safety margins
JOINT_LIMIT_MARGIN = 0.3  # radians - warn when this close to limits
VELOCITY_FAST_FACTOR = 0.7  # fraction of OMEGA_MAX considered "too fast"


class ReflexBand:
    """
    Fast safety sensing layer.

    Runs at 100 Hz (every tick).
    """

    def step(self, state: ArmSharedState) -> None:
        """
        Detect safety-relevant conditions.

        Reads: state.obs
        Writes: state.reflex_flags
        """
        obs = state.obs

        # Extract joint state
        theta1 = obs["theta1"]
        theta2 = obs["theta2"]
        omega1 = obs["omega1"]
        omega2 = obs["omega2"]

        # Compute distance to nearest joint limits
        d1_min = abs(theta1 - THETA_MIN)
        d1_max = abs(THETA_MAX - theta1)
        d2_min = abs(theta2 - THETA_MIN)
        d2_max = abs(THETA_MAX - theta2)

        d1 = min(d1_min, d1_max)
        d2 = min(d2_min, d2_max)

        # Check proximity to limits
        joint1_near = d1 <= JOINT_LIMIT_MARGIN
        joint2_near = d2 <= JOINT_LIMIT_MARGIN

        # Check velocity thresholds
        joints_too_fast = (
            abs(omega1) >= VELOCITY_FAST_FACTOR * OMEGA_MAX
            or abs(omega2) >= VELOCITY_FAST_FACTOR * OMEGA_MAX
        )

        # Create flags (no obstacles in v0.4)
        flags = ArmReflexFlags(
            joint1_near_limit=joint1_near,
            joint2_near_limit=joint2_near,
            joint1_distance_to_limit=d1,
            joint2_distance_to_limit=d2,
            joints_too_fast=joints_too_fast,
            near_obstacle=False,  # stubbed for v0.4
            obstacle_distance=None,
        )
        state.reflex_flags = flags
