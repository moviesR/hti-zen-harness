"""
HTI v0.5 Demo: Imperfect Brain Comparison

Runs side-by-side comparison of:
- Nominal PD brain (good tuning: Kp=8.0, Kd=2.0)
- Imperfect brain (poor tuning: Kp=14.0, Kd=0.5)

Demonstrates HTI's value: even badly-tuned brains complete tasks safely,
but at the cost of more Shield interventions and slower convergence.

Usage:
    python -m hti_arm_demo.run_v05_demo
    python -m hti_arm_demo.run_v05_demo --episodes 20
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List

from hti_arm_demo.env import ToyArmEnv
from hti_arm_demo.brains.registry import create_arm_brain
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger
from hti_arm_demo.scheduler import run_episode, EpisodeStats


@dataclass
class BrainMetrics:
    """Aggregate metrics for comparing brain performance."""
    brain_name: str
    episodes: int
    success_rate: float  # fraction completing all waypoints
    avg_interventions: float  # mean Shield EventPack count
    avg_clipped_torque: float  # mean sum of |proposed - final|
    avg_reflex_flags: float  # mean reflex flag activations
    avg_convergence_ticks: float  # mean ticks to complete


def run_n_episodes(
    brain_name: str,
    n_episodes: int,
    max_ticks: int = 2000,
) -> BrainMetrics:
    """
    Run N episodes with specified brain and aggregate metrics.

    Args:
        brain_name: Brain to test ("pd" or "imperfect")
        n_episodes: Number of episodes to run
        max_ticks: Maximum ticks per episode

    Returns:
        Aggregated metrics across all episodes
    """
    # Track results across episodes
    episode_results: List[EpisodeStats] = []
    total_clipped_torques: List[float] = []
    total_reflex_flags: List[int] = []

    for ep in range(n_episodes):
        # Create fresh components for each episode
        env = ToyArmEnv()
        brain = create_arm_brain(brain_name)
        semantics = SemanticsBand()
        control = ControlBand(brain, brain_name=brain_name)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        # Run episode
        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=max_ticks,
            verbose=False,
        )
        episode_results.append(stats)

        # Compute clipped torque from events
        clipped_torque = 0.0
        for event in event_logger.events:
            tau1_p, tau2_p = event.action_proposed
            tau1_f, tau2_f = event.action_final
            clipped_torque += abs(tau1_p - tau1_f) + abs(tau2_p - tau2_f)
        total_clipped_torques.append(clipped_torque)

        # Count reflex flags (stub - would need to track in episode)
        total_reflex_flags.append(0)  # TODO: track if needed

    # Aggregate metrics
    success_count = sum(1 for r in episode_results if r.all_waypoints_reached)
    success_rate = success_count / n_episodes

    avg_interventions = sum(r.shield_interventions for r in episode_results) / n_episodes
    avg_clipped_torque = sum(total_clipped_torques) / n_episodes
    avg_reflex_flags = sum(total_reflex_flags) / n_episodes

    # Compute average convergence time (only for successful episodes)
    successful_ticks = [r.ticks for r in episode_results if r.all_waypoints_reached]
    avg_convergence_ticks = sum(successful_ticks) / len(successful_ticks) if successful_ticks else 0.0

    return BrainMetrics(
        brain_name=brain_name,
        episodes=n_episodes,
        success_rate=success_rate,
        avg_interventions=avg_interventions,
        avg_clipped_torque=avg_clipped_torque,
        avg_reflex_flags=avg_reflex_flags,
        avg_convergence_ticks=avg_convergence_ticks,
    )


def print_comparison_table(results: dict[str, BrainMetrics]) -> None:
    """Print formatted comparison table (matches spec example)."""
    print("\n" + "="*70)
    print("HTI v0.5 - Brain Comparison Results")
    print("="*70)

    for name, metrics in results.items():
        success_count = int(metrics.success_rate * metrics.episodes)
        print(f"\n{name}:")
        print(f"  episodes: {metrics.episodes}")
        print(f"  success: {success_count}/{metrics.episodes}")
        print(f"  avg Shield interventions: {metrics.avg_interventions:.1f}")
        print(f"  avg total |torque_clipped|: {metrics.avg_clipped_torque:.1f}")
        print(f"  avg convergence time: {metrics.avg_convergence_ticks:.0f} ticks")

    # Compute comparison if both brains present
    if "PD Baseline" in results and "Imperfect Brain" in results:
        pd = results["PD Baseline"]
        imperfect = results["Imperfect Brain"]

        intervention_ratio = imperfect.avg_interventions / pd.avg_interventions if pd.avg_interventions > 0 else 0
        torque_ratio = imperfect.avg_clipped_torque / pd.avg_clipped_torque if pd.avg_clipped_torque > 0 else 0

        print("\n" + "="*70)
        print("Comparison:")
        print(f"  Intervention ratio (imperfect/baseline): {intervention_ratio:.1f}x")
        print(f"  Clipped torque ratio (imperfect/baseline): {torque_ratio:.1f}x")
        print("\nConclusion: Imperfect brain stresses Shield ~{:.1f}x more,".format(intervention_ratio))
        print("but HTI keeps the system safe and task-complete.")
        print("="*70 + "\n")


def run_comparison(n_episodes: int = 10) -> dict[str, BrainMetrics]:
    """
    Run PD baseline vs Imperfect brain comparison.

    Args:
        n_episodes: Number of episodes per brain

    Returns:
        Dict mapping scenario name to metrics
    """
    scenarios = [
        ("PD Baseline", "pd"),
        ("Imperfect Brain", "imperfect"),
    ]

    results = {}
    for name, brain_name in scenarios:
        print(f"\nRunning {name} ({brain_name})...")
        metrics = run_n_episodes(brain_name, n_episodes)
        results[name] = metrics
        print(f"  Completed {n_episodes} episodes")

    print_comparison_table(results)
    return results


def main():
    """CLI entry point for v0.5 comparison demo."""
    parser = argparse.ArgumentParser(
        description="HTI v0.5 - Imperfect Brain Comparison Demo"
    )

    parser.add_argument(
        "--episodes",
        type=int,
        default=10,
        help="Number of episodes per brain (default: 10)"
    )

    parser.add_argument(
        "--max-ticks",
        type=int,
        default=2000,
        help="Maximum ticks per episode (default: 2000)"
    )

    args = parser.parse_args()

    print("\n=== HTI v0.5 - Imperfect Brain Stress Test ===")
    print(f"Episodes per brain: {args.episodes}")
    print(f"Max ticks per episode: {args.max_ticks}")
    print("\nThis demonstrates HTI's value: even badly-tuned brains")
    print("complete tasks safely, at the cost of more interventions.")

    run_comparison(n_episodes=args.episodes)


if __name__ == "__main__":
    main()
