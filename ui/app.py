"""Streamlit reviewer console — API only (lane P5-A)."""

from __future__ import annotations

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import glossary
from ui.session import get_client

_CSS = """
<style>
.block-container { max-width: 1100px; padding-top: 1.5rem; }
</style>
"""
_ROOT = __import__("pathlib").Path(__file__).resolve().parent


def _sidebar_status() -> None:
    client = get_client()
    try:
        health = client.health()
    except ArbiterAPIError as exc:
        st.sidebar.error(exc.message)
        return
    mode = health.mode
    st.sidebar.markdown(f"**Data:** {mode.get('data', 'unknown')}")
    st.sidebar.markdown(f"**LLM:** {mode.get('llm', 'unknown')}")
    if health.provider and health.provider.get("models"):
        st.sidebar.caption(f"Models: {health.provider.get('models')}")


def main() -> None:
    st.set_page_config(page_title="Arbiter Reviewer", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    _sidebar_status()
    glossary()
    pages = [
        st.Page(str(_ROOT / "pages" / "new_assessment.py"), title="New assessment", default=True),
        st.Page(str(_ROOT / "pages" / "queue.py"), title="Queue"),
        st.Page(str(_ROOT / "pages" / "case.py"), title="Case"),
        st.Page(str(_ROOT / "pages" / "review.py"), title="Review"),
        st.Page(str(_ROOT / "pages" / "memory.py"), title="Memory"),
        st.Page(str(_ROOT / "pages" / "audit.py"), title="Audit"),
        st.Page(str(_ROOT / "pages" / "evaluation.py"), title="Evaluation"),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
