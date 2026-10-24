// One pure reducer for live, paced and recorded playback (design §6, §7). It never throws: an event it
// does not understand only reaches the activity feed.
import type { TraceEvent } from "../api/types";
import { addCounters, emptyCounters } from "./counters";
import { describe, modelLabel } from "./describe";
import { NODE_DEFS, nodeForAgent } from "./nodes";
import { completeSummary, contradictionsIn, gaps, int, kv, list, plural, sentenceCase, transition } from "./parse";
import { queryEvidenceWords, type Registry, sourceNode, systemLabel, targetsForQuery, VENDOR_NODES } from "./registry";
import { countsAsVisit, initialStages, stageFor } from "./stages";
import type { BenchEdge, BenchNode, EdgeType, NodeKind, RunState, Tone } from "./types";

/** Every TraceEvent field the reducer reads; a test checks each against the generated type. */
export const FIELDS_READ = [
  "timestamp",
  "run_id",
  "agent_name",
  "action",
  "status",
  "target_agent",
  "input_summary",
  "output_summary",
  "model",
  "provider",
  "provider_meta",
  "purpose",
  "route",
  "backend",
  "query_id",
  "latency_ms",
  "retry_count",
  "rows",
  "mode",
] as const;

/** Evaluator → Planner loops and Challenger re-plans are bounded (AGENTS.md invariant 11). */
const MAX_SENDBACKS = 2;
const MAX_REPLANS = 1;

export function initialState(): RunState {
  return {
    runId: null,
    caseId: null,
    mode: null,
    startedAt: null,
    lastAt: null,
    nodes: {},
    edges: {},
    activeNode: null,
    clash: [],
    stages: initialStages(),
    currentStage: null,
    safeEscalate: false,
    inFlight: [],
    counters: emptyCounters(),
    fallbacks: 0,
    coerced: false,
    policy: null,
    outcome: null,
    guard: {},
    stageOf: [],
    index: 0,
    events: [],
  };
}

type Draft = RunState;

function offline(s: Draft): boolean {
  return s.mode?.llm === "offline";
}

function ensure(s: Draft, id: string, i: number, override?: Partial<BenchNode>): BenchNode {
  const existing = s.nodes[id];
  if (existing) return existing;
  const def = NODE_DEFS[id];
  let kind: NodeKind = def?.kind ?? (id.startsWith("vendor.") ? "vendor" : id.startsWith("rec.") ? "source" : "agent");
  let label = def?.label ?? id;
  let role = def?.role ?? "";
  if (id === "engine" && offline(s)) {
    label = "Deterministic fallback (no model call)";
    role = "Sample mode: no model is called";
  }
  if (id === "usl" && s.mode?.data === "duckdb") {
    label = "DuckDB mirror";
    role = "Sample-mode copy of the records";
  }
  if (id.startsWith("model:")) kind = "model";
  const node: BenchNode = {
    id,
    kind,
    label,
    role,
    ring: "idle",
    count: 0,
    countNoun: def?.noun ?? "events",
    fellBack: false,
    note: null,
    firstIndex: i,
    eventIdx: [],
    ...override,
  };
  s.nodes = { ...s.nodes, [id]: node };
  return node;
}

function patch(s: Draft, id: string, change: Partial<BenchNode>): void {
  s.nodes = { ...s.nodes, [id]: { ...s.nodes[id], ...change } };
}

/** The node an event touches. It becomes the one active node unless it is a still node. */
function touch(s: Draft, id: string, i: number, opts: { activate?: boolean; count?: number | "inc" } = {}): void {
  const node = ensure(s, id, i);
  const sticky = node.ring === "fallback" || node.ring === "failed";
  const still = id === "engine" && offline(s);
  const change: Partial<BenchNode> = { eventIdx: node.eventIdx.includes(i) ? node.eventIdx : [...node.eventIdx, i] };
  if (opts.count === "inc") change.count = node.count + 1;
  else if (typeof opts.count === "number") change.count = opts.count;
  const activate = opts.activate ?? true;
  if (activate && !still) {
    const prev = s.activeNode;
    if (prev && prev !== id && s.nodes[prev]?.ring === "active") patch(s, prev, { ring: "done" });
    s.activeNode = id;
    if (!sticky) change.ring = "active";
  } else if (!sticky && node.ring === "idle" && !still) {
    change.ring = "done";
  }
  patch(s, id, change);
}

