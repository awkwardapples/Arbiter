// Fetch wrapper for the Arbiter API. Same origin by default; VITE_API_BASE overrides it.

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail?: unknown;

  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

interface ErrorShape {
  error?: { type?: string; message?: string };
  detail?: unknown;
}

function describeFailure(status: number, body: ErrorShape | null): ApiError {
  if (body?.error?.message) return new ApiError(status, body.error.type ?? "error", body.error.message, body);
  if (status === 404) return new ApiError(status, "not_found", "The API has no such resource.", body?.detail);
  if (typeof body?.detail === "string") return new ApiError(status, "error", body.detail, body.detail);
  return new ApiError(status, "error", `The API answered with HTTP ${status}.`, body?.detail);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { accept: "application/json", ...(init.body ? { "content-type": "application/json" } : {}), ...init.headers },
    });
  } catch {
    throw new ApiError(0, "network", "Could not reach the Arbiter API. Is `python run.py serve` running?");
  }
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!response.ok) throw describeFailure(response.status, body as ErrorShape | null);
  return body as T;
}

export const api = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, payload: unknown, init?: RequestInit) =>
    request<T>(path, { ...init, method: "POST", body: JSON.stringify(payload) }),
};

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
