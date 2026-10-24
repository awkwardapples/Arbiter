"""Streamlit reviewer console — API only (lane P5-A)."""

from __future__ import annotations

import streamlit as st

from ui.client import ArbiterAPIError
from ui.provider import provider_lines
from ui.session import get_client

_CSS = """
<style>
.block-container { max-width: 1100px; padding-top: 1.5rem; }
</style>
"""
_ROOT = __import__("pathlib").Path(__file__).resolve().parent
_LOGO = _ROOT.parent / "docs" / "img" / "arbiter_logo.png"


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = ""
        for char in piece:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _streamlit_supports_logo() -> bool:
    return _version_tuple(st.__version__) >= (1, 31) and hasattr(st, "logo")


def _install_logo() -> None:
    # st.logo size="large" is a 32px max height. This wordmark is 800x300, so that
    # cap leaves the name illegible. The sidebar image is the persistent small mark.
    st.sidebar.image(str(_LOGO), width=200)


def _hero_wordmark() -> None:
    """Centered wordmark at the top of the main area, above the page title."""
    _left, center, _right = st.columns([1, 1, 1])
    with center:
        st.image(str(_LOGO), width=300)


def _last_trace(client: object) -> list[dict]:
    """Trace of the most recent case, for the provider proof. Empty when there is none."""
    try:
        items = client.list_cases()  # type: ignore[attr-defined]
        if not items:
            return []
        newest = max(items, key=lambda item: str(item.get("created") or ""))
        return client.get_trace(str(newest["case_id"]))  # type: ignore[attr-defined]
    except (ArbiterAPIError, KeyError):
        return []


def _sidebar_status() -> None:
    client = get_client()
    try:
        health = client.health()
    except ArbiterAPIError as exc:
        st.sidebar.error(exc.message)
        return
    mode = health.get("mode") or {}
    st.sidebar.markdown(f"**Data:** {mode.get('data', 'unknown')}")
    st.sidebar.markdown(f"**LLM:** {mode.get('llm', 'unknown')}")
    for line in provider_lines(health, _last_trace(client)):
        st.sidebar.caption(line)


def main() -> None:
    st.set_page_config(page_title="Arbiter Reviewer", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    _install_logo()
    _sidebar_status()
    pages = [
        st.Page(str(_ROOT / "pages" / "new_assessment.py"), title="New assessment", default=True),
        st.Page(str(_ROOT / "pages" / "queue.py"), title="Cases"),
        st.Page(str(_ROOT / "pages" / "case.py"), title="Case"),
        st.Page(str(_ROOT / "pages" / "sources.py"), title="Sources"),
        st.Page(str(_ROOT / "pages" / "review.py"), title="Review"),
        st.Page(str(_ROOT / "pages" / "memory.py"), title="Precedents"),
        st.Page(str(_ROOT / "pages" / "audit.py"), title="Audit"),
        st.Page(str(_ROOT / "pages" / "evaluation.py"), title="Evaluation"),
    ]
    _hero_wordmark()
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
