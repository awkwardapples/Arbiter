import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { TraceEvent } from "../../api/types";
import { Inspector } from "../Inspector";
import { replay } from "../reducer";
import { LIVE, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T6 provider metadata whitelist in the Inspector", () => {
  it("never puts a token canary in the DOM, even in the raw trace line", async () => {
    const registry = loadRegistry();
    const events = loadTrace(LIVE);
    const index = events.findIndex((e) => e.action === "model_call");
    const poisoned = {
      ...events[index],
      provider_meta: {
        ...(events[index].provider_meta ?? {}),
        Authorization: "Bearer canary-xyz",
        METERLESS_RUNTIME_TOKEN: "canary-abc",
        nested: { Authorization: "Bearer canary-xyz" },
      },
    } as unknown as TraceEvent;
    const all = [...events.slice(0, index), poisoned, ...events.slice(index + 1)];
    const state = replay(all, registry);
    const { container } = render(
      <Inspector state={state} selection={{ kind: "event", index }} registry={registry} agents={[]} recordingPath={null} />,
    );
    const check = () => {
      expect(container.innerHTML).not.toContain("canary-xyz");
      expect(container.innerHTML).not.toContain("canary-abc");
      expect(container.textContent ?? "").not.toContain("canary");
    };
    check();
    await userEvent.click(screen.getByRole("button", { name: /show the trace line/i }));
    expect(container.textContent).toContain("receipt_id");
    check();
  });
});
