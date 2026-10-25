import { describe, expect, it } from "vitest";
import { modeChipText } from "../mode";
import { replay } from "../reducer";
import { SAMPLE, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T3 reducer on the sample-mode trace run-a90b795279e5", () => {
  const state = replay(loadTrace(SAMPLE), loadRegistry());

  it("never shows a model node in sample mode", () => {
    expect(Object.keys(state.nodes).some((id) => id.startsWith("model:"))).toBe(false);
  });

  it("labels the engine and the data hub honestly", () => {
    expect(state.nodes.engine.label).toBe("Deterministic fallback (no model call)");
    expect(state.nodes.usl.label).toBe("DuckDB mirror");
  });

  it("counts 14 mirror queries", () => {
    expect(state.counters.mirror).toBe(14);
    expect(state.counters.zetaris).toBe(0);
  });

  it("produces the sample-mode chip text", () => {
    expect(modeChipText({ kind: "mode", mode: state.mode }).text).toBe("Sample mode: DuckDB mirror, deterministic fallback");
  });
});
