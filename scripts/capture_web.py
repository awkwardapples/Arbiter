"""Smoke-test and screenshot the web console (lane P18-B). Not part of CI.

Needs a running API that serves the built console at /console/, and Playwright with Chromium
(a dev-only step, like scripts/capture_ui.py):

    pip install playwright && playwright install chromium
    SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve
    python scripts/capture_web.py --smoke     # checks the console; writes docs/img/console_run_*.png
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
SIZES = {"1440": {"width": 1440, "height": 900}, "1280": {"width": 1280, "height": 720}}
INSTALL_HINT = "Playwright is not installed. Run: pip install playwright && playwright install chromium"
SECRET_ENV = (
    "METERLESS_TOKEN",
    "METERLESS_RUNTIME_TOKEN",
    "NVIDIA_API_KEY",
    "ZETARIS_PASSWORD",
    "ZETARIS_API_KEY",
    "ARBITER_SIGNING_KEY",
)
RAIL_LABELS = ("Assess", "Cases", "Memory", "Sources", "Provider", "Audit", "Evaluation")
SMOKE_EXAMPLE = "example_2.json"  # the residency contradiction case named in the pass spec
SMOKE_RECORDING = "run-257c86984507"  # the committed live eval run the pass spec names
RUN_TIMEOUT_MS = 120_000


class SmokeFailure(AssertionError):
    """A smoke check did not hold; the message says which and what was seen."""


def require_playwright() -> Any:
    """Return Playwright's sync entry point, or exit with the install command."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(INSTALL_HINT) from None
    return sync_playwright


def assert_no_secrets(page: Any) -> None:
    text = page.inner_text("body")
    for name in SECRET_ENV:
        value = os.environ.get(name, "")
        if len(value) >= 8 and value in text:
            raise SystemExit(f"Refusing to capture: the value of {name} is visible on the page.")


