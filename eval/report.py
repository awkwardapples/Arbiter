"""Render and publish evaluation summaries. Numbers come only from the summary dict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVAL_START = "<!-- EVAL:START -->"
EVAL_END = "<!-- EVAL:END -->"
_START = EVAL_START
_END = EVAL_END


def render_summary_md(summary: dict[str, Any]) -> str:
    """Markdown for one summary. Offline runs say offline in the header."""
    mode = summary.get("mode") or {}
    offline = bool(summary.get("offline")) or mode.get("llm") == "offline"
    lines = [
        "# Evaluation",
        "",
        "Synthetic data. Small n. Intervals are Wilson 95% where a rate has a denominator.",
        "Only the tier gates are calibrated. Weights stay at their a-priori values.",
        "",
        (
            f"- mode: {'offline' if offline else 'live'} "
            f"({mode.get('data', 'unknown')} / {mode.get('llm', 'unknown')})"
        ),
        f"- provider: {summary.get('provider') or ('offline' if offline else 'unrecorded')}",
        f"- model ids (from traces): {', '.join(summary.get('model_ids') or []) or 'none recorded'}",
        f"- splits: {', '.join(summary.get('splits') or [])}",
        f"- n: {summary.get('n', 0)}",
        f"- git sha: {summary.get('git_sha') or 'unknown'}",
        f"- generated: {summary.get('generated_at') or 'unknown'}",
        "",
    ]
    if offline:
        lines.append("These numbers are offline. They are not a live Nightshift run.")
        lines.append("")
    lines.append("| System | Accuracy | Unsafe approvals | Invalid | Abstention |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, block in sorted((summary.get("systems") or {}).items()):
        lines.append(
            "| {name} | {acc} | {unsafe} | {invalid} | {abstain} |".format(
                name=name,
                acc=_cell(block.get("accuracy")),
                unsafe=_pair(block.get("unsafe_approvals")),
                invalid=_cell(block.get("invalid_rate")),
                abstain=_cell(block.get("abstention_rate")),
            )
        )
    lines.append("")
    if any(isinstance(block.get("run"), dict) for block in (summary.get("systems") or {}).values()):
        lines.extend(_run_lines(summary))
    return "\n".join(lines)


def _run_lines(summary: dict[str, Any]) -> list[str]:
    """Per-system run facts for a summary that has them (live harness runs)."""
    systems = summary.get("systems") or {}
    runs = {
        name: block["run"] for name, block in sorted(systems.items()) if isinstance(block.get("run"), dict)
    }
    lines: list[str] = []
    subset = summary.get("live_subset")
    if isinstance(subset, dict):
        offline_n = [run["n"] for run in runs.values() if (run.get("mode") or {}).get("llm") == "offline"]
        offline_text = f", n={offline_n[0]} for the offline system" if offline_n else ""
        lines.append(
            f"Reduced n: n={subset.get('n')} for the live systems{offline_text}; "
            f"the live subset is the {subset.get('rule')}."
        )
        lines.append("")
    lines.append(
        "| System | Mode | n | Contradiction recall | Failing-control recall "
        "| p50 ms | p95 ms | Model calls/case | Model-call fallback |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, run in runs.items():
        mode = run.get("mode") or {}
        block = systems[name]
        latency = run.get("latency_ms") or {}
        contradiction = _recall(block.get("contradiction_recall"))
        failing = _recall(block.get("failing_control_recall"))
        lines.append(
            f"| {name} | {mode.get('data', '?')} / {mode.get('llm', '?')} | {run.get('n', 0)} | "
            f"{contradiction} | {failing} | {latency.get('p50', 0)} | {latency.get('p95', 0)} | "
            f"{float(run.get('model_calls_per_case') or 0):.1f} | {_cell(run.get('fallback_rate'))} |"
        )
    lines.append("")
    lanes: dict[str, list[str]] = {}
    for run in runs.values():
        for lane, models in (run.get("routed_models") or {}).items():
            seen = lanes.setdefault(lane, [])
            seen.extend(model for model in models if model not in seen)
    for lane in sorted(lanes):
        lines.append(f"- {lane} lane routed to: {', '.join(lanes[lane])} (from trace receipts)")
    if lanes.get("fast") and lanes.get("fast") == lanes.get("deep"):
        lines.append("")
        lines.append(
            f"Deviation: both the fast and deep lanes were served by {', '.join(lanes['fast'])}. "
            "See docs/evidence/nightshift_proof.json."
        )
    lines.append("")
    return lines


def _recall(block: dict[str, Any] | None) -> str:
    if not block or block.get("rate") is None:
        return "—"
    return f"{block['rate']:.3f} ({block.get('found', 0)}/{block.get('expected', 0)})"


def publish(summary: dict[str, Any], *, docs_path: Path, readme_path: Path | None = None) -> None:
    """Rewrite the docs file. Replace the README block only when both markers exist."""
    text = render_summary_md(summary)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    existing = docs_path.read_text(encoding="utf-8") if docs_path.is_file() else ""
    if _START in existing and _END in existing:
        # Hand-written text around the markers is kept; only the generated block changes.
        _replace_block(docs_path, existing, text)
    else:
        docs_path.write_text(text, encoding="utf-8")
    if readme_path is None or not readme_path.is_file():
        return
    raw = readme_path.read_text(encoding="utf-8")
    if _START not in raw or _END not in raw:
        return
    _replace_block(readme_path, raw, text)


def _replace_block(path: Path, raw: str, text: str) -> None:
    start = raw.index(_START) + len(_START)
    end = raw.index(_END)
    updated = raw[:start] + "\n" + text.rstrip("\n") + "\n" + raw[end:]
    if updated != raw:
        path.write_text(updated, encoding="utf-8")


def latest_summary(results_root: Path) -> dict[str, Any]:
    """Newest `summary.json` under `results_root`, by directory name."""
    found = sorted(results_root.glob("*/summary.json"))
    if not found:
        raise FileNotFoundError(f"no summary.json under {results_root}")
    payload = json.loads(found[-1].read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FileNotFoundError(f"summary.json in {found[-1].parent} is not an object")
    return payload


def _cell(block: dict[str, Any] | None) -> str:
    if not block or block.get("rate") is None:
        return "—"
    correct = block.get("correct", block.get("count"))
    return f"{block['rate']:.3f} ({correct}/{block['n']})"


def _pair(block: dict[str, Any] | None) -> str:
    if not block:
        return "—"
    return f"{block.get('count', 0)}/{block.get('n', 0)}"
