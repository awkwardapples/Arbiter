# 06: Launch plan: from today to three agents running in parallel

This is the literal sequence. Commands are for your **WSL 2 Ubuntu** terminal unless marked PowerShell. Times are UK (BST until Sun 25 Oct).

## 0. Two different things are both called "lanes"

| Term | What it is | Where it lives | How many you need |
|---|---|---|---|
| **Nightshift lane** | A model route *Arbiter itself* calls at run time (`meterless/fast` → Nemotron 3.5 Lightning, `meterless/deep` → Nemotron 3 Super) | Nightshift on Windows | Two (already set up). **Running more coding agents needs no more Nightshift lanes.** |
| **Build lane** | A parallel work stream for *building* Arbiter: one Cursor agent, one git worktree, one branch, one pass section | Cursor + git | At most 3 at once |

Cursor's coding agents use Cursor's own models (Composer, Grok, Claude). They never go through Nightshift. Nightshift is only used when Arbiter's code runs: P2-B's live tests, P3's live run, the demo and the eval.

## 1. Wednesday, before 01:00 (setup only; nothing is committed)

### 1.1 Move the Zetaris starter kit *out* of the Arbiter repo

Your `~/arbiter` folder is currently a clone of `zetaris/getting-started` with its remote changed. Do not push it:

