"""Scheduler - main control loop for HTI v0.1

Orchestrates time-banded execution with strict ordering.
"""

import time
from typing import Optional

from hti_v0_demo.env import ToyEnv
from hti_v0_demo.shared_state import SharedState
from hti_v0_demo.bands import SemanticsBand, ControlBand, ReflexBand
from hti_v0_demo.shield import SafetyShield
from hti_v0_demo.event_log import EventLogger


class TimingStats:
    """Simple timing statistics collector for band execution times."""

    def __init__(self):
        """Initialize timing statistics."""
        self.times: dict[str, list[float]] = {}

    def record(self, band: str, duration: float) -> None:
        """Record execution time for a band.

        Args:
            band: Name of the band
            duration: Execution time in seconds
        """
        if band not in self.times:
            self.times[band] = []
        self.times[band].append(duration)

    def report(self) -> None:
        """Print timing statistics summary."""
        if not self.times:
            return

        print("\n=== Timing Stats ===")
        for band in ["semantics", "control", "reflex", "shield"]:
            if band in self.times:
                times = self.times[band]
                mean_ms = (sum(times) / len(times)) * 1000
                max_ms = max(times) * 1000
                print(f"{band:10s}: mean={mean_ms:.2f}ms, max={max_ms:.2f}ms")


def run_episode(
    env: Optional[ToyEnv] = None,
    max_ticks: int = 2000,
    verbose: bool = False
) -> dict:
    """Run one episode of the HTI demo.

    Args:
        env: Environment to use (creates default if None)
        max_ticks: Maximum ticks to run
        verbose: If True, print per-tick info

    Returns:
        Summary dict with episode statistics
    """
    # Create environment if not provided
    if env is None:
        env = ToyEnv()

    # Initialize components
    state = SharedState()
    bands = {
        "semantics": SemanticsBand(),
        "control": ControlBand(),
        "reflex": ReflexBand(),
    }
    shield = SafetyShield()
    logger = EventLogger()
    timing_stats = TimingStats()

    # Reset environment
    obs = env.reset()
    state.obs = obs

    print(f"Running HTI v0.1 Demo...")
    print(f"Initial state: x={obs['x']:.3f}, target={obs['x_target']:.3f}")

    # Main loop
    for tick in range(max_ticks):
        state.tick = tick
        state.t = tick * 0.01  # 100 Hz base rate

        # Semantics band (10 Hz)
        if tick % 10 == 0:
            t0 = time.perf_counter()
            bands["semantics"].step(state)
            timing_stats.record("semantics", time.perf_counter() - t0)

        # Control band (50 Hz)
        if tick % 2 == 0:
            t0 = time.perf_counter()
            bands["control"].step(state)
            timing_stats.record("control", time.perf_counter() - t0)

        # Reflex band (100 Hz)
        t0 = time.perf_counter()
        bands["reflex"].step(state)
        timing_stats.record("reflex", time.perf_counter() - t0)

        # Safety Shield (always last before env.step)
        t0 = time.perf_counter()
        safe_u, event = shield.apply(state)
        timing_stats.record("shield", time.perf_counter() - t0)

        if event is not None:
            logger.log(event)
            if verbose:
                print(f"[{tick:4d}] Shield intervention: {event.action_proposed:.4f} → {event.action_final:.4f}")

        # Environment step
        obs, reward, done, info = env.step(safe_u)
        state.obs = obs

        if verbose and tick % 100 == 0:
            print(f"[{tick:4d}] x={obs['x']:.3f}, target={obs['x_target']:.3f}, action={safe_u:.4f}")

        if done:
            success = info.get("success", False)
            print(f"Episode complete after {tick+1} ticks ({state.t:.2f}s simulated)")
            if success:
                print(f"✓ Target reached! Final distance: {info['distance']:.4f}")
            else:
                print(f"✗ Max steps reached. Final distance: {info['distance']:.4f}")
            break

    # Print summaries
    logger.dump()
    timing_stats.report()

    # Return summary
    return {
        "ticks": state.tick + 1,
        "simulated_time": state.t,
        "interventions": len(logger.events),
        "success": info.get("success", False),
        "final_distance": info.get("distance", 0.0)
    }
