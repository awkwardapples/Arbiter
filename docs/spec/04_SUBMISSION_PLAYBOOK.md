# 04: Submission playbook

Sources: Submission Requirements, Submission Form Preview, Demo Video Guide, Disqualification Checklist, Technical Execution Guide, Strong and Weak Submission Examples, AI Usage Policy, Official Rules (working draft) and Participant onboarding deck. Where these disagree, the Official Rules on the event page apply.

## 1. Deliverables map

| Required item (official wording) | Arbiter artefact | Built in | Verified by |
|---|---|---|---|
| Demo video, 1–4 min: main workflow, how the agent solves the challenge, key features, Zetaris and Meterless integration | `OAH2026-Arbiter-ReasoningArchitecture-Demo.mp4`, 3:15–3:40 | P7 | §2.5 checklist; private-window link test |
| Slide deck: 8 points | PDF deck, 13 slides (§3) | P7 | §3 coverage table |
| Public GitHub repo with README (setup, usage, dependencies) | `github.com/<user>/arbiter` | P0–P7 | `scripts/clean_clone_check.py` (§6) |
| Sponsor technology explanation: Zetaris, Meterless, Cursor, NVIDIA, plus what was unique | `docs/SPONSORS.md`, README §Sponsor technology, form text (§4) | P6 | Each claim links to a file and a trace line |
| Pre-existing components declared | Form text (§7), README §Pre-existing components, `docs/PRIOR_WORK.md` | P6 | Matches the git history |
| Project name, description, team, track | Form worksheet (§7) | P7 | Same track named in README, deck and video |
| *Recommended:* ≥ 3 sample inputs and outputs; logs/traces; `.env.example`; `SAMPLE_MODE=true` | `input_examples/` (6), `output_examples/` (6, generated), `logs/examples/`, `.env.example`, sample mode | P3–P6 | `tasks.py verify`, `check_trace.py` |
| *Sponsor overviews:* "Say how your team used … in your README and metadata.json" | `metadata.json` (§5) | P6 | `scripts/check_metadata.py` |

## 2. Demo video

### 2.1 Rules that shape the script

- **Length:** 1–4 min; the guide recommends 2:30–3:30. Target **3:30**, hard stop at 3:45.
- **Must show:** at least two agents with clear roles, real collaboration, a real run, Zetaris and Meterless doing real work, the final output, why it matters.
- **Strong signals:** an architecture diagram; trace lines showing agent-to-agent interaction; a failure, retry, critique or validation loop.
  - The guide's own example of a strong line: "The Critic rejected the Analyst's pricing claim because no pricing data was retrieved…". Narrate a moment where one agent *changes* another's work.
- **Waiting can be cut**, but input and output must be real. Record every case from real live runs (Zetaris + Nightshift). Keep each run's `run_id` on screen, so the trace file in `logs/examples/` matches the video.
- **No secrets on screen.** Masked env (`ZETARIS_API_KEY=***`) is fine. Never open the Nightshift Providers tab or the Zetaris API-keys page while recording.

### 2.2 Script (about 470 spoken words at about 140 wpm, plus visuals)

