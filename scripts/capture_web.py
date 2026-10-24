"""Smoke-test and screenshot the web console (lane P18-B). Not part of CI.

Needs a running API that serves the built console at /console/, and Playwright with Chromium
(a dev-only step, like scripts/capture_ui.py):

    pip install playwright && playwright install chromium
    SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve
    python scripts/capture_web.py --smoke     # checks the console; writes docs/img/console_run_*.png
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

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


def run_smoke(page: Any, base: str, out: Path) -> None:
    smoke_shell(page, base)
    shoot(page, out, "console_run_empty.png")


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
