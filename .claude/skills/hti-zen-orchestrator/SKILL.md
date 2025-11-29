---
name: hti-zen-orchestrator
description: Guidelines for using Zen MCP tools effectively in this repo. Use for complex multi-model tasks, architectural decisions, or when cross-model validation adds value.
---

# HTI Zen Orchestrator

This Skill defines **when and how** to use Zen MCP tools in the **hti-zen-harness** project.

Zen provides multi-model orchestration (`planner`, `consensus`, `codereview`, `thinkdeep`, `debug`, `clink`). Use them deliberately when they add real value, not reflexively.

---

## When Zen Tools Add Value

### Consider using Zen MCP tools when:

**Complex architectural work**
- Multi-file refactors spanning 5+ files
- New subsystems or major feature additions
- Changes to core HTI abstractions (bands, adapters, guards, probes)
- Redesigning interfaces or data flows

**Safety-critical code**
- Modifying timing bands or HTI invariants
- Changes to error handling or recovery logic
- Adapter implementations that interact with external models
- CI/CD pipeline changes that affect safety guarantees

**Ambiguous or contentious decisions**
- Multiple valid implementation approaches exist
- Trade-offs between performance, safety, and complexity
- Unusual patterns where you're unsure of best practice

**Deep investigation needed**
- Complex bugs with unclear root cause
- Performance issues requiring systematic analysis
- Understanding unfamiliar codebases or dependencies

### When Zen is overkill:

**Simple changes**
- Single-file bug fixes
- Adding straightforward tests
- Documentation updates
- Simple refactors (renaming, extracting functions)
- Configuration tweaks

For these, direct implementation is faster and more appropriate.

---

## Zen Tool Selection Guide

### `planner` - Multi-step planning with reflection

**Use when:**
- Task has 5+ distinct steps
- Multiple architectural approaches possible
- Need to think through dependencies and ordering
- Want progressive refinement of a complex plan

**Example**: "Plan migration of adapter interface to support streaming responses"

### `consensus` - Multi-model debate and synthesis

**Use when:**
- Two+ valid approaches with different trade-offs
- Safety-critical decisions need validation
- Controversial architectural choices
- Want diverse perspectives on a design

**Example**: "Should we use async generators or callback patterns for streaming? Get consensus from multiple models."

**Models to include**: At least 2, typically 3-4. Mix code-specialized models with general reasoning models.

### `codereview` - Systematic code analysis

**Use when:**
- Reviewing large PRs or branches
- Safety-critical changes to core logic
- Unfamiliar code needs audit
- Want comprehensive security/performance review

**Example**: "Review the new HTI band scheduler implementation for correctness and edge cases."

### `thinkdeep` - Hypothesis-driven investigation

**Use when:**
- Complex architectural questions
- Performance analysis and optimization planning
- Security threat modeling
- Understanding subtle interactions

**Example**: "Investigate why adapter timeout logic behaves differently under load."

### `debug` - Root cause analysis

**Use when:**
- Complex bugs with mysterious symptoms
- Race conditions or timing issues
- Failures that only occur in specific conditions
- Need systematic hypothesis testing

**Example**: "Debug why HTI band transitions occasionally skip validation steps."

### `clink` - Delegating to external CLI tools

**Use when:**
- Need capabilities of a specific AI CLI (gemini, codex, claude)
- Want to leverage role presets (codereviewer, planner)
- Continuing a conversation thread across tools

**Example**: "Use clink with gemini CLI for large-scale codebase exploration."

### `chat` - General-purpose thinking partner

**Use for:**
- Brainstorming approaches
- Quick sanity checks
- Explaining concepts
- Rubber-duck debugging

---

## Model Selection Guidelines

When calling Zen tools, choose models deliberately based on the task:

### For reading, exploration, summarization:
- **Prefer**: Models with large context windows and good efficiency
- **Pattern**: Large-context, efficient models
- **Use case**: "Scan 50 test files to find coverage gaps"

### For core implementation and refactoring:
- **Prefer**: Code-specialized, high-quality models
- **Pattern**: Code-specialized models (e.g., models with "codex" in the name or any available code-focused equivalent)
- **Use case**: "Implement new HTI adapter with proper error handling"

### For safety-critical validation:
- **Use**: Multiple models via `consensus` or sequential `codereview`
- **Pattern**: Mix of code-specialized and general reasoning models for diverse perspectives
- **Use case**: "Validate timing band logic won't introduce deadlocks"

