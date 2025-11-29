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
    """Run the HTI v0.1 demonstration."""
    parser = argparse.ArgumentParser(
        description="HTI v0.1 - Hierarchical Temporal Intelligence Demo"
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=None,
        help="Control gain (default: run both 0.3 and 1.0 for comparison)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-tick information"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HTI v0.1 - Minimal Demo Harness")
    print("=" * 60)
    print()

    if args.gain is not None:
        # Single run with custom gain
        print(f"Running single scenario with gain={args.gain}")
        summary = run_episode(verbose=args.verbose, control_gain=args.gain)
        print_summary("Custom Scenario", summary, args.gain)
    else:
        # Educational comparison: conservative vs aggressive
        print("Running comparative demonstration:")
        print("  1. Conservative control (gain=0.3)")
        print("  2. Aggressive control (gain=1.0)")
        print("\nThis shows how the SafetyShield responds to different control policies.")
        print()

        # Conservative run
        print("\n" + ">" * 60)
        print("SCENARIO 1: Conservative Control")
        print(">" * 60)
        summary_conservative = run_episode(verbose=args.verbose, control_gain=0.3)
        print_summary("Conservative Control", summary_conservative, 0.3)

        # Aggressive run
        print("\n" + ">" * 60)
        print("SCENARIO 2: Aggressive Control")
        print(">" * 60)
        summary_aggressive = run_episode(verbose=args.verbose, control_gain=1.0)
        print_summary("Aggressive Control", summary_aggressive, 1.0)

        # Comparison
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        delta_interventions = summary_aggressive['interventions'] - summary_conservative['interventions']
        print(f"Shield interventions: {summary_conservative['interventions']} → {summary_aggressive['interventions']} (+{delta_interventions})")
        print(f"\nThe aggressive controller triggers {delta_interventions} additional")
        print(f"Shield interventions, demonstrating the Shield's role in")
        print(f"maintaining safety despite different control policies.")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
