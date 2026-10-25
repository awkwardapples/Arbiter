import { describe, expect, it } from "vitest";
import { replay } from "../reducer";
import { EVAL, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T2 reducer on the live eval trace run-257c86984507", () => {
  const state = replay(loadTrace(EVAL), loadRegistry());

  it("counts behaviour exactly", () => {
    expect(state.counters).toMatchObject({ critiques: 6, sent_back: 3, retries_fallbacks: 1, shared_context: 4, model_calls: 3, zetaris: 14 });
  });

  it("shows CISA KEV with an edge that mentions 15 rows", () => {
    expect(state.nodes["rec.kev"]).toBeDefined();
    const kevEdges = Object.values(state.edges).filter((e) => e.to === "rec.kev");
    expect(kevEdges.some((e) => /15 rows/.test(e.lastLabel))).toBe(true);
  });

  it("sends back twice and re-plans once", () => {
    expect(Object.values(state.edges).find((e) => e.type === "sendback")?.count).toBe(2);
    expect(Object.values(state.edges).find((e) => e.type === "replan")?.count).toBe(1);
  });

  it("creates one clash item from the evaluate summary without inventing values", () => {
    expect(state.clash).toHaveLength(1);
    expect(state.clash[0].text).toBe("1 contradiction found; details in the case record");
    expect(state.clash[0].vendorValue).toBeUndefined();
    expect(state.clash[0].recordValue).toBeUndefined();
  });

  it("ends with ESCALATE", () => {
    expect(state.outcome?.outcome).toBe("ESCALATE");
  });
});