| Time | Screen | Narration (draft; final wording after P6) |
|---|---|---|
| 0:00–0:20 | README header: track badge, one-liner | "Our entry is for **Reasoning Architecture**. Third parties are now involved in 48% of breaches (Verizon DBIR 2026), usually through basic failures like missing MFA. The moment to catch that is vendor onboarding. But a third-party risk analyst's evidence is spread across five systems and a vendor questionnaire, so decisions are slow, inconsistent and hard to audit." |
| 0:20–0:45 | Input JSON → five outcome badges | "Arbiter takes an onboarding request and returns one of five decisions: approve, approve with conditions, request information, escalate or decline. Every fact is cited, a counterfactual says what would change the answer, and the next action is drafted under a signed contract. All company data in this demo is synthetic; the vulnerability catalogue is CISA's real public KEV feed." |
| 0:45–1:25 | Architecture diagram, then authority table | "The models read; the policy decides. The Planner chooses evidence queries. The Evidence agent runs them through Zetaris and extracts vendor claims with verbatim quotes. The Evaluator checks every quote and cross-checks claims against systems of record. If something is missing or contradicted, it sends the Planner back. A deterministic, versioned policy makes the decision. The Challenger attacks it and can force a re-plan or an escalation, never an approval. Memory and actions are governed by Meterless engines." |
| 1:25–2:15 | Reviewer console → case A (Quillfeather Payroll, T1) → agent timeline → trace JSONL | "A real run. The Planner's first, cost-aware plan skips the vulnerability check. The Evaluator flags C12 as unevidenced and sends it back: here is the `needs_revision` line. On the second pass, the Evidence agent runs a federated Zetaris query that joins the vendor's declared components with CISA KEV, and finds MOVEit Transfer. The Evaluator also catches a contradiction: the vendor says EU-only hosting, but the contract system says US. The policy escalates; the Challenger agrees; an ITSM ticket is drafted and executed under a signed contract." |
| 2:15–2:45 | Zetaris UI (USL `vendor_risk` model, query history) → trace lines with `zetaris_request_id` → **`python run.py preflight`** (shows the Meterless provider connection: Console Runtime URL `http://127.0.0.1:8088/v1`, status online, routes, token masked) → Nightshift showing Nemotron lanes → trace `provider=meterless model=nvidia/nemotron…` for one real request and its result. This covers the Setup Guide's "What to show judges": the app, its Meterless provider connection, and one real request through Nightshift | "Zetaris is the single SQL access point. Five synthetic systems and the public KEV feed are federated into one semantic model with data-quality rules. Every model call goes through Meterless Nightshift to NVIDIA Nemotron: the fast lane for extraction, the deep lane for planning and challenge. Meterless H-MEM holds memory; a Meterless Scout guard screens untrusted vendor text and signs every action." |
| 2:45–3:15 | Case B (Marrowgate) ESCALATE → Review form (lead, bridge letter, create precedent) → Memory page (P-0001, ledger) → case C (Tessellate) APPROVE_WITH_CONDITIONS citing P-0001 | "Memory changes decisions, under governance. Marrowgate has no current SOC 2, so it escalates. A TPRM lead approves with conditions on the strength of a bridge letter, and that becomes a precedent in H-MEM. Next session, Tessellate has the same gap. Arbiter retrieves the precedent, the policy permits the exception, and the decision becomes approve-with-conditions, still waiting for a lead's sign-off." |
| 3:15–3:35 | Eval table (generated) → injection catch flash (Oakhaven) → replay "match ✓" | "On our held-out synthetic test set, Arbiter made zero unsafe approvals versus [n] for a single-LLM baseline with the same data and model. It blocked an injected instruction hidden in a SOC 2 summary, and any decision replays identically from the audit log." *(Numbers are read from `summary.json` on the day; if the baseline wins a metric, say so.)* |
| 3:35–3:45 | Closing card | "Arbiter: reliable vendor decisions your auditors can replay. Built in Cursor." |

### 2.3 Shot list and pre-recording

1. **Pre-run cases B and C** live with `python run.py demo-session --live --reset --yes` (the session test; it never runs case A). Then record **case A fresh on camera** with `ARBITER_MEMORY=off`, so it has no prior assessment and its verify loop is visible. Keep every run id.
2. **Clean the screen.** Terminal font ≥ 16 pt; browser zoom 125%; dark/light consistent; hide the dock and notifications; close `.env`; `history -c` (or PowerShell `Clear-History`).
3. **Recording settings:** OBS (or the Windows Game Bar / QuickTime) at 1080p, 16:9, headset mic.
4. **Captions** are optional but helpful. Generate them and add `.srt` if time allows.

### 2.4 Hosting

- Upload to HackOS (primary).
- Keep a YouTube *unlisted* backup and a Google Drive copy with "anyone with the link" access.
- Test both in a private window.
- Put the link in the README under `## Demo video`.
- Keep the files live until after 6 Nov.

### 2.5 Video checklist

