"""P6-T1: README sections follow the pass order, and documented commands parse."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

import pytest

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]

# P17 retarget: the README order is P17 §3.2 (the same list as P17-T5 in test_claims.py).
H2 = [
    "Quick start",
    "Why it matters",
    "Track 3 mapping",
    "See it work",
    "How it works",
    "Zetaris USL",
    "Nemotron and Nightshift",
    "Evaluation",
    "Setup and usage",
    "Sponsor technology",
    "AI and model usage",
    "Data and licensing",
    "Third-party code and licences",
    "Limitations",
    "Responsible AI",
    "Pre-existing components",
    "Repository map",
]

_FENCE = re.compile(r"```(?:bash|sh|console|shell)\n(.*?)```", re.DOTALL)


def test_p6_t1_section_order() -> None:
    """P6-T1: H2 headings match the pass file, including the licences spelling."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    found = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert found == H2


def test_p6_t1_commands_parse() -> None:
    """P6-T1: every python run.py / tasks.py line in a shell fence is a real argparse command."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = _commands(text)
    assert commands, "README has no python run.py or tasks.py commands in shell fences"
    run_parser = _capture_parser(_run_main, ["serve"])
    tasks_parser = _capture_parser(_tasks_main, ["setup"])
    for kind, argv in commands:
        parser = run_parser if kind == "run.py" else tasks_parser
        try:
            parser.parse_args(argv)
        except SystemExit as exc:
            pytest.fail(f"{kind} {' '.join(argv)} did not parse ({exc})")


def _commands(text: str) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    for block in _FENCE.findall(text):
        pending = ""
        for raw in block.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                pending = ""
                continue
            if line.endswith("\\"):
                pending += line[:-1].strip() + " "
                continue
            line = pending + line
            pending = ""
            parsed = _python_invocation(line)
            if parsed is not None:
                found.append(parsed)
    return found


def _python_invocation(line: str) -> tuple[str, list[str]] | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None
    while parts and "=" in parts[0] and not parts[0].startswith("-"):
        parts = parts[1:]
    if len(parts) < 3 or parts[0] not in {"python", "python3"}:
        return None
    if parts[1] not in {"run.py", "scripts/tasks.py"}:
        return None
    return parts[1], parts[2:]


def _capture_parser(main, probe: list[str]) -> argparse.ArgumentParser:
    box: dict[str, argparse.ArgumentParser] = {}
    original = argparse.ArgumentParser.parse_args

    def wrapped(self: argparse.ArgumentParser, *args: object, **kwargs: object) -> object:
        del args, kwargs
        box["parser"] = self
        raise RuntimeError("captured")

    argparse.ArgumentParser.parse_args = wrapped  # type: ignore[method-assign]
    try:
        main(probe)
    except RuntimeError as exc:
        if str(exc) != "captured":
            raise
    finally:
        argparse.ArgumentParser.parse_args = original  # type: ignore[method-assign]
    return box["parser"]


def _run_main(argv: list[str]) -> None:
    import run

    run.main(argv)


def _tasks_main(argv: list[str]) -> None:
    import scripts.tasks as tasks

    tasks.main(argv)