function mark(s: Draft, id: string, ring: "fallback" | "failed", note?: string): void {
  if (!s.nodes[id]) return;
  patch(s, id, { ring, fellBack: ring === "fallback" || s.nodes[id].fellBack, note: note ?? s.nodes[id].note });
}

function link(
  s: Draft,
  from: string,
  to: string,
  type: EdgeType,
  tone: Tone,
  label: string,
  i: number,
  latency: number | null = null,
  loopTotal: number | null = null,
): void {
  const id = `${from}->${to}:${type}`;
  const prev = s.edges[id];
  const edge: BenchEdge = {
    id,
    from,
    to,
    type,
    tone,
    count: (prev?.count ?? 0) + 1,
    lastLabel: label,
    lastIndex: i,
    lastLatencyMs: latency,
    loopTotal: loopTotal ?? prev?.loopTotal ?? null,
    eventIdx: [...(prev?.eventIdx ?? []), i],
  };
  s.edges = { ...s.edges, [id]: edge };
}

function settle(s: Draft): void {
  if (s.activeNode && s.nodes[s.activeNode]?.ring === "active") patch(s, s.activeNode, { ring: "done" });
  s.activeNode = null;
}

function onTransition(s: Draft, e: TraceEvent, i: number): void {
  const t = transition(e.output_summary);
  if (!t) return;
  if (t.to === "SAFE_ESCALATE") s.safeEscalate = true;
  const stage = stageFor(t.to);
  if (!stage) return;
  s.stages = s.stages.map((st) =>
    st.name === stage ? { ...st, visits: st.visits + (countsAsVisit(t.to) ? 1 : 0), escalated: st.escalated || s.safeEscalate } : st,
  );
  s.currentStage = stage;
  if (t.to === "DECIDE_1") touch(s, "policy", i);
}

function onModel(s: Draft, e: TraceEvent, i: number, agentNode: string | null): void {
  const meta = (e.provider_meta ?? {}) as Record<string, unknown>;
  if (meta["app_policy.mode_coerced"] === "True") s.coerced = true;
  if (agentNode) touch(s, agentNode, i, { activate: e.action === "model_request" });
  ensure(s, "engine", i);
  if (e.action === "model_request") {
    s.inFlight = [...s.inFlight, { agent: e.agent_name, purpose: e.purpose ?? null, route: e.route ?? null, startedAt: e.timestamp, index: i }];
    touch(s, "engine", i);
    if (agentNode) link(s, agentNode, "engine", "forward", "reason", describe(e).text, i);
    return;
  }
  const waiting = s.inFlight.findIndex((f) => f.agent === e.agent_name && (!f.purpose || f.purpose === e.purpose));
  if (waiting >= 0) s.inFlight = s.inFlight.filter((_, k) => k !== waiting);
  touch(s, "engine", i, { count: "inc" });
  if (s.coerced) patch(s, "engine", { note: "Lane coerced to auto by a Nightshift app rule" });
  const failed = e.status !== "success";
  if (agentNode) link(s, agentNode, "engine", "forward", failed ? "clash" : "reason", describe(e).text, i, e.latency_ms ?? null);
  if (e.model) {
    const id = `model:${e.model}`;
    ensure(s, id, i, { label: modelLabel(e), role: e.model.split("/")[0] || "model" });
    touch(s, id, i, { count: "inc" });
    link(s, "engine", id, "forward", "reason", describe(e).text, i, e.latency_ms ?? null);
  }
  if (failed && agentNode) mark(s, agentNode, "fallback", "fell back");
}

