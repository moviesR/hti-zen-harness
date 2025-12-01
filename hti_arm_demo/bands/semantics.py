"""
Semantics Band - High-level task planning (10 Hz)

Responsibilities:
- Track multi-stage waypoint task progress
- Detect waypoint completion
- Provide task-space goals to lower bands

Reads: state.obs
Writes: state.semantics_advice
"""

from __future__ import annotations

import math

from hti_arm_demo.shared_state import ArmSharedState, ArmSemanticsAdvice
from hti_arm_demo.env import WORKSPACE_TOL


class SemanticsBand:
    """
    High-level task band for waypoint A → B → C navigation.

    Runs at 10 Hz (every 10 ticks).
    """

    def step(self, state: ArmSharedState) -> None:
        """
        Update task-level advice based on current state.

        Checks if end-effector has reached current waypoint and
        updates advice accordingly.
        """
        obs = state.obs

        # Extract current positions
        x_ee = obs["x_ee"]
        y_ee = obs["y_ee"]
        x_goal = obs["x_goal"]
        y_goal = obs["y_goal"]
        stage_index = int(obs["stage_index"])

        # Compute distance to current goal
        dx = x_goal - x_ee
        dy = y_goal - y_ee
        dist = math.sqrt(dx * dx + dy * dy)

        # Check if waypoint reached
        stage_complete = dist <= WORKSPACE_TOL

        # Write semantics advice
        advice = ArmSemanticsAdvice(
            stage_index=stage_index,
            x_goal=x_goal,
            y_goal=y_goal,
            stage_complete=stage_complete,
        )
        state.semantics_advice = advice
