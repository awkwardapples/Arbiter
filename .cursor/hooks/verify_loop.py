#!/usr/bin/env python3
"""Cursor `stop` hook: re-run the active pass's verification and feed failures back to the agent.

Contract (Cursor hooks, schema version 1):
  stdin  : JSON with at least {"status": "completed"|"aborted"|"error", "loop_count": int, "workspace_roots": [...]}
  stdout : JSON. {} = let the agent stop.  {"followup_message": "..."} = send the agent another turn.

Behaviour:
  * Idle unless .cursor/ACTIVE_PASS exists and its phase is "build"  (format: "<ID> <phase>").
  * Idle unless status == "completed".
  * Runs:  <python> scripts/tasks.py verify-pass --pass <ID> --quiet   (timeout 840 s).
  * Green  -> reminds the agent to finish the pass (report, usage log, push) once, then idles.
  * Red    -> returns the failure tail (secrets masked) as a follow-up, up to MAX_LOOPS times,
              then asks the agent to stop, summarise and hand back to the human.
  * Never raises: any internal error prints {} so Cursor is never blocked by the hook itself.
Logs one JSON line per invocation to logs/cursor-hook.jsonl (gitignored; summarise in docs/CURSOR_USAGE.md).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MAX_LOOPS = int(os.environ.get("ARBITER_HOOK_MAX_LOOPS", "5"))
TIMEOUT_S = int(os.environ.get("ARBITER_HOOK_TIMEOUT", "840"))
TAIL_LINES = 80
MAX_CHARS = 6000
VALID_IDS = {"0", "1a", "1b", "2a", "2b", "2c", "2d", "3", "4a", "4b", "5a", "5b", "6", "7"}


def label(pass_id: str) -> str:
    """Lane id -> label used in file names: '0' -> 'P0', '1a' -> 'P1-A'."""
    return f"P{pass_id[:-1]}-{pass_id[-1].upper()}" if pass_id[-1].isalpha() else f"P{pass_id}"


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"nvapi-[A-Za-z0-9_-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]{8,}"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?)[^\s'\"#]{8,}"),
]


def mask(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub(lambda m: (m.group(1) if m.groups() else "") + "***", text)
    return text


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def log(root: Path, record: dict) -> None:
    try:
        d = root / "logs"
        d.mkdir(exist_ok=True)
        with (d / "cursor-hook.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}) + "\n")
    except OSError:
        pass


def read_active(root: Path) -> tuple[str, str] | None:
    f = root / ".cursor" / "ACTIVE_PASS"
    if not f.is_file():
        return None
    parts = f.read_text(encoding="utf-8").strip().split()
    if not parts:
        return None
    pass_id = parts[0].lower().replace("-", "").removeprefix("p")  # accepts 1a, P1-A, p1a
    phase = parts[1].lower() if len(parts) > 1 else "build"
    if pass_id not in VALID_IDS:
        return None
    return pass_id, phase


def interpreter(root: Path) -> str:
    """Prefer the project's .venv so verify-pass sees the pinned dependencies."""
    for cand in (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe"):
        if cand.is_file():
            return str(cand)
    return sys.executable


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    roots = payload.get("workspace_roots") or []
    root = Path(roots[0]) if roots else Path.cwd()
    status = payload.get("status", "completed")
    loop_count = int(payload.get("loop_count", 0) or 0)

    active = read_active(root)
    if active is None or status != "completed":
        emit({})
        return
    pass_id, phase = active
    if phase != "build":
        log(root, {"pass": pass_id, "phase": phase, "action": "idle"})
        emit({})
        return

    if loop_count > MAX_LOOPS:
        log(root, {"pass": pass_id, "loop": loop_count, "action": "exhausted"})
        emit({})
        return

    cmd = [interpreter(root), "scripts/tasks.py", "verify-pass", "--pass", pass_id, "--quiet"]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
        code, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, f"verify-pass timed out after {TIMEOUT_S}s"
    except OSError as exc:  # scripts/tasks.py missing (e.g. before P0) or interpreter problem
        code, out = 127, f"could not run verify-pass: {exc}"
    elapsed = round(time.monotonic() - started, 1)

    if code == 0:
        report = root / "docs" / "passes" / f"{label(pass_id)}_REPORT.md"
        log(root, {"pass": pass_id, "loop": loop_count, "result": "green", "seconds": elapsed})
        if report.is_file() or loop_count >= MAX_LOOPS:
            emit({})
        else:
            emit(
                {
                    "followup_message": (
                        f"`verify-pass --pass {pass_id}` is green. Complete AGENTS.md §6 steps 6–7 now: write "
                        f"docs/passes/{label(pass_id)}_REPORT.md (built / deviations with reasons / known gaps / "
                        "commands run / Explain-it answers), write docs/cursor-usage/<LABEL>.md, push the branch, "
                        "delete .cursor/ACTIVE_PASS, and stop."
                    )
                }
            )
        return

    tail = "\n".join(out.strip().splitlines()[-TAIL_LINES:])
    tail = mask(tail)[-MAX_CHARS:]
    log(root, {"pass": pass_id, "loop": loop_count, "result": "red", "exit": code, "seconds": elapsed})

    if loop_count >= MAX_LOOPS:
        emit(
            {
                "followup_message": (
                    f"`verify-pass --pass {pass_id}` is still failing after {MAX_LOOPS} automatic iterations. "
                    f"Stop changing code. Set .cursor/ACTIVE_PASS to `{pass_id} blocked`, then summarise for the human: "
                    "each remaining failure, what you tried, and your best hypothesis. Then stop."
                )
            }
        )
        return

    emit(
        {
            "followup_message": (
                f"Automatic verification (iteration {loop_count + 1}/{MAX_LOOPS}): "
                f"`python scripts/tasks.py verify-pass --pass {pass_id}` failed (exit {code}).\n"
                "Fix the failures below. Do NOT weaken, skip, xfail or delete tests. If a test itself is wrong, "
                f"set .cursor/ACTIVE_PASS to `{pass_id} blocked` and ask the human.\n\n```\n{tail}\n```"
            )
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - the hook must never break the editor
        emit({})
