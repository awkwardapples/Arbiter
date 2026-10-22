"""Pass 2d gate: guard assets and domain eval size."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    required = [
        root / "vendor/meterless/scout_adversarial.jsonl",
        root / "vendor/meterless/scout_thresholds.yaml",
        root / "data/evals/injection_domain.jsonl",
    ]
    for path in required:
        if not path.is_file():
            print(f"gate p2d: missing {path}")
            return 1
    domain_path = root / "data/evals/injection_domain.jsonl"
    domain_lines = [line for line in domain_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(domain_lines) < 40:
        print(f"gate p2d: domain set {len(domain_lines)} < 40")
        return 1
    from app.actions.contracts import sign, verify  # noqa: F401
    from app.audit.chain import AuditChain  # noqa: F401
    from app.guard.scout_guard import guard  # noqa: F401

    print("gate p2d: ok")
    return 0
