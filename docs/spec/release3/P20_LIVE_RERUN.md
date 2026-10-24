# P20: live re-run after the Nightshift fix, then the docs (lane `20`, you attend)

Branch `p20-live` from `main`, after **P18-A and P19 are merged**:
- P18-A first, so new live traces carry `model_request`, `contradiction_found` and `decide`, and the console can show them;
- P19 first, so outputs carry the corrected headlines.

Opus. Nightshift and Zetaris must be running on your machine. Start **Sun 25, 09:00 GMT**, or as soon as Meterless ships its routing fix.

## 1. Goal

1. Prove the lanes route as designed now that Meterless has fixed the coercion.
2. Commit **live** outputs for all six examples. The hero is example 2 (Quillfeather).
3. Measure the baseline live, and widen the live eval from 5 cases.
4. Leave no stale file in `output_examples/` or `logs/examples/` (C6).
5. Bring every document in line with the new evidence and with whichever console ships at Gate B. Also fix C4 and C5.

## 2. Procedure (stop at each ⏸ and show me the result)

### S1: Did the fix ship?

1. Update Nightshift to the release with the routing fix. Note the version shown in the Console.
2. `python run.py llm proof` with `METERLESS_MODEL_FAST=meterless/fast` and `METERLESS_MODEL_DEEP=meterless/deep` (routing modes, as today).
3. ⏸ Read the two receipts:
   - **Fixed:** `app_policy.mode_coerced` is `False`, or `routed_model` matches the lane design (fast → Lightning, deep → Super VL). Keep the routing modes. Go to S2.
   - **Still coerced:** Meterless said the fix makes *exact model ids* respected. Set:
     - `METERLESS_MODEL_FAST=nvidia/nemotron-3.5-lightning-30b-a3b`
     - `METERLESS_MODEL_DEEP=nvidia/nemotron-3.5-super-vl-120b-a12b`

     Re-run the proof. If the receipts now show the requested model, keep these settings and record in `docs/evidence/nightshift_deviations.md` that lanes now name exact model ids through Nightshift.
   - **Neither works by Sun 16:00 GMT:** keep the routing modes, keep the deviation text as it is, and run S2–S5 anyway with `METERLESS_NO_THINK=1`.
4. Move the previous proof to `docs/evidence/history/nightshift_proof-run3.json`. Commit the new proof.

### S2: Live examples

```bash
METERLESS_NO_THINK=1 python run.py examples --live
python scripts/check_trace.py --require-live --require-collaboration logs/examples/live
```

- A run whose first model call failed fails `--require-live`. Re-run that example **once**. If it fails again, move its trace to `logs/examples/live_failed/` (as P15 did) and keep the sample-mode output for that example.
- ⏸ Review example 2's live brief and trace together before committing:
  - the contradiction and the KEV evidence are present;
  - `contradiction_found` is in the trace.

### S3: Live memory session (only if S1 changed the routing)

```bash
ARBITER_MEMORY=on METERLESS_NO_THINK=1 SAMPLE_MODE=false python run.py demo-session --live --reset --yes
```

Commit the traces to `logs/examples/session/` (move the old ones to `logs/examples/session/history/`) and regenerate `docs/evidence/memory_session.md`.

### S4: Live evaluation

```bash
METERLESS_NO_THINK=1 python run.py eval --live --split test --systems arbiter,baseline,arbiter_offline --cases 10 --consistency 4x2 --publish
```

- About 60–90 minutes. Concurrency stays at the harness default.
- **If the baseline still returns 502 on every call** because routing is still coerced, publish exactly that, as P15 did. Do not change the baseline prompt to make it pass.
- If time runs short, use `--cases 5`. **Never cut the baseline.**
- ⏸ Read the summary together before publishing. If the baseline beats Arbiter on any metric, publish it and explain it.

### S5: Stale outputs (C6)

The root of `output_examples/` must contain only:
- live outputs from S2; or
- for an example with no passing live run, a **current** sample-mode output.

Steps:
1. Regenerate the sample set: `python run.py examples`, which writes `output_examples/sample_mode/` and `logs/examples/sample_mode/`.
   - For an example with no passing live run, byte-copy its file from `sample_mode/` to the root. Its header already says `duckdb / offline`; never edit it.
   - The README repo map then says which root files are live and which are sample mode.
2. Move the 12 superseded top-level `logs/examples/trace-run-*.jsonl` to `logs/examples/history/` with a `README.md` line explaining what they are.
3. Update every reference to a moved path (`docs/SPONSORS.md`, `docs/IMPACT.md`, `docs/passes/*` and tests) so `tests/unit/docs/*` stay green.
   - The Oakhaven injection quote in SPONSORS may point to the new sample-mode or live trace of example 3, if one shows the block.
4. **Test** (`tests/unit/docs/test_outputs_current.py`): no file in `output_examples/` (root or `sample_mode/`) contains `ALL_REQUIRED_CONTROLS_MET` together with an outcome other than APPROVE. Every root file's `header.git_sha` is a descendant of the P14-A merge (`228c52d`).

### S6: Documents

Regenerate or edit, keeping every P17 claims test green:

- **`README.md`:**
  - **See it work:** example 2 live (brief, the contradiction trace line, a Nemotron `model_call` with its receipt, the Evaluator send-back), plus the console screenshots from `scripts/capture_web.py` (or `capture_ui.py` if Gate B held the web console back).
  - **Quick start** says "open http://localhost:8000" if the web console shipped.
  - **Nemotron and Nightshift:** the new proof table and the deviation paragraph rewritten to the S1 outcome (keep the history in one sentence).
  - **Evaluation:** the new block.
  - Fix C4: "The report comes from the deterministic template `template:v1`; the brief from `template:v2`."
