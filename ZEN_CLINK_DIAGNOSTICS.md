# Zen MCP `clink` Tool Diagnostics

**Date**: 2025-11-30
**Issue**: `clink` tool failures with gemini and codex CLIs
**Status**: 🔴 **IDENTIFIED** - Two separate configuration issues

---

## Executive Summary

The `clink` tool requires **external CLI executables** to be installed and configured separately from Zen MCP's API access. Think of it this way:

- **Zen MCP API access** (✅ working): Direct model calls via API keys (chat, consensus, thinkdeep, etc.)
- **clink CLI bridge** (❌ broken): Spawns external CLI processes (gemini CLI, codex CLI, claude CLI)

**Key Insight**: Having a Gemini API key in Zen MCP's `.env` doesn't mean the Gemini CLI executable is installed!

---

## Issue 1: Gemini CLI Not Installed

### Error
```
CLI 'gemini' execution failed: Executable 'gemini' not found in PATH
```

### Root Cause
The **Gemini CLI** is a separate tool from Google's Gemini API:
- **Gemini API**: Used by Zen MCP for direct `mcp__zen__chat`, `mcp__zen__consensus` calls ✅ Working
- **Gemini CLI**: External command-line tool for interactive Gemini sessions ❌ Not installed

### Expected Configuration
**File**: `/home/john2/claude-projects/zenlab/zen-mcp-server/conf/cli_clients/gemini.json`
```json
{
  "name": "gemini",
  "command": "gemini",  // <-- This executable doesn't exist
  "additional_args": ["--yolo"],
  ...
}
```

### Current Status
```bash
$ which gemini
# (no output - not found)
```

### Solution
Install the Gemini CLI from: https://github.com/google-gemini/gemini-cli

**Installation (likely npm-based)**:
```bash
# Check if Gemini CLI is available via npm
npm search gemini-cli

# Or install via npm (hypothetical - check official docs)
npm install -g @google/gemini-cli
```

**Verification after install**:
```bash
which gemini  # Should show: /path/to/gemini
gemini --version  # Should show version
```

---

## Issue 2: Codex CLI Authentication Failure

### Error
```
401 Unauthorized (exceeded retry limit after 5 attempts)
```

### Root Cause
Codex CLI is **installed** but not **authenticated**:
- **Codex CLI location**: `/mnt/c/Users/john2/AppData/Roaming/npm/codex`
- **Version**: `codex-cli 0.44.0` ✅ Installed
- **Auth status**: 401 Unauthorized ❌ Not configured

### Current Status
```bash
$ which codex
/mnt/c/Users/john2/AppData/Roaming/npm/codex

$ codex --version
codex-cli 0.44.0
```

### Expected Configuration
Codex CLI has **separate authentication** from Zen MCP's OpenAI API key. The CLI likely stores credentials in:
- `~/.config/codex/` (Linux/macOS)
- `C:\Users\john2\AppData\Roaming\codex\` (Windows)

### Solution

**Option 1: Check existing Codex CLI auth**
```bash
# Check if Codex CLI has auth configured
codex config list
# or
codex auth status
```

**Option 2: Re-authenticate Codex CLI**
```bash
# Login to Codex CLI (separate from Zen MCP API key)
codex auth login
# or
codex login
```

**Option 3: Set API key for Codex CLI**
```bash
# If Codex CLI uses environment variable
export OPENAI_API_KEY=your_openai_key_here
codex test  # Test if it works
```

**Note**: Codex CLI authentication is **independent** of Zen MCP's `OPENAI_API_KEY` in `.env`. They are two separate systems.

---

## Issue 3: Claude CLI Status

### Current Status
```bash
$ which claude
/home/john2/.nvm/versions/node/v20.19.6/bin/claude

