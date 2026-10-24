"""Capture the analyst console as PNG screenshots for the docs (lane P14-B). Not part of CI.

Needs a running API and console, and Playwright with Chromium (a dev-only capture step):

    pip install playwright && playwright install chromium
    python run.py serve                      # API on :8000
    streamlit run ui/app.py                  # console on :8501
    python run.py demo-session               # once, so the precedents page has rows
    python scripts/capture_ui.py             # writes docs/img/ui_<page>.png at 1440x1000

Case pages are found by vendor name from the API; an example is run only if its case is missing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
VIEWPORT = {"width": 1440, "height": 1000}
INSTALL_HINT = "Playwright is not installed. Run: pip install playwright && playwright install chromium"

# name, output file, example (case pages), console path
PAGES: list[dict[str, str]] = [
    {"name": "brief", "file": "ui_brief.png", "example": "example_2.json", "path": "case"},
    {"name": "next_action", "file": "ui_next_action.png", "example": "example_4.json", "path": "case"},
    {"name": "questionnaire", "file": "ui_questionnaire.png", "example": "", "path": ""},
    {"name": "cases", "file": "ui_cases.png", "example": "", "path": "queue"},
    {"name": "sources", "file": "ui_sources.png", "example": "", "path": "sources"},
    {"name": "precedents", "file": "ui_precedents.png", "example": "", "path": "memory"},
    {"name": "audit", "file": "ui_audit.png", "example": "", "path": "audit"},
]
SECRET_ENV = ("METERLESS_TOKEN", "NVIDIA_API_KEY", "ZETARIS_PASSWORD", "ARBITER_SIGNING_KEY")


def require_playwright() -> Any:
    """Return Playwright's sync entry point, or exit with the install command."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(INSTALL_HINT) from None
    return sync_playwright


def find_case(api: httpx.Client, example: str) -> str:
    """Case id for an input example: match by vendor, else run the example once."""
    payload = json.loads((ROOT / "input_examples" / example).read_text(encoding="utf-8"))
    vendor_id = payload.get("vendor_id")
    vendors = {v["vendor_id"]: v["legal_name"] for v in api.get("/vendors").json()}
    name = vendors.get(vendor_id)
    for item in api.get("/cases").json():
        if name and item.get("vendor") == name:
            return str(item["case_id"])
    response = api.post("/run", json={"case": payload}, timeout=180)
    response.raise_for_status()
    return str(response.json()["output"]["case_id"])


def wait_idle(page: Any, settle: float = 0.8) -> None:
    """Streamlit is idle when its running indicator is gone and the network is quiet."""
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("[data-testid='stStatusWidget']", state="detached", timeout=60_000)
    time.sleep(settle)


def assert_no_secrets(page: Any) -> None:
    text = page.inner_text("body")
    for name in SECRET_ENV:
        value = os.environ.get(name, "")
        if len(value) >= 8 and value in text:
            raise SystemExit(f"Refusing to capture: the value of {name} is visible on the page.")


def prepare(page: Any, spec: dict[str, str], ui_url: str, api: httpx.Client) -> None:
    if spec["name"] in ("brief", "next_action"):
        case_id = find_case(api, spec["example"])
        page.goto(f"{ui_url}/{spec['path']}?case_id={case_id}")
        wait_idle(page)
        if spec["name"] == "next_action":
            page.get_by_role("heading", name="Next action").scroll_into_view_if_needed()
    elif spec["name"] == "questionnaire":
        page.goto(ui_url)
        wait_idle(page)
        page.get_by_role("tab", name="New vendor questionnaire").click()
        wait_idle(page)
        page.get_by_role("combobox", name="Load an example vendor").click()
        page.get_by_role("option").nth(1).click()
        wait_idle(page)
    else:
        page.goto(f"{ui_url}/{spec['path']}")
        wait_idle(page)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api-url", default=os.environ.get("ARBITER_API_URL", "http://localhost:8000"))
    parser.add_argument("--ui-url", default="http://localhost:8501")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img")
    parser.add_argument(
        "--browser-path", default=os.environ.get("ARBITER_CHROMIUM"), help="Chromium executable"
    )
    parser.add_argument(
        "--only", nargs="*", choices=[p["name"] for p in PAGES], help="capture just these pages"
    )
    args = parser.parse_args(argv)

    sync_playwright = require_playwright()
    args.out.mkdir(parents=True, exist_ok=True)
    chosen = [p for p in PAGES if not args.only or p["name"] in args.only]
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=30) as api, sync_playwright() as pw:
        launch: dict[str, Any] = {"headless": True}
        if args.browser_path:
            launch["executable_path"] = args.browser_path
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport=VIEWPORT)
        for spec in chosen:
            prepare(page, spec, args.ui_url.rstrip("/"), api)
            assert_no_secrets(page)
            target = args.out / spec["file"]
            page.screenshot(path=str(target), full_page=False)
            print(f"wrote {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