- [ ] 1:00 ≤ length ≤ 3:45
- [ ] Track, user and problem stated in the first 20 s
- [ ] At least two agents with a visible interaction, including one loop line in the trace
- [ ] Zetaris shown doing work (UI or trace lines with request ids)
- [ ] Meterless shown doing work (Nightshift lanes and trace provider/model, H-MEM ledger, contract)
- [ ] Final output shown, plus why it matters
- [ ] No secrets in any frame (scrub around every terminal)
- [ ] Numbers match `summary.json`

## 3. Slide deck (13 slides; covers all 8 required points)

| # | Slide | Required point | Content source |
|---|---|---|---|
| 1 | Arbiter: title, track, one-line description, team | – | Form §7 |
| 2 | **The problem**: DBIR 2026 (48% third-party involvement, +60% YoY; MFA, rotation, least-privilege root causes; exploitation the top vector) | 1 Problem and users | **Adapt from the old market-research deck** (update stats) |
| 3 | **Who it's for**: TPRM analyst, lead/CISO, procurement requester, auditor; jobs and pains | 1 | Old deck personas + master spec §1.2 |
| 4 | **The gap**: incumbents automate evidence *collection*; nobody makes the *judgment* reliable; data-sovereignty angle | 1 / 2 | Old deck competitor slide (re-angled) |
| 5 | **The solution**: input → five outcomes; cited facts, counterfactuals, signed next action | 2 Solution | Master spec §1.5 |
| 6 | **Agent workflow**: architecture diagram with loops and authority ("models read, policy decides") | 3 Workflow/architecture | `docs/ARCHITECTURE.md` diagram |
| 7 | **Reasoning in action**: a real trace excerpt (Evaluator → Planner `needs_revision`; Challenger) | 3 | `logs/examples/…` |
| 8 | **Memory under governance**: three sessions; precedent exception rules | 3 / 6 | Session test table |
| 9 | **Technical stack**: Python 3.12, FastAPI, Streamlit, pydantic, DuckDB, SQLite, Docker, CI | 4 Technical stack | README |
| 10 | **How Zetaris and Meterless were used** (+ NVIDIA, Cursor) | 5 Sponsor use | `docs/SPONSORS.md` |
| 11 | **What was unique** about our sponsor use | 6 Unique | §4 "What was unique" |
| 12 | **Product visuals**: console Queue, Case "Why", Review, Memory | 7 Product visuals | UI screenshots (synthetic data) |
| 13 | **Results and future**: generated eval table plus limitations; future enhancements (real connectors via Zetaris JDBC, OCR of real SOC 2 PDFs with NVIDIA NeMo Retriever, policy what-if simulation, renewal monitoring from KEV deltas, multi-tenant RBAC) | 8 Future | `summary.json`, master spec §4 |

**Adapting the old market-research deck.**

- **Not provided.** I have not seen the file. Share it and I will map it slide by slide.
- **Rules:**
  - Reuse problem, market and persona research (slides 2–4) after refreshing statistics to DBIR 2026.
  - Drop every slide that describes the old prototype's features. Its confidence score, "RAG" and audit claims do not describe this build and would read as overclaiming.
  - Declare the research and narrative as pre-existing (§7).
  - Track 3 is not Wildcard, so no before/after story is needed.
- **Format:** build the deck as an editable Slides artifact (exports to PDF/PPTX) or in your PowerPoint, and submit the PDF.
- **Visual rules:**
  - About 30 words per slide.
  - Text plus colour, never colour alone.
  - No keys or real personal data in screenshots.

## 4. Sponsor technology explanation (draft; finalise in P6 with file links)

**Zetaris (data).**

- Third-party risk evidence lives in five disconnected systems: procurement, contracts (CLM), ITSM incidents, a GRC sanctions watchlist and a vendor trust portal. They are synthetic and served as REST APIs.
- We registered each one in Zetaris as a Lightning REST table, exposed them as SchemaStore views, and modelled them in a Unified Semantic Layer (`arbiter.vendor_risk`) with keys and data-quality rules.
- We also registered CISA's public Known Exploited Vulnerabilities feed. One federated SQL query joins a vendor's declared software components with KEV.
- Arbiter's agents never hold a connector. Every evidence query is a registry query sent to Zetaris's REST SQL endpoint, and every fact in a decision cites the Zetaris query id and request id that produced it.
- Zetaris DQ rules (for example, "DPA marked signed without a date") become evidence gaps that stop an approval.

