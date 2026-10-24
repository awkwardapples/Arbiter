#!/usr/bin/env python3
"""Claude Code `PreToolUse` hook for Bash: the same rules as .cursor/hooks/shell_guard.py.

stdin : JSON with tool_input.command.
Deny  : exit code 2 with the reason on stderr (Claude Code blocks the call and shows Claude the reason).
Ask   : a PreToolUse permission decision of "ask", so the human confirms.
Allow : exit 0 with no output (Claude Code's normal permission rules still apply).
Never raises: on an internal error it allows, and the deny rules in .claude/settings.json still apply.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


def _rules(root: Path):
    path = root / ".cursor" / "hooks" / "shell_guard.py"
    spec = importlib.util.spec_from_file_location("arbiter_shell_guard", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.DENY, mod.ASK


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    command = str((payload.get("tool_input") or {}).get("command", ""))
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or Path.cwd())
    deny, ask = _rules(root)
    for pattern, reason in deny:
        if re.search(pattern, command, flags=re.IGNORECASE):
            sys.stderr.write(f"Blocked by the Arbiter shell guard: {reason} Find another way or ask the human.")
            return 2
    for pattern, reason in ask:
        if re.search(pattern, command, flags=re.IGNORECASE):
            sys.stdout.write(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "ask",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 - never trap the session
        sys.exit(0)
