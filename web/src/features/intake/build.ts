// Questionnaire state → CaseInput. A port of build_case_input in ui/intake.py: the same rules, the
// same answer text, the same document and component ids, so both consoles post the same body.
import presetsFile from "./presets.json";
import type { Choice, Criticality, DataCategory } from "./options";
import { type CaseInputBody, caseInputSchema, pastedCaseInputSchema } from "./schema";

export interface Question {
  question_id: string;
  question: string;
  help?: string | null;
  type: "yes_no" | "text" | string;
  options?: string[] | null;
}

export interface AnswerEntry {
  choice: Choice;
  how: string;
}

export interface DocumentRow {
  doc_type: string;
  title: string;
  issued_on: string;
  expires_on: string;
  text: string;
}

export interface ComponentRow {
  vendor: string;
  product: string;
  version: string;
}

export interface IntakeForm {
  legal_name: string;
  trading_name: string;
  requested_service: string;
  category: string;
  criticality: Criticality;
  annual_spend_gbp: string;
  data_categories: DataCategory[];
  processing_countries: string[];
  patch_sla_critical_days: string;
  answers: Record<string, AnswerEntry>;
  documents: DocumentRow[];
  components: ComponentRow[];
}

/** Field key → what is wrong, shown next to that field. */
export type FieldErrors = Record<string, string>;
export type BuildResult = { ok: true; body: CaseInputBody } | { ok: false; errors: FieldErrors };

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const DOC_COLUMNS = ["doc_type", "title", "issued_on", "expires_on", "text"] as const;
const COMPONENT_COLUMNS = ["vendor", "product", "version"] as const;

export const emptyDocument = (): DocumentRow => ({ doc_type: "", title: "", issued_on: "", expires_on: "", text: "" });
export const emptyComponent = (): ComponentRow => ({ vendor: "", product: "", version: "" });

export function emptyForm(questions: Question[]): IntakeForm {
  return {
    legal_name: "",
    trading_name: "",
    requested_service: "",
    category: "SaaS",
    criticality: "low",
    annual_spend_gbp: "0",
    data_categories: [],
    processing_countries: [],
    patch_sla_critical_days: "0",
    answers: Object.fromEntries(questions.map((q) => [q.question_id, { choice: "Not answered", how: "" }])),
    documents: [],
    components: [],
  };
}

interface Preset {
  name: string;
  legal_name: string;
  trading_name?: string | null;
  category: string;
  requested_service: string;
  criticality: Criticality;
  annual_spend_gbp: number;
  data_categories: DataCategory[];
  processing_countries: string[];
  patch_sla_critical_days?: number | null;
  documents?: Partial<DocumentRow>[];
  components?: Partial<ComponentRow>[];
  answers: Record<string, { choice: string | null; how?: string | null }>;
}

export const PRESETS = presetsFile.presets as Preset[];

/** Fill the whole form from a preset, as _apply_preset does. */
export function applyPreset(preset: Preset, questions: Question[]): IntakeForm {
  const form = emptyForm(questions);
  for (const [qid, entry] of Object.entries(preset.answers)) {
    const choice = entry.choice === "Yes" || entry.choice === "No" ? entry.choice : "Not answered";
    form.answers[qid] = { choice, how: entry.how ?? "" };
  }
  return {
    ...form,
    legal_name: preset.legal_name ?? "",
    trading_name: preset.trading_name ?? "",
    category: preset.category ?? "Other",
    requested_service: preset.requested_service ?? "",
    criticality: preset.criticality ?? "low",
    annual_spend_gbp: String(preset.annual_spend_gbp ?? 0),
    data_categories: [...preset.data_categories],
    processing_countries: [...preset.processing_countries],
    patch_sla_critical_days: String(preset.patch_sla_critical_days ?? 0),
    documents: (preset.documents ?? []).map((row) => ({ ...emptyDocument(), ...stringify(row) })),
    components: (preset.components ?? []).map((row) => ({ ...emptyComponent(), ...stringify(row) })),
  };
}

function stringify<T extends object>(row: T): Record<string, string> {
  return Object.fromEntries(Object.entries(row).map(([k, v]) => [k, v == null ? "" : String(v)]));
}

function answerText(question: Question, entry: AnswerEntry | undefined): string {
  const how = (entry?.how ?? "").trim();
  if (question.type === "yes_no") {
    if (entry?.choice !== "Yes" && entry?.choice !== "No") return "";
    return how ? `${entry.choice}. ${how}` : `${entry.choice}.`;
  }
  return how;
}

