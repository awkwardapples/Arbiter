// Runtime validation of SSE payloads (design §11). Unknown fields pass through so newer events still render.
import { z } from "zod";
import type { TraceEvent } from "./types";

const nullableString = z.string().nullable().optional();
const nullableInt = z.number().nullable().optional();

export const traceEventSchema = z.looseObject({
  timestamp: z.string(),
  run_id: z.string(),
  trace_id: z.string(),
  span_id: z.string(),
  agent_name: z.string(),
  action: z.string(),
  input_summary: z.string(),
  output_summary: z.string(),
  status: z.string(),
  target_agent: nullableString,
  parent_span_id: nullableString,
  model: nullableString,
  provider: nullableString,
  route: nullableString,
  purpose: nullableString,
  backend: nullableString,
  query_id: nullableString,
  source_system: nullableString,
  loop: nullableString,
  latency_ms: nullableInt,
  retry_count: nullableInt,
  rows: nullableInt,
  iteration: nullableInt,
  tokens_in: nullableInt,
  tokens_out: nullableInt,
  confidence: z.number().nullable().optional(),
  mode: z.record(z.string(), z.string()).nullable().optional(),
  provider_meta: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const doneSchema = z.looseObject({
  run_id: z.string(),
  status: z.string(),
  case_id: z.string().nullable().optional(),
  outcome: z.string().nullable().optional(),
  execution_time_seconds: z.number().nullable().optional(),
  mode: z.record(z.string(), z.string()).nullable().optional(),
});

export const errorSchema = z.looseObject({ run_id: z.string().optional(), message: z.string() });

export type DoneEvent = z.infer<typeof doneSchema>;

export function parseTraceEvent(data: unknown): TraceEvent | null {
  const result = traceEventSchema.safeParse(data);
  return result.success ? (result.data as TraceEvent) : null;
}

export function parseDone(data: unknown): DoneEvent | null {
  const result = doneSchema.safeParse(data);
  return result.success ? result.data : null;
}

export function parseError(data: unknown): string | null {
  const result = errorSchema.safeParse(data);
  return result.success ? result.data.message : null;
}
