"""Zetaris onboarding runner (split on -- @@stmt only)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml

from app.config import Settings, get_settings, mask_secrets
from app.data.registry import load_registry
from app.data.zetaris import ZetarisBackend
from app.tracing import Tracer

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = Path(__file__).resolve().parent / "sql"
SOURCES = Path(__file__).resolve().parent / "sources.yaml"
STMT_DELIM = re.compile(r"^\s*--\s*@@stmt\s*$", re.MULTILINE)


def load_sources() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or {}
    return dict(raw.get("rest_tables") or {})


def rest_url(table_key: str, settings: Settings) -> str:
    spec = load_sources()[table_key]
    if settings.ZETARIS_SOURCE_MODE == "simulator":
        base = settings.SOURCES_PUBLIC_BASE.rstrip("/")
        return f"{base}{spec['simulator_path']}"
    base = settings.GITHUB_RAW_BASE.rstrip("/")
    return f"{base}/{spec['raw_file']}"


def kev_rest_url(settings: Settings) -> str:
    """KEV REST endpoint. Zetaris always reads the configured CISA catalogue URL."""
    return settings.KEV_URL


def substitute_placeholders(sql: str, settings: Settings) -> str:
    out = sql.replace("{KEV_URL}", kev_rest_url(settings))
    for key in load_sources():
        out = out.replace(f"{{URL:{key}}}", rest_url(key, settings))
    return out


def strip_comments(sql: str) -> str:
    lines: list[str] = []
    for line in sql.splitlines():
        if STMT_DELIM.match(line):
            continue
        if re.match(r"^\s*--", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def load_statements(*, only: Literal["01", "02", "03"] | None = None) -> list[tuple[str, str]]:
    name_map = {"01": "01_sources.sql", "02": "02_kev.sql", "03": "03_usl.sql"}
    files = [name_map[only]] if only else list(name_map.values())
    out: list[tuple[str, str]] = []
    for fname in files:
        path = SQL_DIR / fname
        text = path.read_text(encoding="utf-8")
        parts = STMT_DELIM.split(text)
        for idx, part in enumerate(parts):
            stmt = strip_comments(part)
            if not stmt:
                continue
            out.append((f"{fname}#{idx}", stmt))
    return out


def _already_exists_message(msg: str) -> bool:
    low = msg.lower()
    return "already exists" in low or "duplicate" in low


def run_onboard(
    settings: Settings,
    *,
    dry_run: bool = False,
    skip_exists: bool = False,
    only: Literal["01", "02", "03"] | None = None,
    yes: bool = False,
) -> int:
    if not dry_run and not yes:
        print("Refusing to run destructive onboarding without --yes (use --dry-run to preview).")
        return 2
    statements = load_statements(only=only)
    log_path = ROOT / "logs" / f"zetaris-onboard-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tracer = Tracer("zetaris-onboard", mode=settings.mode(), log_dir=str(ROOT / "logs"))
    backend = ZetarisBackend(settings, load_registry(), tracer, agent_name="onboard")
    for label, stmt in statements:
        rendered = substitute_placeholders(stmt, settings)
        print(f"-- {label}")
        print(mask_secrets(rendered))
        print()
        if dry_run:
            continue
        try:
            backend.execute_sql(rendered, purpose=f"onboard:{label}")
            with log_path.open("a", encoding="utf-8") as lf:
                lf.write(json.dumps({"label": label, "status": "ok"}) + "\n")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if skip_exists and _already_exists_message(msg):
                print(f"skip (already exists): {label}")
                continue
            print(f"onboard failed at {label}: {type(exc).__name__}: {mask_secrets(msg)}")
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Zetaris onboarding")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-exists", action="store_true")
    parser.add_argument("--only", choices=["01", "02", "03"])
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    return run_onboard(
        get_settings(),
        dry_run=args.dry_run,
        skip_exists=args.skip_exists,
        only=args.only,
        yes=args.yes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
