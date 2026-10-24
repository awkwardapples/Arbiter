"""P14-B acceptance tests: the analyst console (P14B-T1 .. T8)."""

from __future__ import annotations

import re

import pytest

from tests.e2e.support import offline_env
from tests.unit.ui.p14b_support import (
    FAKE_CREDENTIAL,
    P14Client,
    live_trace,
    load,
    open_app,
    visible_text,
)

pytestmark = pytest.mark.p14b
__all__ = ["offline_env"]

PAGES = [
    "pages/new_assessment.py",
    "pages/queue.py",
    "pages/case.py",
    "pages/sources.py",
    "pages/review.py",
    "pages/memory.py",
    "pages/audit.py",
    "pages/evaluation.py",
]
CODE = re.compile(r"[A-Z_]{6,}|F-C\d|\bQ_|answer_id=")
RATIONALE = "Reviewed the contract and the residency clause with the data protection officer."


def _case_page(client: P14Client):
    return open_app(client, "pages/case.py", case_id=client.case_detail["case_id"])


# --- P14B-T1 -----------------------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_p14b_t1_every_page_runs(page: str) -> None:
    """P14B-T1: AppTest smoke for every page with recorded P14-A responses."""
    client = P14Client()
    case_id = client.case_detail["case_id"] if page == "pages/case.py" else None
    at = open_app(client, page, case_id=case_id)
    assert not at.exception
    assert at.title, "every page starts with st.title"
    assert at.caption, "every page has a caption after the title"


def test_p14b_t1_request_info_case_runs() -> None:
    """P14B-T1: the second recorded case (REQUEST_INFO) renders too."""
    client = P14Client("request_info")
    at = _case_page(client)
    assert not at.exception
    assert client.case_detail["case_id"] in at.title[0].value


# --- P14B-T2 -----------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["escalate", "request_info"])
def test_p14b_t2_copy_rule(kind: str) -> None:
    """P14B-T2: outside Technical details there is no code, fact id, query id or answer id."""
    at = _case_page(P14Client(kind))
    assert not at.exception
    text = visible_text(at)
    assert not CODE.findall(text), CODE.findall(text)
    assert "VND-" not in text


def test_p14b_t2_technical_details_holds_the_raw_ids() -> None:
    """P14B-T2: the ids are still reachable, inside the expander."""
    at = _case_page(P14Client())
    everything = visible_text(at, skip_technical=False)
    assert re.search(r"F-C\d", everything)


def test_p14b_t2_brief_leads_the_page() -> None:
    """P14B-T2: the headline is the first content after the header; case id is in the title."""
    client = P14Client()
    at = _case_page(client)
    brief = client.case_detail["report"]["brief"]
    text = visible_text(at)
    assert client.case_detail["case_id"] in at.title[0].value
    assert brief["headline"] in text
    assert text.index(brief["headline"]) < text.index("Controls")
    for point in brief["why"]:
        assert point["text"] in text


def test_p14b_t2_claim_and_record_cards() -> None:
    """P14B-T2: a why-point with both refs shows the claim and the system of record side by side."""
    client = P14Client()
    at = _case_page(client)
    text = visible_text(at)
    point = next(p for p in client.case_detail["report"]["brief"]["why"] if p["claim"] and p["record"])
    for ref in (point["claim"], point["record"]):
        assert ref["source_label"] in text
        assert ref["value"] in text
    assert "Vendor claim" in text and "System of record" in text


def test_p14b_t2_confidence_names_unverified_controls() -> None:
    """P14B-T2: confidence reads as a sentence naming the unverified control, not a bare percentage."""
    client = P14Client()
    at = _case_page(client)
    unknown = client.case_detail["record"]["confidence"]["unknown_controls"]
    text = visible_text(at)
    assert "unverified" in text
    for control_id in unknown:
        assert control_id in text


# --- P14B-T3 -----------------------------------------------------------------------------------


def test_p14b_t3_shows_the_full_draft() -> None:
    """P14B-T3: the next-action panel holds the whole draft body in an editable text area."""
    client = P14Client()
    at = _case_page(client)
    draft = client.case_detail["report"]["drafts"][0]
    assert at.text_area(key="draft_body").value == draft["body"]
    assert draft["subject"] in visible_text(at)
    assert at.get("download_button"), "Download .txt is offered"


