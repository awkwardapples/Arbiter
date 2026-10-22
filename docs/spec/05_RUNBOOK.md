# 05: Runbook (schedule, environment checks, review protocol, risks)

All times are **UK local**. BST (UTC+1) applies until **Sun 25 Oct 02:00**, when clocks go back to GMT (UTC+0). The deadline of 27 Oct 23:45 UTC is **23:45 UK time** on Tuesday.

## 1. Key times

| Event | UTC | UK | Status |
|---|---|---|---|
| Participant onboarding | Wed 21 Oct 12:00–13:30 | **Wed 21 Oct 13:00–14:30 BST** | Attend live |
| Build window opens | Thu 22 Oct 00:00 | Thu 22 Oct 01:00 BST | First commit after this |
| Registration closes | Thu 22 Oct 23:45 | Fri 23 Oct 00:45 BST | Confirm you are registered and your solo team shows only you |
| Clocks go back | – | Sun 25 Oct 02:00 BST → 01:00 GMT | Check scheduled runs |
| **First complete submission (our target)** | Mon 26 Oct 20:00 | Mon 26 Oct 20:00 GMT | Tie-break timestamp; can update until the deadline |
| Feature freeze | Tue 27 Oct 12:00 | Tue 27 Oct 12:00 GMT | Bug fixes and docs only |
| **Final submission (our target)** | Tue 27 Oct 18:00 | Tue 27 Oct 18:00 GMT | Leaves 5 h 45 m of buffer |
| Submissions close | Tue 27 Oct 23:45 | Tue 27 Oct 23:45 GMT | Hard deadline |
| Judging | From Wed 28 Oct | – | Watch HackOS Announcements daily |
| Results | Fri 6 Nov 16:00 | Fri 6 Nov 16:00 GMT | Optional call |

## 2. Build schedule (solo; about 14 working hours a day; independent lanes run as parallel Cursor agents)

| Day | Morning | Afternoon | Evening | Exit criterion |
|---|---|---|---|---|
| **Tue 20 / Wed 21** (pre-window) | Day-0 environment checks (§3); email organiser questions (§6) | **Onboarding 13:00–14:30 BST.** Read the Track 3 challenge statement on HackOS and send it to me | Check the Cursor and NVIDIA access folders. Sleep early | §3 all green. **No project commits** |
| **Thu 22** (Day 1) | 08:00 **P0** bootstrap (one agent); 10:30 my review | Parallel: **P1-A** data world and DuckDB · **P2-C** policy · **P2-A** H-MEM port | **P1-B** Zetaris live onboarding (you attend: Docker and the GUI) | P0 merged; P1-A, P2-A and P2-C green; Zetaris tables registered |
| **Fri 23** (Day 2) | Parallel: **P2-B** LLM and Nightshift (needs Nightshift running) · **P2-D** guard and contracts · P1-B parity | **P3** agent loop (one lane; the core) | P3 continues | P1 and P2 merged; P3 e2e sample started |
| **Sat 24** (Day 3) | P3 finish: e2e sample green, traces valid | Parallel: **P4-A** memory, precedents and review · **P4-B** store, approvals, replay, API, **Dockerfile, CI Docker job, `clean_clone_check.py`** | First **live** e2e on 3 cases (Zetaris + Nightshift); fix | P3 and P4 merged; live path proven |
| **Sun 25** (Day 4) | Parallel: **P5-A** reviewer console · **P5-B** eval harness and calibration | `clean_clone_check.py` (day four, as the checklist advises) | **Live eval run** (about 1 h) and session test | Console usable; eval summary exists |
| **Mon 26** (Day 5) | **P6** hardening: Docker, CI, examples, docs, metadata | Record video draft; build deck | **20:00 first full submission on HackOS** | Complete entry submitted |
| **Tue 27** (Day 6) | **P7** polish and Q&A prep; 12:00 freeze | Final eval publish; re-record if needed; final clean-clone check | **18:00 final submission**; tag `submission-final` | Done |

Rules:

- **At most three agents running at once.** You are the review bottleneck.
- Each lane works in its own git worktree and branch (`p1a-data`, …) and merges to `main` only after `verify-pass` is green **and** review.
- **Merge order:** P0 → {P1-A, P2-C, P2-A} → {P2-B, P2-D} → P3 → {P4-A, P4-B} → {P5-A, P5-B} → P6 → P7. **P1-B merges whenever it is green** (it is human-attended and may slip into Friday; P3 starts on DuckDB without it). To pick up merged work, **merge** `origin/main` into the lane branch (`git fetch origin && git merge origin/main`); never rebase a pushed branch (it needs a force-push, which the shell guard blocks).

