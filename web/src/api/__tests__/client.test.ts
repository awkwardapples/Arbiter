import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../client";

function respond(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
}

describe("api client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", respond(200, { status: "ok" }));
    await expect(api.get<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });

  it("turns the ErrorResponse shape into a typed ApiError", async () => {
    const body = { status: "error", error: { type: "busy", message: "Two assessments are already running.", recoverable: true } };
    vi.stubGlobal("fetch", respond(429, body));
    const err = await api.post("/runs", {}).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(429);
    expect((err as ApiError).code).toBe("busy");
    expect((err as ApiError).message).toBe("Two assessments are already running.");
  });

  it("explains a network failure in words", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const err = await api.get("/health").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toMatch(/could not reach the Arbiter API/i);
  });
});
