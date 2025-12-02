"""
Tests for empirically-optimized PD controller damping.

These tests validate Phase 1 damping validation experiment findings:
- Empirical optimum: Kd=3.50 (ζ≈0.636) → ~302 ticks (1.51x speedup)
- Original prediction (ζ=1.0) was incorrect for this task
- Under-damping (ζ≈0.636) outperforms critical damping (ζ=1.0)
"""

import unittest
from hti_arm_demo.env import ToyArmEnv
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger
from hti_arm_demo.scheduler import run_episode
from hti_arm_demo.brains import create_arm_brain


class TestOptimalDamping(unittest.TestCase):
    """Tests for empirically-optimized damping validation."""

    def test_optimal_brain_faster_than_nominal(self):
        """
        Empirically-optimized PD (Kd=3.5) should be faster than nominal (Kd=2.0).

        Grid search found:
        - Nominal: Kd=2.0 → 455 ticks
        - Optimal: Kd=3.5 → 302 ticks
        - Speedup: 1.51x

        Test enforces: optimal < nominal (any speedup validates improvement)
        """
        NUM_RUNS = 5

        # Run nominal PD
        nominal_ticks = []
        for _ in range(NUM_RUNS):
            env = ToyArmEnv()
            brain = create_arm_brain("pd")  # Kd=2.0
            semantics = SemanticsBand()
            control = ControlBand(brain)
            reflex = ReflexBand()
            shield = SafetyShield()
            logger = EventLogger(verbose=False)

            stats = run_episode(env, semantics, control, reflex, shield, logger, max_ticks=1000)
            nominal_ticks.append(stats.ticks)

        # Run optimal PD
        optimal_ticks = []
        for _ in range(NUM_RUNS):
            env = ToyArmEnv()
            brain = create_arm_brain("optimal")  # Kd=3.5
            semantics = SemanticsBand()
            control = ControlBand(brain)
            reflex = ReflexBand()
            shield = SafetyShield()
            logger = EventLogger(verbose=False)

            stats = run_episode(env, semantics, control, reflex, shield, logger, max_ticks=1000)
            optimal_ticks.append(stats.ticks)

        avg_nominal = sum(nominal_ticks) / len(nominal_ticks)
        avg_optimal = sum(optimal_ticks) / len(optimal_ticks)

        # Assert optimal is faster
        self.assertLess(
            avg_optimal,
            avg_nominal,
            f"Optimal PD should be faster than nominal: {avg_optimal:.0f} vs {avg_nominal:.0f} ticks"
        )

        # Optional: report speedup if test passes
        if avg_optimal < avg_nominal:
            speedup = avg_nominal / avg_optimal
            print(f"\n  Optimal PD speedup: {speedup:.2f}x ({avg_nominal:.0f} → {avg_optimal:.0f} ticks)")

    def test_optimal_brain_succeeds(self):
        """
        Empirically-optimized PD should complete all waypoints successfully.

        Validates that speedup doesn't sacrifice task completion.
        """
        env = ToyArmEnv()
        brain = create_arm_brain("optimal")
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        logger = EventLogger(verbose=False)

        stats = run_episode(env, semantics, control, reflex, shield, logger, max_ticks=1000)

        self.assertTrue(
            stats.all_waypoints_reached,
            "Optimal PD should complete all waypoints"
        )

    def test_optimal_parameters(self):
        """
        Verify optimal brain has correct empirically-tuned parameters.

        Based on grid search results:
        - Kp = 8.0 (same as nominal)
        - Kd = 3.5 (empirical optimum, ζ≈0.636)
        """
        brain = create_arm_brain("optimal")

        self.assertEqual(brain.Kp, 8.0, "Optimal Kp should be 8.0")
        self.assertAlmostEqual(brain.Kd, 3.5, places=2, msg="Optimal Kd should be 3.5")

        # Calculate damping ratio: ζ = (Kd + b_plant) / (2 * sqrt(Kp))
        # where b_plant ≈ 0.1 for ToyArmEnv
        zeta = (brain.Kd + 0.1) / (2 * (brain.Kp ** 0.5))
        self.assertAlmostEqual(zeta, 0.636, places=2, msg="Optimal damping ratio should be ~0.636")


if __name__ == "__main__":
    unittest.main()