## 3. Day-0 environment checks (before Thursday; record results in `docs/DAY0_CHECKS.md` on Thursday)

### 3.1 Machine

- [ ] **OS.** Nightshift supports Windows, Mac M1+, Mac M5+ and DGX. **If your laptop runs Linux, tell me now**: Nightshift is not listed for Linux, which changes the Power plan.
- [ ] **RAM ≥ 16 GB** (Zetaris needs 8 GB and 4 CPUs allocated to Docker, plus Nightshift, Cursor and a browser). Disk ≥ 25 GB free.
- [ ] Python 3.12, Git, GitHub CLI (`gh auth login`), Docker Desktop. In the project folder you will create a `.venv` on Thursday (`python -m venv .venv`, then activate it before `scripts/tasks.py setup`); the stop hook uses `.venv`'s interpreter automatically. Node 20 is optional; it is only needed to run the official H-MEM TS runner as a cross-check.
- [ ] `git config user.name` / `user.email` match the GitHub account you will list on the submission form.

### 3.2 Windows-specific (skip on Mac)

> **Your setup (repo in WSL 2 Ubuntu, Zetaris in Docker Desktop, Nightshift native on Windows) is supported** with one condition: WSL must reach Nightshift on the Windows host's `127.0.0.1:8088`. That needs mirrored networking (`%UserProfile%\.wslconfig` → `[wsl2]` / `networkingMode=mirrored`, then `wsl --shutdown`). Check it from **inside WSL** (`docs/spec/06_LAUNCH.md` §1.4). If you prefer not to use WSL, the native-Windows guidance below applies instead.

- [ ] **Run Python natively on Windows (PowerShell), not inside WSL.** Nightshift binds to `127.0.0.1` on Windows, which WSL cannot reach unless mirrored networking is on (`[wsl2] networkingMode=mirrored` in `%UserProfile%\.wslconfig`). Native Windows avoids that. `scripts/tasks.py` is cross-platform for this reason.
- [ ] Docker Desktop on the WSL2 backend gives containers `host.docker.internal`. Allow Python through Windows Firewall on *private* networks when it first binds `:8100`.
- [ ] **Cursor hooks on Windows:** there is a reported Cursor bug where stop-hook stdout (`followup_message`) is not captured on Windows. Test it (§3.5). If it fails, use `/verify-pass` manually; the workflow is designed to work either way.

### 3.3 Zetaris (Data)

- [ ] Follow the Setup Guide: `preflight.sh` passes; Docker resources 8 GB / 4 CPU; `verify.sh` shows **9/9**.
- [ ] UI at `http://localhost:3000`. REST SQL works: run `SELECT 1` via `POST http://localhost:8888/api/v1.0/sql-editor/sqls/run` (headers `Authorization: Bearer`, `X-Org-ID: 1`, UUID `X-Request-ID`).
- [ ] **Create the API key yourself in the Zetaris GUI.** Store it in your password manager. Never paste it into Cursor chat or this chat.
- [ ] Keep `zetaris/getting-started` as a **separate sibling folder** (`~/zetaris-getting-started`, never inside the Arbiter repo), put the key in its `.env.local`, and run `python3 scripts/preflight.py`.
- [ ] **Container → host reachability** (the riskiest unknown). In a scratch folder outside the project:
  1. Run `python -m http.server 8100` serving a tiny `{"records":[{"a":1}]}` file.
  2. From a Zetaris container: `docker compose exec <api-service> curl -s http://host.docker.internal:8100/test.json`.
  3. If it works, register a throwaway REST table to it in the GUI, query it, then delete it.
  - On Linux Docker Engine, add `extra_hosts: ["host.docker.internal:host-gateway"]`.
  - If this cannot be made to work, **fallback B** is ready: Zetaris reads the public repo's raw JSON (`raw.githubusercontent.com/<you>/arbiter/main/data/sample/systems/*.json`), the same proven path it uses for KEV.
