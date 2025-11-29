# Implementation Guidelines for HTI v0.1

**Note:** This file contains Python-specific implementation requirements and guidelines.
For language-agnostic architecture and system design, see SPEC.md.

This document provides specific implementation guidance for developers and AI assistants working on the HTI v0.1 demo harness.

## Python Version and Compatibility

- **Target version:** Python 3.11
- **Compatibility:** Code must work on Python 3.10+
- **Restrictions:** No Python 3.12+ only features
- **Type hints:** Use `dict[str, float]` (3.10+ style), not `Dict[str, float]` in runtime code
  - In type stubs or where `from typing import Dict` is already present, either style is acceptable

## Dependencies

- **Standard library only** - No external dependencies (no numpy, no pandas, no pytest plugins)
- Built-in modules allowed: `dataclasses`, `time`, `json`, `pathlib`, etc.
- Testing: Use built-in `unittest` or install `pytest` as dev dependency only

## Code Style

- **Simple and readable** - Prioritize clarity over cleverness
- **Explicit over implicit** - Make data flows obvious
- **Minimal magic** - No metaclasses, descriptors, or advanced decorators
- **Type hints** - Use them consistently for all public interfaces
- **Docstrings** - Brief docstrings for all public classes and functions

## Event Logging Requirements

The event logging system must support **dual output**:

### 1. JSON Log File (Machine-Readable)

- **Format:** JSONL (JSON Lines) - one event per line
- **File location:** `event_log.jsonl` in the current working directory
- **Schema:** Each line is a JSON object matching the `EventPack` dataclass:
  ```json
  {"timestamp": 0.42, "tick": 42, "band": "SafetyShield", "obs_before": {"x": 0.5, "x_target": 0.8}, "action_proposed": 0.1, "action_final": 0.05, "reason": "clip_out_of_bounds", "metadata": {}}
  ```
- **Implementation:**
  - Use `dataclasses.asdict()` to convert EventPack to dict
  - Use `json.dumps()` to serialize each event
  - Append each event as a new line immediately (no buffering)
  - File should be human-readable with one event per line

### 2. Console Summary (Human-Readable)

- **During run:** Print a simple progress indicator or key events
- **After run:** Print a summary including:
  - Total events logged
  - Breakdown by reason (e.g., "15 clip_out_of_bounds, 3 clip_near_boundary")
  - Example events (first and last, or most interesting)

**Example console output:**
```
Running HTI v0.1 Demo...
Episode complete after 247 ticks (2.47s simulated)

=== Event Summary ===
Total Shield interventions: 18

By reason:
  clip_out_of_bounds: 15
  clip_near_boundary: 3

First event (tick 5):
  Proposed: 0.08 → Final: 0.05 (clip_out_of_bounds)

Last event (tick 231):
  Proposed: 0.06 → Final: 0.05 (clip_near_boundary)

Event log written to: event_log.jsonl

=== Timing Stats ===
semantics: mean=0.15ms, max=0.23ms
control:   mean=0.08ms, max=0.12ms
reflex:    mean=0.05ms, max=0.09ms
shield:    mean=0.06ms, max=0.11ms
```

## File Structure

Follow the structure defined in SPEC.md:

```
hti_v0_demo/
  __init__.py
  env.py              # ToyEnv class
  shared_state.py     # SharedState, SemanticsAdvice, ReflexFlags
  event_log.py        # EventPack, EventLogger classes
  bands/
    __init__.py
    semantics.py      # SemanticsBand
    control.py        # ControlBand
    reflex.py         # ReflexBand
  shield.py           # SafetyShield
  scheduler.py        # run_episode() and TimingStats
  run_demo.py         # main entry point

tests/
  test_invariants.py  # All invariant tests from SPEC.md
```

## Implementation Order

Suggested order to minimize rework:

1. **Data structures first** (`shared_state.py`, `event_log.py`)
2. **Environment** (`env.py`) - simple and self-contained
3. **Bands** (`bands/*.py`) - implement with stub logic initially
4. **Shield** (`shield.py`) - core safety logic
5. **Scheduler** (`scheduler.py`) - ties everything together
6. **Tests** (`tests/test_invariants.py`) - validate invariants
7. **Demo runner** (`run_demo.py`) - main entry point
8. **Refine band logic** - add smarter heuristics if desired

## Testing Approach

- Write tests matching the concrete examples in SPEC.md Section 6
- Use simple assertions, no complex test fixtures
- Each test should be runnable independently
- Tests should be deterministic (no random behavior unless seeded)

## Common Pitfalls to Avoid

1. **Don't let bands maintain internal state** - They should be pure functions of SharedState
2. **Don't use wall-clock time for control flow** - Use `state.tick` and `state.t`
3. **Don't make Shield optional** - It must always run, even if action is in-bounds
4. **Don't buffer event logs** - Write immediately so logs are preserved on crashes
5. **Don't over-engineer** - This is a demo, not production code

## Success Criteria

The implementation is complete when:

- ✓ `python -m hti_v0_demo.run_demo` runs without errors
- ✓ Console shows human-readable summary with timing stats
- ✓ `event_log.jsonl` contains valid JSON lines
- ✓ All tests in `test_invariants.py` pass
- ✓ Code works on Python 3.10 and 3.11 (test both if possible)

## Questions?

If you encounter ambiguity not covered by SPEC.md or this file, consult the principle:

> "Simplest thing that demonstrates the pattern."

When in doubt, choose the more explicit, more testable option.
