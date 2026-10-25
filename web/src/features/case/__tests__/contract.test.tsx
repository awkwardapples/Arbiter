// P18C-T4: contract approval needs a 30-character rationale and posts exactly {by, role, decision, rationale}.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { callsTo, caseRoutes, fill, load, mockApi, renderAt, type Recorded } from "./helpers";

const pending = load<Recorded>("p18c_case_pending.json");
const approved = load<Recorded>("p18c_case_approved.json");
const trace = load("p18c_trace_pending.json");
const result = load<{ artifact: string }>("p18c_approve_result.json");
const contract = pending.contracts.find((c) => c.state === "pending_approval")!;
const APPROVE_PATH = `/contracts/${contract.contract_id}/approve`;
const RATIONALE = "Reviewed the decline memo; the hard gate failure is confirmed in the record.";

function routes() {
  let done = false;
  return {
    ...caseRoutes(pending, trace),
    [`GET /cases/${pending.case_id}`]: () => (done ? approved : pending),
    [`POST ${APPROVE_PATH}`]: () => {
      done = true;
      return result;
    },
  };
}

describe("P18C-T4 Contract approval", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("keeps Approve disabled under 30 characters and never calls the API", async () => {
    const fetch = mockApi(routes());
    renderAt(`/cases/${pending.case_id}`);
    const block = await screen.findByTestId("contract-approval");
    await userEvent.type(within(block).getByLabelText("Your name"), "Dana Reviewer");
    await fill(userEvent, within(block).getByLabelText(/Rationale/), "x".repeat(29));
    expect(within(block).getByTestId("rationale-count")).toHaveTextContent("29 / 30");
    const approve = within(block).getByRole("button", { name: "Approve contract" });
    expect(approve).toBeDisabled();
    expect(within(block).getByRole("button", { name: "Reject contract" })).toBeDisabled();
    await userEvent.click(approve);
    expect(callsTo(fetch, "POST", APPROVE_PATH)).toHaveLength(0);
  });

  it("posts the approval and shows the toast and the outbox file", async () => {
    const fetch = mockApi(routes());
    renderAt(`/cases/${pending.case_id}`);
    const block = await screen.findByTestId("contract-approval");
    await userEvent.type(within(block).getByLabelText("Your name"), "Dana Reviewer");
    await fill(userEvent, within(block).getByLabelText(/Rationale/), RATIONALE);
    const approve = within(block).getByRole("button", { name: "Approve contract" });
    expect(approve).toBeEnabled();
    await userEvent.click(approve);

    await waitFor(() => expect(callsTo(fetch, "POST", APPROVE_PATH)).toHaveLength(1));
    const [, init] = callsTo(fetch, "POST", APPROVE_PATH)[0];
    const body = JSON.parse(String(init?.body));
    expect(Object.keys(body).sort()).toEqual(["by", "decision", "rationale", "role"]);
    expect(body).toEqual({ by: "Dana Reviewer", role: "tprm_lead", decision: "approve", rationale: RATIONALE });

    const file = result.artifact.split("/").pop()!;
    expect(await screen.findByText("Contract approved")).toBeInTheDocument();
    expect(await screen.findAllByText(new RegExp(file.replace(".", "\\.")))).not.toHaveLength(0);
    await waitFor(() => expect(screen.getByTestId("contract-block")).toHaveTextContent(`Sent to the outbox: ${file}`));
  });

  it("names the outbox file of a contract the run executed, from its trace", async () => {
    const detail = load<Recorded>("p18c_case_contradiction.json");
    mockApi(caseRoutes(detail, load("p18c_trace_contradiction.json")));
    renderAt(`/cases/${detail.case_id}`);
    const block = await screen.findByTestId("contract-block");
    await waitFor(() => expect(block).toHaveTextContent(`Sent to the outbox: ${detail.contracts[0].contract_id}.json`));
  });
});
