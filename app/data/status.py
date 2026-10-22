"""Data backend status (lane P1-A implements)."""


def check() -> dict[str, object]:
    from app.config import get_settings

    mode = get_settings().mode()["data"]
    return {"backend": mode, "status": "stub"}
