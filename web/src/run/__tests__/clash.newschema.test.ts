import { describe, expect, it } from "vitest";
import { replay } from "../reducer";
import { NEW_SCHEMA, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T8 contradiction_found from a real P18-A sample run", () => {
  const events = loadTrace(NEW_SCHEMA);
  const state = replay(events, loadRegistry());

  it("is a real capture with the new event", () => {
    expect(events.some((e) => e.action === "contradiction_found")).toBe(true);
  });

  it("creates a clash item with both values", () => {
    const item = state.clash.find((c) => c.vendorValue);
    expect(item).toMatchObject({ key: "residency.regions", control: "C09", vendorValue: "EU", recordValue: "US", system: "clm", recordKey: "contract_id=CTR-30007" });
    expect(state.clash).toHaveLength(1);
  });

  it("hangs two threads on the clash card: one from the vendor's word, one from the record", () => {
    const threads = Object.values(state.edges).filter((e) => e.type === "thread");
    expect(threads.map((t) => t.from).sort()).toEqual(["rec.clm", "vendor.answers"]);
    expect(threads.every((t) => t.to === "clash")).toBe(true);
  });

  it("records the policy decision from the new decide events", () => {
    expect(state.policy?.outcome).toBe("ESCALATE");
    expect(state.policy?.tier).toBe("T1");
    expect(state.policy?.failing).toEqual(["C09", "C12"]);
  });
});
