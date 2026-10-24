import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RunCanvas } from "../RunCanvas";
import { SAMPLE, loadRegistry, loadTrace } from "./helpers";

describe("P18B-T7 RunCanvas under reduced motion", () => {
  const original = window.matchMedia;
  beforeEach(() => {
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 404 })));
  });
  afterEach(() => {
    window.matchMedia = original;
    vi.unstubAllGlobals();
  });

  it("renders the whole run with no travelling dots", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <RunCanvas source={{ kind: "events", events: loadTrace(SAMPLE), mode: "recorded" }} registryOverride={loadRegistry()} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: /skip to result/i }));
    });
    expect(screen.getByTestId("outcome-stamp")).toHaveTextContent("Escalate");
    expect(container.querySelector("[data-travel]")).toBeNull();
  });
});
