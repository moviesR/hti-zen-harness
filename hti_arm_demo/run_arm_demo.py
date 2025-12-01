"""
CLI entry point for HTI v0.4 - 2-DOF Planar Arm Demo

Usage:
    python -m hti_arm_demo.run_arm_demo --brain pd
    python -m hti_arm_demo.run_arm_demo --brain pd_aggressive
    python -m hti_arm_demo.run_arm_demo --brain p  # legacy P-only controller

Example with custom gains:
    python -m hti_arm_demo.run_arm_demo --brain pd --Kp 10.0 --Kd 3.0
"""

from __future__ import annotations

import argparse

from hti_arm_demo.env import ToyArmEnv
from hti_arm_demo.brains.registry import create_arm_brain, list_arm_brains
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger
from hti_arm_demo.scheduler import run_episode


def main():
    """Run HTI arm demo with specified brain."""
    parser = argparse.ArgumentParser(
        description="HTI v0.4 - 2-DOF Planar Arm Demo"
    )

    parser.add_argument(
        "--brain",
        type=str,
        default="pd",
        choices=list_arm_brains(),
        help="Brain policy to use (default: pd)"
    )

    parser.add_argument(
        "--gain",
        type=float,
        default=None,
        help="Override P controller gain (for 'p' or 'aggressive' brains)"
    )

    parser.add_argument(
        "--Kp",
        type=float,
        default=None,
        help="Override PD proportional gain (for 'pd' brains)"
    )

    parser.add_argument(
        "--Kd",
        type=float,
        default=None,
        help="Override PD derivative gain (for 'pd' brains)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tick progress and events"
    )

    parser.add_argument(
        "--max-ticks",
        type=int,
        default=2000,
        help="Maximum ticks per episode"
    )

    args = parser.parse_args()

    # Create brain with optional gain overrides
    brain_config = {}
    if args.gain is not None:
        brain_config["gain"] = args.gain
    if args.Kp is not None:
        brain_config["Kp"] = args.Kp
    if args.Kd is not None:
        brain_config["Kd"] = args.Kd

    brain = create_arm_brain(args.brain, brain_config)

    # Create environment and components
    env = ToyArmEnv()
    semantics = SemanticsBand()
    control = ControlBand(brain, brain_name=args.brain)  # v0.5: pass brain name
    reflex = ReflexBand()
    shield = SafetyShield()
    event_logger = EventLogger(verbose=args.verbose)

    # Run episode
    print(f"\n=== HTI v0.4 - 2-DOF Arm Demo ===")
    print(f"Brain: {args.brain}")
    if args.gain is not None:
        print(f"Gain: {args.gain}")
    print()

    stats = run_episode(
        env=env,
        semantics=semantics,
        control=control,
        reflex=reflex,
        shield=shield,
        event_logger=event_logger,
        max_ticks=args.max_ticks,
        verbose=args.verbose,
    )

    # Print summary
    print("\n=== Episode Summary ===")
    print(f"Ticks: {stats.ticks}")
    print(f"Shield interventions: {stats.shield_interventions}")
    print(f"All waypoints reached: {stats.all_waypoints_reached}")
    print(f"Reason: {stats.reason}")
    print(f"\nEvent log written to: event_log.jsonl")
    print()

    if stats.all_waypoints_reached:
        print("✓ SUCCESS: Arm reached all waypoints!")
    else:
        print("✗ TIMEOUT: Max ticks reached before completing task")


if __name__ == "__main__":
    main()
