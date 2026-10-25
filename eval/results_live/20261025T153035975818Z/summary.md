### Evaluation results

Synthetic data. Small n. Intervals are Wilson 95% where a rate has a denominator.
Only the tier gates are calibrated. Weights stay at their a-priori values.

- mode: live (zetaris / meterless)
- provider: meterless
- model ids (from traces): nvidia/nemotron-3.5-super-vl-120b-a12b, nvidia/nemotron-3.5-lightning-30b-a3b
- splits: test
- n: 20
- git sha: cabd79e95998ea41855deb2d9f7bcd14976c2bc1
- generated: 2026-10-25T16:09:09Z

| System | Accuracy | Unsafe approvals | Invalid | Abstention |
|---|---:|---:|---:|---:|
| arbiter | 1.000 (10/10) | 0/10 | — | 0.200 (2/10) |
| arbiter_offline | 1.000 (16/16) | 0/16 | — | 0.375 (6/16) |
| baseline | 0.000 (0/10) | 0/10 | 1.000 (10/10) | 0.000 (0/10) |

Reduced n: n=10 for the live systems, n=16 for the offline system; the live subset is the first 10 test cases by case_id.

| System | Mode | n | Contradiction recall | Failing-control recall | p50 ms | p95 ms | Model calls/case | Model-call fallback |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| arbiter | zetaris / meterless | 10 | 1.000 (1/1) | 1.000 (3/3) | 76302 | 271577 | 2.1 | 0.476 (10/21) |
| arbiter_offline | duckdb / offline | 16 | 1.000 (2/2) | 1.000 (6/6) | 417 | 571 | 0.0 | — |
| baseline | zetaris / meterless | 10 | 0.000 (0/1) | 0.000 (0/3) | 62659 | 125023 | 1.0 | 1.000 (10/10) |

- deep lane routed to: nvidia/nemotron-3.5-lightning-30b-a3b, nvidia/nemotron-3.5-super-vl-120b-a12b (from trace receipts)
- fast lane routed to: nvidia/nemotron-3.5-super-vl-120b-a12b (from trace receipts)
