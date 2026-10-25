"""P18-C gate: words mirrored from app/labels.py, npm run check and, when possible, the smoke."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = ROOT / "web" / "src" / "features" / "case" / "words.ts"
_ENTRY = re.compile(r'^\s+([A-Za-z_]+): ("(?:[^"\\]|\\.)*"),$')
_BLOCK = re.compile(r"// <labels:(\w+)>[^\n]*\n(.*?)// </labels:\1>", re.S)


def _p18b():
    """The 18b gate. npm run check, dist freshness and the smoke are shared, so reuse it."""
    spec = importlib.util.spec_from_file_location("gate_p18b", ROOT / "scripts" / "gates" / "p18b.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mirrored_blocks(text: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    for name, body in _BLOCK.findall(text):
        entries: dict[str, str] = {}
        for line in body.splitlines():
            match = _ENTRY.match(line)
            if match:
                entries[match.group(1)] = json.loads(match.group(2))
        blocks[name] = entries
    return blocks


def expected_blocks() -> dict[str, dict[str, str]]:
    sys.path.insert(0, str(ROOT))
    from app import labels

    return {
        "outcomes": {code: meaning for code, (_label, meaning) in labels._OUTCOMES.items()},
        "reasons": dict(labels._REASONS),
        "systems": dict(labels._SYSTEMS),
        "states": dict(labels._STATE_WORDS),
    }


def check_words() -> int:
    found = mirrored_blocks(WORDS.read_text(encoding="utf-8"))
    problems = []
    for name, want in expected_blocks().items():
        have = found.get(name)
        if have is None:
            problems.append(f"block <labels:{name}> is missing")
        elif have != want:
            for key in sorted(set(want) | set(have)):
                if want.get(key) != have.get(key):
                    want_text, have_text = want.get(key), have.get(key)
                    problems.append(f"{name}.{key}: app/labels.py {want_text!r}, words.ts {have_text!r}")
    for problem in problems:
        print(f"web/src/features/case/words.ts drifted from app/labels.py: {problem}", file=sys.stderr)
    return 1 if problems else 0


def main() -> int:
    if check_words() != 0:
        return 1
    gate = _p18b()
    for step in (gate._npm_check, gate._dist_fresh, gate._smoke):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
