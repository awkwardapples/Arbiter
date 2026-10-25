// P18C-T6: Agent activity replays the case's own trace on 18b's bench; the counters match the reducer.
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RegistryQuery, TraceEvent } from "../../../api/types";
import { replay } from "../../../run/reducer";
import { buildRegistry } from "../../../run/registry";
import { caseRoutes, load, mockApi, renderAt, type Recorded } from "./helpers";

const detail = load<Recorded>("p18c_case_contradiction.json");
const trace = load<TraceEvent[]>("p18c_trace_contradiction.json");
const registry = buildRegistry(load<RegistryQuery[]>("p18c_registry.json"));

const LABELS: Array<[string, keyof ReturnType<typeof replay>["counters"]]> = [
  ["Critiques", "critiques"],
  ["Sent back", "sent_back"],
  ["Retries and fallbacks", "retries_fallbacks"],
  ["Shared context reads", "shared_context"],
  ["Model calls on Nemotron", "model_calls"],
  ["Mirror queries", "mirror"],
];

describe("P18C-T6 Agent activity", () => {
  const original = window.matchMedia;
  beforeEach(() => {
    // Reduced motion: the number tickers show plain values, so the counters can be read straight away.
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;
  });
  afterEach(() => {
    window.matchMedia = original;
    vi.unstubAllGlobals();
  });

  it("replays the case trace on the bench, and its counters match the reducer", async () => {
    mockApi(caseRoutes(detail, trace));
    renderAt(`/cases/${detail.case_id}?tab=activity`);
    const tab = await screen.findByTestId("agent-activity");
    const skip = await within(tab).findByRole("button", { name: /skip to result/i });
    await act(async () => {
      await userEvent.click(skip);
    });
    expect(within(tab).getByTestId("outcome-stamp")).toHaveTextContent("Escalate");

    const expected = replay(trace, registry).counters;
    const strip = within(tab).getByRole("group", { name: "What the agents did" });
    for (const [label, key] of LABELS) {
      const button = within(strip).getByRole("button", { name: new RegExp(label) });
      expect(Number(/\d+/.exec(button.textContent ?? "")?.[0]), label).toBe(expected[key]);
    }
    expect(screen.getByTestId("workload")).toHaveTextContent(/^Checked \d+ systems/);
  });
});