### Document your choices:

When model selection matters for auditability:
```python
# HTI-NOTE: Implementation reviewed by code-specialized models (consensus check).
# No race conditions detected in band transition logic.
def transition_band(current: Band, target: Band) -> Result:
    ...
```

---

## Shell Access via `clink`

Zen's `clink` tool can execute shell commands. Use it responsibly.

### ✅ OK without asking (read-only, low-risk):

- File inspection: `ls`, `pwd`, `cat`, `head`, `tail`, `find`
- Git inspection: `git status`, `git diff`, `git log`, `git branch`
- Testing: `pytest`, `python -m pytest`, test runners
- Linting: `ruff check`, `black --check`, `mypy`, static analysis
- Info gathering: `python --version`, `uv --version`, dependency checks

### ⚠️ Ask user approval first:

- **Installing packages**: `pip install`, `uv add`, `npm install`
- **Git mutations**: `git commit`, `git push`, `git reset`, `git checkout -b`, `git rebase`
- **File mutations**: `rm`, `mv`, file deletions/moves
- **Network operations**: `curl`, `wget`, API calls
- **Environment changes**: Modifying config files, `.env` files

**How to ask:**
```
I need to run: `pip install pytest-asyncio`
Reason: Required for testing async adapter implementations
Approve?
```

---

## Failure Handling with Zen

When Zen tools or model calls fail, follow these rules (aligned with `hti-fallback-guard`):

### ❌ Do NOT:
- Pretend the call succeeded
- Silently switch to a different model without explanation
- Invent outputs or fake data
- Swallow errors and continue as if nothing happened

### ✅ DO:

**1. Report clearly:**
```
Zen `codereview` call failed:
  Tool: codereview
  Model: <model-name>
  Error: Rate limit exceeded (429)
  Step: Reviewing src/adapters/openai.py
```

**2. Propose alternatives:**
- "Retry with a different model (another available code-specialized option)?"
- "Split the review into smaller chunks?"
- "Proceed with manual review instead?"
- "Wait 60s and retry?"

**3. Document in code if relevant:**
```python
# HTI-TODO: Codereview via Zen failed (rate limit).
# Manual review needed for thread safety in adapter pool.
```

### Structured failure result pattern:

When appropriate, return explicit error states:
```python
@dataclass
class ZenResult:
    ok: bool
    tool: str
    data: dict | None = None
    error: str | None = None

# Never set ok=True when Zen call actually failed
```

---

## Recommended Workflow for Substantial Changes

For non-trivial work (multi-file refactors, new features, safety-critical edits):

### 1. Plan (if complexity warrants it)
- Use Zen `planner` for complex, multi-faceted tasks
- For simpler changes, a bullet list is fine
- Show plan to user, get confirmation

### 2. Implement
- Use appropriate model (code-specialized for core logic)
- Follow `hti-fallback-guard` principles
- Document model choice if safety-critical

### 3. Review (for important changes)
- Use Zen `codereview` for:
  - Large PRs (10+ files)
  - Safety-critical logic
  - HTI band/adapter/guard changes
- Use Zen `precommit` before finalizing

### 4. Summarize
Tell the user:
- What changed (files, behavior)
- Which models/tools were used
- Any TODOs or concerns
- Test coverage added/modified

---

## Integration with Testing and CI

When working on tests or CI:

**Prefer changes that tighten guarantees:**
- Tests that assert explicit failures (not silent fallbacks)
- CI checks that fail loudly when invariants break
- Guards that prevent invalid state transitions

**Use Zen tools to:**
- Validate test coverage (`codereview` with focus on testing)
- Check CI logic for edge cases (`thinkdeep` on pipeline behavior)
- Compare testing strategies (`consensus` on approach)

**Document how changes affect:**
- HTI invariants (timing, safety, ordering)
- Existing guards and probes
- CI failure modes

---

## When in Doubt

Ask yourself:
1. **Is this complex enough to need multi-model orchestration?**
   - Yes → Use Zen deliberately
   - No → Direct implementation is fine

2. **Does this change affect safety or timing?**
   - Yes → Consider `consensus` or `codereview`
   - No → Proceed with standard review

3. **Am I using Zen to avoid thinking, or to think better?**
   - Avoid thinking → Don't use Zen
   - Think better → Use Zen appropriately

The goal is **thoughtful tool use**, not **tool maximalism**.
