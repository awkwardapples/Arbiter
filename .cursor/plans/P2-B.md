# P2-B LLM layer and Nightshift plan

## Goal

Fill the P0 stubs under `app/llm/` so that every model call in Arbiter goes through one function, `generate()`. It resolves a provider: Meterless Nightshift first, NVIDIA direct second, offline third. Offline raises `OfflineProvider` so callers run their deterministic logic. `generate()` renders the prompt, calls the provider with the POWER-contract headers and timeouts, parses JSON with exactly one repair call, and traces every attempt with provider, route, the returned `model`, latency and tokens. It never logs a token. Prompt templates live in files, render strictly, and wrap vendor text as untrusted data. `preflight` and `llm ping` show which models Nightshift actually served, which is the evidence for the NVIDIA award.

## Branch

The worktree is on `p2b-nightshift`. The pass index and the B9 prompt say `p2b-llm`. I will push the current branch unless you say otherwise (see question 2). Lane id `2b`, marker `p2b`. `.cursor/ACTIVE_PASS` is `2b plan`.

## Provider resolution

```
generate(prompt, route, response, schema, purpose, tracer, agent_name)
  │
  ▼
resolve()  (result cached 60 s; key = LLM_PROVIDER + base URL + token presence)
  │
  ├─ LLM_PROVIDER=offline ──────────────────────────────────────► Offline
  ├─ LLM_PROVIDER=nvidia ── key set? ── yes ──► NVIDIA ── no ──► Offline
  ├─ LLM_PROVIDER=meterless ── discover() == online? ── yes ──► Meterless
  │                                                  └─ no ──► OfflineProvider (no silent switch to NVIDIA)
  └─ LLM_PROVIDER=auto
       1. token missing ─────────────────────────────► skip Meterless (status "offline", reason "no token")
          token == rt-local ─────────────────────────► skip Meterless (status "config_error"), warn once
       2. METERLESS_BASE_URL set → normalise → GET /v1/models
          unset → probe 12 pairs, hosts 127.0.0.1, localhost, [::1] × ports 8088, 8090, 8787, 11434;
                  stop at the first online pair
          200 with meterless/* ids → Meterless
          401/403 → unauthorized → continue;  anything else → offline → continue
       3. NVIDIA_API_KEY set (or the MODEL_API_KEY alias) → NVIDIA
       4. → Offline
Offline.chat() raises OfflineProvider. Explicit LLM_PROVIDER=meterless with rt-local raises ConfigError.
```

`/healthz` is never called. Each call uses only the resolved provider: there is no failover between providers during a call. A timeout or a 5xx raises `UpstreamTimeout` or `UpstreamError`, and the caller falls back for that step (master spec §12).

## Files

Everything is inside P2-B ownership (`app/llm/**`, `app/cli/llm.py`, `tests/unit/llm/**`, `tests/live/test_meterless_*.py`, `tests/fixtures/meterless_*`, `tests/fixtures/nvidia_*`), plus this lane's gate and the two finish docs, with **one flagged exception**:

| File | Action |
|---|---|
| `app/llm/generator.py` | Implement the P0 signature (keeps P0's `tracer` and `agent_name` kwargs). Resolve, render, call, parse, one repair, trace. Purpose table for `max_tokens` and temperature |
| `app/llm/resolve.py` | New. `resolve(settings) -> Provider`, 60 s cache, `reset_cache()` for tests |
| `app/llm/jsonparse.py` | Strip fences, balanced scan, `json.loads`, pydantic validate |
| `app/llm/providers/base.py` | New. `Provider` protocol, `ChatResult`, `DiscoveryResult` |
| `app/llm/providers/meterless.py` | URL normalisation, auto-detect, discovery, chat, headers, 180 s timeout, `meterless-*` response headers |
| `app/llm/providers/nvidia.py` | OpenAI-compatible chat over httpx, 90 s timeout |
| `app/llm/providers/offline.py` | `chat()` raises `OfflineProvider` |
| `app/llm/status.py` | `check()` with no secrets |
| `app/llm/prompts/__init__.py` | `render`, `load`, `list_templates` |
| `app/llm/prompts/{plan,extract,critique,challenge,report,guard_classify,repair}.md` | First working templates. Front matter declares `vars`, `vendor_text: bool` and `schema` |
| `app/llm/prompts/schemas.py` | New. Pydantic output models the JSON templates target (`PlanOut`, `ExtractOut`, `CritiqueOut`, `ChallengeOut`, `GuardClassifyOut`). P3 may refine them |
| `app/llm/__init__.py` | Re-export `generate`, `GenerationResult` |
| `app/cli/llm.py` | `llm ping --route fast\|deep`, `llm status` (full preflight details as JSON, no secrets) |
| `scripts/gates/p2b.py` | Gate: every template renders, no model SDK imports, `status.check()` has no secret values, `LLM_PROVIDER=offline` makes `generate` raise `OfflineProvider` |
| `tests/unit/llm/test_jsonparse.py` | P2-T10 |
| `tests/unit/llm/test_generator.py` | P2-T11, P2-T15 |
| `tests/unit/llm/test_meterless.py` | P2-T12, P2-T13, P2-T14, P2-T16 |
| `tests/unit/llm/test_static.py` | P2-T17 |
| `tests/unit/llm/test_secrets.py` | P2-T18 |
| `tests/unit/llm/test_prompts.py` | P2-T19 |
| `tests/live/test_meterless_live.py` | P2-T20L (`live`, `p2b`). With `ARBITER_CAPTURE_FIXTURES=1` it also writes the two scrubbed fixtures |
| `tests/fixtures/meterless_models.json`, `meterless_chat.json` | Real captures, token-free (response bodies plus `meterless-*` headers only) |
| `docs/passes/P2-B_REPORT.md`, `docs/cursor-usage/P2-B.md` | Finish only |

**Exception (additive schema change, permitted ✎ for `app/schemas/*` with a note in the report):** `app/schemas/trace.py` gains `purpose: str | None = None` and `provider_meta: dict[str, str] | None = None`. Without them, pydantic silently drops the `purpose` extra the spec requires and the Meterless route or receipt headers have nowhere to go.

Not touched: `app/config.py` (every provider field already exists), `app/cli/meta.py` (P0), `app/errors.py`, `app/tracing.py`.

## Interfaces

```python
# app/llm/generator.py
PURPOSES: dict[str, tuple[float, int]]  # purpose -> (temperature, max_tokens)
# plan 0.0/1024, extract 0.0/2048, critique 0.0/1024, challenge 0.0/1024,
# report 0.2/2048, guard_classify 0.0/256, repair 0.0/2048, ping 0.0/64; unknown -> 0.0/1024

def generate(prompt: str, *, system: str | None = None, route: Literal["fast", "deep"] = "fast",
             response: Literal["text", "json"] = "text", schema: type[BaseModel] | None = None,
             timeout_s: float | None = None, purpose: str, tracer: Tracer | None = None,
             agent_name: str = "unknown") -> GenerationResult: ...

# app/llm/resolve.py
def resolve(settings: Settings | None = None) -> Provider: ...
def reset_cache() -> None: ...

# app/llm/providers/base.py
class ChatResult(BaseModel):
    text: str; model: str | None; tokens_in: int | None; tokens_out: int | None
    latency_ms: int; provider_meta: dict[str, str]

class DiscoveryResult(BaseModel):
    status: Literal["online", "unauthorized", "offline", "config_error"]
    base_url: str | None; models_seen: list[str]; detail: str

class Provider(Protocol):
    name: str  # "meterless" | "nvidia" | "offline"
    def model_for(self, route: Literal["fast", "deep"]) -> str: ...
    def chat(self, messages: list[dict[str, str]], *, model: str, temperature: float,
             max_tokens: int, timeout: float | None = None) -> ChatResult: ...

# app/llm/providers/meterless.py
AUTODETECT_HOSTS = ("127.0.0.1", "localhost", "[::1]"); AUTODETECT_PORTS = (8088, 8090, 8787, 11434)
def normalise_base_url(url: str) -> str: ...  # -> scheme://host:port/v1
def discover(base_url: str, token: str, app_id: str, *, transport: httpx.BaseTransport | None = None) -> DiscoveryResult: ...
def autodetect(token: str, app_id: str, *, transport=None) -> DiscoveryResult: ...
class MeterlessProvider:  # from_settings() raises ConfigError on rt-local
    @classmethod
    def from_settings(cls, s: Settings, *, transport=None) -> MeterlessProvider: ...

# app/llm/providers/nvidia.py
class NvidiaProvider: ...  # from_settings(s, *, transport=None)

# app/llm/jsonparse.py
def extract_json(text: str) -> str: ...  # raises ParseFailure
def parse(text: str, schema: type[T]) -> tuple[T, str]: ...  # (model, raw_json)

# app/llm/prompts/__init__.py
def render(name: str, **vars: str) -> str: ...  # ConfigError on a missing or unused var
def load(name: str) -> Template: ...  # Template(name, vars, vendor_text, schema, body)

# app/llm/status.py
def check() -> dict[str, object]:
    # {provider_resolved, meterless: {status, base_url, models_seen, fast_model, deep_model, detail},
    #  nvidia: {configured, fast_model, deep_model}}
```

Details that matter for review:

- **Headers.** `Authorization: Bearer <token>` and `meterless-app: <METERLESS_APP_ID>` on every request. `meterless-scope: user` only on chat. Timeout: `httpx.Timeout(180, connect=...)` on every chat. Discovery under auto-detect uses `httpx.Timeout(180, connect=2.0)`, so the connect timeout is 2 s per probe. A configured base URL uses the same 2 s connect timeout.
- **Trace.** One `model_call` event per attempt. A good first attempt → `success`. A bad first JSON attempt → `retrying`, then the repair attempt → `success` (`repaired=True`) or `fallback`, followed by `ParseFailure`. Timeout or upstream error → `fallback`, then the typed error is raised. Resolved offline → one `fallback` event with `provider=offline`, then `OfflineProvider` is raised. That code really runs, so the event is honest. Summaries are metadata only (purpose, route, char counts), never prompt text. Everything still passes `mask_secrets`.
- **Error hygiene.** httpx exceptions are re-raised as `UpstreamError` or `UpstreamTimeout` with a message built from status code and URL path only. The request object and its headers are never put into a message or log.
- **Rendering.** Placeholders match only `{lower_snake}`, so JSON examples inside templates (`{"a": 1}`) are left alone. Missing or unused variables raise. In a `vendor_text` value, a literal `</vendor_text>` is escaped so the text cannot close the tag. Guarding and redaction stay with P2-D and P3.
- **Repair.** `repair.md` gets `{error}`, `{bad_output}` and `{schema_json}`, and runs on the same route. The bad output is wrapped as untrusted, because it may echo vendor text.

## Acceptance tests (marker `@pytest.mark.p2b`; the id is in each test name)

| Id | How |
|---|---|
| P2-T10 | Parametrised cases: fenced, raw no-fence object, prose before and after, `}` and `{` inside strings, `\"` escapes, top-level array, nested objects pass. Truncated object, `{bad} {"ok":1}` (first balanced object invalid → fail, no skipping ahead), empty string, schema mismatch → `ParseFailure` |
| P2-T11 | Fake provider in a queue. Bad then good gives `repaired=True` and 2 events (`retrying`, `success`). Bad then bad raises `ParseFailure` with events `retrying` and `fallback`. The provider's call count is exactly 2 |
| P2-T12 | respx: `/v1/models` has Bearer and `meterless-app` but no `meterless-scope`. Chat has all three. The body's `model` equals `METERLESS_MODEL_FAST` or `_DEEP` set to custom ids. Normalisation table |
| P2-T13 | respx routes: 200 with `meterless/fast` → online; 200 with only `gpt-x` → offline; 401 and 403 → unauthorized; `ConnectError` → offline; a `/healthz` route asserted as never called |
| P2-T14 | Token `rt-local` + `LLM_PROVIDER=meterless` → `ConfigError`. The message names `METERLESS_RUNTIME_TOKEN` and the Nightshift console, not the value. Under `auto` → skipped, no crash. Missing token → status `offline`, no request sent |
| P2-T15 | Monkeypatched discovery: online → meterless; offline + NVIDIA key → nvidia; neither → offline, and `generate` raises `OfflineProvider`. Explicit `nvidia` wins over an online Meterless. Cache: two resolves within 60 s → one discovery; after a fake clock moves 61 s → two |
| P2-T16 | Custom recording transport captures `request.extensions["timeout"]`. Meterless chat read=180, discovery connect=2, NVIDIA read=90. Four pasted suffixes normalise. Auto-detect with all refused sees exactly 12 probes in order; with the 5th online it stops at 5 |
| P2-T17 | AST and text scan of `app/`, `ui/`, `sources/`, `scripts/`, `run.py`: no `openai`, `anthropic` or `litellm` imports anywhere, and no `chat/completions` string outside `app/llm/providers/` |
| P2-T18 | Fake tokens built at runtime (so the repo secret scanner sees no literal). For Meterless, NVIDIA and offline, on success, 401, 500, timeout and connection error, `caplog.text`, the trace file and exception messages contain neither token |
| P2-T19 | Every template renders with its front-matter vars. Missing or extra vars raise `ConfigError`. `vendor_text: true` templates contain the exact untrusted sentence and `<vendor_text>{vendor_text}</vendor_text>`. A `</vendor_text>` inside a value is escaped |
| P2-T20L | `live`: `generate(..., response="json", schema=Tiny)` on fast and deep succeeds. The trace has `provider=meterless` and a non-empty `model`. Run with you |

The tests are committed first (`test(p2b): acceptance tests`) and fail because of the stubs. T12/T13 load the captured fixtures, so they also fail until the capture exists.

## Build order

1. Tests → commit.
2. jsonparse, prompts, offline, base types → T10, T19.
3. Meterless and NVIDIA providers, resolve, status → T12–T16.
4. Generator and trace fields → T11, T15, T18.
5. CLI and gate → `verify-pass --pass 2b` green.
6. With you: `python run.py llm status`, capture fixtures (`ARBITER_CAPTURE_FIXTURES=1 ARBITER_LIVE_TESTS=1 pytest -m "p2b and live"`), ping both routes, and record the returned model ids. If they are not Nemotron, pin `meterless/<class>` ids in your `.env` (you edit it; I never read it) and re-ping.

## Risks

- **Real fixtures need Nightshift running.** T12/T13 stay red until step 6. If Nightshift is not up this session, I will stop at `blocked` instead of inventing a response shape.
- **Secret scanner's generic `token=…` rule.** Test tokens are assembled at runtime, and fixtures keep only bodies and `meterless-*` headers, never request headers.
- **The response header names (route, receipt) are unknown** until captured. I will record every `meterless-*` header rather than guess names.
- **Cold deep lane.** 180 s chat timeouts make the live test slow. It is marked `live` and stays out of the normal suite.

## Questions

1. **Day-0 discovery.** Please paste your `GET /v1/models` output (ids only), and tell me whether Nightshift is running now and which port it uses. `docs/DAY0_CHECKS.md` rows 12–14 are still blank.
2. **Branch.** Should I push `p2b-nightshift` (current) or rename it to `p2b-llm` (spec)?
3. **Preflight details.** `meta.preflight` (P0-owned) prints only `provider_resolved`. I plan to put the full details in `python run.py llm status` and leave `meta.py` alone. The alternative is a ✎ on `meta.py` to print the nested dict.
4. **`rt-local` under `auto`.** My default is to skip Meterless, warn, and show `config_error` in status. Explicit `meterless` raises. Is that OK, or should it always raise?
5. **Trace schema.** OK to add `purpose` and `provider_meta` to `TraceEvent` as an additive ✎?

Approval can be "go with the defaults" plus answers to 1 and 2.
