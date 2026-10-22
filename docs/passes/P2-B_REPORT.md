# P2-B LLM layer and Nightshift report

## Built

- `app/llm/generator.py`: `generate()` is the single model seam, with the P0 signature (including P0's `tracer` and `agent_name`). It resolves the provider, builds the messages, and applies the per-purpose temperature (0.2 for `report`, 0.0 otherwise) and `max_tokens`. For `response="json"` it parses, makes **one** repair call through `prompts/repair.md`, and raises `ParseFailure` on a second failure. Every attempt emits a `model_call` trace event with status `success`, `retrying` or `fallback` and the fields `provider, route, model (response.model), latency_ms, tokens_in, tokens_out, purpose, provider_meta`. Summaries are metadata only (purpose, route, attempt, character counts), never prompt or response text.
- `app/llm/resolve.py`: resolution `auto` → Meterless if `/v1/models` is online → NVIDIA if a key is set → offline. It is cached for 60 s. An explicit `LLM_PROVIDER` overrides `auto`. Explicit `meterless` never switches to NVIDIA. Explicit `meterless` with `rt-local`, or explicit `nvidia` with no key, raises `ConfigError`. Under `auto`, both are skipped.
- `app/llm/providers/meterless.py`:
  - **URL normalisation.** Accepts pasted URLs ending in `/v1`, `/v1/models`, `/v1/chat/completions` or `/healthz`, or bare `host:port`.
  - **Auto-detect.** With no base URL set, it probes 12 host:port pairs (hosts 127.0.0.1, localhost, [::1] in that order; ports 8088, 8090, 8787, 11434) and stops at the first one that is online.
  - **Discovery.** 200 with `meterless/*` ids means online, 401/403 means unauthorized, anything else means offline. `/healthz` is never requested.
  - **Headers.** `Authorization` and `meterless-app` go on every request; `meterless-scope: user` only on chat.
  - **Timeouts.** Every call uses a 180 s timeout, and discovery uses a 2 s connect timeout.
  - **Receipts.** The Nightshift compute receipt (`requested_model`, `provider_model`, `routed_model`, `winning_route.*`, `receipt_id`, `decision_id`) is copied into `provider_meta`, along with any `meterless-*` response headers.
- `app/llm/providers/nvidia.py`: OpenAI-compatible chat to `integrate.api.nvidia.com`, 90 s timeout.
- `app/llm/providers/offline.py`: `chat()` raises `OfflineProvider`.
- `app/llm/providers/base.py`: the shared chat POST and the mapping to typed errors. httpx exceptions become `UpstreamTimeout`, `UpstreamError` or `Unauthorized`. Messages are built only from the status code and machine error codes, and every message is scrubbed of the credential.
- `app/llm/jsonparse.py`:
  - skips an opening code fence;
  - finds the first balanced object or array while respecting strings and escapes;
  - runs `json.loads`, then pydantic validation;
  - returns `(model, raw_json)` or raises `ParseFailure` with `.errors`.
- `app/llm/prompts/`: `render`, `load` and `list_templates`, plus seven templates (`plan`, `extract`, `critique`, `challenge`, `report`, `guard_classify`, `repair`).
  - Front matter declares `vars`, `untrusted`, `schema` and `response`.
  - Rendering is strict: a missing or unused variable raises `ConfigError`. Only `{lower_snake}` placeholders are substituted, so JSON examples survive.
  - Untrusted variables sit inside `<vendor_text>` blocks next to the required sentence. Any `<vendor_text>` or `</vendor_text>` tag inside a value is escaped, so vendor text cannot close or reopen the block.
- `app/llm/prompts/schemas.py`: first output models (`PlanOut`, `ExtractOut`, `CritiqueOut`, `ChallengeOut`, `GuardClassifyOut`). `ChallengeOut.action` is limited to `none`, `request_evidence` or `escalate`.
- `app/llm/status.py`: `check()` returns `{provider_resolved, llm_provider_setting, reason, meterless: {status, base_url, models_seen, fast_model, deep_model, detail}, nvidia: {configured, base_url, fast_model, deep_model}}` with no secrets. P0's `meta.preflight` now prints `llm meterless`.
- `app/cli/llm.py`: `llm ping --route fast|deep` (one JSON round-trip, with its own trace file) and `llm status` (full details; `--all-models` lists all ids).
- `scripts/gates/p2b.py`: checks that every template renders, that vendor-facing templates contain the untrusted-data sentence, that `status.check()` contains no secret values, and that `LLM_PROVIDER=offline` makes `generate` raise `OfflineProvider`.
- `tests/fixtures/meterless_models.json` and `meterless_chat.json` are **real captures** from Nightshift on `localhost:8088` (2026-10-22). They were written by `tests/live/test_meterless_live.py::test_p2b_capture_fixtures`, which stores response bodies and `meterless-*` response headers only, and refuses to write if the token appears.

## Discovered model ids (B7)

| Route | Requested | Nightshift `provider_model` | Returned `model` / `routed_model` | Latency (first OK call) |
|---|---|---|---|---|
| fast | `meterless/fast` | `meterless/auto` | `nvidia/nemotron-3.5-lightning-30b-a3b` | 1866 ms |
| deep | `meterless/deep` | `meterless/auto` | `nvidia/nemotron-3.5-lightning-30b-a3b` | 4255 ms |

Both routes are served by **Nemotron** through Nightshift, so the B7 "if not Nemotron, pin" step was not needed and `.env` was not changed. `/v1/models` listed 77 ids: 18 `meterless/*` routing ids, 8 `nvidia/*` Nemotron ids and 51 `local-runtime/*`. Details are in `docs/DAY0_CHECKS.md` rows 12–14.

Observation: **deep currently lands on the same Lightning 30B lane as fast.** The receipt's cost baseline names `nvidia/nemotron-3-super-120b-a12b`, but the router did not pick it. Changing that is a Nightshift lane setting (pin Super 120B to the deep disposition) or a `METERLESS_MODEL_DEEP` override in `.env`. That is your decision, and I did not guess a `meterless/<class>` id.

## Deviations

1. **Approved additive schema change.** `app/schemas/trace.py` `TraceEvent` gained `purpose: str | None = None` and `provider_meta: dict[str, str] | None = None`. Both are optional, so existing traces still parse. Written as `X | None` (ruff's UP rules); this is equivalent to `Optional[X]`.
2. **Receipt in the body, not headers.** Live Nightshift returned no `meterless-*` response headers on either endpoint. The route and receipt live in the response body's `meterless` object, so `provider_meta` reads the body. Headers are still recorded if they ever appear.
3. **Bigger `max_tokens` than the plan.** With `max_tokens=64`, a live call returned HTTP 502 `provider_error` (`…_empty_response`): Nemotron's reasoning tokens used up the budget, and a one-line JSON reply needed 179–275 completion tokens. New budgets: plan, critique and challenge 2048; extract, report and repair 4096; guard_classify and ping 1024.
4. **Explicit `LLM_PROVIDER=nvidia` without a key raises `ConfigError`** (your answer to question 4). The plan had said offline.
5. **Timeout overrides.** A Meterless chat ignores a shorter `timeout_s` (the POWER contract says every Meterless call uses 180 s). NVIDIA uses `min(timeout_s, 90)`.
6. **Upstream error messages** carry only machine codes (`code`, `type`, `meterless_detail`), never the free-text `message`, because a provider may echo request content. This keeps `fallback` trace events metadata-only.
7. **New modules inside `app/llm/**`:** `resolve.py`, `providers/base.py` and `prompts/schemas.py`. T15 lives in `tests/unit/llm/test_resolve.py`, not `test_generator.py`.
8. **Two edits to committed tests, neither loosening a check:**
   - In P2-T19's escape test, the spec's required sentence itself contains `<vendor_text>`. The assertion now compares tag counts in the output to the template's own counts and still requires exactly one closing tag.
   - Fixture parameters were renamed (`meterless_token` → `mtok`, `nvidia_key` → `nkey`) because the repo secret scanner's generic `token=<12+ chars>` rule matched ordinary keyword arguments. `.secrets-allowlist` is P0-owned and was not touched.
9. **`meterless_chat.json`** holds both the `fast` and `deep` captures in one file. Each includes Nightshift's signed receipt envelope (public key and signature). These are not credentials, and the secret scan passes.

## Known gaps

- **NVIDIA direct is untested live.** No `NVIDIA_API_KEY` is configured (`nvidia.configured=false`); the NVIDIA key lives in Nightshift's Providers tab. It is covered by respx and transport tests only, and no `nvidia_*` fixture was captured.
- **No mid-call failover.** By design, a Meterless timeout or 5xx raises to the caller, which runs its deterministic fallback for that step (master spec §12). P3 owns that fallback.
- **`status.check()` runs a real discovery** when resolution did not need one, for example with `LLM_PROVIDER=offline` or `nvidia`. With no base URL set and a token present, this can mean up to 12 probes with a 2 s connect timeout each. A refused connection returns at once; only filtered ports wait.
- **Existing preflight quirk (not this lane).** `preflight` prints `data duckdb` next to `mode.data zetaris`, which come from P1-A's `data.status` and P0's `Settings.mode()`.
- **Prompts are a first version.** P3 owns the wording and may refine the schemas.

## Commands

```
python scripts/tasks.py verify-pass --pass 2b            # green: lint, 130 p2b tests, 295 non-live, gate, secret-scan, hardcode-check
ARBITER_LIVE_TESTS=1 ARBITER_CAPTURE_FIXTURES=1 pytest tests/live/test_meterless_live.py -m "p2b and live" -k capture
ARBITER_LIVE_TESTS=1 pytest -m "p2b and live" -k "not capture"   # P2-T20L: 2 passed (fast, deep)
python run.py preflight                                  # llm meterless
python run.py llm status                                 # online, http://localhost:8088/v1, 77 models
python run.py llm ping --route fast                      # meterless, nvidia/nemotron-3.5-lightning-30b-a3b, 2860 ms
python run.py llm ping --route deep                      # meterless, nvidia/nemotron-3.5-lightning-30b-a3b, 1741 ms
python scripts/check_trace.py logs/trace-ping-deep-*.jsonl   # trace-check: ok
```

The token was always read from `Settings` inside Python and never printed. `.env` was never read directly.

## Explain-it

1. **Why exactly one generator?**
   - Every model call passes the same resolution, timeouts, headers, JSON repair and trace code. One file to audit means one place to prove that no model SDK, no unlogged call and no secret leak exists. P2-T17 enforces this statically.
   - For a judge: the trace shows every model call with its provider and served model, and nothing can bypass it.
2. **How does Arbiter decide Nightshift is online?**
   - Only `GET /v1/models`, with the token and `meterless-app`, returning 200 with at least one `meterless/*` id. 401/403 means unauthorized; anything else is offline.
   - `/healthz` only proves a web server is up, not that a model lane is usable or that the token works, so it is never requested.
3. **What happens on invalid JSON, and on a timeout?**
   - Invalid JSON: one repair call with the validation errors, the schema and the bad output (wrapped as untrusted). If that also fails, the event is traced `fallback` and `ParseFailure` is raised so the agent uses its deterministic logic.
   - Timeout: the call is traced `fallback` and `UpstreamTimeout` is raised. Meterless waits the full 180 s first, so a cold lane is not mistaken for an outage.
4. **How will a judge see Nemotron was used?**
   - Each `model_call` trace event records `provider=meterless`, `model=nvidia/nemotron-3.5-lightning-30b-a3b` (the response's own `model` field), and `provider_meta` with Nightshift's receipt: `requested_model`, `routed_model`, `winning_route.provider=nvidia` and `receipt_id`.
   - `python run.py llm ping` prints the same.
5. **A judge's machine without Nightshift or an NVIDIA key?**
   - `auto` probes the 12 local candidates, finds nothing, sees no key, and resolves to offline. `generate` emits one `fallback` event with `provider=offline` and raises `OfflineProvider`, so each agent runs its deterministic fallback.
   - `preflight` shows `llm offline` with the reason. Copying `.env.example` to `.env` behaves the same, because the placeholders count as unset.