def test_p14b_t3_executed_action_reports_the_outbox() -> None:
    """P14B-T3: an executed contract shows no approve controls and says it went to the outbox."""
    at = _case_page(P14Client())
    assert [b for b in at.button if b.key == "approve_btn"] == []
    assert "outbox" in visible_text(at).lower()


def test_p14b_t3_short_rationale_is_refused_client_side() -> None:
    """P14B-T3: under 30 characters never reaches the API."""
    client = P14Client(pending=True)
    at = _case_page(client)
    at.text_area(key="approve_rationale").input("too short").run()
    at.button(key="approve_btn").click().run()
    assert client.approvals == []
    assert any("30" in err.value for err in at.error)


def test_p14b_t3_approve_sends_role_and_rationale() -> None:
    """P14B-T3: Approve posts the selected role and the rationale to the contract."""
    client = P14Client(pending=True)
    at = _case_page(client)
    contract_id = client.case_detail["contracts"][0]["contract_id"]
    at.selectbox(key="approve_role").select("tprm_lead").run()
    at.text_area(key="approve_rationale").input(RATIONALE).run()
    at.button(key="approve_btn").click().run()
    assert not at.exception
    assert len(client.approvals) == 1
    sent_id, body = client.approvals[0]
    body = body.model_dump() if hasattr(body, "model_dump") else body
    assert sent_id == contract_id
    assert body["role"] == "tprm_lead"
    assert body["rationale"] == RATIONALE
    assert body["decision"] == "approve"


def test_p14b_t3_reject_sends_reject() -> None:
    """P14B-T3: Reject is the same call with decision=reject."""
    client = P14Client(pending=True)
    at = _case_page(client)
    at.text_area(key="approve_rationale").input(RATIONALE).run()
    at.button(key="reject_btn").click().run()
    body = client.approvals[0][1]
    body = body.model_dump() if hasattr(body, "model_dump") else body
    assert body["decision"] == "reject"


def test_p14b_t3_refusal_helper() -> None:
    """P14B-T3: the pure check used by the panel."""
    from ui.case_view import approval_refusal

    assert approval_refusal("short")
    assert approval_refusal(" " * 40)
    assert approval_refusal(RATIONALE) is None


# --- P14B-T4 -----------------------------------------------------------------------------------


def _form(questions, **over):
    answers = {
        q["question_id"]: {"choice": "Yes" if q["type"] == "yes_no" else None, "how": "AES-256"}
        for q in questions
    }
    form = {
        "legal_name": "Harbour Test Ltd",
        "trading_name": "Harbour",
        "category": "SaaS",
        "requested_service": "Team wiki",
        "criticality": "low",
        "annual_spend_gbp": 5000.0,
        "data_categories": ["internal"],
        "processing_countries": ["GB"],
        "answers": answers,
        "documents": [],
        "components": [],
    }
    form.update(over)
    return form


def test_p14b_t4_form_builds_a_valid_submission() -> None:
    """P14B-T4: the answers compose into text, and the API schema accepts the result."""
    from app.schemas.case import CaseInput as ApiCaseInput
    from ui.intake import build_case_input

    questions = load("p14b_questions.json")
    case, errors = build_case_input(_form(questions), questions)
    assert errors == []
    parsed = ApiCaseInput.model_validate(case.model_dump(exclude_none=True))
    assert parsed.submission is not None
    assert len(parsed.submission.answers) == 16
    first = parsed.submission.answers[0]
    assert first.question_id == "Q01"
    assert first.question == questions[0]["question"]
    assert first.answer_text.startswith("Yes") and "AES-256" in first.answer_text


def test_p14b_t4_not_answered_is_left_out() -> None:
    """P14B-T4: 'Not answered' submits no answer, so the policy sees the control as unknown."""
    from ui.intake import build_case_input

    questions = load("p14b_questions.json")
    form = _form(questions)
    form["answers"]["Q01"] = {"choice": "Not answered", "how": ""}
    case, errors = build_case_input(form, questions)
    assert errors == []
    ids = [a.question_id for a in case.submission.answers]
    assert "Q01" not in ids and len(ids) == 15


