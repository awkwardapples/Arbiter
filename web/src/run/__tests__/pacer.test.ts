import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPacer } from "../pacer";
import { replay } from "../reducer";
import { LIVE, SAMPLE, loadRegistry, loadTrace } from "./helpers";

function playToEnd(mode: "paced" | "recorded", file: string, speed: 1 | 4 | 16 = 4): number {
  const events = loadTrace(file);
  let applied = 0;
  const pacer = createPacer({ events, mode, speed, onApply: (n) => (applied = n) });
  const start = Date.now();
  pacer.start();
  let guard = 0;
  while (applied < events.length && guard++ < 100_000) vi.advanceTimersByTime(10);
  pacer.stop();
  return (Date.now() - start) / 1000;
}

describe("P18B-T5 pacer", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("plays a 73-event sample trace in 10-30 s when paced", () => {
    expect(loadTrace(SAMPLE)).toHaveLength(73);
    const seconds = playToEnd("paced", SAMPLE);
    expect(seconds).toBeGreaterThanOrEqual(10);
    expect(seconds).toBeLessThanOrEqual(30);
  });

  it("plays the live recording at 4x in 60 s or less", () => {
    const seconds = playToEnd("recorded", LIVE, 4);
    expect(seconds).toBeGreaterThan(1);
    expect(seconds).toBeLessThanOrEqual(60);
  });

  it("skips to the result and reaches the final state", () => {
    const events = loadTrace(LIVE);
    const registry = loadRegistry();
    let applied = 0;
    const pacer = createPacer({ events, mode: "recorded", speed: 1, onApply: (n) => (applied = n) });
    pacer.start();
    vi.advanceTimersByTime(500);
    pacer.skipToEnd();
    expect(applied).toBe(events.length);
    expect(replay(events.slice(0, applied), registry)).toEqual(replay(events, registry));
  });

  it("steps to the next moment and seeks to an index", () => {
    const events = loadTrace(LIVE);
    let applied = 0;
    const pacer = createPacer({ events, mode: "recorded", speed: 1, onApply: (n) => (applied = n) });
    pacer.pause();
    pacer.step();
    const first = applied;
    expect(first).toBeGreaterThan(0);
    expect(events[first - 1].target_agent || events[first - 1].status !== "success" || ["complete_run", "decide", "contradiction_found"].includes(events[first - 1].action)).toBeTruthy();
    pacer.seek(10);
    expect(applied).toBe(10);
  });

  it("passes live events straight through", () => {
    const events = loadTrace(SAMPLE);
    let applied = 0;
    const pacer = createPacer({ events: [], mode: "live", speed: 1, onApply: (n) => (applied = n) });
    pacer.start();
    pacer.push(events[0]);
    pacer.push(events[1]);
    expect(applied).toBe(2);
  });
});
