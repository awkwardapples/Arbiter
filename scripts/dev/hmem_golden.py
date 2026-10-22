"""Golden check: Python `embed()` against the Meterless TypeScript reference.

Needs Node (`npx tsx`) and a Meterless clone (`METERLESS_DIR`, default `~/meterless`).
Usage: python scripts/dev/hmem_golden.py   (exit 0 = match, 1 = mismatch, 3 = unavailable)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOLERANCE = 1e-12


def golden_strings() -> list[str]:
    base = [
        "",
        "a",
        "hello world",
        "We deploy the API with Docker on Mondays",
        "prefer short bullet answers",
        "precedent control c05 mitigation bridge letter tier t2 category saas",
        "The deadline is March 14, not March 4.",
        "café naïve résumé",
        "emoji \U0001f600 inside text",
        "tabs\tand\nnewlines\r\nmixed",
        "BOM\ufeffjoined",
        "x" * 300,
        "numbers 123 4.56 7e8",
        "UPPER lower MiXeD",
        "punctuation!!! ??? ... ---",
    ]
    words = ["vendor", "risk", "soc2", "iso27001", "breach", "notify", "72h", "dpa", "kev", "cve"]
    while len(base) < 50:
        i = len(base)
        base.append(" ".join(words[(i * k) % len(words)] for k in range(1, 2 + i % 7)))
    return base


def unavailable_reason() -> str | None:
    if shutil.which("node") is None:
        return "node is not on PATH"
    if shutil.which("npx") is None:
        return "npx is not on PATH"
    ref = reference_embeddings_path()
    if not ref.is_file():
        return f"Meterless reference not found at {ref}"
    return None


def reference_embeddings_path() -> Path:
    base = Path(os.environ.get("METERLESS_DIR", Path.home() / "meterless")).expanduser()
    return base / "engines" / "hmem" / "reference" / "src" / "embeddings.ts"


def run_reference(strings: list[str]) -> list[list[float]]:
    script = (
        f"import {{ embed }} from {json.dumps(reference_embeddings_path().as_posix())};\n"
        f"const inputs: string[] = {json.dumps(strings)};\n"
        "process.stdout.write(JSON.stringify(inputs.map((s) => embed(s))));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "golden.ts"
        path.write_text(script, encoding="utf-8")
        out = subprocess.run(
            ["npx", "--yes", "tsx", str(path)], capture_output=True, text=True, timeout=180, check=True
        )
    return json.loads(out.stdout)


def compare(strings: list[str]) -> list[str]:
    sys.path.insert(0, str(ROOT))
    from app.memory.hmem.embeddings import embed

    problems = []
    for s, ref in zip(strings, run_reference(strings), strict=True):
        ours = embed(s)
        worst = max((abs(a - b) for a, b in zip(ours, ref, strict=True)), default=0.0)
        if len(ours) != len(ref) or worst > TOLERANCE:
            problems.append(f"{s[:40]!r}: max abs diff {worst:.3e}")
    return problems


def main() -> int:
    reason = unavailable_reason()
    if reason:
        print(f"hmem golden: skipped ({reason})")
        return 3
    strings = golden_strings()
    problems = compare(strings)
    for p in problems:
        print(f"hmem golden: MISMATCH {p}")
    print(f"hmem golden: {len(strings) - len(problems)}/{len(strings)} match to {TOLERANCE:g}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