function onQuery(s: Draft, e: TraceEvent, i: number, agentNode: string | null, registry: Registry): void {
  const queryId = e.query_id ?? kv(e.input_summary).query_id ?? null;
  const backend = e.backend ?? kv(e.output_summary).backend ?? null;
  ensure(s, "usl", i, backend === "duckdb" ? { label: "DuckDB mirror", role: "Sample-mode copy of the records" } : undefined);
  touch(s, "usl", i, { activate: false, count: "inc" });
  const failed = e.status !== "success";
  const text = describe(e, registry).text;
  const isBench = agentNode !== null && NODE_DEFS[agentNode]?.kind === "agent";
  if (isBench) touch(s, agentNode, i);
  for (const target of targetsForQuery(registry, queryId)) {
    ensure(s, target.id, i, { label: target.label, role: target.role, kind: target.vendor ? "vendor" : "source" });
    touch(s, target.id, i, { activate: false, count: "inc" });
    if (failed) mark(s, target.id, "failed");
    if (isBench) link(s, agentNode, target.id, "forward", failed ? "clash" : target.vendor ? "claim" : "record", text, i, e.latency_ms ?? null);
  }
}

function onGuard(s: Draft, e: TraceEvent, i: number): void {
  const segment = kv(e.input_summary).segment_id ?? "";
  const vendor = segment.startsWith("doc-") ? VENDOR_NODES.documents : VENDOR_NODES.answers;
  const kindWord = segment.startsWith("doc-") ? "document" : "answer";
  const blocked = e.status === "blocked" || kv(e.output_summary).level === "block";
  const score = Number.parseFloat(kv(e.output_summary).score ?? "0") || 0;
  const prev = s.guard[vendor.id] ?? { screened: 0, passed: 0, blocked: 0, topScore: 0 };
  const stats = {
    screened: prev.screened + 1,
    passed: prev.passed + (blocked ? 0 : 1),
    blocked: prev.blocked + (blocked ? 1 : 0),
    topScore: blocked ? Math.max(prev.topScore, score) : prev.topScore,
  };
  s.guard = { ...s.guard, [vendor.id]: stats };
  ensure(s, vendor.id, i, { label: vendor.label, role: "The vendor's word", kind: "vendor" });
  touch(s, vendor.id, i, { activate: false });
  touch(s, "guard", i, { count: "inc" });
  const label = stats.blocked
    ? `${plural(stats.blocked, kindWord)} blocked (score ${stats.topScore.toFixed(2)}), ${stats.passed} passed`
    : `${plural(stats.screened, kindWord)} screened, ${stats.passed} passed`;
  link(s, vendor.id, "guard", "forward", stats.blocked ? "clash" : "claim", label, i);
  if (blocked) mark(s, vendor.id, "failed");
  if (s.nodes.evidence || !blocked) {
    ensure(s, "evidence", i);
    link(s, "guard", "evidence", "forward", "claim", label, i);
  }
}

function onEvaluate(s: Draft, e: TraceEvent, i: number, registry: Registry): void {
  touch(s, "evaluator", i, { count: "inc" });
  if (e.status === "needs_revision") {
    const pairs = gaps(e.output_summary);
    const words = [...new Set(pairs.flatMap((p) => queryEvidenceWords(registry, p.query)))];
    const codes = [...new Set(pairs.map((p) => p.control))];
    const sent = (s.edges["evaluator->planner:sendback"]?.count ?? 0) + 1;
    const what = words.length ? `Sent back for evidence from ${joinWords(words)}` : "Sent back for more evidence";
    ensure(s, "planner", i);
    link(s, "evaluator", "planner", "sendback", "clash", `${what}${codes.length ? ` (${codes.join(", ")})` : ""}. Loop ${sent} of ${MAX_SENDBACKS}`, i, null, MAX_SENDBACKS);
    return;
  }
  const n = contradictionsIn(e.output_summary);
  if (n && n > 0 && !s.clash.some((c) => c.vendorValue !== undefined)) {
    // Traces from before P18-A carry only the count; the values stay in the case record.
    const text = `${plural(n, "contradiction")} found; details in the case record`;
    s.clash = [{ text, fromEvent: i }];
    ensure(s, "clash", i);
    touch(s, "clash", i, { activate: false, count: n });
  }
  if (e.target_agent === "PolicyEngine") {
    ensure(s, "policy", i);
    link(s, "evaluator", "policy", "forward", "ink", e.output_summary.replace(/^sufficient:\s*/, ""), i);
  }
}

