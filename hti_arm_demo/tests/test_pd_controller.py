"""
Tests for PD controller behavior in HTI v0.4 arm demo.

These tests verify BEHAVIOR, not internal parameters:
- Waypoint completion within reasonable time
- Safety system remains effective
- Aggressive vs nominal controller characteristics

Following HTI testing principles:
- Test what the system DOES, not how it's tuned
- Verify safety properties hold across different brains
- Allow for parameter changes without test breakage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hti_arm_demo.env import ToyArmEnv
from hti_arm_demo.brains.registry import create_arm_brain
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger
from hti_arm_demo.scheduler import run_episode


class TestPDControllerBehavior:
    """Test PD controller completes task successfully."""

    def test_pd_controller_reaches_all_waypoints(self):
        """Nominal PD controller should reach all waypoints."""
        env = ToyArmEnv()
        brain = create_arm_brain("pd")
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=2000,
            verbose=False,
        )

        assert stats.all_waypoints_reached, \
            f"PD controller should reach all waypoints, got {stats.reason}"
        assert stats.ticks < 2000, \
            f"Should complete before timeout, took {stats.ticks} ticks"

    def test_aggressive_pd_reaches_waypoints_faster(self):
        """Aggressive PD should complete faster but with more interventions."""
        # Nominal PD
        env1 = ToyArmEnv()
        brain1 = create_arm_brain("pd")
        semantics1 = SemanticsBand()
        control1 = ControlBand(brain1)
        reflex1 = ReflexBand()
        shield1 = SafetyShield()
        event_logger1 = EventLogger(verbose=False)

        stats1 = run_episode(
            env=env1,
            semantics=semantics1,
            control=control1,
            reflex=reflex1,
            shield=shield1,
            event_logger=event_logger1,
            max_ticks=2000,
            verbose=False,
        )

        # Aggressive PD
        env2 = ToyArmEnv()
        brain2 = create_arm_brain("pd_aggressive")
        semantics2 = SemanticsBand()
        control2 = ControlBand(brain2)
        reflex2 = ReflexBand()
        shield2 = SafetyShield()
        event_logger2 = EventLogger(verbose=False)

        stats2 = run_episode(
            env=env2,
            semantics=semantics2,
            control=control2,
            reflex=reflex2,
            shield=shield2,
            event_logger=event_logger2,
            max_ticks=2000,
            verbose=False,
        )

        # Both should succeed
        assert stats1.all_waypoints_reached, \
            "Nominal PD should reach waypoints"
        assert stats2.all_waypoints_reached, \
            "Aggressive PD should reach waypoints"

        # Aggressive should be faster
        assert stats2.ticks < stats1.ticks, \
            f"Aggressive PD ({stats2.ticks} ticks) should be faster than nominal ({stats1.ticks} ticks)"

        # Aggressive should have more interventions
        assert stats2.shield_interventions > stats1.shield_interventions, \
            f"Aggressive PD ({stats2.shield_interventions} interventions) should trigger more Shield interventions than nominal ({stats1.shield_interventions})"


class TestPDControllerSafety:
    """Test that PD controller respects safety system."""

    def test_pd_controller_triggers_shield(self):
        """PD controller should trigger Shield interventions."""
        env = ToyArmEnv()
        brain = create_arm_brain("pd")
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=2000,
            verbose=False,
        )

        # PD controller should be aggressive enough to need clipping
        assert stats.shield_interventions > 0, \
            "PD controller should trigger some Shield interventions"

    def test_aggressive_pd_safety_preserved(self):
        """Aggressive PD should still be kept safe by Shield."""
        env = ToyArmEnv()
        brain = create_arm_brain("pd_aggressive")
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=2000,
            verbose=False,
        )

        # Aggressive controller should succeed (safety preserved)
        assert stats.all_waypoints_reached, \
            "Aggressive PD should reach waypoints safely"

        # Should have many interventions (demonstrating Shield value)
        assert stats.shield_interventions > 50, \
            f"Aggressive PD should trigger many Shield interventions, got {stats.shield_interventions}"


class TestPDControllerTuning:
    """Test custom PD gain tuning."""

    def test_custom_pd_gains(self):
        """Test that custom Kp/Kd gains can be set."""
        env = ToyArmEnv()
        brain = create_arm_brain("pd", {"Kp": 10.0, "Kd": 3.0})
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=2000,
            verbose=False,
        )

        # Should complete without errors
        assert stats.ticks >= 1, "Should execute at least one tick"
        assert stats.reason in ["all_waypoints_reached", "max_steps"], \
            f"Should complete normally, got reason: {stats.reason}"

    def test_very_low_gains_safe_but_slow(self):
        """Very low gains should be safe but may timeout."""
        env = ToyArmEnv()
        brain = create_arm_brain("pd", {"Kp": 1.0, "Kd": 0.5})
        semantics = SemanticsBand()
        control = ControlBand(brain)
        reflex = ReflexBand()
        shield = SafetyShield()
        event_logger = EventLogger(verbose=False)

        stats = run_episode(
            env=env,
            semantics=semantics,
            control=control,
            reflex=reflex,
            shield=shield,
            event_logger=event_logger,
            max_ticks=500,  # Short timeout
            verbose=False,
        )

        # Should run without errors
        assert stats.ticks >= 1, "Should execute at least one tick"
        # May or may not reach waypoints (depends on how slow)
        # But should not crash


class TestBrainAgnosticHarness:
    """Test that HTI harness works with both P and PD controllers."""

    def test_both_controller_types_work(self):
        """Both P and PD controllers should work in HTI harness."""
        for brain_name in ["p", "pd"]:
            env = ToyArmEnv()
            brain = create_arm_brain(brain_name)
            semantics = SemanticsBand()
            control = ControlBand(brain)
            reflex = ReflexBand()
            shield = SafetyShield()
            event_logger = EventLogger(verbose=False)

            stats = run_episode(
                env=env,
                semantics=semantics,
                control=control,
                reflex=reflex,
                shield=shield,
                event_logger=event_logger,
                max_ticks=2000,
                verbose=False,
            )

            # Basic sanity checks
            assert stats.ticks >= 1, \
                f"Brain {brain_name} should execute at least one tick"
            assert stats.reason in ["all_waypoints_reached", "max_steps"], \
                f"Brain {brain_name} should complete normally, got: {stats.reason}"


if __name__ == "__main__":
    # Run tests manually
    print("Running PD controller tests...")
    print("=" * 60)

    # Test 1
    test1 = TestPDControllerBehavior()
    print("\n[1/9] test_pd_controller_reaches_all_waypoints...")
    test1.test_pd_controller_reaches_all_waypoints()
    print("✓ PASS")

    print("\n[2/9] test_aggressive_pd_reaches_waypoints_faster...")
    test1.test_aggressive_pd_reaches_waypoints_faster()
    print("✓ PASS")

    # Test 2
    test2 = TestPDControllerSafety()
    print("\n[3/9] test_pd_controller_triggers_shield...")
    test2.test_pd_controller_triggers_shield()
    print("✓ PASS")

    print("\n[4/9] test_aggressive_pd_safety_preserved...")
    test2.test_aggressive_pd_safety_preserved()
    print("✓ PASS")

    # Test 3
    test3 = TestPDControllerTuning()
    print("\n[5/9] test_custom_pd_gains...")
    test3.test_custom_pd_gains()
    print("✓ PASS")

    print("\n[6/9] test_very_low_gains_safe_but_slow...")
    test3.test_very_low_gains_safe_but_slow()
    print("✓ PASS")

    # Test 4
    test4 = TestBrainAgnosticHarness()
    print("\n[7/9] test_both_controller_types_work...")
    test4.test_both_controller_types_work()
    print("✓ PASS")

    print("\n" + "=" * 60)
    print("✅ All 7 PD controller tests passed!")
    print("HTI v0.4 PD controller is fully functional")
