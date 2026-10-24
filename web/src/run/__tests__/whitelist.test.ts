import { describe, expect, it } from "vitest";
import { PROVIDER_WHITELIST, filterProviderMeta, safeTraceLine } from "../whitelist";

describe("provider metadata whitelist (design §11)", () => {
  it("keeps only whitelisted keys, flat or nested", () => {
    const meta = {
      requested_model: "auto",
      routed_model: "nvidia/x",
      receipt_id: "rcpt_1",
      "winning_route.label": "Nemotron",
      Authorization: "Bearer canary-xyz",
      METERLESS_RUNTIME_TOKEN: "canary-abc",
      app_policy: { mode_coerced: "True", internal: "canary-nested" },
    };
    const kept = filterProviderMeta(meta);
    expect(kept).toEqual({
      requested_model: "auto",
      routed_model: "nvidia/x",
      receipt_id: "rcpt_1",
      "winning_route.label": "Nemotron",
      "app_policy.mode_coerced": "True",
    });
    expect(JSON.stringify(kept)).not.toMatch(/canary/);
  });

  it("filters provider_meta inside a raw trace line", () => {
    const line = safeTraceLine({ action: "model_call", provider_meta: { Authorization: "Bearer canary-xyz", mode: "deep" } });
    expect(JSON.stringify(line)).not.toMatch(/canary/);
    expect((line.provider_meta as Record<string, string>).mode).toBe("deep");
  });

  it("lists exactly the design §11 keys", () => {
    expect([...PROVIDER_WHITELIST].sort()).toEqual(
      [
        "app_policy.mode_coerced",
        "app_policy.requested_mode",
        "app_policy.routed_mode",
        "cost.actual_usd",
        "decision_id",
        "mode",
        "no_think",
        "receipt_id",
        "requested_model",
        "routed_model",
        "winning_route.label",
        "winning_route.model",
      ].sort(),
    );
  });
});
