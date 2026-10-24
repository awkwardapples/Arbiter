import { describe as group, expect, it } from "vitest";
import type { TraceEvent } from "../../api/types";
import { describe } from "../describe";
import { allTraceFiles, loadRegistry, loadTrace, NEW_SCHEMA } from "./helpers";

const CODE_START = /^[A-Z]{1,3}\d|^Q_|^[A-Z_]{6,}/;
const registry = loadRegistry();

group("P18B-T4 plain-English activity lines", () => {
  const files = [...allTraceFiles(), NEW_SCHEMA];

  it("covers the committed traces", () => {
    expect(files.length).toBeGreaterThan(50);
  });

  it("never starts a sentence with a code", () => {
    for (const file of files) {
      for (const event of loadTrace(file)) {
        const line = describe(event, registry);
        expect(line.text, `${file}: ${event.agent_name} ${event.action}`).not.toMatch(CODE_START);
        expect(line.text.length).toBeGreaterThan(8);
      }
    }
  });

  it("has a specific sentence for every (agent, action) pair in the traces", () => {
    const seen = new Map<string, TraceEvent>();
    for (const file of files) for (const event of loadTrace(file)) seen.set(`${event.agent_name} ${event.action} ${event.status}`, event);
    for (const [pair, event] of seen) {
      const line = describe(event, registry);
      expect(line.generic, pair).toBe(false);
    }
  });

  it("falls back to the generic form for an unknown action", () => {
    const event = { ...loadTrace(NEW_SCHEMA)[0], agent_name: "PlannerAgent", action: "dream", output_summary: "something new" } as TraceEvent;
    const line = describe(event, registry);
    expect(line.generic).toBe(true);
    expect(line.text).toBe("Planner dream: something new");
  });

  it("matches the design's example sentences", () => {
    const live = loadTrace("logs/examples/live/trace-run-83de5da137c0.jsonl");
    const texts = live.map((e) => describe(e, registry).text);
    expect(texts).toContain("Started the assessment of CASE-0003 with a 600 s budget.");
    expect(texts).toContain("The Planner read the semantic layer's model (304 tokens).");
    expect(texts).toContain("Nemotron 3.5 Super VL 120B A12B answered in 14.2 s with a valid plan.");
    expect(texts).toContain("The policy re-added 3 required checks the model left out.");
    expect(texts).toContain("The Planner sent 7 queries to Evidence.");
    expect(texts).toContain("Contracts (CLM): 1 row in 1.7 s through Zetaris.");
    expect(texts).toContain("Evidence extracted 16 claims from 15 answers, each with a quote.");
    expect(texts).toContain("Nightshift returned an error (HTTP 502), so the Planner used its deterministic fallback.");
    expect(texts).toContain("Decided Approve in 2 min 39 s.");
    const fresh = loadTrace(NEW_SCHEMA).map((e) => describe(e, registry).text);
    expect(fresh).toContain("The vendor says EU; Contracts (CLM) says US.");
  });
});
