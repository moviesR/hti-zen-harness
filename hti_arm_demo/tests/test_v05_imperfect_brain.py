"""
HTI v0.5 Tests - Imperfect Brain

Tests the mis-tuned brain implementation and validates that:
1. PD baseline still works (no regressions)
2. Imperfect brain stresses Shield more
3. Imperfect brain still succeeds under HTI (100% completion)
4. EventPack metadata contains brain_name
"""

from hti_arm_demo.env import ToyArmEnv
from hti_arm_demo.brains.registry import create_arm_brain
from hti_arm_demo.bands.semantics import SemanticsBand
from hti_arm_demo.bands.control import ControlBand
from hti_arm_demo.bands.reflex import ReflexBand
from hti_arm_demo.bands.shield import SafetyShield
from hti_arm_demo.event_log import EventLogger
from hti_arm_demo.scheduler import run_episode


def test_pd_baseline_still_works():
    """
    Test 1 (Spec): Baseline PD still works.

    Verifies v0.4 nominal PD behavior unchanged:
    - All waypoints reached
    - Shield active (interventions > 0)
    - No joint limit violations (implicit from Shield design)
    """
    env = ToyArmEnv()
    brain = create_arm_brain("pd")
    semantics = SemanticsBand()
    control = ControlBand(brain, brain_name="pd")
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
        max_ticks=1000,
        verbose=False,
    )

    assert stats.all_waypoints_reached, "PD baseline failed to complete task"
    assert stats.shield_interventions > 0, "Shield inactive (unexpected)"
    # Joint limits never violated (implicit from Shield design)
    print(f"✓ PD baseline: {stats.ticks} ticks, {stats.shield_interventions} interventions")


def test_imperfect_stresses_shield_more():
    """
    Test 2 (Spec): Imperfect brain stresses Shield more.

    Runs PD for 3 episodes, Imperfect for 3 episodes.
    Asserts: avg_interventions_imperfect > avg_interventions_pd
    """
    n = 3

    # Run PD baseline
    pd_interventions = []
    for _ in range(n):
        env = ToyArmEnv()
        brain = create_arm_brain("pd")
        semantics = SemanticsBand()
        control = ControlBand(brain, brain_name="pd")
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
            max_ticks=1000,
            verbose=False,
        )
        pd_interventions.append(stats.shield_interventions)

    # Run Imperfect brain
    imperfect_interventions = []
    for _ in range(n):
        env = ToyArmEnv()
        brain = create_arm_brain("imperfect")
        semantics = SemanticsBand()
        control = ControlBand(brain, brain_name="imperfect")
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
            max_ticks=2000,  # More time for imperfect brain
            verbose=False,
        )
        imperfect_interventions.append(stats.shield_interventions)

    avg_pd = sum(pd_interventions) / n
    avg_imperfect = sum(imperfect_interventions) / n

    assert avg_imperfect > avg_pd, \
        f"Imperfect brain should stress Shield more: {avg_imperfect:.1f} vs {avg_pd:.1f}"

    print(f"✓ Shield stress: PD={avg_pd:.1f}, Imperfect={avg_imperfect:.1f} interventions")


def test_imperfect_still_succeeds_under_hti():
    """
    Test 3 (Spec): Imperfect brain still succeeds under HTI.

    Runs Imperfect brain for M episodes.
    Asserts: success_rate == 1.0 (all complete despite poor tuning)
    """
    n = 10
    results = []

    for _ in range(n):
        env = ToyArmEnv()
        brain = create_arm_brain("imperfect")
        semantics = SemanticsBand()
        control = ControlBand(brain, brain_name="imperfect")
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
            max_ticks=2000,  # Generous timeout for imperfect brain
            verbose=False,
        )
        results.append(stats)

    success_count = sum(1 for r in results if r.all_waypoints_reached)
    success_rate = success_count / n

    assert success_rate == 1.0, \
        f"Imperfect brain failed {n - success_count}/{n} episodes under HTI"

    print(f"✓ Imperfect brain: {success_count}/{n} successful (100%)")


def test_eventpack_metadata_contains_brain_name():
    """
    Test 4 (Spec): EventPack metadata contains brain_name.

    Triggers at least one Shield intervention.
    Asserts: event.metadata["brain_name"] exists and matches brain.
    """
    env = ToyArmEnv()
    brain = create_arm_brain("imperfect")
    semantics = SemanticsBand()
    control = ControlBand(brain, brain_name="imperfect")
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
        max_ticks=500,
        verbose=False,
    )

    events = event_logger.events
    assert len(events) > 0, "No Shield interventions triggered"

    # Check all events have brain_name in metadata
    for event in events:
        assert "brain_name" in event.metadata, "Missing brain_name in metadata"
        assert event.metadata["brain_name"] == "imperfect", \
            f"Wrong brain_name: {event.metadata['brain_name']}"

    print(f"✓ EventPack metadata: {len(events)} events, all have brain_name='imperfect'")


if __name__ == "__main__":
    # Run all tests
    print("\n=== HTI v0.5 Tests ===\n")

    print("Test 1: PD baseline still works")
    test_pd_baseline_still_works()

    print("\nTest 2: Imperfect stresses Shield more")
    test_imperfect_stresses_shield_more()

    print("\nTest 3: Imperfect still succeeds under HTI")
    test_imperfect_still_succeeds_under_hti()

    print("\nTest 4: EventPack metadata contains brain_name")
    test_eventpack_metadata_contains_brain_name()

    print("\n=== All v0.5 tests passed! ===\n")
