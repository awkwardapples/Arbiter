from __future__ import annotations

import importlib
import json
import pkgutil
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.p0

RUN_RESPONSE_EXAMPLE = {
    "run_id": "run-20261024-0007-a1b2",
    "status": "success",
    "output": {
        "case_id": "CASE-0007",
        "vendor": {"vendor_id": "VND-0007", "legal_name": "Quillfeather Payroll Cloud Ltd"},
        "decision": "ESCALATE",
        "risk_tier": "T1",
        "residual_risk": 74,
        "confidence": {"value": 0.58, "gate": 0.9, "abstained": True},
        "summary": "cited summary",
        "findings": [{"text": "finding", "citations": ["F-C09-1", "E-clm-CTR-00031"]}],
        "contradictions": [
            {"key": "residency.regions", "claim": "EU only", "system_of_record": "US (CLM clause)"}
        ],
        "counterfactuals": [
            {"control_id": "C12", "evidence_required": ["patch attestation for MOVEit Transfer"]}
        ],
        "precedents": [],
        "recommendations": ["recommend"],
        "actions": [
            {
                "contract_id": "CTR-01J",
                "intent": "vendor.onboarding.escalate",
                "state": "executed",
                "capability": "itsm.ticket.create",
            }
        ],
        "artifacts": ["var/outbox/itsm/ITSM-DRAFT-0007.json"],
        "limitations": ["Synthetic data"],
    },
    "agents": [{"name": "PlannerAgent", "role": "Plans evidence gathering; revises on feedback"}],
    "trace_id": "run-20261024-0007-a1b2",
    "log_file": "logs/trace-run-20261024-0007-a1b2.jsonl",
    "execution_time_seconds": 71.4,
    "mode": {
        "data": "zetaris",
        "llm": "meterless",
        "models": ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3.5-lightning-30b-a3b"],
    },
}

EXPECTED_FACT_KEYS_FROM_SPECS = {
    "mfa.admin_enforced",
    "mfa.remote_enforced",
    "creds.rotation_days",
    "creds.vaulted",
    "access.review_interval_days",
    "crypto.at_rest",
    "crypto.in_transit_tls12",
    "assurance.claimed",
    "incidents.vendor_reported_24m",
    "breach.notify_hours_claimed",
    "residency.regions_claimed",
    "transfer.mechanism_claimed",
    "subprocessors.disclosed_claimed",
    "vuln.patch_sla_critical_days",
    "pentest.interval_months",
    "dpa.vendor_commits",
    "vendor.data_categories",
    "assurance.soc2_type2_current",
    "assurance.iso27001_current",
    "assurance.bridge_letter_current",
    "incidents.itsm_vendor_related_24m",
    "incidents.material_unremediated_24m",
    "breach.notify_hours",
    "dpa.signed",
    "residency.regions",
    "transfer.mechanism",
    "subprocessors.disclosed",
    "sanctions.watchlist_matches",
    "sanctions.near_matches",
    "vuln.components_declared",
    "vuln.kev_matches",
    "contract.status",
    "breach.notify_hours_contract",
    "residency.regions_contract",
}


