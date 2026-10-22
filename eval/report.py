"""Render and publish evaluation summaries. Numbers come only from the summary dict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_START = "<!-- EVAL:START -->"
_END = "<!-- EVAL:END -->"


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
    return "\n".join(lines)


def publish(summary: dict[str, Any], *, docs_path: Path, readme_path: Path | None = None) -> None:
    """Rewrite the docs file. Replace the README block only when both markers exist."""
    text = render_summary_md(summary)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(text, encoding="utf-8")
    if readme_path is None or not readme_path.is_file():
        return
    raw = readme_path.read_text(encoding="utf-8")
    if _START not in raw or _END not in raw:
        return
    start = raw.index(_START) + len(_START)
    end = raw.index(_END)
    updated = raw[:start] + "\n" + text.rstrip("\n") + "\n" + raw[end:]
    if updated != raw:
        readme_path.write_text(updated, encoding="utf-8")


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