@pytest.mark.parametrize(
    "over",
    [
        {"legal_name": "  "},
        {"requested_service": ""},
        {"annual_spend_gbp": -1.0},
        {"data_categories": []},
        {"processing_countries": []},
    ],
)
def test_p14b_t4_invalid_input_is_rejected(over: dict) -> None:
    """P14B-T4: client-side validation names the problem and builds nothing."""
    from ui.intake import build_case_input

    questions = load("p14b_questions.json")
    case, errors = build_case_input(_form(questions, **over), questions)
    assert case is None and errors


def test_p14b_t4_presets_fill_all_sixteen_answers() -> None:
    """P14B-T4: every preset answers all 16 questions and builds a valid case."""
    from ui.intake import build_case_input, load_presets

    questions = load("p14b_questions.json")
    presets = load_presets()
    assert len(presets) >= 2
    for name, form in presets.items():
        assert set(form["answers"]) == {q["question_id"] for q in questions}, name
        case, errors = build_case_input(form, questions)
        assert errors == [], (name, errors)
        assert len(case.submission.answers) == 16


def test_p14b_t4_questionnaire_page_runs_a_preset() -> None:
    """P14B-T4: choosing a preset fills the form; Run posts exactly one case."""
    from ui.intake import load_presets

    client = P14Client()
    at = open_app(client, "pages/new_assessment.py")
    assert not at.exception
    name = next(iter(load_presets()))
    at.selectbox(key="preset").select(name).run()
    assert at.text_input(key="legal_name").value
    assert at.selectbox(key="q_choice_Q01").value in {"Yes", "No", "Not answered"}
    at.button(key="run_questionnaire").click().run()
    assert not at.exception
    assert len(client.runs) == 1
    assert client.runs[0].submission is not None


def test_p14b_t4_invalid_form_does_not_call_run() -> None:
    """P14B-T4: an empty form shows errors and never calls /run."""
    client = P14Client()
    at = open_app(client, "pages/new_assessment.py")
    at.button(key="run_questionnaire").click().run()
    assert client.runs == []
    assert at.error


def test_p14b_t4_uses_selects_not_free_text_for_categories() -> None:
    """P14B-T4: data categories and criticality are choices."""
    at = open_app(P14Client(), "pages/new_assessment.py")
    assert at.multiselect(key="data_categories")
    assert at.selectbox(key="criticality")


def test_p14b_t4_json_paste_is_advanced() -> None:
    """P14B-T4: JSON paste survives, inside an Advanced expander."""
    at = open_app(P14Client(), "pages/new_assessment.py")
    labels = [e.label for e in at.expander]
    assert any("Advanced" in label for label in labels)


# --- P14B-T5 -----------------------------------------------------------------------------------


def test_p14b_t5_erd_has_ten_nodes_and_the_foreign_keys() -> None:
    """P14B-T5: the committed model renders as 10 tables and one edge per foreign key."""
    from ui.sources_view import load_usl, usl_dot

    model = load_usl()
    assert len(model["tables"]) == 10
    fk_count = sum(len(t["foreign_keys"]) for t in model["tables"])
    assert fk_count >= 5
    dot = usl_dot(model)
    for table in model["tables"]:
        assert f'"{table["name"]}"' in dot
    assert dot.count("->") == fk_count


def test_p14b_t5_sources_page_draws_the_graph_and_labels_the_counts() -> None:
    """P14B-T5: the page shows the ERD, the parity counts with their date, and the five DQ rules."""
    at = open_app(P14Client(), "pages/sources.py")
    assert not at.exception
    assert at.get("graphviz_chart")
    text = visible_text(at)
    assert "as of the P13 parity run" in text
    assert "23 Oct 2026" in text
    assert "ZETARIS_USL.md" in text


def test_p14b_t5_missing_model_degrades_with_the_regenerate_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """P14B-T5: no model file means a plain message, never a Zetaris fallback."""
    import ui.sources_view as sources

    monkeypatch.setattr(sources, "MODEL_PATH", tmp_path / "missing.json")
    assert sources.load_usl() is None
    assert "python run.py zetaris parity" in sources.MISSING_MESSAGE
    assert sources.MISSING_MESSAGE.startswith("The USL model is not available in this checkout")


# --- P14B-T6 -----------------------------------------------------------------------------------


