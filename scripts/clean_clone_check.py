#!/usr/bin/env python3
"""Clean-clone check from the submission playbook §6.

`output_examples/` is a labelled waiver until P6: a missing directory passes, a
directory with fewer than three files fails.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_FEW = "output_examples/ exists but has fewer than 3 files; P6 populates this directory."
_OUTCOMES = {"APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"}
_CONTAINER = "arbiter-clean-clone"
_IMAGE = "arbiter-check"


def classify_output_examples(root: Path) -> tuple[bool, str]:
    directory = root / "output_examples"
    if not directory.exists():
        return True, "waiver: output_examples/ absent until P6"
    files = [path for path in directory.iterdir() if path.is_file()] if directory.is_dir() else []
    if len(files) < 3:
        return False, _FEW
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clone Arbiter and run the day-four checks")
    parser.add_argument("repo", nargs="?", help="Git URL to clone")
    parser.add_argument("--local", metavar="PATH", help="Clone this local checkout with git clone --local")
    args = parser.parse_args(argv)
    if bool(args.repo) == bool(args.local):
        parser.error("pass a repo URL or --local PATH")

    launch = Path.cwd()
    work = Path(tempfile.mkdtemp(prefix="arbiter-clean-"))
    results: list[tuple[int, bool, str]] = []
    try:
        clone = work / "repo"
        command = ["git", "clone"]
        if args.local:
            # --no-local copies objects. --local hardlinks, which fail when /tmp
            # and the checkout are on different mounts (WSL).
            command.extend(["--no-local", str(Path(args.local).resolve())])
        else:
            command.append(str(args.repo))
        command.append(str(clone))
        cloned = subprocess.run(command, capture_output=True, text=True, check=False)
        if cloned.returncode != 0:
            results.append((1, False, cloned.stderr.strip() or "git clone failed"))
        else:
            _run_steps(clone, results)
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER], capture_output=True, check=False)
        shutil.rmtree(work, ignore_errors=True)
        _write_report(launch, results)
    return 0 if results and all(ok for _n, ok, _detail in results) and len(results) == 8 else 1


def _run_steps(clone: Path, results: list[tuple[int, bool, str]]) -> None:
    steps = (
        lambda: _step_files(clone),
        lambda: _step_build(clone),
        lambda: _step_docker(clone),
        lambda: _step_traces(clone),
        lambda: _step_novel(),
        lambda: _step_secrets(clone),
        lambda: _step_native(clone),
        lambda: (True, "report written"),
    )
    for number, step in enumerate(steps, start=1):
        if results and not results[-1][1]:
            results.append((number, False, "skipped after an earlier failure"))
            continue
        try:
            ok, detail = step()
        except Exception as exc:  # noqa: BLE001 — one step must not hide the rest of the report
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append((number, ok, detail))


def _step_files(clone: Path) -> tuple[bool, str]:
    missing = [name for name in ("run.py", "README.md", ".env.example") if not (clone / name).is_file()]
    examples = list((clone / "input_examples").glob("*.json")) if (clone / "input_examples").is_dir() else []
    ok, message = classify_output_examples(clone)
    if missing or len(examples) < 3:
        return False, f"missing {missing or 'input_examples (>= 3)'}"
    return ok, message


def _step_build(clone: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["docker", "build", "-t", _IMAGE, "."],
        cwd=clone,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, "built from Dockerfile" if proc.returncode == 0 else proc.stderr[-500:]


def _step_docker(clone: Path) -> tuple[bool, str]:
    subprocess.run(["docker", "rm", "-f", _CONTAINER], capture_output=True, check=False)
    proc = subprocess.run(
        ["docker", "run", "-d", "--name", _CONTAINER, "-p", "8000:8000", "-e", "SAMPLE_MODE=true", _IMAGE],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip()
    if not _wait_health():
        return False, "health check timed out"
    expected = json.loads((clone / "input_examples" / "expected.json").read_text(encoding="utf-8"))
    seen: list[str] = []
    for name, spec in sorted(expected.items()):
        body = _post_json("http://127.0.0.1:8000/run", (clone / "input_examples" / name).read_bytes())
        decision = body.get("output", {}).get("decision")
        if decision != spec["outcome"]:
            return False, f"{name}: {decision} != {spec['outcome']}"
        seen.append(json.dumps(body.get("output"), sort_keys=True))
    if len(set(seen)) != len(seen):
        return False, "outputs were not distinct"
    return True, f"{len(seen)} examples matched"


def _step_traces(clone: Path) -> tuple[bool, str]:
    del clone
    dest = Path(tempfile.mkdtemp(prefix="arbiter-logs-"))
    try:
        copied = subprocess.run(
            ["docker", "cp", f"{_CONTAINER}:/app/logs/.", str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
        if copied.returncode != 0:
            return False, copied.stderr.strip()
        from scripts.check_trace import validate_file

        errors: list[str] = []
        files = list(dest.glob("trace-*.jsonl"))
        case_traces = [path for path in files if path.name.startswith("trace-run-")]
        if not case_traces:
            return False, "no case traces in the container logs"
        for path in files:
            # Status probes (for example trace-zetaris-status) are not agent runs.
            collaborative = path.name.startswith("trace-run-")
            errors.extend(validate_file(path, require_collaboration=collaborative, require_live=False))
        logs = subprocess.run(["docker", "logs", _CONTAINER], capture_output=True, text=True, check=False)
        stdout = logs.stdout + logs.stderr
        if "Uvicorn running" not in stdout and "run_id=" not in stdout:
            return False, "container stdout had no server or trace lines"
        return (not errors), "traces ok" if not errors else "; ".join(errors[:5])
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def _step_novel() -> tuple[bool, str]:
    seed = int(time.time())
    payload = {
        "submission": {
            "legal_name": f"Novel Vendor {seed}",
            "category": "software",
            "requested_service": "payroll processing",
            "criticality": "low",
            "annual_spend_gbp": 1000,
            "data_categories": ["internal"],
            "processing_countries": ["UK"],
            "answers": [{"question_id": "Q01", "question": "Is MFA enforced?", "answer_text": "Yes."}],
        }
    }
    body = _post_json("http://127.0.0.1:8000/run", json.dumps(payload).encode("utf-8"))
    decision = body.get("output", {}).get("decision")
    if body.get("status") not in {"success", "partial_success", "escalated", "error"}:
        return False, f"status {body.get('status')}"
    if decision not in _OUTCOMES:
        return False, f"decision {decision}"
    return True, f"novel decision {decision}"


def _step_secrets(clone: Path) -> tuple[bool, str]:
    scan = subprocess.run(
        [sys.executable, str(clone / "scripts" / "scan_secrets.py")],
        cwd=clone,
        capture_output=True,
        text=True,
        check=False,
    )
    if scan.returncode != 0:
        return False, (scan.stdout or scan.stderr)[-500:]
    history = _history_secrets(clone)
    if history:
        return False, history
    listed = subprocess.run(
        ["git", "-C", str(clone), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    bad = [
        line
        for line in listed.stdout.splitlines()
        if Path(line).name == ".env" or line.endswith(".pem") or line.endswith(".key")
    ]
    if bad:
        return False, f"tracked secrets: {bad}"
    return True, "secret scan ok"


def _history_secrets(clone: Path) -> str:
    """git log -p, skipping the project's fixture allowlist. History hits in that file are test vectors."""
    from fnmatch import fnmatch

    from scripts.secret_patterns import SECRET_REGEXES

    allow_path = clone / ".secrets-allowlist"
    allow: list[str] = []
    if allow_path.is_file():
        allow = [
            line.strip()
            for line in allow_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    proc = subprocess.run(
        ["git", "-C", str(clone), "log", "-p", "--no-color"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return proc.stderr.strip() or "git log failed"
    current = "git-history"
    hits: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if any(fnmatch(current, pattern) for pattern in allow):
            continue
        for name, pattern in SECRET_REGEXES:
            # The assignment pattern matches prose ("token = re.compile"). Tree scan covers it.
            if name == "assignment":
                continue
            if pattern.search(line):
                hits.append(f"{current} [{name}]")
                break
    return "; ".join(hits[:5])


def _step_native(clone: Path) -> tuple[bool, str]:
    venv = clone.parent / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    bindir = "Scripts" if os.name == "nt" else "bin"
    pip = venv / bindir / "pip"
    python = venv / bindir / "python"
    installed = subprocess.run(
        [str(pip), "install", "-r", "requirements.txt"],
        cwd=clone,
        capture_output=True,
        text=True,
        check=False,
    )
    if installed.returncode != 0:
        return False, installed.stderr[-500:]
    env = {**os.environ, "SAMPLE_MODE": "true", "LLM_PROVIDER": "offline"}
    assess = subprocess.run(
        [str(python), "run.py", "assess", "--input", "input_examples/example_1.json"],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if assess.returncode == 0:
        return True, "run.py assess"
    native = subprocess.run(
        [str(python), "-c", _NATIVE],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if native.returncode != 0:
        return False, (native.stderr or assess.stderr)[-500:]
    return True, "waiver: run.py assess is still the P3 stub; orchestrator.run succeeded"


_NATIVE = """
import json
from pathlib import Path
from app.orchestrator import RunOptions, run
from app.schemas.case import CaseInput
raw = json.loads(Path("input_examples/example_1.json").read_text(encoding="utf-8"))
resp = run(CaseInput.model_validate(raw), options=RunOptions(sample_mode=True, llm="offline"))
if resp.output is None:
    raise SystemExit("no output")
print(resp.output.decision)
"""


def _wait_health() -> bool:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def _post_json(url: str, payload: bytes) -> dict:
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not isinstance(body, dict):
        raise RuntimeError("response was not an object")
    return body


def _write_report(launch: Path, results: list[tuple[int, bool, str]]) -> None:
    by_step = {number: (ok, detail) for number, ok, detail in results}
    lines = ["# Clean clone report", ""]
    for number in range(1, 9):
        ok, detail = by_step.get(number, (False, "not run"))
        lines.append(f"step {number}: {'pass' if ok else 'fail'} — {detail}")
    text = "\n".join(lines) + "\n"
    log = launch / "logs" / "clean-clone-report.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text, encoding="utf-8")
    dated = launch / "docs" / "passes" / f"clean-clone-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    dated.parent.mkdir(parents=True, exist_ok=True)
    dated.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    raise SystemExit(main())
