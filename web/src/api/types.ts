// Shapes the console reads. TraceEvent is generated from docs/trace_schema.json (npm run gen:trace);
// the rest mirror docs/spec/release3/P18A_STREAM_API.md §3 until schema.d.ts carries those routes.
import type { TraceEvent as GeneratedTraceEvent } from "./trace";

export type TraceEvent = GeneratedTraceEvent;
export type RunMode = Record<string, string>;

export interface Health {
  status: string;
  mode: RunMode;
  data?: Record<string, unknown> | null;
  provider?: Record<string, unknown> | null;
  hmem_records?: number | null;
  audit_chain_length?: number;
}

export interface Vendor {
  vendor_id: string;
  legal_name: string;
  category?: string | null;
  criticality?: string | null;
  onboarding_status?: string | null;
}

export interface RunStarted {
  run_id: string;
  events_url: string;
  status_url: string;
}

export interface RunStatus {
  run_id: string;
  state: "running" | "done" | "error";
  n_events: number;
  started_at: string;
  finished_at?: string | null;
  response?: Record<string, unknown> | null;
  error?: string | null;
}

export type RecordingKind = "live_example" | "live_eval" | "live_session" | "sample_example";

export interface RecordingMeta {
  run_id: string;
  kind: RecordingKind | string;
  path: string;
  case_id: string | null;
  vendor_name: string | null;
  outcome: string | null;
  duration_s: number | null;
  recorded_at: string | null;
  mode: RunMode | null;
  model_ids: string[];
  n_events: number;
  n_model_calls: number;
  n_fallbacks: number;
  n_queries: number;
  failed?: boolean;
}

export interface Recording {
  meta: RecordingMeta;
  events: TraceEvent[];
}

export interface RegistryQuery {
  id: string;
  description: string;
  systems: string[];
  control_ids?: string[];
  params?: string[];
  sql?: string | null;
}

export interface AgentInfo {
  name: string;
  trace_name: string;
  kind: string;
  lane: string;
  can: string;
  cannot: string;
}

export interface CaseDetail {
  case_id: string;
  vendor: string;
  status: string;
  record: { outcome: string; tier: string; residual_risk: number } & Record<string, unknown>;
  report: { summary: string; brief?: { headline: string } | null } & Record<string, unknown>;
  trace_path: string;
}
