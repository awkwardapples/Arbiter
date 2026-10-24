"""New assessment: existing-vendor picker, the questionnaire form, and the JSON escape hatch (lane P14-B)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import streamlit as st
from pydantic import ValidationError

from ui.client import ArbiterAPIError
from ui.components import NEW_ASSESSMENT_CAPTION
from ui.labels_ui import workload_sentence
from ui.models import CaseInput
from ui.screens import ASSESSMENT_SPINNER
from ui.session import get_client
from ui.validation import parse_case_input

PRESETS_PATH = Path(__file__).with_name("presets.json")
CATEGORIES = ["SaaS", "Internal tools", "Infrastructure", "Professional services", "Hardware", "Other"]
DATA_CATEGORIES = ["none", "internal", "personal", "payment", "special_category"]
COUNTRIES = ["GB", "IE", "DE", "FR", "NL", "ES", "IT", "US", "CA", "IN", "SG", "AU", "JP"]
DOC_TYPES = ["SOC 2 Type II", "ISO 27001", "Penetration test", "Bridge letter", "Other"]
CHOICES = ["Yes", "No", "Not answered"]
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DOC_COLUMNS = ["doc_type", "title", "issued_on", "expires_on", "text"]
_COMPONENT_COLUMNS = ["vendor", "product", "version"]


def load_presets() -> dict[str, dict[str, Any]]:
    data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {str(item["name"]): item for item in data["presets"]}


def _answer_text(question: dict[str, Any], entry: dict[str, Any]) -> str:
    choice = entry.get("choice")
    how = str(entry.get("how") or "").strip()
    if question["type"] == "yes_no":
        if choice not in ("Yes", "No"):
            return ""
        return f"{choice}. {how}" if how else f"{choice}."
    return how


def _clean_rows(rows: Any, columns: list[str]) -> list[dict[str, str]]:
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    cleaned = []
    for row in rows or []:
        item = {col: str(row.get(col) or "").strip() for col in columns}
        if any(item.values()):
            cleaned.append(item)
    return cleaned


def build_case_input(
    form: dict[str, Any], questions: list[dict[str, Any]]
) -> tuple[CaseInput | None, list[str]]:
    """Turn the questionnaire into a CaseInput. Returns (None, errors) when anything is invalid."""
    errors: list[str] = []
    if not str(form.get("legal_name") or "").strip():
        errors.append("Legal name is required.")
    if not str(form.get("requested_service") or "").strip():
        errors.append("Describe the service being requested.")
    if float(form.get("annual_spend_gbp") or 0) < 0:
        errors.append("Annual spend cannot be negative.")
    if not form.get("data_categories"):
        errors.append("Choose at least one data category (or 'none').")
    if not form.get("processing_countries"):
        errors.append("Choose at least one processing country.")
    documents = []
    for index, row in enumerate(_clean_rows(form.get("documents"), _DOC_COLUMNS), start=1):
        for field in ("issued_on", "expires_on"):
            if row[field] and not _DATE.fullmatch(row[field]):
                errors.append(f"Document {index}: {field.replace('_', ' ')} must look like 2026-03-01.")
        if not row["text"]:
            errors.append(f"Document {index}: paste the document text.")
        documents.append(
            {
                "doc_id": f"D{index:02d}",
                "doc_type": row["doc_type"] or "Other",
                "title": row["title"] or row["doc_type"] or f"Document {index}",
                "issued_on": row["issued_on"] or None,
                "expires_on": row["expires_on"] or None,
                "text": row["text"],
            }
        )
    components = []
    for index, row in enumerate(_clean_rows(form.get("components"), _COMPONENT_COLUMNS), start=1):
        if not row["product"]:
            errors.append(f"Component {index}: product is required.")
            continue
        components.append({k: (row[k] or None) for k in _COMPONENT_COLUMNS} | {"product": row["product"]})
    answers = []
    for question in questions:
        text = _answer_text(question, (form.get("answers") or {}).get(question["question_id"]) or {})
        if text:
            answers.append(
                {
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "answer_text": text,
                }
            )
    if errors:
        return None, errors
    patch = form.get("patch_sla_critical_days")
    submission = {
        "legal_name": str(form["legal_name"]).strip(),
        "trading_name": str(form.get("trading_name") or "").strip() or None,
        "category": form.get("category") or "Other",
        "requested_service": str(form["requested_service"]).strip(),
        "criticality": form.get("criticality") or "low",
        "annual_spend_gbp": float(form.get("annual_spend_gbp") or 0),
        "data_categories": list(form["data_categories"]),
        "processing_countries": list(form["processing_countries"]),
        "answers": answers,
        "documents": documents,
        "declared_components": components,
        "patch_sla_critical_days": int(patch) if patch else None,
    }
    try:
        return CaseInput.model_validate({"submission": submission}), []
    except ValidationError as exc:
        return None, [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]


# --- widgets -----------------------------------------------------------------------------------


def _apply_preset() -> None:
    preset = load_presets().get(st.session_state.get("preset", ""))
    if preset is None:
        return
    for key in ("legal_name", "trading_name", "category", "requested_service", "criticality"):
        st.session_state[key] = preset.get(key) or ""
    st.session_state["annual_spend_gbp"] = float(preset["annual_spend_gbp"])
    st.session_state["data_categories"] = list(preset["data_categories"])
    st.session_state["processing_countries"] = list(preset["processing_countries"])
    st.session_state["patch_sla_critical_days"] = int(preset.get("patch_sla_critical_days") or 0)
    st.session_state["documents_rows"] = list(preset.get("documents") or [])
    st.session_state["components_rows"] = list(preset.get("components") or [])
    for question_id, entry in preset["answers"].items():
        st.session_state[f"q_choice_{question_id}"] = entry.get("choice") or "Not answered"
        st.session_state[f"q_how_{question_id}"] = entry.get("how") or ""


def _form_values(questions: list[dict[str, Any]], documents: Any, components: Any) -> dict[str, Any]:
    state = st.session_state
    return {
        "legal_name": state.get("legal_name", ""),
        "trading_name": state.get("trading_name", ""),
        "category": state.get("category", "SaaS"),
        "requested_service": state.get("requested_service", ""),
        "criticality": state.get("criticality", "low"),
        "annual_spend_gbp": state.get("annual_spend_gbp", 0.0),
        "data_categories": state.get("data_categories", []),
        "processing_countries": state.get("processing_countries", []),
        "patch_sla_critical_days": state.get("patch_sla_critical_days", 0),
        "documents": documents,
        "components": components,
        "answers": {
            q["question_id"]: {
                "choice": state.get(f"q_choice_{q['question_id']}"),
                "how": state.get(f"q_how_{q['question_id']}", ""),
            }
            for q in questions
        },
    }


def run_and_open(client: Any, case_input: CaseInput) -> None:
    """Run the assessment, report what was actually done, then open the case."""
    with st.status(ASSESSMENT_SPINNER) as status:
        try:
            response = client.run(case_input)
        except ArbiterAPIError as exc:
            status.update(label="The assessment did not complete", state="error")
            st.error(exc.message)
            return
        output = response.get("output") or {}
        case_id = str(output.get("case_id") or "")
        status.update(label=f"Assessment complete: {case_id}", state="complete")
        if output.get("workload"):
            st.write(workload_sentence(output["workload"]))
    if case_id:
        st.session_state["last_case_id"] = case_id
        st.session_state["nav_case_id"] = case_id
        st.switch_page("pages/case.py")


def _existing_tab(client: Any) -> None:
    try:
        vendors = client.list_vendors()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    labels: dict[str, str] = {}
    for vendor in vendors:
        status = str(vendor.get("onboarding_status") or "").replace("_", " ")
        label = f"{vendor.get('legal_name')} ({status})" if status else str(vendor.get("legal_name"))
        while label in labels:
            label += " "
        labels[label] = str(vendor.get("vendor_id"))
    pick = st.selectbox("Vendor", list(labels) or ["No vendors available"], key="existing_vendor")
    case_input, errors = parse_case_input({"vendor_id": labels[pick]}) if pick in labels else (None, [])
    for err in errors:
        st.error(err)
    if st.button("Run assessment", type="primary", disabled=case_input is None, key="run_existing"):
        run_and_open(client, case_input)


def _question_widget(question: dict[str, Any]) -> None:
    qid = question["question_id"]
    with st.container(border=True):
        st.markdown(f"**{question['question']}**")
        if question.get("help"):
            st.caption(question["help"])
        if question["type"] == "yes_no":
            cols = st.columns([1, 3])
            cols[0].selectbox("Answer", question.get("options") or CHOICES, index=2, key=f"q_choice_{qid}")
            cols[1].text_input("How? (mechanism, e.g. AES-256)", key=f"q_how_{qid}")
        else:
            st.text_input("Answer", key=f"q_how_{qid}")


def _questionnaire_tab(client: Any) -> None:
    try:
        questions = client.questions()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    presets = load_presets()
    st.selectbox(
        "Load an example vendor",
        ["—", *presets],
        key="preset",
        on_change=_apply_preset,
        help="Fills the whole form; edit anything before running.",
    )
    left, right = st.columns(2)
    left.text_input("Legal name", key="legal_name")
    right.text_input("Trading name (optional)", key="trading_name")
    left.text_input("Service requested", key="requested_service")
    right.selectbox("Category", CATEGORIES, key="category")
    left.selectbox("Criticality", ["low", "medium", "high"], key="criticality")
    right.number_input("Annual spend (GBP)", min_value=0.0, step=1000.0, key="annual_spend_gbp")
    left.multiselect("Data categories", DATA_CATEGORIES, key="data_categories")
    right.multiselect("Processing countries", COUNTRIES, key="processing_countries")
    st.number_input(
        "Critical patch SLA in days (0 = not stated)", min_value=0, step=1, key="patch_sla_critical_days"
    )
    st.subheader("Security questionnaire")
    st.caption(
        "Leave a question as 'Not answered' if the vendor did not reply; the policy treats it as unverified."
    )
    for question in questions:
        _question_widget(question)
    st.subheader("Assurance documents (optional)")
    documents = st.data_editor(
        st.session_state.get("documents_rows") or [dict.fromkeys(_DOC_COLUMNS, "")],
        num_rows="dynamic",
        key="documents_editor",
        column_config={"doc_type": st.column_config.SelectboxColumn("Type", options=DOC_TYPES)},
    )
    st.subheader("Declared software components (optional)")
    components = st.data_editor(
        st.session_state.get("components_rows") or [dict.fromkeys(_COMPONENT_COLUMNS, "")],
        num_rows="dynamic",
        key="components_editor",
    )
    if st.button("Run assessment", type="primary", key="run_questionnaire"):
        case_input, errors = build_case_input(_form_values(questions, documents, components), questions)
        for err in errors:
            st.error(err)
        if case_input is not None:
            run_and_open(client, case_input)


def _advanced_tab(client: Any) -> None:
    uploaded = st.file_uploader("Upload JSON", type=["json"])
    raw_text = st.text_area("Or paste JSON", height=160)
    payload = uploaded.read().decode("utf-8") if uploaded is not None else raw_text
    case_input, errors = parse_case_input(payload) if payload.strip() else (None, [])
    for err in errors:
        st.error(err)
    if st.button("Run assessment", disabled=case_input is None, key="run_json"):
        run_and_open(client, case_input)


def render_new_assessment() -> None:
    st.title("New assessment")
    st.caption(NEW_ASSESSMENT_CAPTION)
    client = get_client()
    existing, questionnaire = st.tabs(["Existing vendor", "New vendor questionnaire"])
    with existing:
        _existing_tab(client)
    with questionnaire:
        _questionnaire_tab(client)
    with st.expander("Advanced: paste or upload JSON"):
        _advanced_tab(client)
