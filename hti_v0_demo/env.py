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

    def __init__(
        self,
        dt: float = 0.01,
        success_threshold: float = 0.02,
        enable_glitches: bool = False,
        glitch_start_tick: int = 50,
        glitch_end_tick: int = 70,
        glitch_magnitude: float = 0.3
    ):
        """Initialize the environment.

        Args:
            dt: Time step in seconds (100 Hz = 0.01s)
            success_threshold: Distance to target considered "success"
            enable_glitches: Enable sensor glitch simulation (v0.2)
            glitch_start_tick: Tick when glitch starts (v0.2)
            glitch_end_tick: Tick when glitch ends (exclusive) (v0.2)
            glitch_magnitude: Magnitude of sensor offset during glitch (v0.2)
        """
        self.dt = dt
        self.success_threshold = success_threshold
        self.x = 0.0
        self.x_target = 0.0
        self.step_count = 0
        self.max_steps = 2000
        # v0.2: Sensor glitch simulation
        self.enable_glitches = enable_glitches
        self.glitch_start_tick = glitch_start_tick
        self.glitch_end_tick = glitch_end_tick
        self.glitch_magnitude = glitch_magnitude
        self.current_tick = 0

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
        self.current_tick = 0  # v0.2: Reset tick counter

        # v0.2: Return x_true and x_meas (initially identical)
        return {
            "x": self.x,          # Backward compatibility
            "x_true": self.x,     # v0.2: Ground truth
            "x_meas": self.x,     # v0.2: Measured (initially accurate)
            "x_target": self.x_target
        }

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
        # Apply action to TRUE state (already bounded by Shield)
        self.x = max(0.0, min(1.0, self.x + u))
        self.step_count += 1
        self.current_tick += 1  # v0.2: Increment tick counter

        # v0.2: Compute measured state with optional glitch
        x_meas = self.x  # Default: measurement matches reality
        if self.enable_glitches:
            if self.glitch_start_tick <= self.current_tick < self.glitch_end_tick:
                # Deterministic glitch: add fixed offset
                x_meas = self.x + self.glitch_magnitude
                # Keep x_meas in bounds for realism
                x_meas = max(0.0, min(1.0, x_meas))

        # Observation (v0.2: includes x_true and x_meas)
        obs = {
            "x": self.x,          # Backward compatibility (uses true state)
            "x_true": self.x,     # v0.2: Ground truth
            "x_meas": x_meas,     # v0.2: Measured (potentially corrupted)
            "x_target": self.x_target
        }

        # Reward based on TRUE state
        reward = -abs(self.x - self.x_target)

        # Done condition based on TRUE state
        distance = abs(self.x - self.x_target)
        done = (distance < self.success_threshold) or (self.step_count >= self.max_steps)

        # Info (v0.2: includes glitch status)
        info = {
            "step_count": self.step_count,
            "distance": distance,
            "success": distance < self.success_threshold,
            "glitch_active": (self.enable_glitches and
                             self.glitch_start_tick <= self.current_tick < self.glitch_end_tick),
            "sensor_mismatch": abs(self.x - x_meas) > 1e-6
        }

        return obs, reward, done, info
