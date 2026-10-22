# Meterless Scout Intent eval assets: third-party notice

Arbiter implements a **Scout Intent guard subset** in `app/guard/`; the regression injection set and thresholds are copied unchanged for evaluation.

- Source repository: https://github.com/Meterless/Meterless (`engines/scout-intent/`)
- Licence: Apache License 2.0 (see [`LICENSE`](LICENSE) from the Meterless repo).
- Copyright: the Meterless authors. Domain eval set `data/evals/injection_domain.jsonl` is **synthetic** and labelled by Arbiter.

## Files copied verbatim

| File here | Upstream path | sha256 |
|---|---|---|
| `scout_adversarial.jsonl` | `evals/regression-set/v1/injection/adversarial.jsonl` | `141f1db3a42ac3e42c78edd014863d5561cb0931e792954c16fb3a545eeb663e` |
| `scout_thresholds.yaml` | `evals/config/thresholds.yaml` | `f49b4db850298c9a2fa7fc258af7d968fb6ecdda97e6d12d7fb32c5c61ede02d` |