function onContradiction(s: Draft, e: TraceEvent, i: number): void {
  const input = kv(e.input_summary);
  const out = kv(e.output_summary);
  const item = {
    key: input.key,
    control: input.control,
    vendorValue: out.vendor,
    recordValue: out.record,
    system: out.system,
    recordKey: out.record_key,
    text: describe(e).text,
    fromEvent: i,
  };
  const existing = s.clash.filter((c) => c.vendorValue !== undefined);
  if (existing.some((c) => c.key === item.key && c.recordKey === item.recordKey)) return;
  s.clash = [...existing, item];
  touch(s, "evaluator", i);
  ensure(s, "clash", i);
  touch(s, "clash", i, { activate: false, count: s.clash.length });
  const topic = sentenceCase((item.key ?? "value").split(".")[0]);
  const record = item.recordKey?.split("=").pop() ?? "";
  const label = `${topic}: vendor says ${item.vendorValue ?? "?"}, ${systemLabel(item.system ?? "")} ${record} says ${item.recordValue ?? "?"}`.replace(/\s+/g, " ");
  ensure(s, VENDOR_NODES.answers.id, i, { label: VENDOR_NODES.answers.label, role: "The vendor's word", kind: "vendor" });
  link(s, VENDOR_NODES.answers.id, "clash", "thread", "clash", label, i);
  if (item.system) {
    const src = sourceNode(item.system);
    ensure(s, src.id, i, { label: src.label, role: src.role, kind: "source" });
    link(s, src.id, "clash", "thread", "clash", label, i);
  }
}

