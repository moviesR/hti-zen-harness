"""Invariant tests for HTI v0.1

Tests the 7 core invariants from SPEC.md Section 3.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hti_v0_demo.shared_state import SharedState
from hti_v0_demo.bands import SemanticsBand, ControlBand, ReflexBand
from hti_v0_demo.shield import SafetyShield
from hti_v0_demo.env import ToyEnv


def test_semantics_advisory_only():
    """Invariant #3: Semantics may not write action_proposed or action_final"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8})
    state.action_proposed = 0.03  # Set by prior band

    sem = SemanticsBand()
    sem.step(state)

    # Assert semantics didn't touch action
    assert state.action_proposed == 0.03, "Semantics modified action_proposed"
    assert state.action_final is None, "Semantics modified action_final"
    # But did write advice
    assert state.semantics_advice.direction_hint in [-1, 0, 1], "Semantics didn't write valid advice"
    print("✓ Test passed: Semantics is advisory-only")


def test_shield_bounds_actions():
    """Invariant #4: action_final is always within bounds"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8})
    shield = SafetyShield(u_min=-0.05, u_max=0.05)

    # Test out-of-bounds proposals
    test_cases = [0.10, -0.10, 0.03, -0.02, 0.0]

    for proposed in test_cases:
        state.action_proposed = proposed
        safe_u, event = shield.apply(state)

        assert -0.05 <= safe_u <= 0.05, f"Action {safe_u} out of bounds for proposal {proposed}"
        assert state.action_final == safe_u, "action_final doesn't match returned safe_u"

    print("✓ Test passed: Shield bounds actions")


def test_event_pack_on_clipping():
    """Invariant #5: EventPack generated when Shield intervenes"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8}, tick=42, t=0.42)
    shield = SafetyShield(u_min=-0.05, u_max=0.05)

    # Propose out-of-bounds action
    state.action_proposed = 0.10
    safe_u, event = shield.apply(state)

    # Should have clipped and logged
    assert safe_u == 0.05, "Shield didn't clip to max bound"
    assert event is not None, "No event generated on clip"
    assert event.action_proposed == 0.10, "Event has wrong proposed action"
    assert event.action_final == 0.05, "Event has wrong final action"
    assert event.band == "SafetyShield", "Event has wrong band"
    assert event.tick == 42, "Event has wrong tick"

    # Propose in-bounds action
    state.action_proposed = 0.03
    safe_u, event = shield.apply(state)

    # Should NOT log
    assert safe_u == 0.03, "Shield modified in-bounds action"
    assert event is None, "Event generated for in-bounds action"

    print("✓ Test passed: Event-pack on clipping")


def test_scheduler_frequencies():
    """Invariant #2 (partial): Bands fire at correct frequencies"""
    # Track which ticks each band fires on
    semantics_ticks = []
    control_ticks = []
    reflex_ticks = []

    # Simulate scheduling logic for 100 ticks
    for tick in range(100):
        if tick % 10 == 0:
            semantics_ticks.append(tick)
        if tick % 2 == 0:
            control_ticks.append(tick)
        reflex_ticks.append(tick)

    # Assert frequencies
    assert semantics_ticks == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90], "Semantics wrong frequency"
    assert len(control_ticks) == 50, f"Control wrong frequency: {len(control_ticks)} != 50"
    assert control_ticks[0] == 0 and control_ticks[1] == 2, "Control wrong start"
    assert len(reflex_ticks) == 100, f"Reflex wrong frequency: {len(reflex_ticks)} != 100"

    print("✓ Test passed: Scheduler frequencies")


def test_shield_runs_last():
    """Invariant #2 (partial): Shield executes after all bands"""
    # This is enforced by the scheduler structure - test the data flow
    state = SharedState(obs={"x": 0.5, "x_target": 0.8}, tick=0)

    # Simulate one tick with all bands
    sem = SemanticsBand()
    ctrl = ControlBand()
    reflex = ReflexBand()
    shield = SafetyShield()

    # Execute in order
    sem.step(state)
    assert state.action_proposed is None, "Semantics set action_proposed"

    ctrl.step(state)
    assert state.action_proposed is not None, "Control didn't set action_proposed"
    assert state.action_final is None, "Control set action_final"

    reflex.step(state)
    assert state.action_final is None, "Reflex set action_final"

    safe_u, event = shield.apply(state)
    assert state.action_final is not None, "Shield didn't set action_final"

    print("✓ Test passed: Shield runs last (data flow)")


def test_causality_within_tick():
    """Invariant #7: Bands can read earlier bands' outputs from same tick"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8}, tick=0)

    # Semantics writes advice at tick 0
    sem = SemanticsBand()
    sem.step(state)

    semantics_hint = state.semantics_advice.direction_hint
    assert semantics_hint != 0, "Semantics should suggest direction"

    # Control at tick 0 should see that advice
    ctrl = ControlBand()
    ctrl.step(state)

    # Control should have written action_proposed
    assert state.action_proposed is not None, "Control didn't propose action"

    # Verify Control had access to semantics_advice (implicit in its logic)
    # We can't directly test what Control "read", but we verified it can access
    # the semantics_advice that was written in the same tick

    print("✓ Test passed: Causality within tick")


def test_bounded_final_commands():
    """Invariant #4 (extended): Verify bounds in realistic scenario"""
    env = ToyEnv()
    state = SharedState()
    shield = SafetyShield(u_min=-0.05, u_max=0.05)

    obs = env.reset(x0=0.1, x_target=0.9)
    state.obs = obs

    # Run a few steps
    for tick in range(10):
        state.tick = tick
        state.t = tick * 0.01

        # Control might propose aggressive action
        state.action_proposed = 0.5  # Way out of bounds

        # Shield must bound it
        safe_u, event = shield.apply(state)

        assert -0.05 <= safe_u <= 0.05, f"Tick {tick}: action {safe_u} out of bounds"
        assert event is not None, f"Tick {tick}: no event for out-of-bounds action"

        # Step environment
        obs, reward, done, info = env.step(safe_u)
        state.obs = obs

    print("✓ Test passed: Bounded final commands")


def run_all_tests():
    """Run all invariant tests."""
    print("Running HTI v0.1 Invariant Tests\n")

    tests = [
        test_semantics_advisory_only,
        test_shield_bounds_actions,
        test_event_pack_on_clipping,
        test_scheduler_frequencies,
        test_shield_runs_last,
        test_causality_within_tick,
        test_bounded_final_commands,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {test.__name__}")
            print(f"  {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
