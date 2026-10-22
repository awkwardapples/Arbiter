#!/usr/bin/env python3
"""Cursor `beforeShellExecution` hook: block commands that could leak secrets or damage sponsor setups.

stdin  : JSON with at least {"command": "...", "cwd": "..."}
stdout : {"permission": "allow"|"deny"|"ask", "user_message": "...", "agent_message": "..."}
Never raises; on any internal error it allows (the agent's own rules still apply).
VERIFY on Day 0 that your Cursor version supports this hook and these output fields
(see docs/spec/05_RUNBOOK.md §3.5). If not, remove the entry from .cursor/hooks.json.
"""

from __future__ import annotations

import json
import re
import sys

ENV_FILE = r"\.env(?:\.(?!example\b)[\w.-]+)?(?=$|[\s'\";|&)])"  # .env, .env.local … but not .env.example
SECRET_VARS = r"(ZETARIS_API_KEY|ZETARIS_PASSWORD|METERLESS_RUNTIME_TOKEN|NVIDIA_API_KEY|ARBITER_SIGNING_KEY|MODEL_API_KEY)"
DENY = [
    (
        r"(^|[\s;&|(])(cat|type|more|less|head|tail|bat|nl|strings|grep|rg|sed|awk|Get-Content|gc|Select-String|sls)\b[^|;&]*"
        + ENV_FILE,
        "Reading .env files would expose secrets.",
    ),
    (r"(^|[;&|]\s*)\s*(printenv|env|set|export)\s*($|[|>])", "Dumping the environment would expose secrets."),
    (r"(^|[;&|]\s*)\s*printenv\s+\w+", "Printing an environment variable is not allowed; secrets may leak."),
    (r"(Get-ChildItem|gci|dir|ls)\s+env:", "Dumping the environment would expose secrets."),
    (
        r"(python[0-9.]*|py)(\s+-\d)?\s+-c\b.*os\.environ(?!\.get\(\s*['\"](PORT|LOG_LEVEL|SAMPLE_MODE)['\"])",
        "Reading environment values from inline Python is not allowed.",
    ),
    (
        r"(echo|print|Write-Output|Write-Host)\s+[^|;&]*\$\{?(?:env:)?" + SECRET_VARS,
        "Echoing a secret variable is not allowed.",
    ),
    (r":8889\b", "Port 8889 on the local Zetaris instance must never be called."),
    (r"git\s+push\s+[^|;&]*(--force|-f)(\s|$)", "Force-push is not allowed; ask the human."),
    (r"git\s+add\s+[^|;&]*" + ENV_FILE, "Never stage .env files."),
    (
        r"(^|\s)rm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+(/|~|\.|\./|/\*|\*)(\s|$)",
        "Destructive delete blocked.",
    ),
]
ASK = [
    (
        r"docker\s+compose\s+[^|;&]*down[^|;&]*(-v|--volumes)",
        "This deletes Docker volumes (Zetaris data). Confirm?",
    ),
    (r"docker\s+(system|volume)\s+prune", "This prunes Docker data. Confirm?"),
    (r"git\s+(reset\s+--hard|clean\s+-[a-z]*f)", "This discards work. Confirm?"),
    (
        r"zetaris\s+onboard(?![^|;&]*--dry-run)",
        "This creates objects in Zetaris. Confirm you reviewed the dry run?",
    ),
    (
        r"onboard\.py(?![^|;&]*--dry-run)",
        "This creates objects in Zetaris. Confirm you reviewed the dry run?",
    ),
]


def respond(permission: str, user: str, agent: str) -> dict:
    # Emit both spellings: Cursor versions differ (snake_case vs camelCase). Verify on Day 0.
    return {
        "permission": permission,
        "user_message": user,
        "agent_message": agent,
        "userMessage": user,
        "agentMessage": agent,
    }


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    command = str(payload.get("command", ""))
    for pattern, reason in DENY:
        if re.search(pattern, command, flags=re.IGNORECASE):
            out = respond(
                "deny",
                f"Blocked by shell_guard: {reason}",
                f"Command blocked by project hook: {reason} Find another way or ask the human.",
            )
            sys.stdout.write(json.dumps(out))
            return
    for pattern, reason in ASK:
        if re.search(pattern, command, flags=re.IGNORECASE):
            out = respond("ask", reason, "Waiting for human confirmation.")
            sys.stdout.write(json.dumps(out))
            return
    sys.stdout.write(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        sys.stdout.write(json.dumps({"permission": "allow"}))