def shoot(page: Any, out: Path, name: str) -> Path:
    assert_no_secrets(page)
    out.mkdir(parents=True, exist_ok=True)
    target = out / name
    page.screenshot(path=str(target), full_page=False)
    print(f"wrote {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
    return target


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def smoke_shell(page: Any, base: str) -> None:
    """Part 1: the shell loads, the rail renders every page and the mode chip has text."""
    page.goto(f"{base}/console/")
    page.wait_for_selector("nav[aria-label='Main']", timeout=15_000)
    nav = page.inner_text("nav[aria-label='Main']")
    for label in RAIL_LABELS:
        check(label in nav, f"rail is missing {label!r}; saw {nav!r}")
    page.wait_for_selector("[data-testid='mode-chip']", timeout=15_000)
    chip = page.inner_text("[data-testid='mode-chip']")
    check(bool(chip.strip()), "the mode chip is empty")


def vendor_name_for(base: str, example: str) -> str:
    """The legal name of an input example's vendor, looked up through the API (no ids in this script)."""
    payload = json.loads((ROOT / "input_examples" / example).read_text(encoding="utf-8"))
    vendors = httpx.get(f"{base}/vendors", timeout=30).json()
    for vendor in vendors:
        if vendor.get("vendor_id") == payload.get("vendor_id"):
            return str(vendor["legal_name"])
    raise SmokeFailure(f"the vendor of {example} is not in GET /vendors")


def wait_for_ruling(page: Any) -> str:
    page.wait_for_selector("[data-testid='ruling-card']", timeout=RUN_TIMEOUT_MS)
    return page.inner_text("[data-testid='outcome-stamp']").strip()


def smoke_run(page: Any, base: str, out: Path) -> str:
    """Start the example from Assess, watch the bench fill, check the ruling and the clash card."""
    name = vendor_name_for(base, SMOKE_EXAMPLE)
    page.goto(f"{base}/console/")
    page.get_by_role("button", name=f"Start assessment of {name}").click()
    page.wait_for_url(re.compile(r".*/console/runs/run-[0-9a-f]{12}$"), timeout=15_000)
    page.wait_for_selector("[data-node='evidence']", timeout=30_000)
    time.sleep(3)
    shoot(page, out, "console_run_mid.png")
    stamp = wait_for_ruling(page)
    check(stamp == "Escalate", f"the ruling stamp reads {stamp!r}, expected 'Escalate'")
    clash = page.inner_text("[data-testid='clash-card']")
    check("EU" in clash and "US" in clash, f"the clash card does not mention EU and US: {clash!r}")
    chip = page.inner_text("[data-testid='mode-chip']")
    check(not chip.startswith("Recorded"), f"a fresh run is labelled as a recording: {chip!r}")
    time.sleep(1.5)
    shoot(page, out, "console_run_ruling.png")
    page.get_by_role("link", name="Open the case").click()
    page.wait_for_url(re.compile(r".*/console/cases/[^/]+$"), timeout=15_000)
    page.wait_for_selector("main h1", timeout=15_000)
    return page.url


def smoke_recording(page: Any, base: str, out: Path) -> None:
    """Watch the committed live run at 16x from Recorded live runs; check its ruling and its label."""
    page.goto(f"{base}/console/")
    row = page.locator(f"li[data-run-id='{SMOKE_RECORDING}']")
    row.wait_for(timeout=15_000)
    row.get_by_role("button").click()
    page.wait_for_url(re.compile(rf".*/console/recordings/{SMOKE_RECORDING}$"), timeout=15_000)
    page.get_by_role("button", name="16×").click()
    stamp = wait_for_ruling(page)
    check(stamp == "Escalate", f"the recording's stamp reads {stamp!r}, expected 'Escalate'")
    chip = page.inner_text("[data-testid='mode-chip']")
    check("Recorded live run" in chip, f"the mode chip says {chip!r}, expected 'Recorded live run'")
    time.sleep(1.5)
    shoot(page, out, "console_run_recorded.png")


def smoke_empty(page: Any, base: str, out: Path) -> None:
    """The empty bench: a recording held at its first event."""
    page.goto(f"{base}/console/recordings/{SMOKE_RECORDING}")
    page.wait_for_selector("[data-testid='bench']", timeout=15_000)
    page.get_by_role("button", name="Pause").click()
    page.get_by_role("slider", name="Timeline").fill("0")
    time.sleep(0.8)
    shoot(page, out, "console_run_empty.png")


CASE_TABS = {
    "Decision": "decision-tab",
    "Evidence": "evidence-tab",
    "Agent activity": "agent-activity-tab",
    "Audit trail": "audit-trail-tab",
    "Technical details": "technical-tab",
}


def smoke_case(page: Any, case_url: str, out: Path) -> None:
    """Lane P18-C: every Case tab renders, the replay matches, and the Decision and Agent activity shots."""
    page.goto(f"{case_url}?tab=decision")
    page.wait_for_selector("[data-testid='claim-card']", timeout=15_000)
    shoot(page, out, "console_case_decision.png")
    for name, test_id in CASE_TABS.items():
        page.get_by_role("tab", name=name).click()
        page.wait_for_selector(f"[data-testid='{test_id}']", timeout=15_000)
    page.get_by_role("tab", name="Audit trail").click()
    page.get_by_role("button", name="Replay decision").click()
    result = page.locator("[data-testid='replay-result']")
    result.wait_for(timeout=15_000)
    check("Decision replays identically" in result.inner_text(), f"the replay says {result.inner_text()!r}")
    page.get_by_role("tab", name="Agent activity").click()
    activity = page.locator("[data-testid='agent-activity']")
    activity.get_by_role("button", name=re.compile("skip to result", re.I)).click()
    activity.locator("[data-testid='outcome-stamp']").wait_for(timeout=15_000)
    time.sleep(1.5)
    shoot(page, out, "console_case_activity.png")


def run_smoke(page: Any, base: str, out: Path) -> None:
    smoke_shell(page, base)
    case_url = smoke_run(page, base, out)
    print(f"opened the case at {case_url}")
    smoke_case(page, case_url, out)
    smoke_recording(page, base, out)
    smoke_empty(page, base, out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-url", default=os.environ.get("ARBITER_API_URL", "http://localhost:8000"))
    parser.add_argument("--smoke", action="store_true", help="run the smoke flow and its screenshots")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "img")
    parser.add_argument("--size", choices=sorted(SIZES), default="1440")
    parser.add_argument(
        "--browser-path", default=os.environ.get("ARBITER_CHROMIUM"), help="Chromium executable"
    )
    args = parser.parse_args(argv)

    sync_playwright = require_playwright()
    base = args.base_url.rstrip("/")
    with sync_playwright() as pw:
        launch: dict[str, Any] = {"headless": True}
        if args.browser_path:
            launch["executable_path"] = args.browser_path
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport=SIZES[args.size])
        try:
            if args.smoke:
                run_smoke(page, base, args.out)
                print("smoke: ok")
            else:
                smoke_shell(page, base)
                shoot(page, args.out, f"console_shell_{args.size}.png")
        except SmokeFailure as exc:
            print(f"smoke: failed: {exc}", file=sys.stderr)
            return 1
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
