// Test harness for pages that call the API: a router, a fresh QueryClient, and a fetch that answers
// from recorded payloads by method and path. Unrouted calls fail loudly so a test never hits a network.
/* eslint-disable @typescript-eslint/no-explicit-any -- recorded payloads are read untyped; each test narrows them */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

export interface Reply {
  status?: number;
  body: unknown;
}

export type ApiRoutes = Record<string, Reply | ((body: unknown) => Reply)>;

export interface Call {
  method: string;
  path: string;
  body: unknown;
}

/** Stub fetch. Keys are "GET /health" or "POST /runs"; the query string is part of the path. */
export function stubApi(routes: ApiRoutes): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://console.test");
      const method = (init?.method ?? "GET").toUpperCase();
      const path = `${url.pathname}${url.search}`;
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
      calls.push({ method, path, body });
      const route = routes[`${method} ${path}`] ?? routes[`${method} ${url.pathname}`];
      if (!route) return new Response(JSON.stringify({ detail: `unrouted ${method} ${path}` }), { status: 599 });
      const reply = typeof route === "function" ? route(body) : route;
      return new Response(JSON.stringify(reply.body), { status: reply.status ?? 200, headers: { "content-type": "application/json" } });
    }),
  );
  return calls;
}

/** Render `element` at `path` (matched against `pattern`), with a stub run page to land on. */
export function renderPage(element: ReactElement, { path = "/", pattern = "/" }: { path?: string; pattern?: string } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={pattern} element={element} />
          <Route path="/runs/:runId" element={<p data-testid="landed-run">run view</p>} />
          <Route path="/cases/:caseId" element={<p data-testid="landed-case">case page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const SRC = resolve(__dirname, "../..");

/** A recorded payload, by path under web/src (or under the repo with `fromRepo`). */
export function fixture<T = any>(path: string): T {
  return JSON.parse(readFileSync(resolve(SRC, path), "utf-8")) as T;
}

export function fromRepo<T = any>(path: string): T {
  return JSON.parse(readFileSync(resolve(SRC, "../..", path), "utf-8")) as T;
}