function cleanRows<T extends object>(rows: T[], columns: readonly (keyof T)[]): { index: number; row: Record<keyof T, string> }[] {
  const out: { index: number; row: Record<keyof T, string> }[] = [];
  rows.forEach((raw, position) => {
    const row = Object.fromEntries(columns.map((c) => [c, String(raw[c] ?? "").trim()])) as Record<keyof T, string>;
    if (Object.values(row).some(Boolean)) out.push({ index: position, row });
  });
  return out;
}

export function buildCaseInput(form: IntakeForm, questions: Question[]): BuildResult {
  const errors: FieldErrors = {};
  if (!form.legal_name.trim()) errors.legal_name = "Legal name is required.";
  if (!form.requested_service.trim()) errors.requested_service = "Describe the service being requested.";
  const spend = form.annual_spend_gbp.trim() === "" ? 0 : Number(form.annual_spend_gbp);
  if (Number.isNaN(spend)) errors.annual_spend_gbp = "Annual spend must be a number.";
  else if (spend < 0) errors.annual_spend_gbp = "Annual spend cannot be negative.";
  if (form.data_categories.length === 0) errors.data_categories = "Choose at least one data category (or 'none').";
  if (form.processing_countries.length === 0) errors.processing_countries = "Choose at least one processing country.";
  const patchRaw = form.patch_sla_critical_days.trim();
  const patch = patchRaw === "" ? 0 : Number(patchRaw);
  if (!Number.isInteger(patch) || patch < 0) errors.patch_sla_critical_days = "Use a whole number of days, or 0 if not stated.";

  const documents = cleanRows(form.documents, DOC_COLUMNS).map(({ index, row }, n) => {
    for (const field of ["issued_on", "expires_on"] as const) {
      if (row[field] && !DATE.test(row[field])) errors[`documents.${index}.${field}`] = "Use a date like 2026-03-01.";
    }
    if (!row.text) errors[`documents.${index}.text`] = "Paste the document text.";
    const number = n + 1;
    return {
      doc_id: `D${String(number).padStart(2, "0")}`,
      doc_type: row.doc_type || "Other",
      title: row.title || row.doc_type || `Document ${number}`,
      issued_on: row.issued_on || null,
      expires_on: row.expires_on || null,
      text: row.text,
    };
  });

  const declared_components = cleanRows(form.components, COMPONENT_COLUMNS).flatMap(({ index, row }) => {
    if (!row.product) {
      errors[`components.${index}.product`] = "Product is required.";
      return [];
    }
    return [{ vendor: row.vendor || null, product: row.product, version: row.version || null }];
  });

  const answers = questions.flatMap((question) => {
    const text = answerText(question, form.answers[question.question_id]);
    return text ? [{ question_id: question.question_id, question: question.question, answer_text: text }] : [];
  });

  if (Object.keys(errors).length > 0) return { ok: false, errors };
  const body = {
    submission: {
      legal_name: form.legal_name.trim(),
      trading_name: form.trading_name.trim() || null,
      category: form.category || "Other",
      requested_service: form.requested_service.trim(),
      criticality: form.criticality || "low",
      annual_spend_gbp: spend,
      data_categories: [...form.data_categories],
      processing_countries: [...form.processing_countries],
      answers,
      documents,
      declared_components,
      patch_sla_critical_days: patch ? patch : null,
    },
  };
  const parsed = caseInputSchema.safeParse(body);
  if (!parsed.success) {
    return { ok: false, errors: Object.fromEntries(parsed.error.issues.map((i) => [i.path.slice(1).join("."), i.message])) };
  }
  return { ok: true, body: parsed.data };
}

/** Advanced: a pasted JSON CaseInput, bare or wrapped as {"case": …} like POST /runs accepts. */
export function parsePasted(text: string): { ok: true; body: unknown } | { ok: false; errors: string[] } {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    return { ok: false, errors: ["This is not valid JSON."] };
  }
  const inner = value && typeof value === "object" && "case" in value ? (value as { case: unknown }).case : value;
  const parsed = pastedCaseInputSchema.safeParse(inner);
  if (parsed.success) return { ok: true, body: parsed.data };
  const issues = parsed.error.issues.flatMap((issue) =>
    issue.code === "invalid_union" ? issue.errors.flat() : [issue],
  );
  return {
    ok: false,
    errors: issues.map((issue) => (issue.path.length ? `${issue.path.join(".")}: ${issue.message}` : issue.message)),
  };
}