**Meterless (runtime, memory, intent).** Three engines are load-bearing:

1. **Nightshift / Runtime (POWER).**
   - Every model call goes through one injected generator to the Meterless Runtime: OpenAI-compatible, with `meterless/fast` and `meterless/deep` routing modes.
   - It follows the Meterless POWER contract (discovery via `/v1/models`, required headers, token handling) and falls back to NVIDIA direct, then to deterministic logic.
2. **H-MEM.**
   - A Python port of the reference engine that passes a Python port of the official conformance runner (all 13 vectors).
   - It stores governed precedents from human reviews and prior assessments, with a trust ledger and feedback deltas, so memory measurably changes later decisions.
3. **Scout Intent**: our implementation of its guard and execution-contract specification (Scout ships as a spec with eval sets, not a library).
   - Untrusted vendor text is screened for injection and redacted before any model sees it.
   - Every action is issued as an HMAC-signed execution contract with scoped capabilities and approval gates.

**NVIDIA (models).**

- The agents reason with NVIDIA Nemotron, reached through Meterless Nightshift lanes:
  - Nemotron 3.5 Lightning (fast lane) for extraction and the guard's ambiguous band;
  - Nemotron 3 Super (deep lane) for planning, challenge and the cited report.
- The model id returned by the runtime is logged on every call.

**Cursor (with Space XAI) (development).**

- The whole project was built in Cursor, driven by a written specification:
  - `AGENTS.md` and project rules encode invariants;
  - each pass started in Plan Mode with the plan saved to `.cursor/plans/`;
  - acceptance tests were written first;
  - a stop hook re-ran the pass's verification and fed failures back to the agent until green;
  - independent pass lanes ran as parallel worktree agents.
- Models used per pass (Composer / Grok / others) are logged in `docs/CURSOR_USAGE.md`.

**What was unique.**

1. **The policy decides; models only read, plan, critique and write.** Approval is impossible without verified facts.
2. **The Evaluator uses Zetaris to verify the vendor.** It re-queries systems of record and the public KEV feed to test the vendor's own claims, and turns contradictions into escalations.
3. **Memory is governed.** An H-MEM precedent can change a decision only through a policy-declared exception, and only with the right human approval. Wrong precedents lose trust through the ledger.
4. **Scout-style signed contracts make every downstream action verifiable,** and any decision replays identically from the hash-chained audit log.

## 5. `metadata.json`

The Cursor, NVIDIA and Meterless overviews ask for it, but **no schema has been published**. Ask the organisers (05_RUNBOOK §6). Until they answer, ship this; `scripts/check_metadata.py` validates that every `files` path exists.

