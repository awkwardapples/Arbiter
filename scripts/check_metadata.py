#!/usr/bin/env python3
"""Validate metadata.json shape, file paths, track, and runtime model ids."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_STRINGS = (
    "schema",
    "project_name",
    "description",
    "track",
    "repository",
    "demo_video",
    "slide_deck",
    "sample_mode",
    "licence",
)
_LISTS = ("agents", "models", "pre_existing_components")
_OBJECTS = ("team", "entry_points", "sponsor_technologies", "data")
_TRACK = "Reasoning Architecture"


def validate(root: Path) -> list[str]:
    meta_path = root / "metadata.json"
    if not meta_path.is_file():
        return ["metadata.json is missing"]
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"metadata.json is not JSON: {exc}"]
    if not isinstance(meta, dict):
        return ["metadata.json is not an object"]

    errors: list[str] = []
    for key in _STRINGS:
        if key not in meta:
            errors.append(f"missing {key}")
        elif not isinstance(meta[key], str):
            errors.append(f"{key} has the wrong type")
    for key in _LISTS:
        if key not in meta:
            errors.append(f"missing {key}")
        elif not isinstance(meta[key], list):
            errors.append(f"{key} has the wrong type")
    for key in _OBJECTS:
        if key not in meta:
            errors.append(f"missing {key}")
        elif not isinstance(meta[key], dict):
            errors.append(f"{key} has the wrong type")

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    if meta.get("track") != _TRACK:
        errors.append(f"track must be {_TRACK}")
    elif _TRACK not in readme:
        errors.append("track is not in the README")

    for rel in _cited_paths(meta):
        if not (root / rel).exists():
            errors.append(f"missing file {rel}")

    models = meta.get("models")
    if isinstance(models, list):
        if not models:
            errors.append("models is empty")
        elif _traces_attribute_a_model(root):
            corpus = _trace_text(root)
            for model in models:
                if not isinstance(model, str) or model not in corpus:
                    errors.append(f"model id {model} is not in logs/examples")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser_root = ROOT
    if argv:
        parser_root = Path(argv[0])
    errors = validate(parser_root)
    if errors:
        for item in errors:
            print(item)
        return 1
    print("metadata: ok")
    return 0


def _trace_text(root: Path) -> str:
    directory = root / "logs" / "examples"
    if not directory.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(directory.glob("trace-*.jsonl")):
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def _traces_attribute_a_model(root: Path) -> bool:
    """True when any example trace names a provider other than offline or a model id.

    An offline run records provider=offline and model=null, so the configured
    routes are absent. That corpus does not satisfy the live assertion.
    """
    directory = root / "logs" / "examples"
    if not directory.is_dir():
        return False
    for path in sorted(directory.glob("trace-*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            provider = item.get("provider")
            if isinstance(provider, str) and provider not in ("", "offline"):
                return True
            model = item.get("model")
            if isinstance(model, str) and model.strip():
                return True
    return False


def _cited_paths(meta: dict) -> list[str]:
    found: list[str] = []
    sponsors = meta.get("sponsor_technologies")
    if not isinstance(sponsors, dict):
        return found
    for block in sponsors.values():
        if not isinstance(block, dict):
            continue
        for key in ("files", "evidence"):
            values = block.get(key)
            if not isinstance(values, list):
                continue
            for item in values:
                if isinstance(item, str) and item.strip():
                    found.append(item.strip().rstrip("/"))
    return found


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
