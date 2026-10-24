// P18C-T2: the Case page for example 2 (Quillfeather, recorded by P14-A in sample mode).
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { caseRoutes, codeLikeText, load, mockApi, renderAt, type Recorded } from "./helpers";

const detail = load<Recorded>("p14a_case_escalate.json");
const trace = load("p14a_trace_escalate.json");
const TABS = ["Decision", "Evidence", "Audit trail"];

describe("P18C-T2 Case, example 2", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("stamps Escalate and shows the vendor's claim against the contract record", async () => {
    mockApi(caseRoutes(detail, trace));
    renderAt(`/cases/${detail.case_id}`);
    expect(await screen.findByTestId("outcome-stamp")).toHaveTextContent("Escalate");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(detail.vendor);
    const claim = screen.getByTestId("claim-card");
    const record = screen.getByTestId("record-card");
    expect(claim).toHaveTextContent("EU");
    expect(record).toHaveTextContent("US");
    expect(record).toHaveTextContent("CTR-30007");
    expect(within(record).getByText("US")).toHaveAttribute("data-clash", "true");
  });

  it("names the unverified controls in words in the header", async () => {
    mockApi(caseRoutes(detail, trace));
    renderAt(`/cases/${detail.case_id}`);
    const confidence = await screen.findByTestId("case-confidence");
    expect(confidence).toHaveTextContent("75%");
    expect(confidence).not.toHaveTextContent(/C\d\d/);
  });

  it("shows no reason code outside Technical details", async () => {
    mockApi(caseRoutes(detail, trace));
    renderAt(`/cases/${detail.case_id}`);
    await screen.findByTestId("outcome-stamp");
    for (const name of TABS) {
      await userEvent.click(screen.getByRole("tab", { name }));
      await screen.findByTestId(`${name.toLowerCase().replace(" ", "-")}-tab`);
      expect(codeLikeText(document.body), `tab ${name}`).toEqual([]);
    }
  });

  it("lets codes lead only in Technical details", async () => {
    mockApi(caseRoutes(detail, trace));
    renderAt(`/cases/${detail.case_id}?tab=technical`);
    const tab = await screen.findByTestId("technical-tab");
    expect(within(tab).getByTestId("technical-reasons")).toHaveTextContent("CONTRADICTION");
  });
});
