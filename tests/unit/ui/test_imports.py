"""P5-T10: the reviewer console imports nothing from the core package."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5a

UI_ROOT = Path(__file__).resolve().parents[3] / "ui"
_IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+app(?:\.|\s|$)", re.MULTILINE)


def _imported_modules(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
    return found


def test_p5_t10_ui_imports_nothing_from_app() -> None:
    """P5-T10: any `import app` / `from app.` in ui/ is a boundary violation."""
    violations: list[str] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(UI_ROOT.parent)
        if _IMPORT_LINE.search(source):
            violations.append(f"{rel}: source contains an app import")
        tree = ast.parse(source, filename=str(path))
        for mod in _imported_modules(tree):
            if mod == "app" or mod.startswith("app."):
                violations.append(f"{rel}: imports {mod}")
    assert not violations, "ui/ must not import the core package:\n" + "\n".join(sorted(set(violations)))
