"""
HTI Scheduler for 2-DOF arm demo.

Orchestrates time-banded execution:
- Semantics: 10 Hz (every 10 ticks)
- Control: 50 Hz (every 2 ticks)
- Reflex: 100 Hz (every tick)
- Shield: 100 Hz (every tick)

Strict ordering per tick: Semantics → Control → Reflex → Shield → env.step()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from hti_arm_demo.env import ToyArmEnv, DT
from hti_arm_demo.shared_state import ArmSharedState
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger


@dataclass
class EpisodeStats:
    """Statistics from completed episode."""
    ticks: int
    shield_interventions: int
    all_waypoints_reached: bool
    reason: str  # "all_waypoints_reached" or "max_steps"


def run_episode(
    env: ToyArmEnv,
    semantics: SemanticsBand,
    control: ControlBand,
    reflex: ReflexBand,
    shield: SafetyShield,
    event_logger: EventLogger,
    max_ticks: int = 2000,
    verbose: bool = False,
) -> EpisodeStats:
    """
    Run single episode with time-banded execution.

    Args:
        env: Arm environment
        semantics: Semantics band (10 Hz)
        control: Control band (50 Hz)
        reflex: Reflex band (100 Hz)
        shield: Safety shield (100 Hz)
        event_logger: Event logger
        max_ticks: Maximum ticks per episode
        verbose: Print tick progress

    Returns:
        Episode statistics
    """
    # Reset environment
    obs = env.reset()

    # Initialize shared state
    state = ArmSharedState(obs=obs, tick=0, t=0.0)

    # Initialize control band (must be called after env.reset())
    control.reset_episode()

    # Clear event logger
    event_logger.clear()

    # Episode loop
    done = False
    all_waypoints_reached = False
    reason = "max_steps"

    for tick in range(max_ticks):
        # Update time
        state.tick = tick
        state.t = tick * DT

        # Semantics band (10 Hz: every 10 ticks)
        if tick % 10 == 0:
            semantics.step(state)

        # Control band (50 Hz: every 2 ticks)
        if tick % 2 == 0:
            control.step(state)

        # Reflex band (100 Hz: every tick)
        reflex.step(state)

        # Safety Shield (100 Hz: every tick)
        shield.apply(state, event_logger.events)

        # Apply final action to environment
        tau1, tau2 = state.action_final or (0.0, 0.0)
        obs, done, info = env.step(tau1, tau2)

        # Update state with new observation
        state.obs = obs

        # Check termination
        if done:
            if info.get("reason") == "all_waypoints_reached":
                all_waypoints_reached = True
                reason = "all_waypoints_reached"
            break

        if verbose and tick % 100 == 0:
            stage = int(obs["stage_index"])
            interventions = state.shield_interventions
            print(f"Tick {tick}: stage={stage}, interventions={interventions}")

    # Write events to file
    event_logger.flush()

    return EpisodeStats(
        ticks=tick + 1,
        shield_interventions=state.shield_interventions,
        all_waypoints_reached=all_waypoints_reached,
        reason=reason,
    )