- **`docs/SPONSORS.md`:** the NVIDIA table from the new example 2 live trace (each step, lane, model, receipt). If S1 succeeded, add a line showing the fast lane served by Lightning *in a full run*.
- **`metadata.json`:** `models` and `model_evidence` from the new traces; `lane_deviation` per S1; `entry_points.console` = `http://localhost:8000/console/` if shipped.
- **`docs/IMPACT.md`:** the before/after column from the example 2 live run (queries, Zetaris time counted once per query, claims, contradiction, KEV); reliability from the new eval.
- **`docs/DEMO_SCRIPT.md`:** rewrite around the console (§3 below). Fix C5. Remove "sample mode" captions where a live run now exists.
- **`docs/SLIDES.md`:** slide 6 "Reasoning in action" uses a console screenshot of the bench mid-run; slide 11 "Product visuals" uses the console; slide 12 uses the new eval.
- **`docs/QA_PREP.md`:** add questions on the console ("Is the graph real?" → it is the trace, streamed; recordings are labelled) and on the routing fix.
- **`docs/SUBMISSION.md`:** checklist status.

### S7: Clean clone

```bash
python scripts/clean_clone_check.py https://github.com/awkwardapples/Arbiter --evidence
```

Run after the last merge on Monday. If the web console shipped, also open `http://localhost:<port>/console/` from the container while the script runs, and note it in the report. Commit the report.

## 3. The video (target 3:35, hard stop 3:50)

If the web console ships at Gate B:

| Time | Screen | Narration (essence) |
|---|---|---|
| 0:00–0:20 | Title, then three cited numbers | "Third parties are in 48% of breaches; companies assess only 36% of their vendors… Meet the analyst deciding whether a new SaaS vendor can touch customer data." |
| 0:20–0:35 | Console, Assess page; pick Quillfeather; **Start assessment** | "Arbiter's agents gather and cross-check the evidence; a versioned policy decides; every step is on screen." |
| 0:35–1:50 | **Live run** of example 2 on the bench, sped up in editing with an on-screen "2× / 4×" label. Pause on the Planner reading the USL model, the Nightshift → Nemotron edge (hover: lane, model, receipt), the Zetaris queries filling the records column, the **Evaluator sending the Planner back** (red dashed arc), the **clash card** (EU vs US), the KEV join, and the Challenger | "The Planner reads Zetaris's semantic model… Nemotron plans through Meterless Nightshift; here's the receipt… The Evaluator finds the incident and contract evidence missing and sends the plan back… The vendor says EU-only hosting; the contract system says US… FortiOS is on CISA's exploited list…" |
| 1:50–2:15 | The ruling (Escalate), then the Case page: brief, claim-vs-record, drafted ticket, **Approve contract** with a rationale | "The policy, not a model, rules: escalate to the lead, ticket drafted, nothing sent until a signed contract is approved." |
| 2:15–2:35 | **Provider** page: Runtime URL with the token hidden, the lane table, `python run.py llm proof` in a terminal returning both receipts | "One real request per lane through Nightshift, served by Nemotron; here's where the app connects to the Runtime URL." |
| 2:35–2:55 | **Sources** page: the USL diagram, the DQ finding `CTR-30028`, 416/416 parity | "Five systems and CISA KEV in one Zetaris semantic layer; the Planner reads it in 304 tokens; a DQ rule caught a DPA marked signed without a date." |
| 2:55–3:15 | **Memory**: a recorded session run of Tessellate, with the precedent edge lit; the Memory page | "A lead's precedent lets a similar vendor be approved with conditions, and only through policy." |
| 3:15–3:35 | Evaluation page; Case → Audit trail → **Replay decision** | "Live on held-out cases… every decision replays, including the human override. Arbiter: vendor decisions your auditors can replay." |

**Rules:**
- Say "live" only over live runs. A recorded run is introduced as "recorded live on 24 October".
- No keys, `.env` or Providers tab on screen.

If Gate B held the web console back: use the P17 script, but replace the sample-mode Quillfeather shot with the live example 2 run from S2.

## 4. Acceptance tests (marker `p20`)

| Id | Test |
|---|---|
| P20-T1 | `check_trace --require-live --require-collaboration` passes on every file in `logs/examples/live/` |
| P20-T2 | `test_outputs_current.py` (S5) |
| P20-T3 | The P17 claims tests (`tests/unit/docs/*`) are green on the new evidence |
| P20-T4 | `metadata.json` `models` ⊆ model ids in `logs/examples/live/**` and `docs/evidence/nightshift_proof.json` |
| P20-T5 | The README eval block equals the rendered latest live summary |

## 5. Claude Code prompt

```
/start-pass 20
You are implementing P20 of Arbiter Release 3: the live re-run after the Nightshift routing fix, then the documents. I am attending: Nightshift and Zetaris are running.
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/R3_00_ASSESSMENT.md; docs/spec/release3/P20_LIVE_RERUN.md; docs/passes/P15_REPORT.md; docs/passes/P17_REPORT.md; docs/evidence/*.
Never print or commit a token. Committed evidence comes only from real runs; never edit a trace or an output by hand.
Plan first: .cursor/plans/P20.md with steps S1–S7 and tests P20-T1..T5. Wait for my approval.
Then run each step, stopping at every ⏸ to show me the result.
Finish with docs/passes/P20_REPORT.md and docs/cursor-usage/P20.md (tool: Claude Code); push p20-live; PR into main; delete .cursor/ACTIVE_PASS; stop.
```
