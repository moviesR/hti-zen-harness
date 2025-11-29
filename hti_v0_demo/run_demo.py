"""Main entry point for HTI v0.1 demo

Run with: python -m hti_v0_demo.run_demo
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hti_v0_demo.scheduler import run_episode


def main():
    """Run the HTI v0.1 demonstration."""
    print("=" * 60)
    print("HTI v0.1 - Minimal Demo Harness")
    print("=" * 60)
    print()

    # Run episode
    summary = run_episode(verbose=False)

    # Print final summary
    print(f"\n{'='*60}")
    print("Final Summary")
    print(f"{'='*60}")
    print(f"Ticks executed: {summary['ticks']}")
    print(f"Simulated time: {summary['simulated_time']:.2f}s")
    print(f"Shield interventions: {summary['interventions']}")
    print(f"Success: {'✓' if summary['success'] else '✗'}")
    print(f"Final distance to target: {summary['final_distance']:.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
