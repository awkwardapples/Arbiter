import { describe, expect, it } from "vitest";
import { modeChipText, recordedLive } from "../mode";

describe("mode chip text (design §5)", () => {
  it("names the live stack", () => {
    expect(modeChipText({ kind: "mode", mode: { data: "zetaris", llm: "meterless" } }).text).toBe(
      "Live: Zetaris USL and Meterless Nightshift",
    );
  });
  it("names sample mode", () => {
    expect(modeChipText({ kind: "mode", mode: { data: "duckdb", llm: "offline" } }).text).toBe(
      "Sample mode: DuckDB mirror, deterministic fallback",
    );
  });
  it("labels a recording with its UTC start", () => {
    expect(modeChipText({ kind: "recording", startedAt: "2026-10-24T05:10:18.535Z" }).text).toBe(
      "Recorded live run, 24 Oct 2026 05:10 UTC",
    );
  });
  it("adds a fallback-step count when some steps fell back", () => {
    const chip = modeChipText({ kind: "mode", mode: { data: "zetaris", llm: "meterless" }, fallbacks: 2 });
    expect(chip.fallbacks).toBe("2 fallback steps");
  });
  it("never claims live for an unknown mix", () => {
    expect(modeChipText({ kind: "mode", mode: { data: "zetaris", llm: "offline" } }).text).not.toMatch(/^Live/);
  });
});

describe("recordings are labelled by their recorded mode", () => {
  it("does not call a sample-mode recording live", () => {
    const chip = modeChipText({ kind: "recording", startedAt: "2026-10-24T05:35:02Z", mode: { data: "duckdb", llm: "offline" } });
    expect(chip.text).toBe("Recorded sample-mode run, 24 Oct 2026 05:35 UTC");
  });
});

describe("a recording served by Zetaris and Nightshift is live (P20)", () => {
  const session = { data: "zetaris", llm: "auto" };
  it("counts an auto-provider run as live only when a model call was served", () => {
    expect(recordedLive(session, ["nvidia/nemotron-3.5-super-vl-120b-a12b"])).toBe(true);
    expect(recordedLive(session, [])).toBe(false);
    expect(recordedLive({ data: "duckdb", llm: "offline" }, [])).toBe(false);
    expect(recordedLive({ data: "zetaris", llm: "meterless" }, [])).toBe(true);
  });
  it("labels the live memory session as a recorded live run", () => {
    const chip = modeChipText({ kind: "recording", startedAt: "2026-10-24T05:10:18Z", mode: session, modelIds: ["nvidia/nemotron-3.5-super-vl-120b-a12b"] });
    expect(chip.text).toBe("Recorded live run, 24 Oct 2026 05:10 UTC");
    expect(modeChipText({ kind: "recording", startedAt: "2026-10-24T05:10:18Z", mode: session, modelIds: [] }).text).toBe(
      "Recorded run, 24 Oct 2026 05:10 UTC",
    );
  });
});
