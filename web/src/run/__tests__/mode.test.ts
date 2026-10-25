import { describe, expect, it } from "vitest";
import { modeChipText } from "../mode";

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
  it("adds a fallback count when some calls fell back", () => {
    const chip = modeChipText({ kind: "mode", mode: { data: "zetaris", llm: "meterless" }, fallbacks: 2 });
    expect(chip.fallbacks).toBe("2 fallbacks");
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