```json
{
  "schema": "arbiter-metadata/1",
  "project_name": "Arbiter",
  "description": "Auditable reasoning architecture that helps third-party risk analysts decide whether to approve, query, escalate or decline a new SaaS vendor, producing a replayable, cited decision with the next action under a signed contract.",
  "track": "Reasoning Architecture",
  "team": {"name": "Arbiter", "members": [{"name": "<full name>", "github": "<username>", "role": "Solo builder", "primary_contact": true}]},
  "repository": "https://github.com/<username>/arbiter",
  "demo_video": "<link>",
  "slide_deck": "<link or docs/Arbiter-deck.pdf>",
  "entry_points": {
    "api": "POST http://localhost:8000/run",
    "cli": "python run.py assess --input input_examples/example_1.json",
    "docker_sample_mode": "docker run --rm -p 8000:8000 -e SAMPLE_MODE=true arbiter"
  },
  "agents": [
    {"name": "PlannerAgent", "role": "Plans registry queries; revises on Evaluator/Challenger feedback", "route": "meterless/deep"},
    {"name": "EvidenceAgent", "role": "Runs Zetaris queries; guards and extracts quoted vendor claims", "route": "meterless/fast"},
    {"name": "EvaluatorAgent", "role": "Grounds quotes, cross-checks claims against systems of record, sends work back", "route": "meterless/fast"},
    {"name": "ChallengerAgent", "role": "Attacks the candidate decision; can force re-plan or escalation only", "route": "meterless/deep"},
    {"name": "ReporterAgent", "role": "Writes the cited dossier and drafts actions", "route": "meterless/deep"},
    {"name": "PolicyEngine", "role": "Deterministic, versioned decision (no LLM)", "route": null},
    {"name": "MemoryKeeper", "role": "Meterless H-MEM precedents and trust ledger", "route": null},
    {"name": "ScoutGuard", "role": "Meterless Scout injection/PII guard", "route": "meterless/fast (ambiguous band)"},
    {"name": "ActionExecutor", "role": "Meterless Scout execution contracts; approval-gated actions", "route": null}
  ],
  "sponsor_technologies": {
    "zetaris": {
      "role": "Single SQL access point federating five enterprise systems and CISA KEV",
      "features": ["Lightning REST tables", "SchemaStore views", "USL model arbiter.vendor_risk", "DQ rules", "Federated public+private join", "REST SQL API"],
      "files": ["zetaris/sql/01_sources.sql", "zetaris/sql/02_kev.sql", "zetaris/sql/03_usl.sql", "zetaris/dq_rules.yaml", "app/data/zetaris.py", "app/data/queries.yaml"]
    },
    "meterless": {
      "engines": ["Nightshift Runtime (POWER contract)", "H-MEM", "Scout Intent (guard + execution contracts subset)"],
      "files": ["app/llm/providers/meterless.py", "app/llm/generator.py", "app/memory/hmem/", "app/memory/precedents.py", "app/guard/scout_guard.py", "app/actions/contracts.py"],
      "evidence": ["tests/conformance/test_hmem_conformance.py", "tests/conformance/test_scout_adversarial.py", "logs/hmem-ledger.jsonl"]
    },
    "nvidia": {
      "models": ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-super-120b-a12b"],
      "access": "Via Meterless Nightshift lanes (primary) or build.nvidia.com (fallback)",
      "files": ["app/llm/providers/meterless.py", "app/llm/providers/nvidia.py"]
    },
    "cursor": {
      "usage": ["AGENTS.md + project rules", "Plan Mode per pass", "Tests-first acceptance suites", "Stop-hook verify loop", "Custom commands", "Parallel worktree agents"],
      "files": ["AGENTS.md", ".cursor/rules/", ".cursor/commands/", ".cursor/hooks.json", ".cursor/plans/", "docs/CURSOR_USAGE.md"]
    }
  },
  "models": ["<filled from eval env.json: ids actually returned by the runtime>"],
  "data": {"synthetic": true, "public": [{"name": "CISA Known Exploited Vulnerabilities", "licence": "CC0 1.0", "source": "https://github.com/cisagov/kev-data"}]},
  "sample_mode": "SAMPLE_MODE=true runs the full agent loop on a DuckDB mirror of the Zetaris model with deterministic fallbacks when no model provider is reachable",
  "pre_existing_components": ["See README §Pre-existing components"],
  "licence": "MIT"
}
```

## 6. Final validation flow (`python scripts/clean_clone_check.py <repo-url>`)

This automates the Disqualification Checklist §14, including step 9 ("THE ONE PEOPLE SKIP"):

1. Clone into a temporary directory. Check that `run.py`, `README.md`, `.env.example`, `input_examples/` (≥ 3) and `output_examples/` (≥ 3) exist.
2. `docker build -t arbiter-check .`
3. With **no `.env`**: `docker run -d -p 8000:8000 -e SAMPLE_MODE=true arbiter-check`.
   - Wait for `/health`.
   - POST every `input_examples/*.json` to `/run`.
   - Assert `status`, schema, distinct outputs and outcomes matching `input_examples/expected.json`.
