"""Simple 1D toy environment for HTI v0.1

A minimal environment to demonstrate the harness pattern, not control performance.
"""


class ToyEnv:
    """1D position control environment.

    State:
        x: Position on [0.0, 1.0]
        x_target: Goal position

    Action:
        u: Delta-position per step (already safety-checked by Shield)

    Dynamics:
        x_next = clip(x + u, 0.0, 1.0)
    """

    def __init__(self, dt: float = 0.01, success_threshold: float = 0.02):
        """Initialize the environment.

        Args:
            dt: Time step in seconds (100 Hz = 0.01s)
            success_threshold: Distance to target considered "success"
        """
        self.dt = dt
        self.success_threshold = success_threshold
        self.x = 0.0
        self.x_target = 0.0
        self.step_count = 0
        self.max_steps = 2000

    def reset(self, x0: float = 0.1, x_target: float = 0.8) -> dict[str, float]:
        """Reset environment to initial state.

        Args:
            x0: Initial position
            x_target: Goal position

        Returns:
            Initial observation dict with keys 'x' and 'x_target'

        Raises:
            ValueError: If x0 or x_target are outside valid range [0.0, 1.0]
        """
        if not (0.0 <= x0 <= 1.0):
            raise ValueError(f"x0 ({x0}) must be within [0.0, 1.0]")
        if not (0.0 <= x_target <= 1.0):
            raise ValueError(f"x_target ({x_target}) must be within [0.0, 1.0]")

        self.x = x0
        self.x_target = x_target
        self.step_count = 0
        return {"x": self.x, "x_target": self.x_target}

    def step(self, u: float) -> tuple[dict[str, float], float, bool, dict]:
        """Execute one environment step.

        Args:
            u: Action (delta-position), already bounded by Shield

        Returns:
            obs: {"x": float, "x_target": float}
            reward: Negative distance to target
            done: True if goal reached or max steps exceeded
            info: Additional information dict
        """
        # Apply action (already bounded by Shield)
        self.x = max(0.0, min(1.0, self.x + u))
        self.step_count += 1

        # Observation
        obs = {"x": self.x, "x_target": self.x_target}

        # Reward (negative distance)
        reward = -abs(self.x - self.x_target)

        # Done condition
        distance = abs(self.x - self.x_target)
        done = (distance < self.success_threshold) or (self.step_count >= self.max_steps)

        # Info
        info = {
            "step_count": self.step_count,
            "distance": distance,
            "success": distance < self.success_threshold
        }

        return obs, reward, done, info
