# HTI v0.1 – Minimal Demo Harness

This repo implements a tiny, testable demo of the **HTI (Hierarchical Temporal Intelligence)** pattern:

- Time-banded control:
  - **Semantics** (10 Hz) – high-level advisor
  - **Control** (50 Hz) – chooses actions
  - **Reflex** (100 Hz) – fast safety pre-checks
  - **Safety Shield** (100 Hz) – last writer before the environment
- Explicit invariants:
  - Semantics is advisory-only
  - Shield runs last before `env.step`
  - Actions are bounded
  - Safety interventions generate logged **event-packs**

The goal of v0.1 is **not** robotics performance. It's to prove the harness pattern in code:
- Bands fire at the right frequencies
- The Shield enforces safety bounds
- Event-packs are logged whenever the Shield intervenes
- Basic timing stats are recorded

For full details, see [`SPEC.md`](./SPEC.md).

## Quick Start (Intended)

Once implemented, you should be able to:

```bash
python -m hti_v0_demo.run_demo
```

and see:

* Console output with steps taken and any Shield interventions
* A JSON or text log of event-packs
* A simple summary of per-band execution times

## Layout (Intended)

```text
hti_v0_demo/
  README.md
  SPEC.md
  env.py
  shared_state.py
  event_log.py
  bands/
    __init__.py
    reflex.py
    control.py
    semantics.py
  shield.py
  scheduler.py
  run_demo.py
  tests/
    test_invariants.py
```

Development instructions for Claude Code or other assistants are in `SPEC.md`.