import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parseDone, parseTraceEvent } from "../events";

const LIVE = resolve(__dirname, "../../../../logs/examples/live/trace-run-83de5da137c0.jsonl");

describe("SSE payload validation", () => {
  it("accepts every committed live trace line", () => {
    const lines = readFileSync(LIVE, "utf-8").split("\n").filter(Boolean);
    for (const line of lines) expect(parseTraceEvent(JSON.parse(line))).not.toBeNull();
  });

  it("keeps unknown fields so newer events still render", () => {
    const line = JSON.parse(readFileSync(LIVE, "utf-8").split("\n")[0]);
    const parsed = parseTraceEvent({ ...line, future_field: 3 });
    expect(parsed).not.toBeNull();
    expect((parsed as Record<string, unknown>).future_field).toBe(3);
  });

  it("rejects a payload without the required fields", () => {
    expect(parseTraceEvent({ action: "plan" })).toBeNull();
  });

  it("parses the done message", () => {
    const done = parseDone({ run_id: "run-000000000000", status: "success", case_id: "X", outcome: "ESCALATE", execution_time_seconds: 1.2, mode: { data: "duckdb", llm: "offline" } });
    expect(done?.outcome).toBe("ESCALATE");
  });
});
