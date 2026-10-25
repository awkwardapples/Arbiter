import { screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type ApiRoutes, fixture, fromRepo, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { AuditPage } from "../../audit/AuditPage";
import { EvaluationPage } from "../../evaluation/EvaluationPage";
import { MemoryPage } from "../../memory/MemoryPage";
import { ProviderPage } from "../../provider/ProviderPage";
import { ReviewPage } from "../../review/ReviewPage";
import { SourcesPage } from "../../sources/SourcesPage";
import { NewAssessmentPage } from "../NewAssessmentPage";

const F = (path: string) => fixture(`features/${path}`);
const cases = F("evaluation/__tests__/fixtures/cases.json");
const caseDetail = fromRepo("tests/fixtures/ui/p14a_case_escalate.json");

const API: ApiRoutes = {
  "GET /health": { body: F("usl/__tests__/fixtures/health.json") },
  "GET /questions": { body: F("intake/__tests__/fixtures/questions.json") },
  "GET /usl/model": { body: F("usl/__tests__/fixtures/usl_model.json") },
  "GET /registry/queries": { body: F("usl/__tests__/fixtures/registry_queries.json") },
  "GET /evidence/parity": { body: F("usl/__tests__/fixtures/evidence_parity.json") },
  "GET /evidence/nightshift": { body: F("usl/__tests__/fixtures/evidence_nightshift.json") },
  "GET /agents": { body: F("usl/__tests__/fixtures/agents.json") },
  "GET /cases": { body: cases },
  [`GET /cases/${caseDetail.case_id}`]: { body: caseDetail },
  "GET /memory/precedents": { body: F("memory/__tests__/fixtures/precedents.json") },
  "GET /audit/recent?limit=50": { body: F("audit/__tests__/fixtures/audit_recent.json") },
  "GET /eval/latest": { body: F("evaluation/__tests__/fixtures/eval_latest.json") },
};
// Every case trace answers with the recorded sample-mode trace.
for (const c of cases) API[`GET /cases/${c.case_id}/trace`] = { body: F("usl/__tests__/fixtures/case_trace.json") };

/** Design §9 rows owned by lane 18d, and the elements that carry each one. */
const ROWS: { row: string; page: () => ReactElement; path?: string; pattern?: string; ids: string[] }[] = [
  {
    row: "New assessment: questionnaire form (16 questions, Yes/No/Not answered plus How?, documents and components, presets, validation, JSON under Advanced)",
    page: () => <NewAssessmentPage />,
    ids: ["new-vendor-form", "field-preset", "question-Q01", "question-Q16", "how-Q01", "rows-documents", "rows-components", "advanced-json"],
  },
  { row: "Sources and semantic layer (data mode, ERD with FKs, descriptions, DQ rules)", page: () => <SourcesPage />, ids: ["sources-mode", "usl-diagram", "usl-relationships", "usl-dq", "usl-catalogue"] },
  {
    row: "Review (lead or analyst review form, dry run for precedent eligibility)",
    page: () => <ReviewPage />,
    path: `/review/${caseDetail.case_id}`,
    pattern: "/review/:caseId",
    ids: ["review-form", "field-role", "field-decision", "field-rationale", "review-precedent"],
  },
  { row: "Precedents (list, status, feedback)", page: () => <MemoryPage />, ids: ["memory-rule", "memory-list", "precedent-feedback"] },
  { row: "Audit (recent events, verify chain)", page: () => <AuditPage />, ids: ["audit-table", "audit-verify"] },
  { row: "Evaluation (live summaries; this instance's activity)", page: () => <EvaluationPage />, ids: ["eval-live", "eval-table", "eval-instance"] },
  {
    row: "Sidebar provider proof (Nightshift status, URL with token hidden, served models, last receipt)",
    page: () => <ProviderPage />,
    ids: ["provider-connection", "provider-nightshift", "provider-models", "provider-proof", "provider-receipts", "provider-run-proof"],
  },
];

describe("Parity with the Streamlit console (design §9, lane 18d)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(ROWS)("P18D-T7: $row", async ({ page, path, pattern, ids }) => {
    stubApi(API);
    renderPage(page(), { path: path ?? "/", pattern: pattern ?? "/" });
    for (const id of ids) expect((await screen.findAllByTestId(id))[0]).toBeInTheDocument();
  });
});
