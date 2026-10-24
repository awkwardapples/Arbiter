# Demo script

Target 3:35, hard stop 3:50. File name: `OAH2026-Arbiter-ReasoningArchitecture-Demo.mp4`. The video has not been recorded yet; this is the script to record from.

Every shot below is backed by a committed file. Two rules for the voice-over:

1. **Say "live" only over live evidence.** The live shots are example 1 (`run-83de5da137c0`, `logs/examples/live/`), the Nightshift proof (`docs/evidence/nightshift_proof.json`), the memory session (`logs/examples/session/`) and the live eval (`eval/results_live/`).
2. **Label sample mode on screen.** The Quillfeather contradiction and KEV shots come from the sample-mode run `run-a90b795279e5` (`logs/examples/sample_mode/`), because both live attempts at example 3 failed and Quillfeather is not one of the committed live examples. Put a caption "sample mode (DuckDB mirror, deterministic fallback)" on those frames. The same contradiction and the 15-row KEV join also ran live in the evaluation (`run-257c86984507`, `eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl`, `ESCALATE`), which you may mention in one clause.

## Evidence for each shot

| Shot | Run or file | What it shows |
|---|---|---|
| Live run | `run-83de5da137c0`, `logs/examples/live/trace-run-83de5da137c0.jsonl`, `output_examples/example_1_output.json` | Pellucid Forms Ltd, `APPROVE`, 159 s; 12 Zetaris queries with request ids; 5 Nemotron calls with receipts (Super VL); Evaluator sends the Planner back (C06, C09); Challenger asks for a re-plan; one 502 that falls back |
| Contradiction and KEV (sample mode) | `run-a90b795279e5`, `logs/examples/sample_mode/trace-run-a90b795279e5.jsonl`, `output_examples/sample_mode/example_2_output.json` | Quillfeather Payroll Cloud Ltd, `ESCALATE`: vendor says EU, contract `CTR-30007` says US; FortiOS has 15 known-exploited vulnerabilities; ITSM ticket drafted |
| Nightshift proof | `docs/evidence/nightshift_proof.json` | fast → `nvidia/nemotron-3.5-lightning-30b-a3b`, receipt `rcpt_req_924f14pn`; deep → `nvidia/nemotron-3.5-super-vl-120b-a12b`, receipt `rcpt_req_p412l7ql`; both `mode_coerced` to `auto` |
| Deviation | `docs/evidence/nightshift_deviations.md` | Super 3 120B not entitled; app rule coerces both lanes; Meterless acknowledged, fix targeted for Sunday's release |
| Zetaris USL | `docs/ZETARIS_USL.md`, `docs/img/zetaris_1.png`–`zetaris_3.png`, `docs/passes/P1-B_parity.json` | Sources, KEV REST table, SchemaStore views; USL `vendor_risk` green; DQ flags `CTR-30028` |
| Memory | `docs/evidence/memory_session.md`, `logs/examples/session/trace-run-a1c914808974.jsonl` | Precedent P-0001 from Marrowgate moves Tessellate to `APPROVE_WITH_CONDITIONS`; reset and analyst-role precedents block it |
| Eval and replay | README eval block, `docs/EVALUATION.md`, `python run.py replay CASE-0003` | Live 5/5, 0 unsafe, 5 of 25 calls fell back; baseline not measured; offline 16/16 |

## The video

| Time | Screen | Narration (essence) |
|---|---|---|
| 0:00–0:20 | Title card (track, one-liner), then three numbers with their sources on screen | "Reasoning Architecture. Third parties are in 48% of breaches. Companies assess only 36% of their vendors, and 40% have a backlog. Meet the third-party risk analyst deciding whether a new SaaS vendor can touch customer data." |
| 0:20–0:40 | Console, New assessment (questionnaire form) | "Arbiter turns that decision into a cited, replayable outcome with the next action drafted. The company data is synthetic; the vulnerability data is CISA's public KEV catalogue." |
| 0:40–1:10 | Architecture slide: agents, loops, policy, Zetaris USL, Nightshift | "Nemotron agents plan, gather and challenge. A versioned policy decides, never a model. H-MEM remembers what humans decided, and every action is a signed contract." |
| 1:10–1:35 | **Live run**: example 1 output and its trace, scrolled to a `query_zetaris` line (request id) and a `model_call` line (`nvidia/nemotron-3.5-super-vl-120b-a12b`, `rcpt_req_ltd0d684`), then the Evaluator `needs_revision` line | "This is a live run: twelve queries through Zetaris, each with a request id, and five agent steps on Nemotron through Nightshift, each with a receipt. Here the Evaluator sends the Planner back for incident and contract evidence before anything is decided." |
| 1:35–2:05 | Case page for Quillfeather, captioned **sample mode**: brief headline, claim-versus-record card (EU versus US), KEV bullet, drafted ticket | "The vendor says EU-only hosting. The Evaluator checks the contract system: US. FortiOS has fifteen known-exploited vulnerabilities. The policy escalates to the lead, with the ticket drafted. This frame is sample mode; the same finding ran live in our evaluation." |
| 2:05–2:30 | **Meterless and Nemotron**: terminal showing `docs/evidence/nightshift_proof.json` (or `python run.py llm proof`; Runtime URL shown, token hidden): both receipts and routed models; then the deviation line | "One real request per lane through Nightshift: the fast lane was served by Nemotron 3.5 Lightning, the deep lane by Nemotron 3.5 Super VL, and here are the receipts. Honest note: a Nightshift app rule currently coerces both lanes to auto. Meterless has acknowledged it, with a fix due in Sunday's release." |
| 2:30–2:50 | **Zetaris USL**: `zetaris_1.png`, `zetaris_3.png`, then the DQ result for `CTR-30028` | "Five systems and CISA KEV in one semantic layer. The Planner reads this model, three hundred tokens instead of raw schemas, and a DQ rule caught a DPA marked signed without a date." |
| 2:50–3:15 | **Memory**: `docs/evidence/memory_session.md` table, then the `precedent_applied` line | "Memory changes decisions only through policy and human sign-off. The lead's precedent from Marrowgate lets Tessellate be approved with conditions. Reset memory, or let an analyst try to set a precedent, and it escalates again." |
| 3:15–3:35 | README eval block, then `python run.py replay CASE-0003` showing a match | "Live on held-out cases: five out of five, zero unsafe approvals, and when a model call failed, the decision still matched. The single-prompt baseline couldn't be measured through the routing bug, so we don't claim a win. Every decision replays identically. Arbiter: vendor decisions your auditors can replay." |

## Lines not to say

- "Nemotron 3 Super" or any model other than Nemotron 3.5 Super VL and Nemotron 3.5 Lightning.
- "Arbiter beat the baseline." The baseline is unmeasured.
- "Live" over the Quillfeather sample-mode frames.
- "CISA's live feed." Zetaris federates a committed snapshot of the catalogue.
- Anything about monitoring or re-checking approved vendors. P16 was not shipped.

## Run sheet

Before recording:

```bash
python run.py preflight
python run.py llm status
SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve
python run.py ui
python run.py assess --input input_examples/example_2.json
python run.py replay CASE-0003
```

- Run the replay on the recording machine first. It needs the audit log of the run being replayed.
- Re-capture the console stills with `scripts/capture_ui.py` and dismiss the Streamlit "Help agents write better apps" popup that covers the committed PNGs.
- No secrets in any frame: no `.env`, no Nightshift providers tab, no Zetaris API-keys page. The proof JSON shows the Runtime URL, never a token.
- Keep the on-screen sources for the three numbers: Verizon 2026 DBIR, ProcessUnity / Ponemon-Sullivan 2026.
