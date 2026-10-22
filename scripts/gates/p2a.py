"""Gate for lane P2-A: vendored Meterless files are intact and the H-MEM port passes 13/13."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "meterless"
EXPECTED_CASES = 13


def _fail(msg: str) -> int:
    print(f"gate p2a: FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    for name in ("hmem_vectors.json", "LICENSE", "NOTICE.md"):
        if not (VENDOR / name).is_file():
            return _fail(f"missing vendor/meterless/{name}")

    notice = (VENDOR / "NOTICE.md").read_text(encoding="utf-8")
    for needle in (
        "https://github.com/Meterless/Meterless",
        "Apache License 2.0",
        "ported to Python by Arbiter",
    ):
        if needle not in notice:
            return _fail(f"NOTICE.md does not mention {needle!r}")
    if "1742dec56a66e58eef9dda2d2b865823758ca8cd" not in notice:
        return _fail("NOTICE.md does not record the upstream commit sha")
    for name in ("hmem_vectors.json", "LICENSE"):
        digest = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
        if digest not in notice:
            return _fail(f"sha256 of {name} ({digest}) is not recorded in NOTICE.md")
    if "Apache License" not in (VENDOR / "LICENSE").read_text(encoding="utf-8"):
        return _fail("vendor/meterless/LICENSE is not the Apache licence text")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.conformance.test_hmem_conformance import format_scorecard, run_all

    results = run_all()
    passed = sum(1 for r in results if r[3] is None)
    if len(results) != EXPECTED_CASES or passed != EXPECTED_CASES:
        print(format_scorecard(results), file=sys.stderr)
        return _fail(f"conformance {passed}/{len(results)}, expected {EXPECTED_CASES}/{EXPECTED_CASES}")
    print(f"gate p2a: ok (H-MEM conformance {passed}/{len(results)} PASS, vendor files verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