- It carries Zetaris's own commit history, dated **before** the build window. Pushing it puts pre-window commits by other people into your repo, which is the exact thing the rules make you declare.
- Its `AGENTS.md` is a Zetaris data-engineer guide. It would replace Arbiter's binding `AGENTS.md`, which defines the invariants, lanes and workflow.
- It mandates `.env.local`, while Arbiter (and the judges' `docker run --env-file .env`) uses `.env`.

Keep it as a **sibling reference folder**. The P1-B agent reads its guides from there.

```bash
# Close any Cursor window that has ~/arbiter open first.
git -C ~/arbiter log --oneline | head -3      # Zetaris commits = proof it must not be pushed
mv ~/arbiter ~/zetaris-getting-started
git -C ~/zetaris-getting-started remote set-url origin https://github.com/zetaris/getting-started.git
git -C ~/zetaris-getting-started remote -v    # must NOT mention awkwardapples/Arbiter
git clone https://github.com/Meterless/Meterless.git ~/meterless   # P2-A and P2-D read the engine specs here
```

Its `.env.local` (Zetaris key, username, password) stays in `~/zetaris-getting-started`, where its scripts expect it.

### 1.2 Create the real Arbiter folder (no commit yet)

```bash
mkdir ~/arbiter && cd ~/arbiter
git init -b main
git remote add origin https://github.com/awkwardapples/Arbiter.git
git ls-remote origin                          # must print nothing (remote is empty)
unzip /mnt/c/Users/<you>/Downloads/arbiter-spec-pack.zip -d ~/arbiter
ls -a                                         # .cursor  .gitignore  AGENTS.md  docs
```

### 1.3 Python 3.12 virtual environment in WSL

Don't use `--break-system-packages` globals or the Windows Python 3.14 beta. CI and Docker use 3.12, and beta wheels are unreliable.

```bash
python3 --version                              # Ubuntu 24.04 ships 3.12.x
sudo apt install -y python3.12-venv            # only if the next line complains
python3 -m venv .venv && source .venv/bin/activate && python -m pip install -U pip
```

If `python3` is older than 3.12:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && uv python install 3.12 && uv venv --python 3.12 .venv
```

P0 installs the pinned dependencies into this venv.

### 1.4 Prove connectivity *from inside WSL*

Your Day-0 checks passed, but "Reverted to Standard Virtual Network Layer" means WSL is in NAT mode. In NAT mode WSL often **cannot** reach Nightshift, which binds to the Windows host's 127.0.0.1. Test from the WSL shell itself:

```bash
cd ~/zetaris-getting-started && python3 scripts/preflight.py && cd ~/arbiter      # Zetaris REST from WSL

read -s MT     # paste the Nightshift token here; it is never shown and never typed into Cursor
curl -s -o /dev/null -w "models: %{http_code}\n" -H "Authorization: Bearer $MT" -H "meterless-app: arbiter" http://localhost:8088/v1/models
for m in meterless/fast meterless/deep; do
  curl -s --max-time 180 http://localhost:8088/v1/chat/completions \
    -H "Authorization: Bearer $MT" -H "meterless-app: arbiter" -H "meterless-scope: user" -H "Content-Type: application/json" \
    -d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with one word: ready\"}]}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('$m ->', d.get('model'))"
done
unset MT
```

**Pass:** `models: 200`, `meterless/fast -> nvidia/nemotron-3.5-lightning…` and `meterless/deep -> nvidia/nemotron-3-super…`. Send me those two lines.

**`models: 000` or connection refused** means WSL can't see the host's loopback. Fix it once:

```powershell
# PowerShell
notepad $env:USERPROFILE\.wslconfig        # add the two lines below, save
#   [wsl2]
#   networkingMode=mirrored
wsl --shutdown                              # then reopen Ubuntu and repeat the test
```

### 1.5 Write `~/arbiter/.env` yourself, in the editor

Never ask an agent to create, read or check it.

Copy the variable list from `docs/spec/00_MASTER_SPEC.md` §10, then fill in:

| Variable | Value |
|---|---|
| `SAMPLE_MODE` | `false` |
| `ZETARIS_REST_URL`, `ZETARIS_ORG_ID`, `ZETARIS_API_KEY` | Copy from `~/zetaris-getting-started/.env.local`. **Leave out `ZETARIS_USERNAME` and `ZETARIS_PASSWORD`**: Arbiter only needs the REST key, and fewer secrets means less to leak |
| `METERLESS_BASE_URL` | `http://localhost:8088/v1` |
| `METERLESS_RUNTIME_TOKEN` | Your Nightshift token |
| `METERLESS_MODEL_FAST` | `meterless/fast` (replaces your single `METERLESS_MODEL=meterless/auto`; Arbiter routes per agent) |
| `METERLESS_MODEL_DEEP` | `meterless/deep` |
| `ARBITER_SIGNING_KEY` | Output of `python3 -c "import secrets; print(secrets.token_hex(32))"` |

Then confirm git will ignore it:

```bash
git check-ignore -v .env .venv      # both must be listed (from .gitignore)
```

### 1.6 Open the folder in Cursor and test the guard-rails

1. From the WSL terminal, run `cd ~/arbiter && cursor .` (this opens a Cursor window connected to WSL).
2. Check that **Settings → Rules** lists 5 project rules, typing `/` in the agent box shows `start-pass`, `verify-pass`, `review-pass` and `explain-pass`, and **Settings → Hooks** shows 2 hooks.
3. **Shell-guard test** (uses a decoy file, never the real `.env`):
   - Create a decoy: `echo "nothing secret" > .env.hooktest`.
   - In an agent chat, ask: *"Run `cat .env.hooktest` in the terminal."* **Pass:** Cursor shows it was blocked by shell_guard.
   - Delete the decoy: `rm .env.hooktest`.
4. **Stop-hook test:**
   - Run `echo "0 build" > .cursor/ACTIVE_PASS`, ask the agent *"Reply with OK only"*, and let it finish.
   - **Pass:** within a few seconds the agent receives an automatic follow-up saying `verify-pass` failed (P0 hasn't created `scripts/tasks.py` yet), and `logs/cursor-hook.jsonl` has a new line. Stop the agent before it tries to "fix" anything.
   - Run `rm .cursor/ACTIVE_PASS`.
5. If a hook doesn't fire, that's fine: the workflow falls back to typing `/verify-pass`. Tell me which one failed.

### 1.7 At onboarding (13:00–14:30 BST)

Capture:

- the Track 3 challenge statement;
- how Cursor and NVIDIA credits are issued;
- anything said about `metadata.json`, live judging or finalist demos.

Send me the statement before Thursday morning. If it changes scope I'll patch the spec before you commit it.

## 2. Thursday 01:00 BST: the first commit (5 minutes)

```bash
cd ~/arbiter
git status --short --ignored        # .env and .venv appear ONLY with "!!" (ignored)
git add .gitignore AGENTS.md .cursor docs
git status --short                  # only spec-pack files are staged
git commit -m "docs: import pre-existing design specification (declared)"
git push -u origin main
```

Check on GitHub that the commit is there and **no `.env`** is visible. Then go to sleep: P0 needs you awake to approve its plan.

## 3. Thursday 08:00: P0, one agent in the main checkout

```bash
cd ~/arbiter && source .venv/bin/activate && git switch -c p0-bootstrap
```

1. In Cursor, open a new Agent chat and pick **Composer** (mechanical pass; it also counts toward the "with Space XAI" story).
2. Type `/start-pass 0`. The agent writes `.cursor/plans/P0.md` and stops.
3. Check the plan lists every file in P0 §5 and tests P0-T1…P0-T13. Reply **"Approved"**. The agent switches `ACTIVE_PASS` to build, writes failing tests, commits them, implements, and loops until `verify-pass --pass 0` is green.
4. Your job while it works: approve terminal commands it proposes (pip installs, pytest, git), and refuse anything touching `.env`.
5. When it says done:

   ```bash
   gh pr create --base main --head p0-bootstrap --title "P0: bootstrap" --body-file docs/passes/P0_REPORT.md
   ```

   Wait for the CI check on the PR to go green. Send me **`Review P0 <PR url>`**. I clone the public repo, run the checks and reply PASS / PASS WITH FIXES / BLOCK, with a fix prompt if needed.
6. After PASS:

   ```bash
   gh pr merge --merge --delete-branch && git switch main && git pull
   ```

   Use `--merge`, not squash, so the tests-first commits stay visible as Cursor evidence.
7. **Protect `main`** (GitHub → Settings → Rules → Rulesets → New branch ruleset → target `main`):
   - Require a pull request before merging (0 approvals; you are solo).
   - Require status checks to pass, and select the CI job P0 created.
   - Block force pushes.
   - Leave "require branches to be up to date" **off**, so parallel lanes don't force constant re-merges.

From now on nothing reaches `main` without green CI, and every PR gets my review before you merge it.

## 4. Thursday ~10:30: three agents in parallel

One worktree per lane. Each is a full checkout on its own branch in its own folder, all sharing one git repository. Each gets its own Cursor window and agent.

```bash
cd ~/arbiter && git switch main && git pull
for b in p1a-data p2c-policy p2a-hmem; do
  git worktree add ../arbiter-$b -b $b origin/main
  ln -s ~/arbiter/.env  ../arbiter-$b/.env       # one .env, never copied into git (.gitignore covers it)
  ln -s ~/arbiter/.venv ../arbiter-$b/.venv      # one venv; the stop hook finds it automatically
done
git worktree list
cursor ../arbiter-p1a-data; cursor ../arbiter-p2c-policy; cursor ../arbiter-p2a-hmem
```

| Window | Model | First message |
|---|---|---|
| `arbiter-p1a-data` | Composer or Grok | `/start-pass 1a` |
| `arbiter-p2c-policy` | Claude (or Grok) | `/start-pass 2c` |
| `arbiter-p2a-hmem` | Claude | `/start-pass 2a` |

**How you run three at once:**

1. Approve the three plans one after another (about 10 minutes each).
2. Then rotate windows every 10–15 minutes. You approve terminal commands, answer any agent that set itself to `blocked`, and glance at its commits.
3. Each lane touches only files it owns (`docs/spec/passes/README.md` §3), so the branches don't collide.

**When a lane finishes** (example for P1-A):

```bash
cd ~/arbiter-p1a-data
gh pr create --base main --head p1a-data --title "P1-A: data world, simulator, registry, DuckDB" --body-file docs/passes/P1-A_REPORT.md
# CI green → send me "Review P1-A <PR url>" → after PASS:
gh pr merge --merge --delete-branch
cd ~/arbiter && git pull && git worktree remove ../arbiter-p1a-data
```

Start the next lane in the freed slot by repeating the `git worktree add` block for its branch. If a running lane later needs code that just merged, tell its agent: *"Run `git fetch origin && git merge origin/main`, then continue."* Never rebase: that needs a force-push, which the shell guard blocks on purpose.

**Alternative: Cursor-managed worktrees.** In a chat, type `/worktree` followed by your task. The pack ships `.cursor/worktrees.json`, which links `.env` and `.venv` into each new worktree. You then commit, push and open the PR from that worktree as above. I recommend the manual `git worktree add` route above, because the branch names, folders and PR gate stay explicit. Keep fewer than 25 worktrees: newer Cursor versions clean up the oldest ones above that cap, including manually created ones. Push after every green milestone.

## 5. Which lanes run when

| When | Slot 1 | Slot 2 | Slot 3 |
|---|---|---|---|
| Thu 08:00 | P0 | – | – |
| Thu ~10:30 | P1-A | P2-C | P2-A |
| Thu ~15:00 (after P1-A merges) | **P1-B** (attended: Zetaris + Docker) | P2-C/P2-A finishing | – |
| Fri 08:00 | P1-B (if not done) | P2-B (Nightshift live tests) | P2-D |
| Fri ~13:00 (after P2-B, P2-C, P2-D merge) | **P3** (single core lane) | – | – |
| Sat ~12:00 (after P3 merges) | P4-A | P4-B | – |
| Sun 08:00 | P5-A | P5-B | – |
| Sun evening | `clean_clone_check.py` + live eval | | |
| Mon 08:00 | P6 | | |
| Mon PM–Tue | P7: video, deck, submit | | |

P1-B merges whenever it is green; P3 starts on DuckDB without it. The checkpoints in `05_RUNBOOK.md` §5 tell you what to cut if a day slips.

## 6. Don't freestyle the prompts

Your two draft prompts would hurt more than help:

- **"Read AGENTS.md … acknowledge … the active `.env.local` configuration"**
  - Cursor already injects `AGENTS.md` and the always-on rules into every agent, so an "acknowledge" turn adds nothing.
  - The acknowledgement doesn't carry over to the other agents anyway.
  - It invites the agent to open the env file, which sends your keys to a model provider.
  - Instead, the plan each `/start-pass` produces *is* the acknowledgement, and you can check it.
- **"Implement pass-file-01 … connect it to Zetaris and verify against Nightshift"**
  - Most passes must **not** touch either service. P0 is skeleton only, P2-C is pure policy logic, and P2-A is a conformance port.
  - Telling every pass to connect breaks scope and wastes credits.
  - The live work is already placed exactly where it belongs: P1-B (Zetaris), P2-B (Nightshift) and P3-T15 (both, end to end).

Type only `/start-pass <ID>`, then answer the agent's questions. If an agent drifts, say: *"Stop. Re-read your lane section and AGENTS.md §6. Do only what the pass file says."*

## 7. If something goes wrong

| Symptom | Do this |
|---|---|
| Agent wants to edit a file its lane doesn't own | Answer "No; set ACTIVE_PASS to blocked and explain why you need it", then send me the reason |
| Stop hook never fires | Type `/verify-pass` yourself after each agent stop |
| Agent loops 5 times and stops "blocked" | Send me the summary it wrote; I'll diagnose from the branch |
| CI red on a PR but green locally | Usually an unpinned dependency or a missing file in git. Paste the CI log to the agent |
| Merge conflict | Shouldn't happen between lanes. If it does, `git merge origin/main` in the lane and let the agent resolve **only** its own files |
| Nightshift unreachable from WSL mid-build | Re-run the §1.4 test. Arbiter falls back to the offline path, but P2-B, P3-T15 and the demo need it live |
| Zetaris unhealthy | `verify.sh` in the Zetaris install folder. P1-A, P2 and P3 keep working on DuckDB |
| Cursor credits running low | Switch mechanical lanes to Composer/Grok; keep Claude for P3 |
