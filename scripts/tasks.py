#!/usr/bin/env python3
"""Cross-platform task runner (source of truth for CI and hooks)."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PASS_IDS = [
    *["0", "1a", "1b", "2a", "2b", "2c", "2d", "3", "4a", "4b", "5a", "5b", "6", "7"],
    *["13", "14a", "14b", "15", "16", "17"],  # Release 2 (docs/spec/release2)
    *["18a", "18b", "18c", "18d", "19", "20"],  # Release 3 (docs/spec/release3)
]


def _python() -> str:
    venv = ROOT / ".venv" / "bin" / "python"
    if venv.is_file():
        return str(venv)
    return sys.executable


def _run(cmd: list[str], *, quiet: bool = False) -> int:
    if quiet:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            if proc.stdout:
                print(proc.stdout, end="")
            if proc.stderr:
                print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode
    return subprocess.run(cmd, cwd=ROOT).returncode


def cmd_setup(_args: argparse.Namespace) -> int:
    py = _python()
    for req in ("requirements.txt", "requirements-dev.txt"):
        code = _run([py, "-m", "pip", "install", "-r", str(ROOT / req)])
        if code != 0:
            return code
    return 0


def cmd_lint(_args: argparse.Namespace) -> int:
    py = _python()
    if _run([py, "-m", "ruff", "check", "."]) != 0:
        return 1
    return _run([py, "-m", "ruff", "format", "--check", "."])


def cmd_test(args: argparse.Namespace) -> int:
    py = _python()
    expr = args.mark if args.mark else "not live"
    cmd = [py, "-m", "pytest", "-m", expr]
    if args.quiet:
        cmd.append("-q")
    return _run(cmd, quiet=args.quiet)


def _gate(pass_id: str) -> int:
    gate = ROOT / "scripts" / "gates" / f"p{pass_id}.py"
    if not gate.is_file():
        return 0
    spec = importlib.util.spec_from_file_location(f"gate_p{pass_id}", gate)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return int(mod.main())  # type: ignore[attr-defined]


def cmd_verify_pass(args: argparse.Namespace) -> int:
    pid = args.pass_id.lower()
    if pid not in PASS_IDS:
        print(f"unknown pass id: {args.pass_id}", file=sys.stderr)
        return 2
    quiet = args.quiet
    steps = [
        ("lint", lambda: cmd_lint(argparse.Namespace())),
        ("marker tests", lambda: cmd_test(argparse.Namespace(mark=f"p{pid} and not live", quiet=quiet))),
        ("regression", lambda: cmd_test(argparse.Namespace(mark="not live", quiet=quiet))),
        ("gate", lambda: _gate(pid)),
        ("secret-scan", lambda: cmd_secret_scan(argparse.Namespace(history=False))),
        ("hardcode-check", lambda: cmd_hardcode_check(argparse.Namespace())),
    ]
    for name, fn in steps:
        code = fn()
        if code == 5 and name == "marker tests":
            code = 0
        if code != 0:
            if not quiet:
                print(f"verify-pass: failed at {name}", file=sys.stderr)
            return code
    if not quiet:
        print(f"verify-pass p{pid}: ok")
    return 0


def cmd_verify(_args: argparse.Namespace) -> int:
    if cmd_lint(argparse.Namespace()) != 0:
        return 1
    if cmd_test(argparse.Namespace(mark="not live", quiet=False)) != 0:
        return 1
    if cmd_secret_scan(argparse.Namespace(history=False)) != 0:
        return 1
    if cmd_hardcode_check(argparse.Namespace()) != 0:
        return 1
    print("verify: ok")
    return 0


def cmd_e2e_sample(_args: argparse.Namespace) -> int:
    print("e2e-sample: not implemented until P6 (stub ok for P0 gate)")
    return 0


def cmd_secret_scan(args: argparse.Namespace) -> int:
    py = _python()
    cmd = [py, str(ROOT / "scripts" / "scan_secrets.py"), str(ROOT)]
    if getattr(args, "history", False):
        cmd.append("--history")
    return _run(cmd)


def cmd_trace_check(args: argparse.Namespace) -> int:
    py = _python()
    cmd = [py, str(ROOT / "scripts" / "check_trace.py"), *args.paths]
    if args.require_collaboration:
        cmd.append("--require-collaboration")
    if args.require_live:
        cmd.append("--require-live")
    return _run(cmd)


def cmd_hardcode_check(_args: argparse.Namespace) -> int:
    py = _python()
    return _run([py, str(ROOT / "scripts" / "check_hardcoding.py")])


WEB = ROOT / "web"
NODE_HINT = "The web console needs Node.js 20.19 or newer (https://nodejs.org); install it, then re-run."


def _npm() -> str | None:
    """The npm executable, or None (with a message) when Node is not installed."""
    if shutil.which("node") is None:
        print(NODE_HINT, file=sys.stderr)
        return None
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        print(NODE_HINT, file=sys.stderr)
    return npm


def _npm_run(script: str) -> int:
    npm = _npm()
    if npm is None:
        return 1
    if not (WEB / "node_modules").is_dir():
        code = subprocess.run([npm, "ci"], cwd=WEB).returncode
        if code != 0:
            return code
    return subprocess.run([npm, "run", script], cwd=WEB).returncode


def cmd_web_build(_args: argparse.Namespace) -> int:
    """Build the web console into web/dist (commit the result)."""
    return _npm_run("build")


def cmd_web_check(_args: argparse.Namespace) -> int:
    """Lint, typecheck, test and build the web console."""
    return _npm_run("check")


def main(argv: list[str] | None = None) -> int:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    parser = argparse.ArgumentParser(prog="tasks.py")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("lint").set_defaults(func=cmd_lint)
    t = sub.add_parser("test")
    t.add_argument("--mark", default="not live")
    t.add_argument("--quiet", action="store_true")
    t.set_defaults(func=cmd_test)

    vp = sub.add_parser("verify-pass")
    vp.add_argument("--pass", dest="pass_id", required=True)
    vp.add_argument("--quiet", action="store_true")
    vp.set_defaults(func=cmd_verify_pass)

    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("e2e-sample").set_defaults(func=cmd_e2e_sample)

    ss = sub.add_parser("secret-scan")
    ss.add_argument("--history", action="store_true")
    ss.set_defaults(func=cmd_secret_scan)

    tc = sub.add_parser("trace-check")
    tc.add_argument("paths", nargs="*", default=[str(ROOT / "logs")])
    tc.add_argument("--require-collaboration", action="store_true")
    tc.add_argument("--require-live", action="store_true")
    tc.set_defaults(func=cmd_trace_check)

    sub.add_parser("hardcode-check").set_defaults(func=cmd_hardcode_check)
    sub.add_parser("web-build").set_defaults(func=cmd_web_build)
    sub.add_parser("web-check").set_defaults(func=cmd_web_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
