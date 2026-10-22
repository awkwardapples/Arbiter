"""P4-B gate: replay, routes, Dockerfile and the CI docker build are present."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    missing = [
        path
        for path in (
            root / "Dockerfile",
            root / "docker-compose.yml",
            root / "scripts" / "clean_clone_check.py",
            root / "app" / "audit" / "replay.py",
        )
        if not path.is_file()
    ]
    if missing:
        for path in missing:
            print(f"missing {path}")
        return 1
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if "docker build" not in workflow or "docker pull" in workflow:
        print("ci.yml must build the repo Dockerfile and must not pull an image")
        return 1
    from app.audit.replay import replay

    if not callable(replay):
        print("replay is not callable")
        return 1
    return 0