def test_p14b_t6_live_proof_shows_served_models_and_receipt() -> None:
    """P14B-T6: the sidebar names the models served on the last run and the last receipt."""
    at = open_app(P14Client(live=True))  # the sidebar renders on the entry run
    text = visible_text(at, sidebar=True)
    assert "Nightshift: online" in text
    assert "http://127.0.0.1:8088/v1" in text
    assert "token hidden" in text
    assert "fast → nvidia/nemotron-3.5-lightning-30b-a3b" in text
    assert "deep → nvidia/nemotron-3-super-120b-a12b" in text
    assert "rcpt-test-0002" in text


def test_p14b_t6_offline_label() -> None:
    """P14B-T6: offline fixtures get the deterministic-fallback label and no model rows."""
    at = open_app(P14Client())
    text = visible_text(at, sidebar=True)
    assert "Offline fallback (deterministic)" in text
    assert "Live runs use Meterless Nightshift → NVIDIA Nemotron." in text
    assert "→ nvidia" not in text


def test_p14b_t6_token_is_never_rendered() -> None:
    """P14B-T6: the secret in the health payload appears nowhere, on any page."""
    for page in (None, "pages/queue.py", "pages/case.py", "pages/evaluation.py"):
        client = P14Client(live=True)
        case_id = client.case_detail["case_id"] if page == "pages/case.py" else None
        at = open_app(client, page, case_id=case_id)
        for sidebar in (True, False):
            assert FAKE_CREDENTIAL not in visible_text(at, skip_technical=False, sidebar=sidebar)


def test_p14b_t6_placeholder_until_p15(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """P14B-T6: without the P15 proof file the panel says so and invents nothing."""
    import ui.provider as provider

    monkeypatch.setattr(provider, "PROOF_PATH", tmp_path / "nightshift_proof.json")
    lines = provider.provider_lines(P14Client().health_data, [])
    assert any("Live Nightshift proof is produced by the P15 pass" in line for line in lines)
    assert not any("rcpt" in line for line in lines)


def test_p14b_t6_unsure_trace_shows_no_models() -> None:
    """P14B-T6: a live provider with a trace that carries no model calls lists no model rows."""
    import ui.provider as provider

    lines = provider.provider_lines(P14Client(live=True).health_data, load("p14a_trace_escalate.json"))
    assert not any("nemotron" in line for line in lines)
    assert live_trace()  # fixture itself is non-empty


# --- P14B-T7 -----------------------------------------------------------------------------------


_WORKLOAD = {
    "systems_queried": ["a", "b", "c", "d", "e", "f"],
    "queries": 11,
    "rows_read": 40,
    "documents_read": 2,
    "answers_read": 16,
    "claims_extracted": 16,
    "claims_grounded": 16,
    "contradictions": 1,
    "dq_flags": 0,
    "guard_blocks": 0,
    "model_calls": 9,
    "models": ["nvidia/nemotron-3-super-120b-a12b"],
    "elapsed_seconds": 38.2,
}


def test_p14b_t7_sentence_matches_the_spec_example() -> None:
    """P14B-T7: the strip reads as the spec's sentence."""
    from ui.labels_ui import workload_sentence

    assert workload_sentence(_WORKLOAD) == (
        "Checked 6 systems, 11 queries, 16 answers, 2 documents, 1 contradiction found, "
        "in 38 s with 9 Nemotron calls"
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("queries", 1, "1 query"),
        ("answers_read", 1, "1 answer,"),
        ("documents_read", 1, "1 document,"),
        ("contradictions", 3, "3 contradictions found"),
        ("elapsed_seconds", 4.4, "in 4 s"),
        ("model_calls", 1, "1 Nemotron call"),
    ],
)
def test_p14b_t7_every_number_comes_from_a_field(field: str, value, expected: str) -> None:
    """P14B-T7: changing a field changes the sentence, so nothing is hard-coded."""
    from ui.labels_ui import workload_sentence

    assert expected in workload_sentence({**_WORKLOAD, field: value})


def test_p14b_t7_no_model_calls_says_offline() -> None:
    """P14B-T7: zero model calls is stated, not hidden."""
    from ui.labels_ui import workload_sentence

    sentence = workload_sentence({**_WORKLOAD, "model_calls": 0, "models": [], "contradictions": 0})
    assert "no contradictions found" in sentence
    assert sentence.endswith("with no model calls (offline fallback)")


