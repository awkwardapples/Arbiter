"""P13-T1 and P13-T2: USL SQL is one COMPILE and fully qualified DQ statements."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SQL_PATH = ROOT / "zetaris" / "sql" / "03_usl.sql"
RULES_PATH = ROOT / "zetaris" / "dq_rules.yaml"
FQN = "lightning.metastore.arbiter.vendor_risk"
STMT_DELIM = re.compile(r"(?m)^\s*--\s*@@stmt\s*$")
CREATE_TABLE = re.compile(r"(?m)^CREATE TABLE ")


def _statements(text: str) -> list[str]:
    out: list[str] = []
    for part in STMT_DELIM.split(text):
        lines = [ln for ln in part.splitlines() if not re.match(r"^\s*--", ln)]
        stmt = "\n".join(lines).strip().rstrip(";")
        if stmt:
            out.append(stmt)
    return out


@pytest.mark.p13
def test_p13_t1_compile_is_one_statement_and_names_are_qualified() -> None:
    """P13-T1: one COMPILE with >= 10 CREATE TABLE lines; later commands use the USL name."""
    stmts = _statements(SQL_PATH.read_text(encoding="utf-8"))
    compile_stmts = [s for s in stmts if s.startswith("COMPILE USL")]
    assert len(compile_stmts) == 1
    assert len(CREATE_TABLE.findall(compile_stmts[0])) >= 10
    for stmt in stmts:
        head = stmt.split(None, 2)
        kind = " ".join(head[:2]) if head[:1] == ["UPDATE"] or head[:2] == ["RUN", "DQ"] else " ".join(head[:2])
        if stmt.startswith("ACTIVATE USL") or stmt.startswith("REGISTER DQ") or stmt.startswith("RUN DQ"):
            assert re.search(rf"{re.escape(FQN)}\.[A-Za-z_][A-Za-z0-9_]*", stmt), stmt
        elif stmt.startswith("UPDATE USL"):
            assert FQN in stmt, stmt
        else:
            assert kind  # namespace and COMPILE statements are the rest


@pytest.mark.p13
def test_p13_t2_register_dq_matches_yaml() -> None:
    """P13-T2: REGISTER DQ names and expressions come from dq_rules.yaml, fully qualified."""
    raw = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")) or {}
    expected = [
        f"REGISTER DQ {rule['id']} TABLE {FQN}.{rule['table']} AS {rule['expr']}"
        for rule in raw["rules"]
    ]
    actual = [s for s in _statements(SQL_PATH.read_text(encoding="utf-8")) if s.startswith("REGISTER DQ")]
    assert actual == expected
