"""P17-T9: `tasks.py verify` reaches secret-scan without crashing on a missing --history flag."""

from __future__ import annotations

import argparse

import pytest

import scripts.tasks as tasks

pytestmark = pytest.mark.p17


def test_p17_t9_verify_runs_secret_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """P17-T9: cmd_verify calls secret-scan without --history and finishes."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> int:
        calls.append([str(part) for part in cmd])
        return 0

    monkeypatch.setattr(tasks, "_run", fake_run)
    monkeypatch.setattr(tasks, "cmd_lint", lambda _args: 0)
    monkeypatch.setattr(tasks, "cmd_test", lambda _args: 0)
    assert tasks.cmd_verify(argparse.Namespace()) == 0
    scans = [cmd for cmd in calls if any(part.endswith("scan_secrets.py") for part in cmd)]
    assert len(scans) == 1
    assert "--history" not in scans[0]


def test_p17_t9_secret_scan_tolerates_bare_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """P17-T9: cmd_secret_scan treats a Namespace without history as history=False."""
    monkeypatch.setattr(tasks, "_run", lambda cmd, **_kwargs: 0)
    assert tasks.cmd_secret_scan(argparse.Namespace()) == 0
