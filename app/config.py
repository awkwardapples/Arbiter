"""Application settings from the environment."""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from scripts.secret_patterns import is_placeholder_value, mask_secrets_in_text

SecretField = SecretStr | None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SAMPLE_MODE: bool = False
    LLM_PROVIDER: Literal["auto", "meterless", "nvidia", "offline"] = "auto"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    RUN_BUDGET_SECONDS: int = 600
    ARBITER_AS_OF: date = date(2026, 10, 26)
    ARBITER_MEMORY: Literal["on", "off"] = "on"

    METERLESS_BASE_URL: str = ""
    METERLESS_RUNTIME_TOKEN: SecretField = None
    METERLESS_APP_ID: str = "arbiter"
    METERLESS_MODEL_FAST: str = "meterless/fast"
    METERLESS_MODEL_DEEP: str = "meterless/deep"
    METERLESS_TIMEOUT_SECONDS: int = 180
    # Prepend a `/no_think` system message on Nightshift calls (Nemotron reasoning otherwise
    # spends the whole output budget and returns an empty response). Off by default.
    METERLESS_NO_THINK: bool = False

    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_API_KEY: SecretField = None
    NVIDIA_MODEL_FAST: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NVIDIA_MODEL_DEEP: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    NVIDIA_TIMEOUT_SECONDS: int = 90

    ZETARIS_REST_URL: str = "http://localhost:8888/api/v1.0"
    ZETARIS_ORG_ID: int = 1
    ZETARIS_API_KEY: SecretField = None
    ZETARIS_QUERY_LAYER: Literal["usl", "views"] = "usl"
    ZETARIS_USL_NAMESPACE: str = "lightning.metastore.arbiter"
    ZETARIS_TIMEOUT_SECONDS: int = 30
    ZETARIS_SOURCE_MODE: Literal["simulator", "github_raw"] = "simulator"
    SOURCES_PUBLIC_BASE: str = "http://host.docker.internal:8100"
    GITHUB_RAW_BASE: str = (
        "https://raw.githubusercontent.com/your-github-user/arbiter/main/data/sample/systems"
    )
    KEV_URL: str = (
        "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"
    )

    ARBITER_SIGNING_KEY: SecretField = None

    MODEL_BASE_URL: str | None = Field(default=None, validation_alias="MODEL_BASE_URL")
    MODEL_API_KEY: SecretField = Field(default=None, validation_alias="MODEL_API_KEY")
    NEMOTRON_MODEL: str | None = Field(default=None, validation_alias="NEMOTRON_MODEL")

    @field_validator(
        "METERLESS_RUNTIME_TOKEN",
        "NVIDIA_API_KEY",
        "ZETARIS_API_KEY",
        "ARBITER_SIGNING_KEY",
        "MODEL_API_KEY",
        mode="before",
    )
    @classmethod
    def _empty_secret(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, SecretStr):
            v = v.get_secret_value()
        if isinstance(v, str) and (not v.strip() or is_placeholder_value(v.strip())):
            return None
        return v

    @field_validator("METERLESS_BASE_URL", mode="before")
    @classmethod
    def _empty_string(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and not v.strip()):
            return ""
        return v

    @model_validator(mode="after")
    def _organiser_aliases(self) -> Settings:
        if self.MODEL_BASE_URL and "NVIDIA_BASE_URL" not in os.environ:
            object.__setattr__(self, "NVIDIA_BASE_URL", self.MODEL_BASE_URL)
        if self.NVIDIA_API_KEY is None and self.MODEL_API_KEY is not None:
            object.__setattr__(self, "NVIDIA_API_KEY", self.MODEL_API_KEY)
        if self.NEMOTRON_MODEL and "NVIDIA_MODEL_FAST" not in os.environ:
            object.__setattr__(self, "NVIDIA_MODEL_FAST", self.NEMOTRON_MODEL)
        return self

    def mode(self) -> dict[str, str]:
        data = "duckdb" if self.SAMPLE_MODE else "zetaris"
        llm = self.LLM_PROVIDER if self.LLM_PROVIDER != "auto" else "auto"
        return {"data": data, "llm": llm}

    def secret_values(self) -> list[str]:
        vals: list[str] = []
        for field_name in (
            "METERLESS_RUNTIME_TOKEN",
            "NVIDIA_API_KEY",
            "ZETARIS_API_KEY",
            "ARBITER_SIGNING_KEY",
            "MODEL_API_KEY",
        ):
            raw = getattr(self, field_name)
            if raw is None:
                continue
            raw_val = raw.get_secret_value() if isinstance(raw, SecretStr) else str(raw)
            if raw_val and not is_placeholder_value(raw_val):
                vals.append(raw_val)
        return vals

    def redacted_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        for key in (
            "METERLESS_RUNTIME_TOKEN",
            "NVIDIA_API_KEY",
            "ZETARIS_API_KEY",
            "ARBITER_SIGNING_KEY",
            "MODEL_API_KEY",
        ):
            if data.get(key) is not None:
                data[key] = "***"
        return data

    def __repr__(self) -> str:
        return f"Settings({self.redacted_dict()!r})"

    def __str__(self) -> str:
        return self.__repr__()


def mask_secrets(text: str) -> str:
    settings = get_settings()
    return mask_secrets_in_text(text, extra_values=settings.secret_values())


@lru_cache
def get_settings() -> Settings:
    return Settings()


def env_example_defaults() -> dict[str, str]:
    """Non-secret defaults from .env.example for P0-T1."""
    root = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    out: dict[str, str] = {}
    with open(root, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            out[key.strip()] = val.strip()
    return out
