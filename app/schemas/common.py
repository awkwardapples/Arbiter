from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

TriState = Literal["TRUE", "FALSE", "UNKNOWN"]
Outcome = Literal[
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "REQUEST_INFO",
    "ESCALATE",
    "DECLINE",
]
Tier = Literal["T1", "T2", "T3"]


class Provenance(BaseModel):
    kind: Literal[
        "system_of_record",
        "vendor_answer",
        "vendor_document",
        "public_feed",
        "human_review",
        "derived",
    ]
    system: str | None = None
    query_id: str | None = None
    record_key: str | None = None
    field: str | None = None
    backend: Literal["zetaris", "duckdb", "inline"] | None = None
    zetaris_request_id: str | None = None
    quote: str | None = None
    answer_ref: str | None = None
