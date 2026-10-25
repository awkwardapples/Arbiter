# Pre-existing components (declaration)

Open Agent Hackathon 2026 rules: "Work committed before the build window opens (22 October, 00:00 UTC) is not eligible, except for clearly declared pre-existing components." This file is the declaration referenced by the submission form and the README.

## 1. Design documentation (no code)

- **What:**
  - `AGENTS.md`;
  - `docs/spec/**` (master spec, data and Zetaris design, policy design, evaluation design, submission playbook, runbook, pass specifications);
  - `.cursor/rules/*.mdc`, `.cursor/commands/*.md`, `.cursor/hooks.json`;
  - two small development-tooling hook scripts (`.cursor/hooks/verify_loop.py`, `.cursor/hooks/shell_guard.py`), which are editor automation and not part of the application;
  - `docs/DAY0_CHECKS.md` (template).
- **When:** written 20–21 October 2026, before the build window; committed unchanged in the first commit after the window opened.
  - Import commit sha: `b3c720deca0140efe6ef53fd88e9f18474ca707c`
- **How:** by me with an AI assistant (Claude, Anthropic) acting as architect. All application code for passes P0–P14-A was written in Cursor. From P14-B onwards it was written in Claude Code in VS Code, after the organisers confirmed that any IDE may be used. `docs/CURSOR_USAGE.md` records the tool and model used for each pass. The Release 3 specifications and reviews were drafted by Claude (Anthropic) outside the repository, as for Releases 1 and 2.

## 2. Concept, research and narrative from an earlier prototype

- **What:** the problem framing (third-party vendor onboarding risk), user research and pitch narrative from my earlier prototype "Vendor-Risk-Assessment-Agent" (React/Node; `github.com/awkwardapples/Vendor-Risk-Assessment-Agent`).
- **Code reused:** none. Arbiter is a completely new Python codebase with a different architecture; it reuses only the rough idea.

## 3. Market-research slide content

- **What:** problem, users and competitor research slides from my earlier market-research deck. They are refreshed (DBIR 2026 statistics) and reused in deck slides 4 and 6.

## 4. Third-party open material (used under licence; attributed in README)

- Meterless H-MEM conformance vectors and Scout Intent evaluation cases and thresholds: Apache-2.0, `github.com/Meterless/Meterless`. Copied byte-identical into `vendor/meterless/` with notices. The H-MEM engine was *ported* to Python during the window.
- CISA Known Exploited Vulnerabilities catalogue: CC0 1.0, via `github.com/cisagov/kev-data`. The snapshot was retrieved during the window by `data/kev/fetch_kev.py`.

## 5. Data

None prepared before the window. All synthetic enterprise data is produced during the window by the seeded generator (`python run.py generate-data --seed 2026 --as-of 2026-10-26`).
