"""Pass 2b gate: templates render, status leaks no secrets, offline mode raises OfflineProvider."""

from __future__ import annotations

import os


def main() -> int:
    from app.config import get_settings
    from app.errors import OfflineProvider
    from app.llm import prompts, resolve
    from app.llm.generator import generate

    for name in ("plan", "extract", "critique", "challenge", "report", "guard_classify", "repair"):
        t = prompts.load(name)
        prompts.render(name, **{v: "x" for v in t.vars})
        if t.untrusted and prompts.UNTRUSTED_SENTENCE not in t.body:
            print(f"gate p2b: {name} lacks the untrusted-data sentence")
            return 1

    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "offline"
    get_settings.cache_clear()
    resolve.reset_cache()
    try:
        from app.llm import status

        info = status.check()
        secrets = get_settings().secret_values()
        if any(secret in str(info) for secret in secrets):
            print("gate p2b: status.check() contains a secret value")
            return 1
        if info["provider_resolved"] != "offline":
            print(f"gate p2b: LLM_PROVIDER=offline resolved to {info['provider_resolved']}")
            return 1
        try:
            generate("gate", purpose="ping")
        except OfflineProvider:
            pass
        else:
            print("gate p2b: offline generate did not raise OfflineProvider")
            return 1
    finally:
        if previous is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous
        get_settings.cache_clear()
        resolve.reset_cache()
    print("gate p2b: ok")
    return 0
