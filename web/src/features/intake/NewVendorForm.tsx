import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../../api/client";
import type { RunStarted } from "../../api/types";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { Field, FieldGroup } from "../../ui/Field";
import { Input } from "../../ui/input";
import { NativeSelect } from "../../ui/NativeSelect";
import { Textarea } from "../../ui/textarea";
import { ToggleChips } from "../../ui/ToggleChips";
import {
  type ComponentRow,
  type DocumentRow,
  type FieldErrors,
  type IntakeForm,
  PRESETS,
  type Question,
  applyPreset,
  buildCaseInput,
  emptyComponent,
  emptyDocument,
  emptyForm,
  parsePasted,
} from "./build";
import {
  CATEGORIES,
  COUNTRIES,
  CRITICALITIES,
  CRITICALITY_WORDS,
  DATA_CATEGORIES,
  DATA_CATEGORY_WORDS,
  DOC_TYPES,
} from "./options";
import { useQuestions } from "./api";
import { QuestionField } from "./QuestionField";
import { RowsEditor } from "./RowsEditor";

const DOC_COLUMNS = [
  { key: "doc_type", label: "Type", kind: "select", options: DOC_TYPES },
  { key: "title", label: "Title" },
  { key: "issued_on", label: "Issued on", placeholder: "2026-03-01" },
  { key: "expires_on", label: "Expires on", placeholder: "2027-03-01" },
  { key: "text", label: "Document text", kind: "long", placeholder: "Paste the text of the document" },
] as const;
const COMPONENT_COLUMNS = [
  { key: "vendor", label: "Maker" },
  { key: "product", label: "Product" },
  { key: "version", label: "Version" },
] as const;

/** The New vendor questionnaire (a port of ui/intake.py). Start assessment opens the run view. */
export function NewVendorForm() {
  const questions = useQuestions();
  if (questions.isError) {
    return (
      <Callout tone="error" title="The questionnaire did not load.">
        {questions.error.message} Check that the API is running, then reload the page.
      </Callout>
    );
  }
  if (!questions.data) return <p className="text-sm text-graphite">Loading the questionnaire…</p>;
  return <Questionnaire questions={questions.data} />;
}

