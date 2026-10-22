"""P5-T10: UI import boundary — app.schemas only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5a

UI_ROOT = Path(__file__).resolve().parents[3] / "ui"
FORBIDDEN_PREFIXES = (
    "app.policy",
    "app.orchestrator",
    "app.store",
    "app.audit",
    "app.agents",
    "app.data",
    "app.llm",
    "app.memory",
    "app.actions",
    "app.api",
)


def _module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom):
        return node.module
    if isinstance(node, ast.Import):
        for alias in node.names:
            return alias.name
    return None


def test_p5_t10_ui_imports_only_app_schemas() -> None:
    """P5-T10: static import graph for ui/."""
    violations: list[str] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            mod = _module_name(node)
            if not mod or not mod.startswith("app"):
                continue
            if mod.startswith("app.schemas"):
                continue
            if mod == "app":
                violations.append(f"{path.name}: import app (must use app.schemas)")
                continue
            violations.append(f"{path.relative_to(UI_ROOT.parent)}: {mod}")
            for prefix in FORBIDDEN_PREFIXES:
                if mod == prefix or mod.startswith(prefix + "."):
                    violations.append(f"{path.name}: forbidden {mod}")
    assert not violations, "Forbidden imports:\n" + "\n".join(sorted(set(violations)))
