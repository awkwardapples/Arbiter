import { describe, expect, it } from "vitest";
import { replay } from "../reducer";
import { LIVE, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T1 reducer on the live trace run-83de5da137c0", () => {
  const state = replay(loadTrace(LIVE), loadRegistry());

  it("counts behaviour exactly as pass §5 defines it", () => {
    expect(state.counters).toMatchObject({ critiques: 5, sent_back: 2, retries_fallbacks: 1, shared_context: 5, model_calls: 5, zetaris: 12 });
  });

  it("shows one model node, the Nemotron model named by the events", () => {
    const models = Object.keys(state.nodes).filter((id) => id.startsWith("model:"));
    expect(models).toEqual(["model:nvidia/nemotron-3.5-super-vl-120b-a12b"]);
  });

  it("marks the Planner as having fallen back", () => {
    expect(state.nodes.planner.fellBack).toBe(true);
    expect(state.nodes.planner.ring).toBe("fallback");
  });

  it("draws one send-back and one re-plan back-edge", () => {
    const back = Object.values(state.edges).filter((e) => e.type === "sendback");
    const replan = Object.values(state.edges).filter((e) => e.type === "replan");
    expect(back).toHaveLength(1);
    expect(back[0]).toMatchObject({ from: "evaluator", to: "planner", count: 1 });
    expect(replan).toHaveLength(1);
    expect(replan[0]).toMatchObject({ from: "challenger", to: "planner", count: 1 });
  });

  it("ends with APPROVE and Plan visited three times", () => {
    expect(state.outcome?.outcome).toBe("APPROVE");
    expect(state.stages.find((s) => s.name === "Plan")?.visits).toBe(3);
  });

  it("notes the Nightshift lane coercion the receipts record", () => {
    expect(state.coerced).toBe(true);
  });
});
