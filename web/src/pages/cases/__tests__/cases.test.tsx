// P18C-T1: the Cases queue, from the recorded six-case sample-mode queue.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { load, mockApi, renderAt, status, type Recorded } from "../../../features/case/__tests__/helpers";

interface Item {
  case_id: string;
  vendor: string;
  outcome: string;
  tier: string;
}

const queue = load<Item[]>("p18c_queue.json");
const pending = load<Recorded>("p18c_case_pending.json");
const approved = load<Recorded>("p18c_case_approved.json");
const contradiction = load<Recorded>("p18c_case_contradiction.json");

function routes(detail: Recorded = pending) {
  return {
    "GET /cases": queue,
    [`GET /cases/${detail.case_id}`]: detail,
    [`GET /cases/${contradiction.case_id}`]: contradiction,
    [`GET /cases/${contradiction.case_id}/trace`]: status(404),
    "GET /health": load("p14a_health_offline.json"),
  };
}

const rowIds = () => screen.getAllByTestId("case-row").map((row) => row.getAttribute("data-case-id"));
const count = (pred: (i: Item) => boolean) => queue.filter(pred).length;

describe("P18C-T1 Cases", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists rows in the order the API returns them", async () => {
    mockApi(routes());
    renderAt("/cases");
    await screen.findByTestId("cases-table");
    expect(rowIds()).toEqual(queue.map((i) => i.case_id));
    expect(screen.getByText(queue[0].vendor)).toBeInTheDocument();
  });

  it("counts the summary sentence from the payload", async () => {
    mockApi(routes());
    renderAt("/cases");
    const summary = await screen.findByTestId("cases-summary");
    const lead = count((i) => i.outcome === "ESCALATE" || i.outcome === "DECLINE");
    const vendor = count((i) => i.outcome === "REQUEST_INFO");
    expect(summary).toHaveTextContent(`${queue.length} cases.`);
    expect(summary).toHaveTextContent(new RegExp(`${lead} needs? the TPRM lead`));
    expect(summary).toHaveTextContent(new RegExp(`${vendor} (is|are) waiting for the vendor`));
    // One recorded case has a contract in pending_approval; the others answer 404 and are skipped.
    await waitFor(() => expect(summary).toHaveTextContent(/1 approval is waiting for sign-off/));
  });

  it("does not count a pending contract that an approval has superseded", async () => {
    mockApi(routes(approved));
    renderAt("/cases");
    const summary = await screen.findByTestId("cases-summary");
    await waitFor(() => expect(summary).toHaveTextContent(/no approvals are waiting for sign-off/i));
  });

  it("filters by the outcome in the URL, and the chips carry counts", async () => {
    mockApi(routes());
    const { router } = renderAt("/cases?outcome=ESCALATE");
    await screen.findByTestId("cases-table");
    const escalations = queue.filter((i) => i.outcome === "ESCALATE").map((i) => i.case_id);
    expect(rowIds()).toEqual(escalations);

    const chips = screen.getByTestId("cases-filter-outcome");
    const decline = within(chips).getByRole("button", { name: /^Decline/ });
    expect(decline).toHaveTextContent(String(count((i) => i.outcome === "DECLINE")));
    await userEvent.click(decline);
    expect(router.state.location.search).toContain("outcome=DECLINE");
    expect(rowIds()).toEqual(queue.filter((i) => ["ESCALATE", "DECLINE"].includes(i.outcome)).map((i) => i.case_id));
  });

  it("filters by tier from the URL", async () => {
    mockApi(routes());
    renderAt("/cases?tier=T1");
    await screen.findByTestId("cases-table");
    expect(rowIds()).toEqual(queue.filter((i) => i.tier === "T1").map((i) => i.case_id));
    expect(within(screen.getByTestId("cases-filter-tier")).getByRole("button", { name: /^T1/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("moves between rows with the arrow keys and opens one with Enter", async () => {
    mockApi(routes());
    const { router } = renderAt("/cases");
    await screen.findByTestId("cases-table");
    const rows = screen.getAllByTestId("case-row");
    rows[0].focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(rows[1]).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(router.state.location.pathname).toBe(`/cases/${queue[1].case_id}`);
  });

  it("invites an assessment when there are no cases", async () => {
    mockApi({ "GET /cases": [], "GET /health": load("p14a_health_offline.json") });
    const { router } = renderAt("/cases");
    expect(await screen.findByText("No cases yet. Start an assessment to see the agents work.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start an assessment" }));
    expect(router.state.location.pathname).toBe("/");
  });
});
