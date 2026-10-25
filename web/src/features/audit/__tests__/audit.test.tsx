import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuditPage } from "../../../pages/audit/AuditPage";
import { fixture, renderPage, stubApi } from "../../../ui/__tests__/harness";

const recent = fixture("features/audit/__tests__/fixtures/audit_recent.json");
const verified = fixture("features/audit/__tests__/fixtures/audit_verify.json");
const health = fixture("features/usl/__tests__/fixtures/health.json");

async function verifyWith(result: unknown) {
  const user = userEvent.setup();
  stubApi({ "GET /audit/verify": { body: result }, "GET /audit/recent?limit=50": { body: recent }, "GET /health": { body: health } });
  renderPage(<AuditPage />);
  await screen.findByTestId("audit-table");
  await user.click(screen.getByRole("button", { name: "Verify chain" }));
  return screen.findByTestId("audit-verify-result");
}

describe("Audit", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T5: renders the verified shape and the broken shape", async () => {
    expect(verified.ok).toBe(true);
    const ok = await verifyWith(verified);
    expect(ok).toHaveTextContent(`Audit chain verified: ${health.audit_chain_length} entries.`);
    vi.unstubAllGlobals();
    document.body.innerHTML = "";

    // The broken shape is the recorded one with the chain marked broken at entry 7.
    const broken = await verifyWith({ ...verified, ok: false, first_bad_seq: 7 });
    expect(broken).toHaveTextContent("Chain breaks at entry 7.");
  });

  it("lists the recent entries: entry, time, what happened in words, case", async () => {
    stubApi({ "GET /audit/recent?limit=50": { body: recent }, "GET /health": { body: health } });
    renderPage(<AuditPage />);
    const rows = await screen.findAllByTestId("audit-row");
    expect(rows).toHaveLength(recent.length);
    expect(rows[0]).toHaveTextContent(String(recent[0].seq));
    expect(rows[0]).toHaveTextContent(recent[0].case_id);
    expect(screen.getAllByText("Review recorded").length).toBeGreaterThan(0);
  });
});
