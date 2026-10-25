import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { FIELDS_READ } from "../reducer";

describe("generated TraceEvent type (design §11)", () => {
  it("has every field the reducer reads", () => {
    const generated = readFileSync(resolve(__dirname, "../../api/trace.d.ts"), "utf-8");
    for (const field of FIELDS_READ) expect(generated, field).toMatch(new RegExp(`\\b${field}\\??:`));
  });
});
