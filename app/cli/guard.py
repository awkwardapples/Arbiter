from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.guard.eval_metrics import compute_metrics
from app.guard.scout_guard import guard


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _eval_rows(rows: list[dict], *, use_model: bool) -> tuple[list[bool], list[bool]]:
    predicted: list[bool] = []
    expected: list[bool] = []
    for row in rows:
        text = row.get("text") or row.get("prompt", "")
        surface = row.get("surface", "vendor_answer")
        if surface == "chat":
            surface = "api_input"
        exp = bool(row["expected"]["injection"])
        result = guard(
            text,
            surface=surface,  # type: ignore[arg-type]
            capabilities=set(),
            segment_id=row["id"],
            use_model=use_model,
        )
        predicted.append(result.level == "block")
        expected.append(exp)
    return predicted, expected


def _print_metrics(name: str, metrics) -> None:
    print(
        f"{name}: precision={metrics.precision:.3f} recall={metrics.recall:.3f} f1={metrics.f1:.3f} "
        f"(tp={metrics.tp} fp={metrics.fp} tn={metrics.tn} fn={metrics.fn})"
    )


def run_guard_eval(args: argparse.Namespace) -> int:
    use_model = not args.no_model
    root = Path(__file__).resolve().parents[2]
    sets: dict[str, Path] = {
        "scout": root / "vendor/meterless/scout_adversarial.jsonl",
        "domain": root / "data/evals/injection_domain.jsonl",
    }
    names = ["scout", "domain"] if args.set == "all" else [args.set]
    report: dict = {"ts": datetime.now(UTC).isoformat(), "use_model": use_model, "sets": {}}
    for name in names:
        rows = _load_jsonl(sets[name])
        pred, exp = _eval_rows(rows, use_model=use_model)
        metrics = compute_metrics(predicted_positive=pred, expected_positive=exp)
        _print_metrics(name, metrics)
        report["sets"][name] = {
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "tp": metrics.tp,
            "fp": metrics.fp,
            "tn": metrics.tn,
            "fn": metrics.fn,
        }
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = root / "logs" / f"guard-eval-{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("guard-eval", help="Run Scout guard evaluation")
    p.add_argument("--set", choices=["scout", "domain", "all"], default="all")
    p.add_argument("--no-model", action="store_true")
    p.set_defaults(_handler=run_guard_eval)
