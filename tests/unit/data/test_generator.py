"""Generator acceptance tests P1-T1..T4, T9, T12."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

import pytest
import yaml

from app.canon import sha256_hex
from data.generator.generate import ROOT, _assert_scenarios, _build_vendors, _load_kev
from data.generator.kev_match import kev_matches

SYSTEMS_DIR = ROOT / "data" / "sample" / "systems"
LEAK_RE = re.compile(
    r"\bS0?[0-9]{2}\b|"
    r"\b(APPROVE|DECLINE|ESCALATE|REQUEST_INFO|APPROVE_WITH_CONDITIONS)\b|"
    r"expected|label"
)


def _tracked_files() -> list[Path]:
    paths = list(SYSTEMS_DIR.glob("*.json"))
    paths.extend(
        [
            ROOT / "data" / "evals" / "labels.jsonl",
            ROOT / "data" / "evals" / "splits.json",
            ROOT / "input_examples" / "expected.json",
        ]
    )
    return paths


@pytest.mark.p1a
def test_p1_t1_generator_idempotent() -> None:
    """P1-T1: same seed yields byte-identical outputs."""
    from data.generator.generate import generate

    def file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    before = {p.name: file_hash(p) for p in _tracked_files()}
    generate(seed=2026, as_of=date(2026, 10, 26))
    after = {p.name: file_hash(p) for p in _tracked_files()}
    assert before == after


@pytest.mark.p1a
def test_p1_t2_flat_envelope_and_scalars() -> None:
    """P1-T2: envelope shape and scalar rows."""
    for path in SYSTEMS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert set(data.keys()) >= {"system", "generated_at", "as_of", "count", "records"}
        assert data["count"] == len(data["records"])
        for row in data["records"]:
            for val in row.values():
                assert not isinstance(val, (list, dict))


@pytest.mark.p1a
def test_p1_t3_no_label_leakage() -> None:
    """P1-T3: served records must not contain scenario labels."""
    for path in SYSTEMS_DIR.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert not LEAK_RE.search(text), path.name


@pytest.mark.p1a
def test_p1_t4_scenario_assertions() -> None:
    """P1-T4: planted evidence matches scenarios.yaml."""
    spec = yaml.safe_load((ROOT / "data/generator/scenarios.yaml").read_text(encoding="utf-8"))
    bank = yaml.safe_load((ROOT / "data/generator/phrasebank.yaml").read_text(encoding="utf-8"))
    import random

    vendors = _build_vendors(random.Random(2026), spec, bank)
    kev = _load_kev()
    _assert_scenarios(vendors, kev)
    by_id = {v.vendor_id: v for v in vendors}
    assert _count_kev(by_id["VND-0007"], kev) >= 1
    assert _count_kev(by_id["VND-0003"], kev) == 0
    assert by_id["VND-0028"].dq_dpa_date_null
    assert by_id["VND-0019"].watchlist_hits


def _count_kev(v, kev):  # noqa: ANN001
    n = 0
    for comp in v.components:
        for entry in kev:
            if kev_matches(
                kev_vendor_project=str(entry.get("vendorProject", "")),
                kev_product=str(entry.get("product", "")),
                component_vendor_project=comp["vendor_project"],
                component_product=comp["product"],
            ):
                n += 1
    return n


@pytest.mark.p1a
def test_p1_t9_splits_stratified_and_hashes() -> None:
    """P1-T9: splits.json stratification and sha256 fields."""
    splits = json.loads((ROOT / "data/evals/splits.json").read_text(encoding="utf-8"))
    cal = set(splits["calibration"])
    test = set(splits["test"])
    assert not cal.intersection(test)
    assert splits["sha256"]["calibration"] == sha256_hex(sorted(cal))
    assert splits["sha256"]["test"] == sha256_hex(sorted(test))
    scenario_by_vendor = {
        json.loads(line)["case_ref"]: json.loads(line)["scenario"]
        for line in (ROOT / "data/evals/labels.jsonl").read_text().splitlines()
        if line.strip()
    }
    from collections import Counter

    counts = Counter(scenario_by_vendor.values())
    for scen, n in counts.items():
        if n >= 2:
            vendors = [v for v, s in scenario_by_vendor.items() if s == scen]
            in_cal = sum(1 for v in vendors if v in cal)
            in_test = sum(1 for v in vendors if v in test)
            assert in_cal >= 1 and in_test >= 1, scen


@pytest.mark.p1a
def test_p1_t12_kev_snapshot_shape() -> None:
    """P1-T12: KEV snapshot keeps required keys."""
    data = json.loads((ROOT / "data/kev/kev_snapshot.json").read_text(encoding="utf-8"))
    for key in ("title", "catalogVersion", "dateReleased", "count", "vulnerabilities"):
        assert key in data
    assert data["count"] == len(data["vulnerabilities"])
    if data["vulnerabilities"]:
        entry = data["vulnerabilities"][0]
        assert "cveID" in entry or "cve_id" in entry
