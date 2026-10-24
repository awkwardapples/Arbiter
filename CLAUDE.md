# CLAUDE.md

@AGENTS.md

## Working in Claude Code (Release 3 onwards)

`AGENTS.md` above is binding. It was written for Cursor; this section maps its workflow onto Claude Code. P0–P14-A were built in Cursor; P14-B onwards are built in Claude Code (`docs/CURSOR_USAGE.md` records the tool per pass).

### Lanes

- Start every lane with `/start-pass <ID>`. Release 3 ids: `18a 18b 18c 18d 19 20`. Pass files and file ownership: `docs/spec/release3/README.md`.
- `.cursor/ACTIVE_PASS` holds `<ID> plan|build|blocked`. Claude Code's Stop hook (`.claude/hooks/verify_stop.py`) reads it:
  - `plan` and `blocked`: the hook does nothing;
  - `build`: when you try to stop, it runs `python scripts/tasks.py verify-pass --pass <ID>` and, if that fails, hands you the failures (up to 6 times).
- If the hook does not run on this machine, use `/verify-pass` yourself before stopping.
- **Plan first.** Write `.cursor/plans/<LABEL>.md` and stop until the human approves. Do not edit code in the `plan` phase.
- One lane per git worktree and branch (`docs/spec/release3/README.md` §5). Never commit to `main` directly. PRs merge; never rebase.
- Before asking the human anything mid-lane, set the phase to `blocked`. Set it back to `build` when you resume.

### Commands

| Task | Command |
|---|---|
| Python venv | `.venv/bin/python` (macOS, Linux) or `.venv\Scripts\python.exe` (Windows). `scripts/tasks.py` is the source of truth for commands |
| Lane gate | `python scripts/tasks.py verify-pass --pass <ID>` |
| Full gate | `python scripts/tasks.py verify` |
| Web console (from P18-B) | `cd web && npm ci && npm run dev`, with `python run.py serve` in another terminal. `npm run check` before every commit. Commit `web/dist/` after `npm run build` |
| Sample mode | `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve` (PowerShell: `$env:SAMPLE_MODE="true"; $env:LLM_PROVIDER="offline"; python run.py serve`) |

### Secrets (non-negotiable)

- Never open, read, print or quote `.env`, `.env.local` or any environment variable holding a key. The Bash guard and the deny rules in `.claude/settings.json` block the obvious ways; do not look for others.
- The Nightshift Runtime URL may appear on screen and in docs. The Runtime token never does.
- The Zetaris API key is created by the human in the Zetaris GUI. Never create, request or log it. Never call port 8889.
- 21st.dev, Aceternity and other plugin keys live in the human's Claude Code configuration, never in this repo.

### Design work (P18)

`docs/spec/release3/P18_00_DESIGN.md` is binding: tokens, type, copy rules, honesty labels, the fixed bench layout and the short component list. Do not add components, effects, colours or fonts beyond it without asking.
