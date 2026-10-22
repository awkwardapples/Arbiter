"""Download and filter CISA KEV catalogue for the sample snapshot."""

from __future__ import annotations

import json
import random
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOGUE_PRODUCTS = [
    "MOVEit Transfer",
    "FortiOS",
    "NetScaler ADC",
    "Confluence Data Center",
    "Endpoint Manager Mobile",
]


def fetch_kev(*, url: str, seed: int, out_path: Path, source_md: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    vulns = list(raw.get("vulnerabilities") or [])
    matched = [
        v for v in vulns if any(p.lower() in str(v.get("product", "")).lower() for p in CATALOGUE_PRODUCTS)
    ]
    rng = random.Random(seed)
    others = [v for v in vulns if v not in matched]
    rng.shuffle(others)
    extra = others[:50]
    selected = matched + extra
    out = {
        "title": raw.get("title"),
        "catalogVersion": raw.get("catalogVersion"),
        "dateReleased": raw.get("dateReleased"),
        "count": len(selected),
        "vulnerabilities": selected,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    retrieved = datetime.now(UTC).isoformat()
    source_md.write_text(
        "\n".join(
            [
                "# CISA Known Exploited Vulnerabilities snapshot",
                "",
                f"- **URL:** {url}",
                f"- **catalogVersion:** {out.get('catalogVersion')}",
                f"- **dateReleased:** {out.get('dateReleased')}",
                f"- **Retrieved (UTC):** {retrieved}",
                "- **Licence:** CC0 1.0 (see CISA feed terms)",
                "- **Notice:** No U.S. Government endorsement; synthetic Arbiter sample filter.",
                "",
            ]
        ),
        encoding="utf-8",
    )
