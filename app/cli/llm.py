from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = ROOT / "docs" / "evidence" / "nightshift_proof.json"
HUMAN_OBSERVATIONS = "docs/evidence/nightshift_deviations.md"
# The lane design in docs/spec/release2/P15_LIVE_EVIDENCE.md: fast on Lightning, deep on Super.
_DESIGN = {"fast": ("lightning", "Nemotron 3.5 Lightning"), "deep": ("super", "Nemotron 3 Super")}


class _Pong(BaseModel):
    ok: bool


PING_PROMPT = 'Reply with only this JSON object and nothing else: {"ok": true}'
PROOF_PROMPT = 'Reply with only this JSON object and nothing else: {"ok": true}'


class ProofLane(BaseModel):
    route: Literal["fast", "deep"]
    sent_model: str
    requested_model: str | None = None
    response_model: str
    routed_model: str | None = None
    provider_model: str | None = None
    winning_route_model: str | None = None
    mode_coerced: bool | None = None
    requested_mode: str | None = None
    routed_mode: str | None = None
    receipt_id: str
    response_id: str | None = None
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    receipt: dict[str, str]


class Deviation(BaseModel):
    kind: str
    detail: str
    model: str | None = None
    receipt_ids: list[str] = []


class ProofDocument(BaseModel):
    """`docs/evidence/nightshift_proof.json`: one real request per lane, as recorded in its trace."""

    timestamp: str
    base_url: str
    provider: Literal["meterless"]
    fast: ProofLane
    deep: ProofLane
    deviations: list[Deviation]
    human_observations: str


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("llm", help="LLM provider utilities")
    sub2 = p.add_subparsers(dest="llm_cmd", required=True)
    ping = sub2.add_parser("ping", help="One JSON round-trip on a route; prints provider, model, latency")
    ping.add_argument("--route", choices=["fast", "deep"], default="fast")
    ping.set_defaults(_handler=_ping)
    proof = sub2.add_parser(
        "proof", help="One real request per lane through Nightshift; writes the proof JSON"
    )
    proof.add_argument("--out", type=Path, default=PROOF_PATH)
    proof.set_defaults(_handler=_proof)
    status = sub2.add_parser("status", help="Provider resolution and discovery details (no secrets)")
    status.add_argument("--all-models", action="store_true", help="list every model id seen")
    status.set_defaults(_handler=_status)


def _status(args: argparse.Namespace) -> None:
    from app.llm import status

    info = status.check()
    meterless = dict(info["meterless"])  # type: ignore[arg-type]
    seen = list(meterless.get("models_seen") or [])
    if not args.all_models:
        meterless["models_seen"] = [m for m in seen if m.startswith(("meterless/", "nvidia/"))]
        meterless["models_seen_total"] = len(seen)
    print(json.dumps({**info, "meterless": meterless}, indent=2))


def _ping(args: argparse.Namespace) -> None:
    from app.config import get_settings
    from app.errors import ArbiterError
    from app.llm.generator import generate
    from app.tracing import Tracer

    settings = get_settings()
    run_id = f"ping-{args.route}-{uuid.uuid4().hex[:8]}"
    tracer = Tracer(run_id, mode=settings.mode())
    try:
        result = generate(
            PING_PROMPT,
            route=args.route,
            response="json",
            schema=_Pong,
            purpose="ping",
            tracer=tracer,
            agent_name="CLI",
        )
    except ArbiterError as exc:
        print(f"ping {args.route}: FAILED {exc.type}: {exc.message}")
        print(f"trace: logs/trace-{run_id}.jsonl")
        sys.exit(1)
    finally:
        tracer.close()
    print(f"ping {args.route}: ok")
    print(f"  provider   {result.provider}")
    print(f"  model      {result.model}")
    print(f"  latency_ms {result.latency_ms}")
    print(f"  tokens     in={result.tokens_in} out={result.tokens_out}")
    print(f"  repaired   {result.repaired}")
    print(f"  trace      logs/trace-{run_id}.jsonl")


