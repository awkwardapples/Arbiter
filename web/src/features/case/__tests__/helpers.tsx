// Test support for lane 18c: recorded API payloads from tests/fixtures/ui (never hand-written), a fetch
// double that serves them by route, and a memory router with the console's providers.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import CasePage from "../../../pages/case";
import CasesPage from "../../../pages/cases";
import { Toaster } from "../../../ui/toast";
import { TooltipProvider } from "../../../ui/tooltip";

// jsdom gives import.meta.url a non-file scheme, so walk up from the working directory (web/ or the repo).
function fixturesDir(): string {
  for (let dir = process.cwd(); ; dir = dirname(dir)) {
    const candidate = join(dir, "tests", "fixtures", "ui");
    if (existsSync(candidate)) return `${candidate}/`;
    if (dirname(dir) === dir) throw new Error("tests/fixtures/ui not found above the working directory");
  }
}

const FIXTURES = fixturesDir();

// Whole pages render in jsdom here, four files at a time; the default 5 s is too tight under that load.
vi.setConfig({ testTimeout: 20_000 });

/** jsdom's Blob has no text(); FileReader reads it. */
export function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

/** Put text into a field as one paste; typing long text key by key is slow and tests nothing extra. */
export async function fill(user: { click: (e: Element) => Promise<void>; paste: (t: string) => Promise<void> }, field: Element, text: string) {
  await user.click(field);
  await user.paste(text);
}

export function load<T = unknown>(name: string): T {
  return JSON.parse(readFileSync(`${FIXTURES}${name}`, "utf-8")) as T;
}

export interface Reply {
  status: number;
  body: unknown;
}

export const status = (code: number, body: unknown = { status: "error", error: { type: "not_found", message: "Not found" } }): Reply => ({
  status: code,
  body,
});

type Handler = unknown | Reply | ((body: unknown) => unknown);

function isReply(value: unknown): value is Reply {
  return typeof value === "object" && value !== null && "status" in value && "body" in value && Object.keys(value).length === 2;
}

/** Stub fetch. Keys are "GET /cases" or "POST /contracts/x/approve"; anything else answers 404. */
export function mockApi(routes: Record<string, Handler>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://console.test");
    const method = (init?.method ?? "GET").toUpperCase();
    const key = `${method} ${url.pathname}${url.search}`;
    const bare = `${method} ${url.pathname}`;
    let handler: Handler = key in routes ? routes[key] : bare in routes ? routes[bare] : status(404);
    if (typeof handler === "function") {
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      handler = (handler as (b: unknown) => unknown)(body);
    }
    const reply = isReply(handler) ? handler : { status: 200, body: handler };
    const text = typeof reply.body === "string" ? reply.body : JSON.stringify(reply.body);
    return new Response(text, { status: reply.status, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

/** Calls the fetch double received for one method and path. */
export function callsTo(fn: ReturnType<typeof mockApi>, method: string, path: string) {
  return fn.mock.calls.filter(([input, init]) => {
    const url = new URL(String(input), "http://console.test");
    return url.pathname === path && (init?.method ?? "GET").toUpperCase() === method;
  });
}

export function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: "/", element: <p>Assess page</p> },
      { path: "/cases", element: <CasesPage /> },
      { path: "/cases/:caseId", element: <CasePage /> },
      { path: "/review/:caseId", element: <p>Review page</p> },
    ],
    { initialEntries: [path] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>,
  );
  return { ...view, router };
}

// Recorded sample-mode payloads (scripts/record_p18c_fixtures.py and the P14-A recordings).
export interface Recorded {
  case_id: string;
  vendor: string;
  record: Record<string, unknown> & { outcome: string; run_id: string };
  report: Record<string, unknown>;
  contracts: Array<Record<string, unknown> & { contract_id: string; state: string }>;
}

/** Routes that serve one recorded case with its trace and the questionnaire. */
export function caseRoutes(detail: Recorded, trace: unknown): Record<string, Handler> {
  return {
    [`GET /cases/${detail.case_id}`]: detail,
    [`GET /cases/${detail.case_id}/trace`]: trace,
    "GET /questions": load("p14b_questions.json"),
    "GET /health": load("p14a_health_offline.json"),
  };
}

/** Text nodes outside Technical details that read like codes (design §4; P18C-T2). */
export function codeLikeText(root: HTMLElement): string[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const found: string[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = (node.textContent ?? "").trim();
    if (!text) continue;
    if (node.parentElement?.closest("[data-testid='technical-tab']")) continue;
    if (/[A-Z_]{8,}/.test(text) || /^C\d\d/.test(text)) found.push(text);
  }
  return found;
}
