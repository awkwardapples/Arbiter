// Behaviour strip counters, exactly as P18B_RUN_VIEW.md §5 defines them.
import type { TraceEvent } from "../api/types";
import type { Counters } from "./types";

export const COUNTER_KEYS = ["critiques", "sent_back", "retries_fallbacks", "shared_context", "model_calls", "zetaris", "mirror"] as const;
export type CounterKey = (typeof COUNTER_KEYS)[number];

export function emptyCounters(): Counters {
  return { critiques: 0, sent_back: 0, retries_fallbacks: 0, shared_context: 0, model_calls: 0, zetaris: 0, mirror: 0 };
}

/** Which counters one event adds to. The Activity filter uses the same test. */
export function countersFor(event: TraceEvent): CounterKey[] {
  const out: CounterKey[] = [];
  const { action, status } = event;
  if (action === "critique" || action === "evaluate" || action === "challenge") out.push("critiques");
  if ((action === "evaluate" && status === "needs_revision") || action === "request_replan") out.push("sent_back");
  const retryish = status === "fallback" || status === "retrying" || (event.retry_count ?? 0) > 0;
  if ((action === "model_call" || action.startsWith("query")) && retryish) out.push("retries_fallbacks");
  if (action === "usl_catalogue" || action === "memory_check" || action === "retrieve_precedents") out.push("shared_context");
  if (action === "model_call" && event.model) out.push("model_calls");
  if (action === "query_zetaris") out.push("zetaris");
  if (action === "query_run" && event.backend === "duckdb") out.push("mirror");
  return out;
}

export function addCounters(counters: Counters, event: TraceEvent): Counters {
  const keys = countersFor(event);
  if (!keys.length) return counters;
  const next = { ...counters };
  for (const key of keys) next[key] += 1;
  return next;
}