4. Copy the container's `logs/`, run `check_trace.py` on every trace, and check stdout lines.
5. Run a judge-style novel input: generate a random inline submission (seeded by the current time), POST it, and assert a valid decision.
6. Run `scan_secrets.py` over the tree, plus `git log -p` for secret patterns; run `git ls-files` for `.env`, `*.pem` and `*.key`.
7. Native path: `python -m venv` → `pip install -r requirements.txt` → `SAMPLE_MODE=true python run.py assess --input input_examples/example_1.json`.
8. Write `logs/clean-clone-report.md` with pass/fail per step.

**Run it** Sunday 25 Oct ("day four", as the checklist advises), Monday before the first submission, and Tuesday before the final one.

## 7. Submission form worksheet (pre-filled)

```
Project name: Arbiter
Short description: An agent system that helps third-party risk analysts decide whether to approve, query, escalate or decline a new SaaS vendor, by cross-checking the vendor's claims against five Zetaris-federated internal systems and CISA's exploited-vulnerability catalogue under a versioned policy and governed memory of past human decisions, producing a replayable, cited decision with the next action drafted under a signed contract.
Paragraph: <3–4 sentences: problem (DBIR), user, how (agents + policy + memory), proof (eval, replay)>

Track: [x] Reasoning Architecture

Team member 1:
  Full name: <you>
  HackOS account email: <HackOS email>
  GitHub username: <must match commit author>
  Role: Solo builder: architecture, agents, Zetaris and Meterless integration
  Primary contact: Yes

GitHub repository URL (public): https://github.com/<username>/arbiter
Colab links: none
Demo video: <HackOS upload> (backup: <unlisted link>)
Slide deck: <PDF>
Sponsor technology explanation: §4 (paste per sponsor)

Pre-existing components:
1. Design documentation: architecture and implementation specification (docs/spec/, AGENTS.md, .cursor/ rules, commands and hook scripts), written 20–21 Oct 2026 before the build window and committed after it opened, unchanged in the first commit. It contains no application code.
2. Concept, problem research and pitch narrative from my earlier prototype "Vendor-Risk-Assessment-Agent" (React/Node, github.com/awkwardapples/Vendor-Risk-Assessment-Agent). No code from it is used.
3. Market-research slides (problem, users, competitors), refreshed and reused in deck slides 2–4.
4. Third-party open material used under licence and attributed: Meterless H-MEM conformance vectors and Scout adversarial eval cases (Apache-2.0), CISA KEV (CC0 1.0).
No data was prepared before the window: all synthetic data is produced in-window by a seeded generator.
```

> Confirm the licence of the Meterless repo on Day 0 (`LICENSE` at its root) and quote it exactly in `vendor/meterless/NOTICE.md`. If it is not Apache-2.0, update items 4 and README.

Before you open the form:

- **The roster locks when the first submission is created.** Solo is fine, but check that HackOS shows only you.
- **Create the first submission on Monday evening** for the tie-break timestamp, then update it until the deadline.

## 8. After submission: what to attend and what to keep

| When (UTC / UK) | What | Required? |
|---|---|---|
| 27 Oct 23:45 UTC (23:45 GMT) | Submissions close. Tag `submission-final`; **no further pushes to the default branch** (put post-hackathon work on another branch) | Freeze |
| 28 Oct onwards | Judging. "Judges may ask for clarification; watch Announcements on HackOS." Check daily and answer fast. Keep the repo public, the video live, Zetaris and Nightshift installable, and your machine able to re-run the demo | **Be reachable** |
| Possibly | Live finalist demos: an older Zetaris schedule slide mentioned "live finalist demos" on 27 Oct. Current official documents do not. Keep a 5-minute live-demo script ready (`docs/DEMO_SCRIPT.md`) | Prepare; confirm with organisers |
| Any time | Verification requests (Official Rules §13: "cooperate with reasonable organizer requests"). AI Usage Policy: "Judges may ask how something works… 'the AI wrote it' is not an answer." Study `docs/QA_PREP.md` (P7) | Required if asked |
| 6 Nov 16:00 UTC (16:00 GMT) | Results call on HackOS, with certificates | Optional, recommended |
| Within 30 days of results | Prize paid by bank transfer (if placed) | – |
