// P18C-T7: every design §9 row owned by 18c has a rendered element.
import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { caseRoutes, load, mockApi, renderAt, type Recorded } from "./helpers";

const contradiction = load<Recorded>("p18c_case_contradiction.json");
const pending = load<Recorded>("p18c_case_pending.json");

interface Row {
  row: string;
  detail: Recorded | null;
  tab: string | null;
  ids: string[];
}

const ROWS: Row[] = [
  {
    row: "Cases: totals per outcome, waiting for approval, filters by outcome and tier, sort by residual risk, open case",
    detail: null,
    tab: null,
    ids: ["cases-summary", "cases-filter-outcome", "cases-filter-tier", "cases-table", "case-row"],
  },
  {
    row: "Case header: outcome label and meaning, tier, residual risk, confidence sentence with unverified controls",
    detail: contradiction,
    tab: "decision",
    ids: ["case-header", "outcome-stamp", "case-meaning", "case-tier", "case-risk", "case-confidence", "mode-chip"],
  },
  {
    row: "Brief headline, why-points, claim-versus-record cards (mismatch in red), KEV point",
    detail: contradiction,
    tab: "decision",
    ids: ["brief-headline", "why-point", "claim-card", "record-card"],
  },
  { row: "Next action: recipient, subject, editable body, Copy, Download .txt", detail: contradiction, tab: "decision", ids: ["next-action"] },
  {
    row: "Contract approval (role, name, rationale ≥ 30 characters, Approve or Reject) and the executed or outbox state",
    detail: pending,
    tab: "decision",
    ids: ["contract-block", "contract-approval"],
  },
  {
    row: "Controls in business terms; what would change the decision; precedents considered",
    detail: contradiction,
    tab: "evidence",
    ids: ["evidence-controls", "evidence-changes", "evidence-precedents", "evidence-facts"],
  },
  { row: "Agent timeline in words; workload sentence", detail: contradiction, tab: "activity", ids: ["agent-activity", "workload"] },
  { row: "Dossier download (HTML and Markdown)", detail: contradiction, tab: "audit", ids: ["dossier-download"] },
  { row: "Replay", detail: contradiction, tab: "audit", ids: ["replay-button", "audit-timeline"] },
  {
    row: "Technical details (reason codes, control table with evidence chips, contradictions, counterfactuals, contracts, raw JSON)",
    detail: contradiction,
    tab: "technical",
    ids: ["technical-reasons", "technical-controls", "technical-contradictions", "technical-counterfactuals", "technical-contracts", "technical-raw"],
  },
];

describe("P18C-T7 Parity with the Streamlit console (design §9)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(ROWS)("$row", async ({ detail, tab, ids }) => {
    if (detail) {
      const trace = load(detail === pending ? "p18c_trace_pending.json" : "p18c_trace_contradiction.json");
      mockApi(caseRoutes(detail, trace));
      renderAt(`/cases/${detail.case_id}?tab=${tab}`);
    } else {
      mockApi({ "GET /cases": load("p18c_queue.json"), "GET /health": load("p14a_health_offline.json") });
      renderAt("/cases");
    }
    for (const id of ids) {
      expect((await screen.findAllByTestId(id)).length, id).toBeGreaterThan(0);
    }
  });
});