$ claude --version
2.0.55 (Claude Code)
```

**Status**: ✅ **WORKING** - Claude CLI is installed and should work with clink

### Expected Configuration
**File**: `/home/john2/claude-projects/zenlab/zen-mcp-server/conf/cli_clients/claude.json`
```json
{
  "name": "claude",
  "command": "claude",
  "additional_args": [
    "--permission-mode", "acceptEdits",
    "--model", "sonnet"
  ],
  ...
}
```

**Test clink with Claude CLI**:
```python
# This SHOULD work (Claude CLI is installed)
mcp__zen__clink(
    cli_name="claude",
    role="default",
    prompt="Test: List files in current directory"
)
```

---

## Working vs Broken: Summary Table

| CLI | Executable | Version | Auth | clink Status | Direct Zen Tools |
|-----|-----------|---------|------|--------------|------------------|
| **gemini** | ❌ Not found | N/A | N/A | ❌ Broken | ✅ Working (API) |
| **codex** | ✅ Installed | 0.44.0 | ❌ 401 Error | ❌ Broken | ✅ Working (API) |
| **claude** | ✅ Installed | 2.0.55 | ✅ (assumed) | ✅ Should work | ✅ Working |

---

## Why Direct Zen Tools Work

Direct Zen MCP tools (`chat`, `consensus`, `thinkdeep`, etc.) work because they use **API keys** configured in:

**File**: `/home/john2/claude-projects/zenlab/zen-mcp-server/.env`
```env
GEMINI_API_KEY=your_gemini_api_key_here  # ✅ Working for mcp__zen__chat
OPENAI_API_KEY=your_openai_api_key_here  # ✅ Working for mcp__zen__consensus
```

These tools make **direct HTTP API calls** to OpenAI, Gemini, etc. - no CLI executables needed.

**Example of what works**:
```python
# Direct API call via Zen MCP (uses API key from .env)
mcp__zen__consensus(
    models=[
        {"model": "gpt-5.1", "stance": "for"},
        {"model": "gemini-2.5-pro", "stance": "against"}
    ],
    step="Should we use SB3 or CleanRL?",
    ...
)
# ✅ Works perfectly - no CLI needed
```

---

## Architecture: API vs CLI

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Claude Code Session                  │
│  (running at /home/john2/claude-projects/hti-zen-harness)   │
└─────────────┬───────────────────────────────────────────────┘
              │
              │ MCP Protocol
              ▼
┌─────────────────────────────────────────────────────────────┐
│              Zen MCP Server (Python)                         │
│  Location: /home/john2/claude-projects/zenlab/zen-mcp-server│
│                                                              │
│  ┌────────────────────────┐  ┌──────────────────────────┐  │
│  │   Direct API Tools     │  │   clink (CLI Bridge)     │  │
│  ├────────────────────────┤  ├──────────────────────────┤  │
│  │ • chat                 │  │ • Spawns CLI processes   │  │
│  │ • consensus            │  │ • Isolated contexts      │  │
│  │ • thinkdeep            │  │ • Requires executables   │  │
│  │ • codereview           │  │                          │  │
│  │                        │  │  Needs:                  │  │
│  │ Uses API keys from:    │  │  - gemini CLI ❌         │  │
│  │ .env file ✅           │  │  - codex CLI ❌ (401)    │  │
│  │                        │  │  - claude CLI ✅         │  │
│  └────────────────────────┘  └──────────────────────────┘  │
│              │                           │                   │
└──────────────┼───────────────────────────┼──────────────────┘
               │                           │
               ▼                           ▼
       ┌──────────────┐         ┌────────────────────┐
       │  HTTP APIs   │         │  CLI Executables   │
       ├──────────────┤         ├────────────────────┤
       │ • Gemini API │         │ • gemini (missing) │
       │ • OpenAI API │         │ • codex (no auth)  │
       │ • X.AI API   │         │ • claude (working) │
       └──────────────┘         └────────────────────┘
             ✅                         ❌/✅
```

---

## Recommended Actions

### Priority 1: Fix Codex CLI Auth (Low Hanging Fruit)
```bash
# Try to authenticate Codex CLI
codex auth login
# or check current config
codex config list
```

### Priority 2: Install Gemini CLI (If Needed)
```bash
# Check if Gemini CLI exists in npm registry
npm search gemini-cli

# Install if available
npm install -g @google/gemini-cli  # (hypothetical - check docs)
```

### Priority 3: Test Claude CLI via clink
```python
# Since Claude CLI is installed, test it works:
mcp__zen__clink(
    cli_name="claude",
    role="default",
    prompt="Quick test: what is 2+2?"
)
```

---

## When to Use Direct Tools vs clink

### ✅ Use Direct Zen Tools (chat, consensus, thinkdeep, etc.)
**When**:
- Quick questions or analysis
- Multi-model consensus needed
- Debugging, planning, code review
- No need for context isolation

**Advantage**: Already working, no CLI setup needed

**Example**:
```python
mcp__zen__chat(
    model="gemini-2.5-pro",
    prompt="Explain PD control theory",
    working_directory_absolute_path="/home/john2/claude-projects/hti-zen-harness"
)
```

### ✅ Use clink (when working)
**When**:
- Heavy codebase exploration (save context)
- Isolated code reviews (don't pollute main context)
- Delegating large tasks to fresh context
- Need web search + file access in subagent

**Advantage**: Offloads heavy work to isolated context

**Example (when gemini CLI installed)**:
```python
mcp__zen__clink(
    cli_name="gemini",
    role="codereviewer",
    prompt="Review entire hti_arm_demo/ for safety issues"
)
# Gemini reads all files, explores, returns only summary
# Your context stays clean!
```

---

## Next Steps

1. **Investigate Codex CLI auth**: Run `codex auth login` or check `codex config`
2. **Research Gemini CLI install**: Check https://github.com/google-gemini/gemini-cli
3. **Test Claude CLI via clink**: Verify at least one clink CLI works
4. **Document findings**: Update this file with solutions

---

## Files Referenced

- Zen MCP CLI configs: `/home/john2/claude-projects/zenlab/zen-mcp-server/conf/cli_clients/*.json`
- Zen MCP environment: `/home/john2/claude-projects/zenlab/zen-mcp-server/.env`
- clink documentation: `/home/john2/claude-projects/zenlab/zen-mcp-server/docs/tools/clink.md`

---

**Status**: 🔍 **DIAGNOSIS COMPLETE** - Ready for user action
