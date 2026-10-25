// P18C-T5: Replay decision shows a match, a diff in words, or the P19 human override sentence.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { caseRoutes, load, mockApi, renderAt, type Recorded } from "./helpers";

const detail = load<Recorded>("p18c_case_contradiction.json");
const trace = load("p18c_trace_contradiction.json");
const match = load<Record<string, unknown>>("p18c_replay_match.json");
const override = load<{ human_override: { rationale: string } }>("p18c_replay_override.json");

async function replayWith(payload: unknown) {
  mockApi({ ...caseRoutes(detail, trace), [`POST /cases/${detail.case_id}/replay`]: payload });
  renderAt(`/cases/${detail.case_id}?tab=audit`);
  await userEvent.click(await screen.findByRole("button", { name: "Replay decision" }));
  return screen.findByTestId("replay-result");
}

describe("P18C-T5 Replay", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("says the decision replays identically", async () => {
    const result = await replayWith(match);
    expect(result).toHaveTextContent("Decision replays identically");
  });

  it("shows a differing outcome in words", async () => {
    // The recorded match payload with the spec's mismatch applied, not a payload typed from scratch.
    const result = await replayWith({ ...match, match: false, diff: ["outcome"] });
    expect(result).toHaveTextContent(/differs/i);
    expect(result).toHaveTextContent("the outcome");
    expect(result).not.toHaveTextContent("Decision replays identically");
  });

  it("shows the human override sentence (P19 shape)", async () => {
    const result = await replayWith(override);
    expect(result).toHaveTextContent(
      /Machine decision replays identically; the TPRM lead overrode it to Approve with conditions on \d{1,2} [A-Z][a-z]{2} \d{4}:/,
    );
    expect(result).toHaveTextContent(override.human_override.rationale);
  });

  it("adds each replay to the audit timeline", async () => {
    await replayWith(match);
    expect(within(screen.getByTestId("audit-timeline")).getByText(/Replayed in this session/)).toBeInTheDocument();
  });
});