def test_p0_t1_settings_defaults_and_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import Settings, env_example_defaults

    monkeypatch.chdir(ROOT)
    for var in (
        "SAMPLE_MODE",
        "LLM_PROVIDER",
        "METERLESS_RUNTIME_TOKEN",
        "NVIDIA_API_KEY",
        "ZETARIS_API_KEY",
        "ARBITER_SIGNING_KEY",
        "MODEL_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)
    example = env_example_defaults()
    assert settings.SAMPLE_MODE is (example["SAMPLE_MODE"].lower() == "true")
    assert example["LLM_PROVIDER"] == settings.LLM_PROVIDER
    assert int(example["PORT"]) == settings.PORT
    for secret_field in (
        "METERLESS_RUNTIME_TOKEN",
        "NVIDIA_API_KEY",
        "ZETARIS_API_KEY",
        "ARBITER_SIGNING_KEY",
    ):
        assert getattr(settings, secret_field) is None

    from dotenv import dotenv_values

    env_path = ROOT / ".env.example"
    for k, v in dotenv_values(env_path).items():
        if v is not None:
            monkeypatch.setenv(k, v)
    from app.config import get_settings

    get_settings.cache_clear()
    loaded = Settings()
    for secret_field in (
        "METERLESS_RUNTIME_TOKEN",
        "NVIDIA_API_KEY",
        "ZETARIS_API_KEY",
        "ARBITER_SIGNING_KEY",
    ):
        assert getattr(loaded, secret_field) is None

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-abcdefghijklmnopqrstuvwxyz123456")
    monkeypatch.setenv("ZETARIS_API_KEY", "sk-abcdefghijklmnopqrstuvwxyz1234567890")
    get_settings.cache_clear()
    leaked = Settings()
    blob = repr(leaked) + str(leaked) + json.dumps(leaked.redacted_dict())
    assert "nvapi-abcdefghijklmnopqrstuvwxyz123456" not in blob
    assert "sk-abcdefghijklmnopqrstuvwxyz1234567890" not in blob


def test_p0_t2_organiser_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import Settings

    alias_vars = (
        "NVIDIA_BASE_URL",
        "NVIDIA_API_KEY",
        "NVIDIA_MODEL_FAST",
        "MODEL_BASE_URL",
        "MODEL_API_KEY",
        "NEMOTRON_MODEL",
    )
    for var in alias_vars:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MODEL_BASE_URL", "http://organiser.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "nvapi-organiseraliaskey123456789012345")
    monkeypatch.setenv("NEMOTRON_MODEL", "nvidia/custom-model")
    s = Settings()
    assert s.NVIDIA_BASE_URL == "http://organiser.example/v1"
    assert s.NVIDIA_API_KEY is not None
    assert s.NVIDIA_API_KEY.get_secret_value().startswith("nvapi-organiser")
    assert s.NVIDIA_MODEL_FAST == "nvidia/custom-model"

    for var in ("NVIDIA_BASE_URL", "NVIDIA_API_KEY", "MODEL_BASE_URL", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NVIDIA_BASE_URL", "http://native.example/v1")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-nativekey1234567890123456789012")
    monkeypatch.setenv("MODEL_BASE_URL", "http://organiser.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "nvapi-shouldnotwin123456789012345678901")
    s2 = Settings()
    assert s2.NVIDIA_BASE_URL == "http://native.example/v1"
    assert s2.NVIDIA_API_KEY.get_secret_value().startswith("nvapi-native")


def test_p0_t3_schemas() -> None:
    from pydantic import ValidationError

    from app.schemas.api import RunRequest, RunResponse
    from app.schemas.case import CaseInput
    from app.schemas.trace import TraceEvent

    RunResponse.model_validate(RUN_RESPONSE_EXAMPLE)
    with pytest.raises(ValidationError):
        CaseInput.model_validate({})
    with pytest.raises(ValidationError):
        CaseInput.model_validate({"vendor_id": "VND-0001", "submission": {"legal_name": "x"}})
    bare = RunRequest.model_validate({"vendor_id": "VND-0001"})
    assert bare.case.vendor_id == "VND-0001"
    wrapped = RunRequest.model_validate(
        {"input": {"vendor_id": "VND-0002"}, "options": {"sample_mode": True}}
    )
    assert wrapped.case.vendor_id == "VND-0002"
    assert wrapped.options is not None and wrapped.options.sample_mode is True
    TraceEvent.model_validate(
        {
            "timestamp": "2026-10-24T12:00:00Z",
            "run_id": "r1",
            "trace_id": "r1",
            "span_id": "s1",
            "agent_name": "PlannerAgent",
            "action": "plan",
            "input_summary": "in",
            "output_summary": "out",
            "status": "success",
        }
    )


def test_p0_t4_canonical_json() -> None:
    from pydantic import BaseModel

    from app.canon import canonical_json, sha256_hex

    dt = datetime(2026, 10, 24, 15, 30, 0, tzinfo=UTC)

    class M(BaseModel):
        b: int
        a: str

    obj = {"z": 1, "a": M(a="x", b=2), "t": dt}
    c1 = canonical_json(obj)
    c2 = canonical_json({"a": {"a": "x", "b": 2}, "t": dt, "z": 1})
    assert c1 == c2
    assert "2026-10-24T15:30:00Z" in c1
    golden = sha256_hex({"hello": "arbiter", "n": 1})
    assert sha256_hex({"hello": "arbiter", "n": 1}) == golden
    assert golden == "e3050c1edc1e388c442dbd270fe1829e214b9316bd9ecf3df5a59b3fb5e33c12"


def test_p0_t5_tracer(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    from app.schemas.trace import TraceEvent
    from app.tracing import Tracer

    caplog.set_level(logging.INFO, logger="arbiter.trace")
    fake_key = "nvapi-abcdefghijklmnopqrstuvwxyz1234567890"
    tracer = Tracer("run-test-1", mode={"data": "duckdb", "llm": "offline"}, log_dir=str(tmp_path))
    tracer.event(
        "EvidenceAgent",
        "extract",
        input_summary=f"key={fake_key}",
        output_summary="done",
        target_agent="EvaluatorAgent",
    )
    tracer.close()
    log_file = tmp_path / "trace-run-test-1.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    evt = TraceEvent.model_validate_json(lines[0])
    assert fake_key not in lines[0]
    assert "***" in evt.input_summary or "nvapi" not in evt.input_summary
    assert any("EvidenceAgent" in r.message for r in caplog.records)


def test_p0_t6_api_health_and_errors() -> None:
    from app.api.main import app

    client = TestClient(app, raise_server_exceptions=False)
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert "mode" in body
    assert "nvapi-" not in json.dumps(body)
    run = client.post("/run", json={"vendor_id": "VND-0001"})
    assert run.status_code == 501
    err = run.json()
    assert err["error"]["type"] == "NotImplemented"
    bad = client.post("/run", json={"vendor_id": 123})
    assert bad.status_code == 400
    assert bad.json()["error"]["type"] == "ValidationFailed"

    def _boom() -> None:
        raise RuntimeError("traceback should not appear")

    app.get("/__test_crash")(_boom)
    crash = client.get("/__test_crash")
    assert crash.status_code == 500
    assert "traceback" not in crash.text.lower()
    assert "RuntimeError" not in crash.text


def test_p0_t7_scan_secrets(tmp_path: Path) -> None:
    samples = {
        "sk.txt": "sk-abcdefghijklmnopqrstuvwxyz123456",
        "nv.txt": "nvapi-abcdefghijklmnopqrstuvwxyz",
        "aws.txt": "AKIAIOSFODNN7EXAMPLE",
        "gh.txt": "ghp_1234567890123456789012345678901234",
        "slack.txt": "xoxb-1234567890-abcdefghij",
        "pem.txt": "-----BEGIN RSA PRIVATE KEY-----",
        "jwt.txt": "eyJhbGciOiJIUzI1NiIs.eyJzdWIiOiIxIn0.signature",
        "assign.txt": "api_key = 'real_secret_value_12345'",
        "ok.txt": "api_key=your-nvapi-key",
    }
    for name, content in samples.items():
        (tmp_path / name).write_text(content + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scan_secrets.py"), str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    out = proc.stdout
    assert "real_secret_value_12345" not in out
    assert "sk.txt" in out


def test_p0_t8_check_hardcoding(tmp_path: Path) -> None:
    agents = tmp_path / "app" / "agents"
    agents.mkdir(parents=True)
    (agents / "x.py").write_text('PATH = "output_examples"\nVENDOR = "VND-0007"\n', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_hardcoding.py"), str(tmp_path / "app")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "output_examples" in proc.stdout
    assert "VND-0007" in proc.stdout


def test_p0_t9_check_trace(tmp_path: Path) -> None:
    good = tmp_path / "good.jsonl"
    ts = "2026-10-24T12:00:00+00:00"
    good.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": ts,
                        "run_id": "r",
                        "trace_id": "r",
                        "span_id": "a",
                        "agent_name": "PlannerAgent",
                        "action": "plan",
                        "input_summary": "i",
                        "output_summary": "o",
                        "status": "success",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": ts,
                        "run_id": "r",
                        "trace_id": "r",
                        "span_id": "b",
                        "agent_name": "EvaluatorAgent",
                        "action": "evaluate",
                        "input_summary": "i",
                        "output_summary": "o",
                        "status": "needs_revision",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    ok = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_trace.py"), str(good), "--require-collaboration"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr

    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "run_id": "r",
                "trace_id": "r",
                "span_id": "a",
                "agent_name": "A",
                "action": "x",
                "input_summary": "nvapi-leakedsecret123456789012345678901234",
                "output_summary": "o",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )
    fail = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_trace.py"), str(bad)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert fail.returncode == 1


def test_p0_t10_run_py_help() -> None:
    help_proc = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    text = help_proc.stdout
    for cmd in (
        "serve",
        "ui",
        "preflight",
        "generate-data",
        "sources",
        "zetaris",
        "llm",
        "guard-eval",
        "assess",
        "review",
        "demo-session",
        "replay",
        "audit-verify",
        "eval",
        "calibrate",
        "examples",
    ):
        assert cmd in text
    unknown = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "not-a-command"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert unknown.returncode == 2


def test_p0_t11_env_example_contract() -> None:
    from app.config import Settings

    env_path = ROOT / ".env.example"
    text = env_path.read_text(encoding="utf-8")
    assert not re.search(r"=\S[^\n]*[ \t]+#", text)
    fields = set(Settings.model_fields.keys())
    keys: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    assert fields <= keys
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scan_secrets.py"), str(env_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout


def test_p0_t12_fact_keys() -> None:
    from app.schemas.facts import FACT_KEYS

    assert len(FACT_KEYS) == len(set(FACT_KEYS))
    for key in FACT_KEYS:
        assert key == key.lower()
        assert "." in key
    assert EXPECTED_FACT_KEYS_FROM_SPECS <= FACT_KEYS


def test_p0_t13_import_all_app_modules() -> None:
    import app

    failures: list[str] = []
    prefix = app.__name__ + "."
    for modinfo in pkgutil.walk_packages(app.__path__, prefix):
        try:
            importlib.import_module(modinfo.name)
        except Exception as exc:
            failures.append(f"{modinfo.name}: {exc}")
    assert not failures, "\n".join(failures)
