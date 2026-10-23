# P8 report — reviewer console polish

## Built

Display-only changes in `ui/screens.py` and `ui/components.py`. The API payloads are unchanged.

- Queue rows show `case_id` on the header line. **Open case** sets `last_case_id` and `nav_case_id`, then `st.switch_page("pages/case.py")`.
- Case header renders `outcome_reasons` as bullets. Each bullet has a human sentence and a caption with the raw code.
- The controls table columns are Control id, Name, Status, Fact ids.
- Evidence expanders show `` `{key}` = `{value}` → `{state}` `` and `From: …`. The `{key, value, state}` object is inside a collapsed **See raw** `st.code` block.
- The new-assessment spinner text is the approved sentence. It does not cycle stages.
- Review eligibility is a bullet list (or “Eligible to create a precedent” when the dry-run returns no reasons).
- Audit replay uses success or error, then one line per `checks` key (`✓ policy hash matches` / `✗ record hash mismatch`).
- Audit verify uses `Chain intact — {n} entries across all cases`, or `Chain intact` when the count cannot be read, or `Chain broken at sequence {seq}`.

## Eligibility reason codes

`POST /cases/{id}/review?dry_run=true` returns `{eligible, reasons}` from `check_eligibility` in `app/memory/precedents.py`. That function is the whole list. It returns `sorted(set(reasons))`. Nothing else appends a code on the dry-run path.

| Code | Emitted by dry-run | In the approved map | Sentence on the Review page |
|---|---|---|---|
| `decision_not_approving` | yes | no (alias added) | The review decision is not an approval |
| `mitigation_not_true` | yes | yes | The mitigation fact is not TRUE — this precedent can't apply |
| `no_exception_control_failing` | yes | yes | No exception-eligible control is failing |
| `no_failing_controls` | yes | no (alias added) | No required control is failing |
| `non_exception_control_failing` | yes | yes | A control that can't be excepted is failing |
| `reviewer_role_insufficient` | yes | no (alias added) | The reviewer's role is below the required authority |
| `reviewer_authority` | no | yes | The reviewer's role is below the required authority |
| `precedent_age` | no | yes | The precedent is older than the 365-day window |
| `retrieval_quality` | no | yes | H-MEM confidence or relevance is below the threshold |
| `tier_risk` | no | yes | This case's risk tier is higher than the precedent's |

`precedent_age`, `retrieval_quality`, and `tier_risk` are policy-engine `failed_criteria` on a precedent, not dry-run eligibility codes. `reviewer_authority` is the approved name; the endpoint emits `reviewer_role_insufficient`. Unknown codes still render as the raw code, with that code in the caption.

## `rule_id`

`rule_id` is still on each control in the case payload. The table does not render it. On current data it repeats `control_id` (`C01` and `C01`), so the column was noise. The case page **Raw JSON** expander still includes it.

## Deviations

- There is no `evidence_text` field on `Fact` or `Provenance`. **From:** uses `fact["evidence_text"]` when a payload has it, then `provenance["quote"]`, then “No narrative is stored for this fact.”
- `GET /audit/verify` is `{ok, first_bad_seq}` only. The count is `result["entries"]` when that is an int, otherwise `GET /health` `audit_chain_length`. That number is the whole audit log, so the success line says “across all cases”. If the health call fails, or the count is missing, the line is `Chain intact` with no number.
- **Open case** sets `nav_case_id` as well as `last_case_id`, because the case page already reads `nav_case_id`.

## Known gaps

- Review **Submit review** still shows `json.dumps` of the result.
- Memory still shows `st.json` for precedents considered.
- Case **Actions** still shows each contract with `st.json`. The bottom **Raw JSON** expander is unchanged and collapsed.
- The report summary paragraph can still contain raw reason codes inside the reporter’s sentence. The header bullets are separate.
- This session did not click through a live `python run.py ui`. Pages were rendered with Streamlit `AppTest` and `FakeArbiterClient`.

## Commands

```
python scripts/tasks.py lint
python -m pytest tests/unit/ui -q
DOCKER=0 python scripts/tasks.py verify-pass --pass 5a
```

Lint passed. `tests/unit/ui` passed (the polish file is 17 tests). `verify-pass --pass 5a` with `DOCKER=0` passed: 632 passed, 6 skipped, 8 deselected. A sandboxed run without `DOCKER=0` failed only `test_p4_t18_clean_clone_local`, because that process could not see the Docker socket. That test is unchanged by this pass.