def _proof(args: argparse.Namespace) -> None:
    from app.config import get_settings
    from app.errors import ArbiterError
    from app.llm.resolve import reset_cache, resolve_detail

    settings = get_settings()
    reset_cache()  # the proof always rediscovers Nightshift; never a cached resolution
    try:
        resolution = resolve_detail(settings)
    except ArbiterError as exc:
        _fail(f"Nightshift not reachable: {exc.message}")
    if resolution.provider.name != "meterless":
        _fail(f"Nightshift not reachable: {resolution.reason}")
    base = resolution.meterless.base_url or ""
    lanes = {route: _proof_lane(route, settings) for route in ("fast", "deep")}
    document = ProofDocument(
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        base_url=_host_only(base),
        provider="meterless",
        fast=lanes["fast"],
        deep=lanes["deep"],
        deviations=derive_deviations(lanes["fast"], lanes["deep"]),
        human_observations=HUMAN_OBSERVATIONS,
    )
    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document.model_dump_json(indent=2) + "\n", encoding="utf-8")
    schema = out.parent / "nightshift_proof.schema.json"
    schema.write_text(json.dumps(ProofDocument.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    _print_proof(document, out)


def _proof_lane(route: Literal["fast", "deep"], settings: object) -> ProofLane:
    from app.errors import ArbiterError
    from app.llm.generator import generate
    from app.tracing import Tracer

    run_id = f"proof-{route}-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="arbiter-proof-") as tmp:
        tracer = Tracer(run_id, mode=settings.mode(), log_dir=tmp)  # type: ignore[attr-defined]
        try:
            generate(
                PROOF_PROMPT,
                route=route,
                response="json",
                schema=_Pong,
                purpose="proof",
                tracer=tracer,
                agent_name="CLI",
            )
        except ArbiterError as exc:
            _fail(f"proof {route}: FAILED {exc.type}: {exc.message}")
        finally:
            tracer.close()
        events = [
            json.loads(line)
            for line in (Path(tmp) / f"trace-{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    calls = [e for e in events if e.get("action") == "model_call" and e.get("status") == "success"]
    if not calls:
        _fail(f"proof {route}: no successful model_call in the trace")
    event = calls[-1]
    meta: dict[str, str] = dict(event.get("provider_meta") or {})
    receipt_id = meta.get("receipt_id")
    served = event.get("model") or meta.get("routed_model")
    if not receipt_id or not served:
        _fail(f"proof {route}: Nightshift returned no receipt id or model")
    coerced = meta.get("app_policy.mode_coerced")
    return ProofLane(
        route=route,
        sent_model=str(meta.get("sent_model") or _sent_model(route)),
        requested_model=meta.get("requested_model"),
        response_model=str(served),
        routed_model=meta.get("routed_model"),
        provider_model=meta.get("provider_model"),
        winning_route_model=meta.get("winning_route.model"),
        mode_coerced=None if coerced is None else coerced == "True",
        requested_mode=meta.get("app_policy.requested_mode"),
        routed_mode=meta.get("app_policy.routed_mode"),
        receipt_id=receipt_id,
        response_id=meta.get("response_id"),
        latency_ms=int(event.get("latency_ms") or 0),
        tokens_in=event.get("tokens_in"),
        tokens_out=event.get("tokens_out"),
        receipt=meta,
    )


def derive_deviations(fast: ProofLane, deep: ProofLane) -> list[Deviation]:
    """Deviations from the lane design, read only from the two receipts."""
    found: list[Deviation] = []
    for lane in (fast, deep):
        if lane.mode_coerced:
            found.append(
                Deviation(
                    kind="mode_coerced",
                    detail=(
                        f"{lane.route}: Nightshift coerced requested mode {lane.requested_mode} "
                        f"to {lane.routed_mode} (receipt {lane.receipt_id})"
                    ),
                    model=lane.response_model,
                    receipt_ids=[lane.receipt_id],
                )
            )
    if fast.response_model == deep.response_model:
        found.append(
            Deviation(
                kind="same_model_both_lanes",
                detail=(
                    f"Both lanes were served by {fast.response_model} "
                    f"(receipts {fast.receipt_id}, {deep.receipt_id})"
                ),
                model=fast.response_model,
                receipt_ids=[fast.receipt_id, deep.receipt_id],
            )
        )
    for lane in (fast, deep):
        needle, label = _DESIGN[lane.route]
        if needle not in lane.response_model.lower():
            found.append(
                Deviation(
                    kind="lane_model_differs_from_design",
                    detail=(
                        f"{lane.route}: the design expects {label}; Nightshift served "
                        f"{lane.response_model} (receipt {lane.receipt_id})"
                    ),
                    model=lane.response_model,
                    receipt_ids=[lane.receipt_id],
                )
            )
    return found


def _sent_model(route: str) -> str:
    from app.llm.resolve import resolve

    return resolve().model_for(route)  # type: ignore[arg-type]


def _host_only(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}:{parts.port}{parts.path}" if parts.port else url


def _print_proof(document: ProofDocument, out: Path) -> None:
    print(f"Nightshift {document.base_url} (token hidden)")
    print("| route | sent | requested | routed | response.model | winning route | receipt | ms | tokens |")
    print("|---|---|---|---|---|---|---|---:|---|")
    for lane in (document.fast, document.deep):
        print(
            f"| {lane.route} | {lane.sent_model} | {lane.requested_model} | {lane.routed_model} | "
            f"{lane.response_model} | {lane.winning_route_model} | {lane.receipt_id} | {lane.latency_ms} | "
            f"in={lane.tokens_in} out={lane.tokens_out} |"
        )
    for item in document.deviations:
        print(f"deviation [{item.kind}] {item.detail}")
    print(f"human observations: {document.human_observations}")
    print(f"wrote {out}")


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)
