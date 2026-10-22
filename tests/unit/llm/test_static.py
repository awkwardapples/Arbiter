"""P2-T17: no model SDK imports anywhere; raw chat endpoints only inside app/llm/providers/."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.p2b

ROOT = Path(__file__).resolve().parents[3]
SCAN = ["app", "ui", "sources", "scripts", "eval", "zetaris", "data/generator", "run.py"]
BANNED_MODULES = {
    "openai",
    "anthropic",
    "litellm",
    "cohere",
    "mistralai",
    "groq",
    "langchain",
    "langchain_openai",
    "google.generativeai",
    "vertexai",
}
PROVIDERS = ROOT / "app" / "llm" / "providers"
CHAT_PATH = "chat/" + "completions"


def _py_files() -> list[Path]:
    files: list[Path] = []
    for entry in SCAN:
        path = ROOT / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _imported(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "__import__" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                names.add(arg.value)
    return names


def test_p2_t17_scan_covers_the_llm_layer() -> None:
    files = _py_files()
    assert ROOT / "app" / "llm" / "generator.py" in files
    assert PROVIDERS / "meterless.py" in files


def test_p2_t17_no_model_sdk_imports() -> None:
    offenders: list[str] = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported(tree):
            if any(name == banned or name.startswith(banned + ".") for banned in BANNED_MODULES):
                offenders.append(f"{path.relative_to(ROOT)}: {name}")
    assert offenders == []


def test_p2_t17_chat_endpoint_only_in_providers() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in _py_files()
        if CHAT_PATH in path.read_text(encoding="utf-8") and PROVIDERS not in path.parents
    ]
    assert offenders == []


def test_p2_t17_no_sdk_in_requirements() -> None:
    for req in ROOT.glob("requirements*.txt"):
        for line in req.read_text(encoding="utf-8").splitlines():
            pkg = line.split("==")[0].split("[")[0].strip().lower()
            assert pkg not in BANNED_MODULES, f"{req.name}: {pkg}"