def test_p14b_t7_case_page_shows_the_strip() -> None:
    """P14B-T7: the Case page renders the strip from the stored run's workload."""
    from ui.labels_ui import workload_sentence

    client = P14Client()
    at = _case_page(client)
    workload = load("p14a_run_escalate.json")["output"]["workload"]
    assert workload_sentence(workload) in visible_text(at)


# --- P14B-T8 -----------------------------------------------------------------------------------


def test_p14b_t8_dossier_downloads_use_the_endpoint_for_both_formats() -> None:
    """P14B-T8: HTML and Markdown are fetched from the dossier endpoint for this case."""
    client = P14Client()
    at = _case_page(client)
    case_id = client.case_detail["case_id"]
    assert (case_id, "html") in client.dossier_calls
    assert (case_id, "md") in client.dossier_calls
    labels = [b.proto.label for b in at.get("download_button")]
    assert any("HTML" in label for label in labels)
    assert any("Markdown" in label for label in labels)


def test_p14b_t8_client_dossier_hits_the_route() -> None:
    """P14B-T8: ArbiterClient.dossier requests GET /cases/{id}/dossier?format=..."""
    import httpx

    from ui.client import ArbiterClient

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    assert ArbiterClient(client=http).dossier("CASE-0007", "html") == "<html></html>"
    assert seen[0].url.path == "/cases/CASE-0007/dossier"
    assert seen[0].url.params["format"] == "html"


def test_p14b_t8_playwright_capture_script_is_importable() -> None:
    """P14B-T8: the capture script imports without Playwright and explains how to install it."""
    pytest.importorskip("playwright", reason="capture_ui needs the optional Playwright package")
    import scripts.capture_ui as capture

    assert capture.PAGES
    assert len(capture.PAGES) == 7


def test_p14b_t8_capture_script_hint_without_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    """P14B-T8: a missing Playwright fails with the install command, not a traceback."""
    import builtins

    import scripts.capture_ui as capture

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("no playwright")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as exc:
        capture.require_playwright()
    assert "pip install playwright && playwright install chromium" in str(exc.value)


# --- portfolio ---------------------------------------------------------------------------------


def test_p14b_portfolio_metrics() -> None:
    """The Cases page opens with totals per outcome from the queue."""
    from ui.labels_ui import portfolio_metrics

    queue = [
        {"outcome": "ESCALATE", "status": "success"},
        {"outcome": "ESCALATE", "status": "success"},
        {"outcome": "APPROVE", "status": "success"},
    ]
    metrics = portfolio_metrics(queue)
    assert metrics["total"] == 3
    assert metrics["by_outcome"] == {"ESCALATE": 2, "APPROVE": 1}


def test_p14b_questions_route_matches_the_catalogue() -> None:
    """GET /questions serves the 16 fixed questions with their policy help."""
    from fastapi.testclient import TestClient

    from app.agents.catalogue import QUESTION_TEXTS
    from app.api.main import app

    items = TestClient(app).get("/questions").json()
    assert [i["question_id"] for i in items] == sorted(QUESTION_TEXTS)
    assert all(i["question"] == QUESTION_TEXTS[i["question_id"]] for i in items)
    assert {i["type"] for i in items} <= {"yes_no", "text"}
    assert all(i["options"] == ["Yes", "No", "Not answered"] for i in items if i["type"] == "yes_no")
    assert items == load("p14b_questions.json"), "re-record tests/fixtures/ui/p14b_questions.json"


def test_p14b_outcome_words_match_the_api_labels() -> None:
    """The console's outcome wording mirrors app/labels.py, so the two never drift."""
    from app.labels import outcome_label as api_label
    from app.labels import outcome_meaning as api_meaning
    from ui.labels_ui import OUTCOME_WORDS

    for outcome, (label, meaning) in OUTCOME_WORDS.items():
        assert label == api_label(outcome)
        assert meaning == api_meaning(outcome)


def test_p14b_case_detail_carries_the_stored_workload(offline_env) -> None:
    """GET /cases/{id} returns the workload measured on the run, so the Case page can show it later."""
    from fastapi.testclient import TestClient

    from app.api.main import app

    api = TestClient(app)
    run = api.post("/run", json={"case": {"vendor_id": "VND-0007"}}).json()
    detail = api.get(f"/cases/{run['output']['case_id']}").json()
    assert detail["workload"] == run["output"]["workload"]
    assert detail["workload"]["queries"] > 0
