"""P17-T1..T5, T10, T11: every submission claim maps to a committed file, trace line or cited source."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from eval.report import latest_summary, render_summary_md

pytestmark = pytest.mark.p17

ROOT = Path(__file__).resolve().parents[3]

SUPER_VL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"
NOT_ENTITLED = "nvidia/nemotron-3-super-120b-a12b"

ALLOWED_SOURCES = (
    "https://www.verizon.com/business/resources/Te26/reports/2026-dbir-data-breach-investigations-report.pdf",
    "https://www.verizon.com/about/news/breach-industry-wide-dbir-finds",
    "https://www.whistic.com/resources/blog/2025-impact-report-takeaways",
    "https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/",
)

# Cited industry figures (R2_00_ASSESSMENT.md §5). A line quoting one must carry its source.
_STATS = re.compile(
    r"48%|2,643|\b36%|\b40%|\b67%|\b43%|37\.4|\b94%|\b84%|\b60%|12 third-party|1,465|n = 525|n=525"
)
_FOOTREF = re.compile(r"\[\^([\w-]+)\](?!:)")
_FOOTDEF = re.compile(r"^\[\^([\w-]+)\]:\s*(.+)$", re.MULTILINE)
_JSONL = re.compile(r"```jsonl\n(.*?)```", re.DOTALL)
_TICK = re.compile(r"`([^`\n]+)`")

README_H2 = [
    "Quick start",
    "Why it matters",
    "Track 3 mapping",
    "See it work",
    "How it works",
    "Zetaris USL",
    "Nemotron and Nightshift",
    "Evaluation",
    "Setup and usage",
    "Sponsor technology",
    "AI and model usage",
    "Data and licensing",
    "Third-party code and licences",
    "Limitations",
    "Responsible AI",
    "Pre-existing components",
    "Repository map",
]

_LIVE_FEATURES = {
    "zetaris": ("REST SQL API", "Federated public and private join"),
    "meterless": ("Nightshift Runtime (POWER contract)",),
}


def _read(rel: str) -> str:
    path = ROOT / rel
    assert path.is_file(), f"{rel} is missing"
    return path.read_text(encoding="utf-8")


def _meta() -> dict:
    return json.loads(_read("metadata.json"))


def _example_trace_lines() -> set[str]:
    """Every committed example trace line, except the failed live attempts."""
    lines: set[str] = set()
    for path in (ROOT / "logs" / "examples").rglob("*.jsonl"):
        if "live_failed" in path.parts:
            continue
        lines.update(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return lines


def _quoted_lines(text: str) -> list[str]:
    return [line for block in _JSONL.findall(text) for line in block.splitlines() if line.strip()]


# --- P17-T1 -------------------------------------------------------------------------------------


def test_p17_t1_metadata_files_exist() -> None:
    """P17-T1: every files/evidence path under sponsor_technologies exists."""
    missing: list[str] = []
    for block in _meta()["sponsor_technologies"].values():
        for key in ("files", "evidence"):
            for rel in block.get(key, []):
                if not (ROOT / rel.rstrip("/")).exists():
                    missing.append(rel)
    assert missing == []


def test_p17_t1_every_sponsor_feature_has_evidence() -> None:
    """P17-T1: each Zetaris feature and Meterless engine maps to a file plus a trace line or evidence file."""
    meta = _meta()
    entries = meta.get("evidence_map")
    assert isinstance(entries, list) and entries, "metadata.json has no evidence_map"
    by_key = {(e["sponsor"], e["feature"]): e for e in entries}
    wanted = [("zetaris", f) for f in meta["sponsor_technologies"]["zetaris"]["features"]]
    wanted += [("meterless", f) for f in meta["sponsor_technologies"]["meterless"]["engines"]]
    absent = [key for key in wanted if key not in by_key]
    assert absent == []
    for key in wanted:
        entry = by_key[key]
        assert (ROOT / entry["file"].rstrip("/")).exists(), entry
        assert "trace" in entry or "evidence" in entry, entry
        if "evidence" in entry:
            assert (ROOT / entry["evidence"]).is_file(), entry
        if "trace" in entry:
            trace = ROOT / entry["trace"]
            assert trace.is_file(), entry
            assert entry["trace"].startswith(("logs/examples/", "eval/results_live/")), entry
            assert "live_failed" not in entry["trace"], entry
            lines = trace.read_text(encoding="utf-8").splitlines()
            assert any(entry["match"] in line for line in lines), entry


def test_p17_t1_live_claims_have_trace_lines() -> None:
    """P17-T1: claims about live behaviour cite a committed live trace line, not just a file."""
    by_key = {(e["sponsor"], e["feature"]): e for e in _meta()["evidence_map"]}
    for sponsor, features in _LIVE_FEATURES.items():
        for feature in features:
            entry = by_key.get((sponsor, feature))
            if entry is None:
                continue
            assert "trace" in entry, entry
            line = next(
                x
                for x in (ROOT / entry["trace"]).read_text(encoding="utf-8").splitlines()
                if entry["match"] in x
            )
            event = json.loads(line)
            assert event["status"] == "success", entry
            assert event.get("backend") == "zetaris" or event.get("provider") == "meterless", entry


def test_p17_t1_usl_and_dq_only_when_parity_green() -> None:
    """P17-T1: USL and DQ are listed only if the committed parity run is USL-layer and all green."""
    features = " ".join(_meta()["sponsor_technologies"]["zetaris"]["features"])
    parity = json.loads(_read("docs/passes/P1-B_parity.json"))
    green = parity.get("query_layer") == "usl" and parity.get("all_green") is True
    if "USL" in features or "DQ" in features:
        assert green


def test_p17_t1_sponsors_paths_exist() -> None:
    """P17-T1: every backticked repo path in SPONSORS.md and README.md exists."""
    prefixes = (
        "app/",
        "docs/",
        "eval/",
        "policy/",
        "zetaris/",
        "tests/",
        "vendor/",
        "scripts/",
        "data/",
        "logs/",
        "input_examples/",
        "output_examples/",
        "ui/",
        "sources/",
        ".cursor/",
    )
    missing: list[str] = []
    for rel in ("docs/SPONSORS.md", "README.md", "docs/IMPACT.md", "docs/DEMO_SCRIPT.md", "docs/QA_PREP.md"):
        for quoted in _TICK.findall(_read(rel)):
            ref = quoted.strip().rstrip("/")
            plain = " " not in ref and "*" not in ref and "<" not in ref
            if ref.startswith(prefixes) and plain and not (ROOT / ref).exists():
                missing.append(f"{rel}: {ref}")
    assert missing == []


# --- P17-T2 -------------------------------------------------------------------------------------


def test_p17_t2_quoted_trace_lines_are_verbatim() -> None:
    """P17-T2: every jsonl line quoted in README and SPONSORS exists verbatim in logs/examples/**."""
    corpus = _example_trace_lines()
    for rel in ("README.md", "docs/SPONSORS.md"):
        quoted = _quoted_lines(_read(rel))
        assert quoted, f"{rel} quotes no trace lines"
        absent = [line[:120] for line in quoted if line not in corpus]
        assert absent == [], rel


def test_p17_t2_live_proof_lines_are_quoted() -> None:
    """P17-T2: README and SPONSORS each quote a Zetaris request id line and a Nemotron receipt line."""
    for rel in ("README.md", "docs/SPONSORS.md"):
        events = [json.loads(line) for line in _quoted_lines(_read(rel))]
        assert any(
            e.get("backend") == "zetaris" and "zetaris_request_id=" in e["output_summary"] for e in events
        ), rel
        assert any(
            e.get("action") == "model_call"
            and e.get("status") == "success"
            and str(e.get("model", "")).startswith("nvidia/nemotron-3.5-")
            and str((e.get("provider_meta") or {}).get("receipt_id", "")).startswith("rcpt_")
            for e in events
        ), rel


# --- P17-T3 -------------------------------------------------------------------------------------


@pytest.mark.parametrize("rel", ["README.md", "docs/IMPACT.md", "docs/SLIDES.md"])
def test_p17_t3_statistics_carry_allowed_sources(rel: str) -> None:
    """P17-T3: each cited statistic has an allowed source URL on its line or in its footnote."""
    text = _read(rel)
    notes = {key: body for key, body in _FOOTDEF.findall(text)}
    bad: list[str] = []
    found = 0
    for line in text.splitlines():
        if _FOOTDEF.match(line) or not _STATS.search(line):
            continue
        found += 1
        sources = [line] + [notes.get(ref, "") for ref in _FOOTREF.findall(line)]
        if not any(url in chunk for url in ALLOWED_SOURCES for chunk in sources):
            bad.append(line[:120])
    assert found, f"{rel} quotes no statistics"
    assert bad == []


def test_p17_t3_footnotes_use_allowed_sources_only() -> None:
    """P17-T3: footnote definitions in IMPACT point only at the allowed sources."""
    for key, body in _FOOTDEF.findall(_read("docs/IMPACT.md")):
        urls = re.findall(r"https?://[^\s)>\]]+", body)
        assert urls, key
        assert all(url in ALLOWED_SOURCES for url in urls), (key, urls)


# --- P17-T4 -------------------------------------------------------------------------------------


def test_p17_t4_one_line_description_is_identical() -> None:
    """P17-T4: the metadata description appears verbatim in README, SLIDES and SUBMISSION."""
    line = _meta()["description"]
    assert line.endswith(".")
    for rel in ("README.md", "docs/SLIDES.md", "docs/SUBMISSION.md"):
        assert line in _read(rel), rel


# --- P17-T5 -------------------------------------------------------------------------------------


def test_p17_t5_readme_section_order() -> None:
    """P17-T5: README H2 headings follow P17 §3.2."""
    found = re.findall(r"^## (.+)$", _read("README.md"), re.MULTILINE)
    assert found == README_H2


def test_p17_t5_readme_eval_block_is_latest_live_summary() -> None:
    """P17-T5: the README eval block is the rendered latest eval/results_live summary."""
    text = _read("README.md")
    start = text.index("<!-- EVAL:START -->") + len("<!-- EVAL:START -->")
    end = text.index("<!-- EVAL:END -->")
    expected = render_summary_md(latest_summary(ROOT / "eval" / "results_live"))
    assert text[start:end].strip("\n") == expected.strip("\n")


def test_p17_t5_readme_eval_labels() -> None:
    """P17-T5: the README labels the live subset, the unmeasured baseline and the offline split."""
    section = _read("README.md").split("## Evaluation", 1)[1].split("\n## ", 1)[0]
    # P20 (human-approved update): the 25 October live run, n=10.
    assert "10/10" in section and "10 of 21" in section and "6 of 10" in section
    assert "baseline could not be measured" in section.lower()
    assert "16/16" in section
    assert "docs/EVALUATION.md" in section and "--publish" in section


# --- P17-T10 ------------------------------------------------------------------------------------


def test_p17_t10_impact_estimate_is_labelled() -> None:
    """P17-T10: the capacity figure is labelled an estimate with an assumptions table."""
    text = _read("docs/IMPACT.md")
    section = text.split("## 5.", 1)[1].split("\n## ", 1)[0]
    assert "estimate" in section.lower()
    assert "not measured" in section.lower()
    assert "| Assumption" in section or "| Step" in section


def test_p17_t10_demo_script_timing() -> None:
    """P17-T10: the video segments are contiguous from 0:00 and end at 3:35 (hard stop 3:50)."""
    text = _read("docs/DEMO_SCRIPT.md")
    spans = re.findall(r"^\| (\d):(\d\d)–(\d):(\d\d) \|", text, re.MULTILINE)
    assert spans, "no timed segments"
    secs = [(int(a) * 60 + int(b), int(c) * 60 + int(d)) for a, b, c, d in spans]
    assert secs[0][0] == 0
    for (_, end), (start, _) in zip(secs, secs[1:], strict=False):
        assert end == start
    assert secs[-1][1] == 215
    # P20 (human-approved update): the hero is the Quillfeather live run, the receipts are proof run 4's.
    assert "run-211916c1544d" in text
    assert "rcpt_req_936ew345" in text and "rcpt_req_wu3r6jyf" in text
    assert "sample mode" in text.lower()
    assert "nightshift_deviations.md" in text


def test_p17_t10_slides_outline() -> None:
    """P17-T10: 23 numbered slides and a rubric coverage table with all six weighted criteria.

    P20 (human-approved update): the outline is the 23-slide submission deck.
    """
    text = _read("docs/SLIDES.md")
    numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", text, re.MULTILINE)]
    assert numbers == list(range(1, 24))
    for criterion in (
        "Impact (30)",
        "Technical (20)",
        "Innovation (15)",
        "Demo (15)",
        "Product & UX (10)",
        "Sponsor Tech (10)",
    ):
        assert criterion in text, criterion
    future = text.split("## 22. ", 1)[1]
    assert "monitor" in future.lower()


def test_p17_t10_no_monitoring_claims() -> None:
    """P17-T10: P16 did not ship, so monitoring appears only as future work."""
    for rel in (
        "README.md",
        "docs/SPONSORS.md",
        "metadata.json",
        "docs/IMPACT.md",
        "docs/DEMO_SCRIPT.md",
        "docs/SUBMISSION.md",
        "docs/QA_PREP.md",
        "docs/SLIDES.md",
    ):
        for line in _read(rel).splitlines():
            if re.search(r"\bmonitor(ing|s|ed)?\b", line, re.IGNORECASE) and "Monitor tab" not in line:
                assert re.search(r"future|not shipped|later|path to production|P16", line, re.IGNORECASE), (
                    rel,
                    line,
                )


def test_p17_t10_submission_checklist_state() -> None:
    """P17-T10: video and deck are open items; metadata links stay empty until upload."""
    text = _read("docs/SUBMISSION.md")
    assert re.search(r"- \[ \] .*[Vv]ideo", text)
    assert re.search(r"- \[ \] .*[Dd]eck", text)
    assert "docs/PRIOR_WORK.md" in text
    meta = _meta()
    assert meta["demo_video"] == "" and meta["slide_deck"] == ""


# --- P17-T11 ------------------------------------------------------------------------------------


def test_p17_t11_cursor_usage_is_compiled() -> None:
    """P17-T11: docs/CURSOR_USAGE.md is exactly the compiler's output over docs/cursor-usage/."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "compile_cursor_usage.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = _read("docs/CURSOR_USAGE.md")
    for label in ("P0", "P14-B", "P15", "P17"):
        assert f"| {label} |" in text, label
