# Demo script

The six committed examples are offline sample runs from `python run.py examples` on 23 Oct 2026 (`provider: offline`, DuckDB). A live recording, if there is time after this pass, would use `python run.py examples --live` and replace these run ids. This script does not describe a video that has already been recorded.

Memory is off on these runs, so they do not show a precedent changing a later case. That session is `python run.py demo-session` (see `app/cli/review.py`). It is not one of the six run ids below.

| Example | Vendor | Outcome | Run id |
|---|---|---|---|
| 1 | Pellucid Forms Ltd | APPROVE | `run-a1ad72bed1f3` |
| 2 | Quillfeather Payroll Cloud Ltd | ESCALATE | `run-3d6b7460d393` |
| 3 | Oakhaven Mail Relay Ltd | ESCALATE | `run-ac35d0a215a4` |
| 4 | Fennimore Survey Tools Ltd | REQUEST_INFO | `run-be10a4e1768e` |
| 5 | Corvid Ledger Services Ltd | DECLINE | `run-3a3fda966d5f` |
| 6 | Inline Clean T3 Ltd | APPROVE | `run-c97e248333c6` |

Traces: `logs/examples/trace-<run_id>.jsonl`.

## Three-and-a-half minutes

Narration follows the submission playbook. Screen text uses the run ids above, not a live Zetaris session.

| Time | Screen | What to say |
|---|---|---|
| 0:00–0:20 | README title and the Reasoning Architecture badge | Third-party involvement is 48% of breaches in Verizon's 2026 DBIR, up from 30%. The control point is vendor onboarding. The analyst's evidence is spread across five systems and a questionnaire. |
| 0:20–0:45 | `input_examples/example_1.json` and the five outcome names | Arbiter returns one of five decisions. Facts are cited, a counterfactual says what would change the answer, and the next action is a signed contract. Company data here is synthetic. The vulnerability catalogue is CISA KEV. |
| 0:45–1:25 | `docs/ARCHITECTURE.md` state machine, then the README authority table | Models read. The policy decides. The Evaluator can send the Planner back. The Challenger can force one re-plan or an escalation, and cannot approve. |
| 1:25–2:15 | Trace `run-3d6b7460d393` | Quillfeather. The Evaluator's first pass is `needs_revision` and names `Q_COMPONENT_KEV`. The next pass runs that query (`backend=duckdb` on this sample run). The contract system disagrees with the vendor on residency (`EU` claim, `US` in the system of record). The outcome is `ESCALATE`. The Challenger agrees (`CHALLENGE_T1_UNCORROBORATED`). An ITSM outbox file is written under a signed contract. |
| 2:15–2:45 | `app/data/queries.yaml` and `python run.py preflight` | On a live machine, preflight shows Nightshift. On this sample run the planner line says `provider=offline`. Zetaris is the live SQL path (`zetaris/sql/03_usl.sql`). Sample mode is the DuckDB mirror of that model. |
| 2:45–3:15 | Say that memory is off on these examples | Do not claim a precedent changed Quillfeather. The memory path is `MEMORY_CHECK` then `redecide`. This run's redecide line says `precedents=0`. A governed session is a separate `demo-session` command. |
| 3:15–3:35 | README eval block, then trace `run-ac35d0a215a4` | The published numbers are offline, 15 synthetic cases, zero unsafe approvals for `arbiter_offline`. Oakhaven's trace has ScoutGuard `status=blocked`. Replay is `python run.py replay CASE-0003` for the Pellucid run. |
| 3:35–3:45 | Closing | Reliable vendor decisions an auditor can replay. Built in Cursor. |

Keep secrets off screen. Do not open `.env`, the Nightshift providers tab, or the Zetaris API-keys page.

## Five-minute live-demo variant

Use this only when Zetaris and Nightshift are up and the API is running on the host, not in Docker. Nightshift binds to `127.0.0.1`.

1. `python run.py preflight`. Read the provider line. If it is not Meterless, stop and say the demo is on the offline fallback.
2. `POST /run` with `input_examples/example_2.json`. Leave the new `run_id` on screen. Open `logs/trace-<run_id>.jsonl` and find `needs_revision`, then `query_id=Q_COMPONENT_KEV`. If `backend` is `zetaris`, show `zetaris_request_id` on that event. If it is `duckdb`, say the fallback fired and do not call the run live.
3. Open the reviewer console with `python run.py ui`. Show the case, the contradiction, and the contract state.
4. If a contract is `pending_approval`, submit `POST /contracts/{id}/approve` as `tprm_lead` with a rationale of at least 30 characters. Show the outbox path from the trace. Do not claim an external ticket was opened.
5. Optional, and only if time remains: `python run.py demo-session --live --reset --yes` was prepared before the recording. Narrate the precedent only from that session's own run ids, which are not the six ids in the table above.
6. End on the README eval block. Read the word "offline" if that is what the block says.

If Nightshift or Zetaris fails mid-demo, keep the recording, say the fallback that the trace shows, and do not switch to a rehearsed outcome.