function Questionnaire({ questions }: { questions: Question[] }) {
  const navigate = useNavigate();
  const [form, setForm] = useState<IntakeForm>(() => emptyForm(questions));
  const [preset, setPreset] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [pasted, setPasted] = useState("");
  const [pastedErrors, setPastedErrors] = useState<string[]>([]);

  const start = useMutation({
    mutationFn: (body: unknown) => api.post<RunStarted>("/runs", body),
    onSuccess: (run) => navigate(`/runs/${encodeURIComponent(run.run_id)}`),
  });

  const update = <K extends keyof IntakeForm>(key: K, value: IntakeForm[K]) => setForm((f) => ({ ...f, [key]: value }));

  const loadPreset = (name: string) => {
    setPreset(name);
    const found = PRESETS.find((p) => p.name === name);
    if (found) {
      setForm(applyPreset(found, questions));
      setErrors({});
    }
  };

  const submit = () => {
    const result = buildCaseInput(form, questions);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    start.mutate(result.body);
  };

  const submitPasted = () => {
    const result = parsePasted(pasted);
    if (!result.ok) {
      setPastedErrors(result.errors);
      return;
    }
    setPastedErrors([]);
    start.mutate(result.body);
  };

  const problems = Object.keys(errors).length;

  return (
    <form
      className="flex max-w-5xl flex-col gap-8"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      data-testid="new-vendor-form"
    >
      <section className="flex flex-col gap-4">
        <Field label="Load an example vendor" hint="Fills the whole form. Edit anything before you start." name="preset">
          <NativeSelect value={preset} onChange={(e) => loadPreset(e.target.value)}>
            <option value="">Choose an example</option>
            {PRESETS.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </NativeSelect>
        </Field>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-ink">The vendor</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Legal name" error={errors.legal_name} name="legal_name">
            <Input value={form.legal_name} onChange={(e) => update("legal_name", e.target.value)} />
          </Field>
          <Field label="Trading name (optional)" name="trading_name">
            <Input value={form.trading_name} onChange={(e) => update("trading_name", e.target.value)} />
          </Field>
          <Field label="Service requested" error={errors.requested_service} name="requested_service">
            <Input value={form.requested_service} onChange={(e) => update("requested_service", e.target.value)} />
          </Field>
          <Field label="Category" name="category">
            <NativeSelect value={form.category} onChange={(e) => update("category", e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <Field label="Criticality" name="criticality">
            <NativeSelect value={form.criticality} onChange={(e) => update("criticality", e.target.value as IntakeForm["criticality"])}>
              {CRITICALITIES.map((c) => (
                <option key={c} value={c}>
                  {CRITICALITY_WORDS[c]}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <Field label="Annual spend (GBP)" error={errors.annual_spend_gbp} name="annual_spend_gbp">
            <Input inputMode="decimal" value={form.annual_spend_gbp} onChange={(e) => update("annual_spend_gbp", e.target.value)} />
          </Field>
          <FieldGroup legend="Data categories" error={errors.data_categories} name="data_categories">
            <ToggleChips
              label="Data categories"
              options={DATA_CATEGORIES}
              value={form.data_categories}
              words={DATA_CATEGORY_WORDS}
              onChange={(next) => update("data_categories", next)}
            />
          </FieldGroup>
          <FieldGroup legend="Processing countries" error={errors.processing_countries} name="processing_countries">
            <ToggleChips
              label="Processing countries"
              options={COUNTRIES}
              value={form.processing_countries as (typeof COUNTRIES)[number][]}
              onChange={(next) => update("processing_countries", next)}
            />
          </FieldGroup>
          <Field
            label="Critical patch SLA in days"
            hint="0 means the vendor did not state one."
            error={errors.patch_sla_critical_days}
            name="patch_sla_critical_days"
          >
            <Input inputMode="numeric" value={form.patch_sla_critical_days} onChange={(e) => update("patch_sla_critical_days", e.target.value)} />
          </Field>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-ink">Security questionnaire</h2>
        <p className="text-sm text-graphite">
          Leave a question as Not answered if the vendor did not reply. The policy treats it as unverified.
        </p>
        {questions.map((q) => (
          <QuestionField
            key={q.question_id}
            question={q}
            value={form.answers[q.question_id] ?? { choice: "Not answered", how: "" }}
            onChange={(entry) => update("answers", { ...form.answers, [q.question_id]: entry })}
          />
        ))}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-ink">Assurance documents (optional)</h2>
        <RowsEditor<DocumentRow>
          name="documents"
          rows={form.documents}
          columns={[...DOC_COLUMNS]}
          onChange={(rows) => update("documents", rows)}
          makeRow={emptyDocument}
          addLabel="Add a document"
          errors={errors}
          emptyText="No documents. Add a SOC 2 report, an ISO certificate or a bridge letter if the vendor sent one."
        />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-ink">Declared software components (optional)</h2>
        <RowsEditor<ComponentRow>
          name="components"
          rows={form.components}
          columns={[...COMPONENT_COLUMNS]}
          onChange={(rows) => update("components", rows)}
          makeRow={emptyComponent}
          addLabel="Add a component"
          errors={errors}
          emptyText="No components. Evidence checks declared products against the CISA known-exploited catalogue."
        />
      </section>

      <section className="flex flex-col gap-3 border-t border-hairline pt-6">
        {problems > 0 ? (
          <Callout tone="error" title={problems === 1 ? "One field needs attention." : `${problems} fields need attention.`}>
            Each problem is shown next to its field.
          </Callout>
        ) : null}
        {start.isError ? (
          <Callout tone="error" title="The assessment did not start.">
            {start.error instanceof ApiError ? start.error.message : "The API did not accept the request."} Check the form and try again.
          </Callout>
        ) : null}
        <div>
          <Button type="submit" size="lg" disabled={start.isPending}>
            {start.isPending ? "Starting…" : "Start assessment"}
          </Button>
        </div>
      </section>

      <details className="rounded-panel border border-hairline bg-sheet px-4 py-3" data-testid="advanced-json">
        <summary className="cursor-pointer text-sm font-semibold text-ink">Advanced: paste a CaseInput as JSON</summary>
        <div className="mt-3 flex flex-col gap-3">
          <Field label="CaseInput JSON" hint='Either {"vendor_id": "…"} or {"submission": {…}}.' name="pasted">
            <Textarea className="min-h-40 font-mono text-xs" value={pasted} onChange={(e) => setPasted(e.target.value)} />
          </Field>
          {pastedErrors.length > 0 ? (
            <ul role="alert" className="list-disc pl-5 text-xs text-clash">
              {pastedErrors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          ) : null}
          <div>
            <Button type="button" variant="secondary" onClick={submitPasted} disabled={!pasted.trim() || start.isPending}>
              Start assessment from JSON
            </Button>
          </div>
        </div>
      </details>
    </form>
  );
}
