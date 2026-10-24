# Evaluation

Synthetic data. Small n. Intervals are Wilson 95% where a rate has a denominator.
Only the tier gates are calibrated. Weights stay at their a-priori values.

- mode: live (zetaris / meterless)
- provider: meterless
- model ids (from traces): nvidia/nemotron-3.5-super-vl-120b-a12b, nvidia/nemotron-3.5-lightning-30b-a3b
- splits: test
- n: 20
- git sha: 4b4680b0586ae50003f87bab2337931aa6f6c37b
- generated: 2026-10-24T05:35:05Z

| System | Accuracy | Unsafe approvals | Invalid | Abstention |
|---|---:|---:|---:|---:|
| arbiter | 1.000 (5/5) | 0/5 | — | 0.200 (1/5) |
| arbiter_offline | 1.000 (16/16) | 0/16 | — | 0.375 (6/16) |
| baseline | 0.000 (0/5) | 0/5 | 1.000 (5/5) | 0.000 (0/5) |

Reduced n: n=5 for the live systems, n=16 for the offline system; the live subset is the first 5 test cases by case_id.

| System | Mode | n | Contradiction recall | Failing-control recall | p50 ms | p95 ms | Model calls/case | Model-call fallback |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| arbiter | zetaris / meterless | 5 | 1.000 (1/1) | 1.000 (2/2) | 141817 | 233333 | 5.0 | 0.200 (5/25) |
| arbiter_offline | duckdb / offline | 16 | 1.000 (2/2) | 1.000 (6/6) | 436 | 611 | 0.0 | — |
| baseline | zetaris / meterless | 5 | 0.000 (0/1) | 0.000 (0/2) | 58800 | 80770 | 1.0 | 1.000 (5/5) |

- deep lane routed to: nvidia/nemotron-3.5-super-vl-120b-a12b, nvidia/nemotron-3.5-lightning-30b-a3b (from trace receipts)
- fast lane routed to: nvidia/nemotron-3.5-super-vl-120b-a12b (from trace receipts)
