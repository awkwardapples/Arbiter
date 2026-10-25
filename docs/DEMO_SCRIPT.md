# Demo script

Target 3:35, hard stop 3:50. File name: `OAH2026-Arbiter-ReasoningArchitecture-Demo.mp4`. Recorded at 1280×720 in the web console (`http://localhost:8000/console/`).

Every shot below is backed by a committed file. Two rules for the voice-over:

1. **Say "live" only over live evidence.** The live runs are examples 2–5 (`logs/examples/live/`), the hero being example 2, Quillfeather (`run-211916c1544d`); the Nightshift proof (`docs/evidence/nightshift_proof.json`); the memory session (`logs/examples/session/`); and the live evaluation (`eval/results_live/`). A live run you record on the day is live. A replayed recording is introduced as "recorded live on 25 October" (24 October for the memory session).
2. **Label sample mode on screen.** Any frame from a sample-mode run (DuckDB mirror, deterministic fallback) keeps the console's own sample mode chip visible. Examples 1 and 6 are sample mode at the root of `output_examples/`; do not use them as live shots.

## Evidence for each shot

| Shot | Run or file | What it shows |
|---|---|---|
| Live run (hero) | `run-211916c1544d`, `logs/examples/live/trace-run-211916c1544d.jsonl`, `output_examples/example_2_output.json` | Quillfeather Payroll Cloud Ltd, `ESCALATE`, 228 s; 14 Zetaris queries with request ids; 4 Nemotron calls with receipts (Super VL); the Evaluator sends the Planner back twice; `contradiction_found` EU versus US on `CTR-30007`; KEV join, 15 rows; Challenger re-plan, then escalate; one 502 that falls back |
| Nightshift proof | `docs/evidence/nightshift_proof.json` | fast → `nvidia/nemotron-3.5-lightning-30b-a3b`, receipt `rcpt_req_936ew345`; deep → `nvidia/nemotron-3.5-super-vl-120b-a12b`, receipt `rcpt_req_wu3r6jyf`; both `mode_coerced` to `auto` |
| Deviation | `docs/evidence/nightshift_deviations.md` | Super 3 120B not entitled; app rule coerces both lanes; Meterless acknowledged, fix targeted for Sunday's release and not yet in this build |
| Zetaris USL | Sources page; `docs/ZETARIS_USL.md`, `docs/passes/P1-B_parity.json` | USL `vendor_risk` diagram; DQ flags `CTR-30028`; parity 416/416 |
| Memory | Memory page; recording of `run-a1c914808974` (`logs/examples/session/`); `docs/evidence/memory_session.md` | Precedent P-0001 from Marrowgate moves Tessellate to `APPROVE_WITH_CONDITIONS`; reset and analyst-role precedents block it |
| Eval and replay | Evaluation page, README eval block, `docs/EVALUATION.md`; Case → Audit trail → Replay decision | Live 10/10, 0 unsafe, 4/4 consistent; 10 of 21 calls fell back (6 of 10 cases without a successful model call); baseline not measured; offline 16/16 |

## The video

| Time | Screen | Narration (essence) |
|---|---|---|
| 0:00–0:20 | Title card (track, one-liner), then three numbers with their sources on screen | "Reasoning Architecture. Third parties are in 48% of breaches. Companies assess only 36% of their vendors. Meet the third-party risk analyst deciding whether a new SaaS vendor can touch customer data." |
| 0:20–0:35 | Console, Assess page: pick Quillfeather Payroll Cloud Ltd; **Start assessment** | "Arbiter's agents gather and cross-check the evidence; a versioned policy decides; every step is on screen." |
| 0:35–1:50 | **Live run** of example 2 on the bench, sped up in editing with an on-screen "2× / 4×" label. Pause on: the Planner reading the USL catalogue; the Nightshift → Nemotron edge (hover: lane, model, receipt); the Zetaris queries filling the records column; the **Evaluator sending the Planner back** (red dashed arc); the **clash card** (EU versus US); the KEV join; the Challenger | "The Planner reads Zetaris's semantic model. Nemotron plans through Meterless Nightshift; here's the receipt. The Evaluator finds the incident and contract evidence missing and sends the plan back. The vendor says EU-only hosting; the contract system says US. FortiOS is on CISA's known-exploited list fifteen times. When one model call fails, the step falls back and the trace says so." |
| 1:50–2:15 | The ruling (Escalate), then the Case page: brief; claim versus record; the drafted ITSM ticket for the lead; Evidence tab, **What would change this decision** | "The policy, not a model, rules: escalate to the TPRM lead, ticket drafted under a signed contract. And here is exactly what evidence would change the decision." |
| 2:15–2:35 | **Provider** page: Runtime URL with the token hidden, the lane table; then `python run.py llm proof` in a terminal returning both receipts | "One real request per lane through Nightshift, served by Nemotron. Honest note: a Nightshift app rule still coerces both lanes to auto. Meterless has acknowledged it; the fix isn't in our build yet." |
| 2:35–2:55 | **Sources** page: the USL diagram, the DQ finding `CTR-30028`, 416/416 parity | "Five systems and CISA KEV in one Zetaris semantic layer. The Planner reads it in 304 tokens, and a DQ rule caught a DPA marked signed without a date." |
| 2:55–3:15 | **Memory**: the recording of the Tessellate run (recorded live on 24 October), with the precedent edge lit; then the Memory page | "A lead's precedent lets a similar vendor be approved with conditions, and only through policy. Reset memory, or let an analyst set the precedent, and it escalates again." |
| 3:15–3:35 | Evaluation page; then Case → Audit trail → **Replay decision** | "Live on ten held-out cases: ten out of ten, zero unsafe approvals. Nearly half the model calls failed through the routing bug, and the policy still decided every case correctly. The single-prompt baseline couldn't be measured, so we don't claim a win. Every decision replays from the audit chain, including the human override. Arbiter: vendor decisions your auditors can replay." |

## Lines not to say

- "Nemotron 3 Super" or any model other than Nemotron 3.5 Super VL and Nemotron 3.5 Lightning.
- "Arbiter beat the baseline", unless the published evaluation shows it.
- "Live" over a sample-mode frame or a replayed recording without its date.
- "CISA's live feed." Zetaris federates a committed snapshot of the catalogue.
- "Approve the contract" for the Quillfeather escalation. An escalation needs no approval; its ticket executes at once.
- Anything about monitoring or re-checking approved vendors. P16 was not shipped.

## Run sheet

Before recording (live: Zetaris and Nightshift running, `METERLESS_NO_THINK=1`):

```bash
python run.py preflight
python run.py llm status
python run.py serve
python run.py llm proof
python run.py replay CASE-0003
```

- A live Quillfeather run takes about four minutes. If the run on the day falls back more than once, use the recording of `run-211916c1544d` instead and say "recorded live on 25 October".
- Run the replay on the recording machine first. It needs the audit log of the run being replayed.
- No secrets in any frame: no `.env`, no Nightshift providers tab, no Zetaris API-keys page. The Provider page and the proof show the Runtime URL, never a token.
- Keep the on-screen sources for the numbers: Verizon 2026 DBIR, ProcessUnity / Ponemon-Sullivan 2026.
