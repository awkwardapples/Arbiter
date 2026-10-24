import type { TraceEvent } from "../api/types";

export type NodeKind = "agent" | "source" | "vendor" | "gate" | "engine" | "model" | "ruling" | "clash";
export type RingState = "idle" | "active" | "done" | "fallback" | "failed";
export type Tone = "record" | "claim" | "reason" | "clash" | "ink" | "plain";
export type EdgeType = "forward" | "sendback" | "replan" | "thread";

export interface BenchNode {
  id: string;
  kind: NodeKind;
  label: string;
  role: string;
  ring: RingState;
  count: number;
  countNoun: string;
  fellBack: boolean;
  note: string | null;
  firstIndex: number;
  eventIdx: number[];
}

export interface BenchEdge {
  id: string;
  from: string;
  to: string;
  type: EdgeType;
  tone: Tone;
  count: number;
  lastLabel: string;
  lastIndex: number;
  lastLatencyMs: number | null;
  loopTotal: number | null;
  eventIdx: number[];
}

export interface ClashItem {
  key?: string;
  control?: string;
  vendorValue?: string;
  recordValue?: string;
  system?: string;
  recordKey?: string;
  text: string;
  fromEvent: number;
}

export interface InFlight {
  agent: string;
  purpose: string | null;
  route: string | null;
  startedAt: string;
  index: number;
}

export interface Counters {
  critiques: number;
  sent_back: number;
  retries_fallbacks: number;
  shared_context: number;
  model_calls: number;
  zetaris: number;
  mirror: number;
}

export const STAGE_NAMES = ["Intake", "Plan", "Gather", "Evaluate", "Decide", "Memory", "Challenge", "Report", "Contract", "Execute", "Done"] as const;
export type StageName = (typeof STAGE_NAMES)[number];

export interface Stage {
  name: StageName;
  visits: number;
  escalated: boolean;
}

export interface PolicyRuling {
  outcome: string;
  tier: string | null;
  failing: string[];
  unknown: string[];
  index: number;
}

export interface RunState {
  runId: string | null;
  caseId: string | null;
  mode: Record<string, string> | null;
  startedAt: string | null;
  lastAt: string | null;
  nodes: Record<string, BenchNode>;
  edges: Record<string, BenchEdge>;
  activeNode: string | null;
  clash: ClashItem[];
  stages: Stage[];
  currentStage: StageName | null;
  safeEscalate: boolean;
  inFlight: InFlight[];
  counters: Counters;
  fallbacks: number;
  coerced: boolean;
  policy: PolicyRuling | null;
  /** Scout guard tallies per vendor node, for the guard edge labels. */
  guard: Record<string, { screened: number; passed: number; blocked: number; topScore: number }>;
  outcome: { outcome: string; seconds: number | null; index: number } | null;
  /** Index of the event each activity line came from, plus the event's stage at the time. */
  stageOf: (StageName | null)[];
  index: number;
  events: TraceEvent[];
}
