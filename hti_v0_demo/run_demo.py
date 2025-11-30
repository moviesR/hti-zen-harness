"""Main entry point for HTI v0.1 demo

Run with:
  python -m hti_v0_demo.run_demo              # Compare conservative vs aggressive
  python -m hti_v0_demo.run_demo --gain 0.5   # Custom gain value
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hti_v0_demo.scheduler import run_episode
from hti_v0_demo.env import ToyEnv


def print_summary(label: str, summary: dict, gain: float) -> None:
    """Print formatted summary for one scenario.

    Args:
        label: Label for this scenario
        summary: Summary dict from run_episode
        gain: Control gain used
    """
    print(f"\n{'='*60}")
    print(f"{label} (gain={gain})")
    print(f"{'='*60}")
    print(f"Ticks executed: {summary['ticks']}")
    print(f"Simulated time: {summary['simulated_time']:.2f}s")
    print(f"Shield interventions: {summary['interventions']}")
    print(f"Success: {'✓' if summary['success'] else '✗'}")
    print(f"Final distance to target: {summary['final_distance']:.4f}")
    print(f"{'='*60}")


def main():
    """Run the HTI v0.1/v0.2 demonstration."""
    parser = argparse.ArgumentParser(
        description="HTI v0.2 - Hierarchical Temporal Intelligence Demo (Sensor Contradiction)"
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=None,
        help="Control gain (default: 0.3)"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["clean", "sensor_glitch", "both"],
        default="both",
        help="Scenario: clean (v0.1.1), sensor_glitch (v0.2), or both (default)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-tick information"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HTI v0.2 - Sensor Contradiction Demo")
    print("=" * 60)
    print()

    gain = args.gain or 0.3

    if args.scenario in ["clean", "both"]:
        print("\n" + ">" * 60)
        print("SCENARIO 1: Clean Sensors (v0.1.1 behavior)")
        print(">" * 60)
        print("No sensor glitches. Control uses accurate measurements.")
        print()

        env_clean = ToyEnv(enable_glitches=False)
        summary_clean = run_episode(
            env=env_clean,
            verbose=args.verbose,
            control_gain=gain
        )
        print_summary("Clean Sensors", summary_clean, gain)

    if args.scenario in ["sensor_glitch", "both"]:
        print("\n" + ">" * 60)
        print("SCENARIO 2: Sensor Glitch (v0.2 demonstration)")
        print(">" * 60)
        print("Sensor glitch from tick 5-25: x_meas = x_true + 0.3")
        print("Control uses corrupted x_meas, Reflex detects mismatch, Shield stops.")
        print()

        env_glitch = ToyEnv(
            enable_glitches=True,
            glitch_start_tick=5,
            glitch_end_tick=25,
            glitch_magnitude=0.3
        )
        summary_glitch = run_episode(
            env=env_glitch,
            verbose=args.verbose,
            control_gain=gain
        )
        print_summary("Sensor Glitch", summary_glitch, gain)

    if args.scenario == "both":
        print(f"\n{'='*60}")
        print("COMPARISON: Clean vs Sensor Glitch")
        print(f"{'='*60}")
        print(f"Clean interventions:  {summary_clean['interventions']}")
        print(f"Glitch interventions: {summary_glitch['interventions']}")
        delta = summary_glitch['interventions'] - summary_clean['interventions']
        print(f"Difference: +{delta} interventions during sensor glitch")
        print(f"\nThe sensor glitch scenario demonstrates HTI's ability to")
        print(f"detect and respond to sensor contradictions (x_true vs x_meas).")
        print(f"Shield automatically stops on mismatch, then recovers when glitch clears.")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
