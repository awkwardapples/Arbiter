import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { api } from "../../api/client";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { Field, FieldGroup } from "../../ui/Field";
import { Input } from "../../ui/input";
import { NativeSelect } from "../../ui/NativeSelect";
import { outcomeWord } from "../../ui/outcome";
import { Textarea } from "../../ui/textarea";
import { toast } from "../../ui/toast";
import { CONDITIONS, type Eligibility, MIN_RATIONALE, MITIGATIONS, OUTCOMES, ROLES, type ReviewBody, reasonWords, reviewProblems } from "./review";

interface ReviewResult {
  review_id: string;
  precedent?: { precedent_id: string } | null;
}

/** The review form: decision, rationale, and an optional precedent, checked before it is recorded. */
export function ReviewForm({ caseId, machineOutcome }: { caseId: string; machineOutcome?: string | null }) {
  const [reviewer, setReviewer] = useState("");
  const [role, setRole] = useState<string>("tprm_lead");
  const [decision, setDecision] = useState<string>(machineOutcome ?? "APPROVE");
  const [rationale, setRationale] = useState("");
  const [mitigations, setMitigations] = useState<string[]>(MITIGATIONS.map((m) => m.value));
  const [conditions, setConditions] = useState<string[]>([]);
  const [otherCondition, setOtherCondition] = useState("");
  const [createPrecedent, setCreatePrecedent] = useState(false);
  const [touched, setTouched] = useState(false);

  const eligibility = useMutation({
    mutationFn: (body: ReviewBody) => api.post<Eligibility>(`/cases/${encodeURIComponent(caseId)}/review?dry_run=true`, body),
  });
  const submit = useMutation({
    mutationFn: (body: ReviewBody) => api.post<ReviewResult>(`/cases/${encodeURIComponent(caseId)}/review`, body),
    onSuccess: (result) =>
      toast.success(result.precedent ? `Review recorded. Precedent ${result.precedent.precedent_id} saved to memory.` : "Review recorded"),
  });

  // A check answers for the decision and role it was asked about; change either and it no longer applies.
  const checkedFor = eligibility.variables;
  const stale = !checkedFor || checkedFor.decision !== decision || checkedFor.role !== role;
  const eligible = !stale && eligibility.data?.eligible === true;
  const allConditions = [...conditions, ...(otherCondition.trim() ? [otherCondition.trim()] : [])];
  const body = (forSubmit: boolean): ReviewBody => ({
    reviewer: reviewer.trim(),
    role,
    decision,
    rationale: rationale.trim(),
    // As in Streamlit: precedent details only travel when the case is eligible.
    mitigations: eligible || !forSubmit ? mitigations : [],
    conditions: eligible || !forSubmit ? allConditions : [],
    create_precedent: forSubmit ? eligible && createPrecedent : true,
  });
  const problems = reviewProblems(body(true));
  const blocked = Object.keys(problems).length > 0;
  const length = rationale.trim().length;

  const toggle = (list: string[], value: string) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  if (submit.isSuccess) {
    return (
      <div className="flex flex-col gap-3" data-testid="review-done">
        <Callout title="Review recorded.">
          {submit.data.precedent ? `Precedent ${submit.data.precedent.precedent_id} is now in memory. ` : ""}
          The decision, the signed contract and the audit entry are on the case.
        </Callout>
        <div>
          <Button asChild>
            <Link to={`/cases/${encodeURIComponent(caseId)}`}>Open the case</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form
      noValidate
      className="flex max-w-3xl flex-col gap-5"
      data-testid="review-form"
      onSubmit={(e) => {
        e.preventDefault();
        setTouched(true);
        if (!blocked) submit.mutate(body(true));
      }}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Reviewer" hint="Your name or email, as it will appear in the audit log." error={touched ? problems.reviewer : undefined} name="reviewer">
          <Input value={reviewer} onChange={(e) => setReviewer(e.target.value)} autoComplete="email" />
        </Field>
        <Field label="Role" hint="Only a TPRM lead can approve an exception or create a precedent." name="role">
          <NativeSelect value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label="Decision" name="decision">
          <NativeSelect value={decision} onChange={(e) => setDecision(e.target.value)}>
            {OUTCOMES.map((o) => (
              <option key={o} value={o}>
                {outcomeWord(o)}
              </option>
            ))}
          </NativeSelect>
        </Field>
      </div>
      <Field
        label="Rationale"
        hint={`${length} of at least ${MIN_RATIONALE} characters. Say why, so a later reviewer can rely on it.`}
        error={touched || length > 0 ? problems.rationale : undefined}
        name="rationale"
      >
        <Textarea value={rationale} onChange={(e) => setRationale(e.target.value)} />
      </Field>

      <section className="flex flex-col gap-3 rounded-panel border border-hairline bg-sheet px-4 py-3" data-testid="review-precedent">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-md font-semibold text-ink">Precedent</h2>
          <Button type="button" variant="secondary" disabled={blocked || eligibility.isPending} onClick={() => eligibility.mutate(body(false))}>
            {eligibility.isPending ? "Checking…" : "Check eligibility"}
          </Button>
        </div>
        <p className="text-sm text-graphite">
          A precedent changes a later decision only where the policy allows an exception. Checking records nothing.
        </p>
        {eligibility.data && !stale ? (
          <div role="status" data-testid="review-eligibility" className="flex flex-col gap-1">
            <p className={`flex items-center gap-2 text-sm font-semibold ${eligibility.data.eligible ? "text-record" : "text-clash"}`}>
              {eligibility.data.eligible ? <CheckCircle2 className="size-4" aria-hidden /> : <XCircle className="size-4" aria-hidden />}
              {eligibility.data.eligible ? "This review can become a precedent." : "This review cannot become a precedent."}
            </p>
            {eligibility.data.eligible ? (
              <p className="text-sm text-graphite">The only failing control allows an exception, the mitigation holds, and the role has the authority.</p>
            ) : (
              <ul className="list-disc pl-5 text-sm text-ink">
                {eligibility.data.reasons.map((code) => (
                  <li key={code}>
                    {reasonWords(code)} <span className="font-mono text-xs text-graphite">{code}</span>
                  </li>
                ))}
              </ul>
            )}
            {!eligibility.data.eligible ? <p className="text-xs text-graphite">You can still record the review. No precedent will be created.</p> : null}
          </div>
        ) : null}
        {eligibility.isError ? (
          <Callout tone="error" title="Eligibility could not be checked.">
            {eligibility.error.message}
          </Callout>
        ) : null}
        <FieldGroup legend="Mitigation the policy will check" name="mitigations">
          {MITIGATIONS.map((m) => (
            <label key={m.value} className={`flex items-center gap-2 text-sm ${eligible ? "text-ink" : "text-graphite"}`}>
              <input type="checkbox" disabled={!eligible} checked={mitigations.includes(m.value)} onChange={() => setMitigations((l) => toggle(l, m.value))} />
              {m.label} <span className="font-mono text-xs text-graphite">{m.value}</span>
            </label>
          ))}
        </FieldGroup>
        <FieldGroup legend="Conditions" name="conditions">
          {CONDITIONS.map((c) => (
            <label key={c} className={`flex items-center gap-2 text-sm ${eligible ? "text-ink" : "text-graphite"}`}>
              <input type="checkbox" disabled={!eligible} checked={conditions.includes(c)} onChange={() => setConditions((l) => toggle(l, c))} />
              {c}
            </label>
          ))}
          <Input
            aria-label="Other condition"
            placeholder="Other condition"
            disabled={!eligible}
            value={otherCondition}
            onChange={(e) => setOtherCondition(e.target.value)}
            className="mt-1 max-w-md"
          />
        </FieldGroup>
        <label className={`flex items-center gap-2 text-sm ${eligible ? "text-ink" : "text-graphite"}`}>
          <input type="checkbox" disabled={!eligible} checked={eligible && createPrecedent} onChange={(e) => setCreatePrecedent(e.target.checked)} />
          Save this exception to memory as a precedent
        </label>
        {!eligible ? <p className="text-xs text-graphite">Available once the check says the review can become a precedent.</p> : null}
      </section>

      {submit.isError ? (
        <Callout tone="error" title="The review was not recorded.">
          {submit.error.message}
        </Callout>
      ) : null}
      <div>
        <Button type="submit" size="lg" disabled={blocked || submit.isPending}>
          {submit.isPending ? "Recording…" : "Submit review"}
        </Button>
      </div>
    </form>
  );
}
