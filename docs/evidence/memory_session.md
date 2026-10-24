# Live governed-memory session

Command, on 24 October 2026 (UTC):

```bash
ARBITER_MEMORY=on METERLESS_NO_THINK=1 SAMPLE_MODE=false python run.py demo-session --live --reset --yes
```

Data came from the Zetaris USL and models from Meterless Nightshift. The traces, both surviving retrieval logs, the H-MEM ledger and the precedent store are committed in `logs/examples/session/`. Every number below is read from those files.

## The six steps

| Step | Action | Result | OK | Trace | Model calls (ok / fallback) |
|---|---|---|---|---|---|
| 1 | run VND-0011 | ESCALATE | yes | `trace-run-a62568bf9fba.jsonl` | 0 / 1 |
| 2 | lead review creates precedent | P-0001 | yes | – (review API, no run) | – |
| 3 | run VND-0012 | APPROVE_WITH_CONDITIONS citing P-0001 | yes | `trace-run-a1c914808974.jsonl` | 3 / 1 |
| 4 | reset memory, run VND-0012 | ESCALATE | yes | `trace-run-17a181588839.jsonl` | 1 / 1 |
| 5 | analyst-role precedent is rejected; VND-0011 then VND-0012 | ESCALATE | yes | `trace-run-4e0c9560952c.jsonl`, `trace-run-3225b3e94b9b.jsonl` | 2 / 1, 0 / 1 |
| 6 | `wrong` feedback on P-0001; VND-0011 then VND-0012 | ESCALATE | yes | `trace-run-2245d0f939d4.jsonl`, `trace-run-0af7942a61a3.jsonl` | 0 / 1, 4 / 1 |

Over the 7 runs there were 17 model calls: 10 succeeded and 7 fell back. Every successful call was served by `nvidia/nemotron-3.5-super-vl-120b-a12b` with a Nightshift receipt and `no_think: true` (for example step 3: `rcpt_req_6vrltss6`, `rcpt_req_5flpsf6z`). Every fallback was the planner's deep-lane call returning HTTP 502 `nvidia/nemotron-3.5-lightning-30b-a3b_empty_response` (see `docs/evidence/nightshift_deviations.md`). After a fallback, the run continued on deterministic logic. In three runs the first call failed, so those runs made no successful model call.

The memory behaviour does not depend on the model calls. The precedent exception is applied by the policy engine, never by a model.

- **Step 3:** the policy engine moved VND-0012 from ESCALATE to APPROVE_WITH_CONDITIONS because P-0001 is a lead-reviewed precedent that the policy allows for C05. The trace shows `memory_check candidates=1`.
- **Step 4:** the same vendor with memory reset escalates (`candidates=0`).

## P-0001

From `logs/examples/session/precedents.json` (the precedent as re-created in step 5 after the reset):

| Field | Value |
|---|---|
| precedent | P-0001 (`hmem_id` `mem-2`) |
| from case | CASE-0011, review `CASE-0011-review` |
| reviewer role | `tprm_lead` |
| control | C05, mitigation `assurance.bridge_letter_current` |
| scope | tier T2, category HR SaaS |
| decision | APPROVE_WITH_CONDITIONS |

Its ledger lines, from `logs/examples/session/hmem-ledger.jsonl` (memory `mem-2`):

| Action | Detail |
|---|---|
| create | layer `long_term`, confidence 0.70 |
| feedback | kind `wrong`, delta −0.2, confidence 0.70 → 0.50 |
| read | query "assessment vendor VND-0012" |
| read | query "precedent control c05 mitigation bridge letter tier t2 category hr saas" |

## Retrieval

`logs/examples/session/hmem-retrieval-run-0af7942a61a3.jsonl` (step 6, VND-0012) ranks the precedent query against H-MEM:

- `mem-2` (P-0001): relevance 0.2934
- `mem-1`: relevance 0.2172
- strategy `comprehensive`

After the `wrong` feedback, P-0001's confidence is 0.50, below the engine's 0.70 floor, and its relevance is below the 0.35 floor. The engine does not apply it, and VND-0012 escalates.

`hmem-retrieval-run-2245d0f939d4.jsonl` (step 6, VND-0011) returned no scores (strategy `minimal`).

The step 3 retrieval log is not committed. `--reset` in step 4 deletes `logs/hmem-*` before the next run, so that file was removed during the session.
