#!/usr/bin/env python3
"""Claude Code `Stop` hook: re-run the active lane's verify-pass and hand failures back.

The Claude Code port of .cursor/hooks/verify_loop.py (same ACTIVE_PASS file, same verify command).

stdin  : JSON from Claude Code; uses `stop_hook_active` and `cwd` if present.
stdout : nothing (let Claude stop), or {"decision": "block", "reason": "..."} (Claude continues with the reason).

Behaviour:
  * Idle unless .cursor/ACTIVE_PASS exists and its phase is "build".
  * Runs <venv python> scripts/tasks.py verify-pass --pass <ID> --quiet.
  * Red   -> block with the masked failure tail, up to MAX_LOOPS consecutive times, then one final
             block asking Claude to set the phase to blocked and summarise, then idle.
  * Green -> once per lane, block with a reminder to write the report and usage note if the report
             is missing; otherwise let Claude stop.
  * Never raises: any internal error lets Claude stop.
State lives in logs/claude-hook-state.json (gitignored with logs/*).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

MAX_LOOPS = int(os.environ.get("ARBITER_HOOK_MAX_LOOPS", "6"))
TIMEOUT_S = int(os.environ.get("ARBITER_HOOK_TIMEOUT", "840"))
TAIL_LINES = 80
MAX_CHARS = 6000


def _root(payload: dict) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(payload.get("cwd") or Path.cwd())


def _cursor_hook(root: Path):
    """Reuse read_active, interpreter, mask and label from the Cursor hook so both stay in step."""
    path = root / ".cursor" / "hooks" / "verify_loop.py"
    spec = importlib.util.spec_from_file_location("arbiter_verify_loop", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _state_path(root: Path) -> Path:
    d = root / "logs"
    d.mkdir(exist_ok=True)
    return d / "claude-hook-state.json"


def _load_state(root: Path) -> dict:
    try:
        return json.loads(_state_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(root: Path, state: dict) -> None:
    try:
        _state_path(root).write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def _log(root: Path, record: dict) -> None:
    try:
        with (root / "logs" / "claude-hook.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}) + "\n")
    except OSError:
        pass


def _block(reason: str) -> None:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.stdout.flush()


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    root = _root(payload)
    hook = _cursor_hook(root)
    active = hook.read_active(root)
    if active is None:
        return
    pass_id, phase = active
    if phase != "build":
        return

    state = _load_state(root)
    lane = state.get(pass_id, {"loops": 0, "reminded": False, "last": 0.0})
    if time.time() - float(lane.get("last", 0.0)) > 30 * 60:
        lane["loops"] = 0  # a new working session on this lane starts a fresh loop budget
    lane["last"] = time.time()

    cmd = [hook.interpreter(root), "scripts/tasks.py", "verify-pass", "--pass", pass_id, "--quiet"]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
        code, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, f"verify-pass timed out after {TIMEOUT_S}s"
    except OSError as exc:
        code, out = 127, f"could not run verify-pass: {exc}"
    elapsed = round(time.monotonic() - started, 1)

    if code == 0:
        lane["loops"] = 0
        report = root / "docs" / "passes" / f"{hook.label(pass_id)}_REPORT.md"
        _log(root, {"pass": pass_id, "result": "green", "seconds": elapsed})
        if not report.is_file() and not lane.get("reminded"):
            lane["reminded"] = True
            state[pass_id] = lane
            _save_state(root, state)
            _block(
                f"`verify-pass --pass {pass_id}` is green. Finish the lane (AGENTS.md §6 steps 6–7): write "
                f"docs/passes/{hook.label(pass_id)}_REPORT.md (built / deviations with reasons / known gaps / "
                f"commands run), write docs/cursor-usage/{hook.label(pass_id)}.md (tool: Claude Code, model, "
                "plan file, hook iterations), push the branch, open the PR, delete .cursor/ACTIVE_PASS, and stop."
            )
            return
        state[pass_id] = lane
        _save_state(root, state)
        return

    lane["loops"] = int(lane.get("loops", 0)) + 1
    state[pass_id] = lane
    _save_state(root, state)
    tail = "\n".join(out.strip().splitlines()[-TAIL_LINES:])
    tail = hook.mask(tail)[-MAX_CHARS:]
    _log(root, {"pass": pass_id, "loop": lane["loops"], "result": "red", "exit": code, "seconds": elapsed})

    if lane["loops"] > MAX_LOOPS + 1:
        return  # already told to stop; let Claude stop
    if lane["loops"] > MAX_LOOPS:
        _block(
            f"`verify-pass --pass {pass_id}` is still failing after {MAX_LOOPS} automatic iterations. "
            f"Stop changing code. Set .cursor/ACTIVE_PASS to `{pass_id} blocked`, then summarise for the human: "
            "each remaining failure, what you tried, and your best hypothesis. Then stop."
        )
        return
    _block(
        f"Automatic verification (iteration {lane['loops']}/{MAX_LOOPS}): "
        f"`python scripts/tasks.py verify-pass --pass {pass_id}` failed (exit {code}).\n"
        "Fix the failures below. Do NOT weaken, skip, xfail or delete tests. If a test itself is wrong, "
        f"set .cursor/ACTIVE_PASS to `{pass_id} blocked` and ask the human.\n\n```\n{tail}\n```"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - the hook must never trap the session
        pass