function joinWords(words: string[]): string {
  if (words.length <= 1) return words.join("");
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

function forward(s: Draft, from: string | null, e: TraceEvent, i: number, tone: Tone = "ink"): void {
  const to = nodeForAgent(e.target_agent);
  if (!from || !to || from === to) return;
  ensure(s, to, i);
  link(s, from, to, "forward", tone, describe(e).text, i);
}

function apply(s: Draft, e: TraceEvent, i: number, registry: Registry): void {
  const agentNode = nodeForAgent(e.agent_name);
  switch (e.action) {
    case "start_run":
      s.caseId = kv(e.input_summary).case_id ?? s.caseId;
      s.stages = s.stages.map((st) => (st.name === "Intake" ? { ...st, visits: st.visits + 1 } : st));
      s.currentStage = "Intake";
      if (offline(s)) ensure(s, "engine", i);
      return;
    case "transition":
      onTransition(s, e, i);
      return;
    case "usl_catalogue":
      touch(s, "planner", i);
      ensure(s, "usl", i);
      touch(s, "usl", i, { activate: false });
      link(s, "planner", "usl", "forward", "record", describe(e).text, i);
      return;
    case "model_request":
    case "model_call":
      onModel(s, e, i, agentNode);
      return;
    case "query_run":
      onQuery(s, e, i, agentNode, registry);
      return;
    case "query_zetaris":
      return;
    case "guard_segment":
      onGuard(s, e, i);
      return;
    case "evaluate":
      onEvaluate(s, e, i, registry);
      return;
    case "contradiction_found":
      onContradiction(s, e, i);
      return;
    case "decide": {
      const out = kv(e.output_summary);
      s.policy = { outcome: out.outcome ?? "", tier: out.tier ?? null, failing: list(out.failing), unknown: list(out.unknown), index: i };
      touch(s, "policy", i, { count: "inc" });
      return;
    }
    case "redecide": {
      touch(s, "policy", i, { count: "inc" });
      const outcome = kv(e.output_summary).outcome;
      if (outcome) s.policy = { ...(s.policy ?? { tier: null, failing: [], unknown: [] }), outcome, index: i };
      forward(s, "policy", e, i);
      return;
    }
    case "memory_check":
    case "retrieve_precedents":
    case "precedent_applied":
    case "precedent_rejected":
      touch(s, "memory", i, { count: e.action === "memory_check" || e.action === "retrieve_precedents" ? "inc" : undefined });
      if (s.nodes.policy) link(s, "policy", "memory", "forward", "ink", describe(e).text, i);
      return;
    case "request_replan": {
      touch(s, "challenger", i, { count: "inc" });
      ensure(s, "planner", i);
      const n = (s.edges["challenger->planner:replan"]?.count ?? 0) + 1;
      const reason = describe(e).detail ?? "";
      link(s, "challenger", "planner", "replan", "clash", `${describe(e).text.replace(/\.$/, "")}. Re-plan ${n} of ${MAX_REPLANS}${reason ? ` (${reason})` : ""}`, i, null, MAX_REPLANS);
      return;
    }
    case "complete_run": {
      const done = completeSummary(e.output_summary);
      settle(s);
      s.inFlight = [];
      if (done) {
        s.outcome = { ...done, index: i };
        ensure(s, "outcome", i, { role: sentenceCase(done.outcome) });
        touch(s, "outcome", i, { activate: false });
        if (s.nodes.contract) link(s, "contract", "outcome", "forward", "ink", describe(e).text, i);
      }
      return;
    }
    default:
      break;
  }
  if (!agentNode) return;
  const countable = ["plan", "extract_claims", "critique", "challenge", "report", "execute_action"].includes(e.action);
  const claims = e.action === "extract_claims" ? int(/^(\d+)\s+claims/.exec(e.output_summary)?.[1]) : null;
  touch(s, agentNode, i, { count: claims ?? (countable ? "inc" : undefined) });
  if (e.status === "fallback" || e.action.endsWith("_fallback")) mark(s, agentNode, "fallback", "fell back");
  else if (e.status === "error" || e.status === "blocked") mark(s, agentNode, "failed");
  if (e.action === "execute_action" && e.status === "pending_approval") patch(s, agentNode, { note: "awaiting approval" });
  if (e.target_agent && e.status !== "needs_revision") forward(s, agentNode, e, i);
}

/** Pure: returns a new state; the input is never mutated. Unknown events change only the feed. */
export function reduce(state: RunState, event: TraceEvent, registry: Registry): RunState {
  const s: Draft = { ...state };
  const i = state.index;
  s.events = [...state.events, event];
  s.index = i + 1;
  s.runId ??= event.run_id ?? null;
  s.startedAt ??= event.timestamp ?? null;
  s.lastAt = event.timestamp ?? s.lastAt;
  if (!s.mode && event.mode && typeof event.mode === "object") s.mode = event.mode as Record<string, string>;
  s.counters = addCounters(state.counters, event);
  if (event.status === "fallback") s.fallbacks = state.fallbacks + 1;
  try {
    apply(s, event, i, registry);
  } catch {
    // A malformed event still shows in the activity feed; the bench is left as it was.
    return { ...state, events: s.events, index: s.index, stageOf: [...state.stageOf, state.currentStage], counters: s.counters };
  }
  s.stageOf = [...state.stageOf, s.currentStage];
  return s;
}

export function replay(events: TraceEvent[], registry: Registry, upTo = events.length): RunState {
  let state = initialState();
  for (let k = 0; k < Math.min(upTo, events.length); k++) state = reduce(state, events[k], registry);
  return state;
}
