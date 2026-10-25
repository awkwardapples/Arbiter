// Provider metadata is rendered from a whitelist only (design §11). Anything else never reaches the DOM.

export const PROVIDER_WHITELIST: ReadonlySet<string> = new Set([
  "requested_model",
  "routed_model",
  "receipt_id",
  "decision_id",
  "mode",
  "winning_route.label",
  "winning_route.model",
  "app_policy.requested_mode",
  "app_policy.routed_mode",
  "app_policy.mode_coerced",
  "cost.actual_usd",
  "no_think",
]);

function flatten(value: unknown, prefix: string, out: Record<string, string>): void {
  if (value === null || value === undefined) return;
  if (typeof value === "object" && !Array.isArray(value)) {
    for (const [key, inner] of Object.entries(value as Record<string, unknown>)) {
      flatten(inner, prefix ? `${prefix}.${key}` : key, out);
    }
    return;
  }
  if (PROVIDER_WHITELIST.has(prefix) && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
    out[prefix] = String(value);
  }
}

export function filterProviderMeta(meta: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (meta && typeof meta === "object") flatten(meta, "", out);
  return out;
}

/** A trace line safe to show raw: provider_meta passes through the same whitelist. */
export function safeTraceLine<T extends Record<string, unknown>>(event: T): T {
  if (!("provider_meta" in event) || event.provider_meta == null) return { ...event };
  return { ...event, provider_meta: filterProviderMeta(event.provider_meta) };
}