- [ ] Note the exact service names from `docker compose ps` (expected: `postgres`, `driver`, `api`, `ui`, `ai-datasteward`); test reachability from `driver` and `api`. Never call port 8889.
- [ ] KEV feed: `curl -sI https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json` returns 200 (the mirror's default branch is `develop`).

### 3.4 Meterless Nightshift (Power)

- [ ] Install Nightshift. In the **Providers** tab, add the NVIDIA key (it lives only there, never in the app's `.env`).
- [ ] Enable the lanes: fast `nvidia/nemotron-3.5-lightning-30b-a3b`, deep `nvidia/nemotron-3-super-120b-a12b`.
- [ ] From the Console, copy `METERLESS_BASE_URL` (expect `http://127.0.0.1:8088/v1`) and `METERLESS_RUNTIME_TOKEN` into your password manager.
- [ ] Discovery (PowerShell):
  ```powershell
  $h = @{ Authorization = "Bearer $env:METERLESS_RUNTIME_TOKEN"; "meterless-app" = "arbiter" }
  Invoke-RestMethod http://127.0.0.1:8088/v1/models -Headers $h | ConvertTo-Json -Depth 5
  ```
  Save the list of ids. **Note whether `meterless/fast` and `meterless/deep` appear,** and which Nemotron model a chat on each returns in `model`.
- [ ] Run one chat each on `meterless/fast` and `meterless/deep` with headers `meterless-app: arbiter` and `meterless-scope: user`. Note the latency of the first (cold) call.
- [ ] Run the organisers' `smoke_test.py` from the Setup Guide.

### 3.5 Cursor (Build)

- [ ] **Access.** Check the HackOS "Space XAI and Cursor" folder (it says access details arrive before 22 Oct, by email and HackOS).
  - **Do not pay yet.** If nothing has arrived by Thu 22 Oct 08:00, buy Pro ($20/month, about £15–16).
  - Pro's included pool is about $20 of usage. Cursor's own models (Composer, Grok) get more included usage than Claude or GPT, which bill at API rates.
  - Plan: use **Composer/Grok for mechanical passes** (P0, P1-A, P5-A, P6). That also strengthens the "with Space XAI" sponsor story. Reserve Claude for P2-A, P2-B and P3.
  - Watch the usage dashboard daily. Upgrade to Pro+ ($60) only if the pool runs out before Sunday.
- [ ] **Hook test.** In a scratch folder, create `.cursor/hooks.json` with a `stop` hook running `python .cursor/hooks/test.py`, which prints `{"followup_message":"say OK"}` when `loop_count == 0`. Ask the agent anything. Pass means the agent replies to the follow-up.
- [ ] Confirm that Plan Mode, worktrees (parallel agents) and the rules picker are present in your version.

### 3.6 GitHub

- [ ] On **Thursday after 01:00 BST**, create the public repo `arbiter` (empty, no template).
- [ ] The first commit is the spec pack, unchanged: `docs: import pre-existing design specification (declared)`. Record its sha in `docs/PRIOR_WORK.md` during P0.

## 4. Review protocol (you, Cursor, and me)

1. **Pass kick-off.**
   - Run `/start-pass <ID>` in Cursor, using the lane id exactly as listed (`0`, `1a`, `1b`, `2a` … `7`).
   - Approve the Plan Mode plan only if it lists every acceptance test id in the pass file.
2. **Agent loop.** Tests first, then implementation, with the stop hook iterating `verify-pass`.
   - You watch for scope creep and secrets.
   - Approve every terminal command that touches Docker, Zetaris or the network.
3. **Pass done.** The agent writes `docs/passes/<LABEL>_REPORT.md` and pushes the branch. Send me:
   > `Review P<n> <branch> <sha>` (+ anything odd you saw)
4. **My review.** I clone the public repo and check out the sha, then:
   - run `python scripts/tasks.py verify-pass --pass <n>` and the full `verify`;
   - read the diff against the pass spec and invariants;
   - run the integrity checks.
   I reply with **PASS**, **PASS WITH FIXES** or **BLOCK**, plus a copy-paste fix prompt for Cursor.
5. **If I am unavailable,** run `/review-pass P<n>` in Cursor **with a different model from the one that built it**. A separate agent that did not write the code reviews it against the pass spec.
6. **Merge** after PASS. Delete the worktree.
7. **Explain-back (15 min).** Read the pass report's "Explain it" section, then ask me anything unclear. The rules say every team member must be able to explain how the system works, and "the AI wrote it" is not an answer.

## 5. Day-by-day definition of "on track"

| Checkpoint | If behind |
|---|---|
| Thu 22:00: P0, P1-A, P2-A and P2-C merged | Drop P2-A to the TS-sidecar fallback (run the reference via Node) and keep going |
| Fri 22:00: P1-B parity and P2-B live chat working | Use `ZETARIS_QUERY_LAYER=views`; use fallback B for sources |
| Sat 22:00: e2e sample green and one live run | Cut the Challenger LLM (keep deterministic triggers); cut the guard model-check layer |
| Sun 22:00: console and eval exist | Console: Queue, Case and Review pages only. Eval: drop consistency to 4×2 |
| Mon 20:00: submitted | Submit whatever is complete and honest; polish Tuesday |

## 6. Questions for the organisers (send Tue 20 / Wed 21)

Email `hackathons@genai.works` for rules questions; post technical ones in HackOS `#help desk`:

1. **metadata.json.** The Cursor, NVIDIA and Meterless overviews say to describe sponsor use "in your README and metadata.json". Is metadata.json required, where should it live (repo root?), and is there a schema?
2. **Pre-written design documents.** I wrote an architecture/implementation spec (no code) before 22 Oct. Is it acceptable to commit it after the window opens and declare it as a pre-existing component?
3. **Judges and live sponsor services.** Will judges run submissions with their own Zetaris and Meterless instances, or is `SAMPLE_MODE=true` (DuckDB mirror plus deterministic fallbacks) the expected judge path?
4. **Live demos.** An earlier schedule slide mentioned "live finalist demos" on 27 Oct. Are there any live sessions or interviews after submission?
5. **Nightshift on Linux** (only if relevant) and the NVIDIA credit claim process.
6. **Cursor access** for teams (the folder still says TBC).

## 7. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner/pass |
|---|---|---|---|---|---|
| R1 | Zetaris containers cannot reach the simulator on `host.docker.internal:8100` | Medium | High | Day-0 test; `host-gateway`; **fallback B**: raw GitHub JSON URLs (same path as KEV) | Day 0, P1-B |
| R2 | USL compile or activation syntax differs from our DDL | Medium | Medium | `ZETARIS_QUERY_LAYER=views` (same query ids, different table names); DDL marked VERIFY | P1-B |
| R3 | Zetaris REST response shape is unknown (columns) | Medium | Medium | Capture a fixture on Day 1; normaliser built against it; the registry declares columns | P1-B |
| R4 | Nightshift lanes do not map `meterless/fast` / `deep` to Nemotron | Medium | Medium | Discover ids; pin `meterless/<class>` ids in env; log `response.model` | P2-B |
| R5 | NVIDIA rate limits or credits run out during eval | Medium | Medium | Concurrency ≤ 2; eval Sunday night; offline numbers labelled as such | P5 |
| R6 | H-MEM port fails vectors | Low | Medium | 1147 lines of deterministic, dependency-free TS; port module by module; fallback is a Node sidecar | P2-A |
| R7 | Cursor stop hook does not work on your OS | Medium | Low | Day-0 test; manual `/verify-pass` | Day 0 |
| R8 | Cursor usage pool exhausted | Medium | Medium | Composer/Grok for mechanical passes; Pro+ if needed | All |
| R9 | Scope overrun in P3 | Medium | High | P3 is a single lane with explicit cut lines; deterministic fallbacks keep e2e green | P3 |
| R10 | Laptop resource exhaustion (Zetaris + Nightshift + Cursor) | Medium | Medium | Close other apps; stop Zetaris when not needed (P2 lanes are offline-testable) | All |
| R11 | Secret leak in a commit, video or screenshot | Low | Critical | `scan_secrets.py` pre-push and in CI; masked config; video checklist; rotate first if leaked | All |
| R12 | Judges cannot run it | Low | Critical | Docker sample mode with no env; `clean_clone_check.py` three times | P6 |
| R13 | The Track 3 challenge statement (HackOS) adds constraints | Medium | Medium | Read on Wed 21; I re-check the spec mapping | Wed 21 |
| R14 | Solo fatigue | High | High | Sleep 7 h; at most 3 parallel agents; freeze Tue 12:00 | You |

## 8. Cut lines (drop in this order; never drop the protected list)

1. Ablation run
2. Captions
3. Memory and Audit UI pages (keep the API endpoints)
4. Guard model-check layer (keep the deterministic layers and the eval gates)
5. Challenger LLM critique (keep deterministic triggers and the re-plan)
6. Consistency eval (reduce to 4×2)
7. NVIDIA-direct provider
8. Zetaris DQ rules (keep the DuckDB-side DQ with parity explained)
9. USL (keep views)

**Never drop:**

- the Zetaris live path;
- the Nightshift provider;
- the H-MEM conformance port;
- the policy engine;
- real loops in traces;
- sample mode;
- Docker;
- the README;
- three or more real examples;
- the video and deck;
- the pre-existing declaration.

## 9. Help channels

| Need | Where |
|---|---|
| Submission questions | HackOS `#help desk` |
| Sponsor setup and errors | HackOS: Help Zetaris, Help Meterless, Help Cursor, Help NVIDIA |
| Agent design and debugging | Mentor office hours (HackOS) |
| Rules | hackathons@genai.works (one working day) |
| Official updates | HackOS Announcements, **check daily** |
