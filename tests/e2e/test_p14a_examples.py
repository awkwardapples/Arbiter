"""P14A-T1, T4, T5, T6, T8, T9: the six offline examples, workload and dossier."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from app.labels import question_text
from fastapi.testclient import TestClient

from app.orchestrator import RunOptions, run
from app.store import Store
from tests.e2e.support import EXAMPLE_FILES, expected, load_example, trace

pytestmark = pytest.mark.p14a

_CODE = re.compile(r"[A-Z_]{6,}|F-C\d+|Q_[A-Z_]+")
_URL = re.compile(r"https?://[^\s\"'<>]+")
_SECTIONS = (
    "Analyst brief",
    "Evidence",
    "Controls",
    "What would change this decision",
    "Drafts",
    "Approvals",
    "Precedents",
    "Integrity",
)
_SECRET_MARKERS = (
    "ZETARIS_API_KEY",
    "METERLESS_RUNTIME_TOKEN",
    "NVIDIA_API_KEY",
    "ARBITER_SIGNING_KEY",
)


@pytest.fixture(scope="module")
def example_runs() -> Iterator[dict]:
    """One offline run of each example, sharing a temporary case store."""
    root = Path(tempfile.mkdtemp(prefix="p14a-"))
    previous = Path.cwd()
    saved = {key: os.environ.get(key) for key in ("SAMPLE_MODE", "LLM_PROVIDER", "ARBITER_MEMORY")}
    os.chdir(root)
    os.environ["SAMPLE_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "offline"
    os.environ["ARBITER_MEMORY"] = "off"
    from app.llm.resolve import reset_cache

    reset_cache()
    try:
        yield {name: run(load_example(name), options=RunOptions()) for name in EXAMPLE_FILES}
    finally:
        os.chdir(previous)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_cache()


def test_p14a_t1_examples_omit_always_unless_it_decided(example_runs: dict) -> None:
    """P14A-T1: the six examples list ALL_REQUIRED_CONTROLS_MET only when it decided."""
    for name, resp in example_runs.items():
        record = Store().get(resp.output.case_id).decision
        if "ALL_REQUIRED_CONTROLS_MET" in record.outcome_reasons:
            assert record.outcome == "APPROVE", name
            assert record.outcome_reasons == ["ALL_REQUIRED_CONTROLS_MET"], name


def test_p14a_t4_example_outcomes_unchanged(example_runs: dict) -> None:
    """P14A-T4: the six example outcomes still match the expected file."""
    wanted = expected()
    for name, resp in example_runs.items():
        assert resp.output is not None
        assert resp.output.decision == wanted[name]["outcome"], name


def test_p14a_t5_example_2_brief_is_plain_english(example_runs: dict) -> None:
    """P14A-T5: example 2 names the vendor, both residencies, the contract and the KEV exposure."""
    resp = example_runs["example_2.json"]
    bundle = Store().get(resp.output.case_id)
    brief = bundle.report.brief
    assert brief is not None
    assert brief.generator == "template:v2"
    prose = "\n".join([brief.headline, *(point.text for point in brief.why)])
    assert bundle.legal_name.split()[0] in prose
    assert "EU" in prose and "US" in prose
    assert "CTR-30007" in prose
    assert "FortiOS" in prose
    kev = next(fact.value for fact in bundle.decision.facts if fact.key == "vuln.kev_matches")
    assert str(kev) in prose
    assert _CODE.search(brief.headline) is None
    for point in brief.why:
        assert _CODE.search(point.text) is None
    assert resp.output.summary == brief.headline


def test_p14a_t6_example_4_email_lists_every_question(example_runs: dict) -> None:
    """P14A-T6: the request-info email contains every counterfactual question."""
    resp = example_runs["example_4.json"]
    record = Store().get(resp.output.case_id).decision
    assert record.outcome == "REQUEST_INFO"
    email = next(draft for draft in resp.output.drafts if draft.to_role == "vendor")
    questions = {qid for item in record.counterfactuals for qid in item.question_ids}
    assert questions
    for question_id in questions:
        assert question_text(question_id) in email.body


def test_p14a_t8_workload_matches_the_trace(example_runs: dict) -> None:
    """P14A-T8: query and model counts are the trace events, not estimates."""
    resp = example_runs["example_1.json"]
    rows = trace(resp.log_file)
    workload = resp.output.workload
    assert workload is not None
    assert workload.queries == sum(1 for row in rows if row["action"] == "query_run")
    assert workload.model_calls == sum(1 for row in rows if row["action"] == "model_call")
    assert workload.queries > 0


def test_p14a_t9_dossier_for_every_example(example_runs: dict) -> None:
    """P14A-T9: markdown and HTML dossiers, and the dossier route, for every example."""
    from app.dossier import render

    client = TestClient(app_client(), raise_server_exceptions=False)
    for name, resp in example_runs.items():
        bundle = Store().get(resp.output.case_id)
        markdown = render(bundle, "md")
        html = render(bundle, "html")
        for section in _SECTIONS:
            assert section in markdown, (name, section)
            assert section in html, (name, section)
        replay = f"python run.py replay {bundle.case_id}"
        assert replay in markdown and replay in html
        for marker in _SECRET_MARKERS:
            assert marker not in markdown and marker not in html
        citation_urls = {
            cite
            for point in (bundle.report.brief.why if bundle.report.brief else [])
            for cite in point.citations
            if cite.startswith("http://") or cite.startswith("https://")
        }
        assert set(_URL.findall(html)) <= citation_urls
        assert "http://" not in html.split("<style>", 1)[-1] or set(_URL.findall(html)) <= citation_urls

        for fmt, media in (("md", "text/markdown"), ("html", "text/html")):
            response = client.get(f"/cases/{bundle.case_id}/dossier", params={"format": fmt})
            assert response.status_code == 200, (name, fmt, response.text)
            assert media in response.headers["content-type"]


def app_client():
    from app.api.main import app

    return app
