// Plain-English activity lines (design §8). Numbers come from the event; codes go in `detail`.
import type { TraceEvent } from "../api/types";
import { completeSummary, contradictionsIn, duration, gaps, int, kv, list, plural, seconds, sentenceCase, transition } from "./parse";
import { queryEvidenceWords, type Registry, systemLabel, targetsForQuery } from "./registry";
import { STAGE_WORDS, stageFor } from "./stages";
import type { Tone } from "./types";

export interface Line {
  text: string;
  detail?: string;
  tone: Tone;
  /** True when no specific sentence exists for this (agent, action) and the generic form was used. */
  generic: boolean;
}

const AGENT_WORDS: Record<string, { the: string; short: string }> = {
  PlannerAgent: { the: "the Planner", short: "Planner" },
  EvidenceAgent: { the: "Evidence", short: "Evidence" },
  EvaluatorAgent: { the: "the Evaluator", short: "Evaluator" },
  ChallengerAgent: { the: "the Challenger", short: "Challenger" },
  ReporterAgent: { the: "the Reporter", short: "Reporter" },
  PolicyEngine: { the: "the policy", short: "Policy engine" },
  MemoryKeeper: { the: "Memory", short: "Memory" },
  ActionExecutor: { the: "the action executor", short: "Action executor" },
  ScoutGuard: { the: "the Scout guard", short: "Scout guard" },
  Orchestrator: { the: "the orchestrator", short: "Orchestrator" },
  data: { the: "the data layer", short: "Data layer" },
};

export function agentWord(name: string, capital = false): string {
  const word = AGENT_WORDS[name]?.the ?? name;
  return capital ? word.charAt(0).toUpperCase() + word.slice(1) : word;
}

export function agentShort(name: string): string {
  return AGENT_WORDS[name]?.short ?? name;
}

const PURPOSE_WORDS: Record<string, string> = {
  plan: "a plan",
  extract: "the claims in the answers",
  critique: "a critique of the claims",
  challenge: "a challenge to the decision",
  report: "the brief",
};

const SCHEMA_WORDS: Record<string, string> = {
  PlanOut: "a valid plan",
  ClaimListOut: "a valid claim list",
  CritiqueOut: "a valid critique",
  ChallengeOut: "a valid challenge",
  BriefWording: "valid brief wording",
};

/** Challenger reason codes in words. Unknown codes are put in sentence case; the code stays in detail. */
const CHALLENGE_WORDS: Record<string, string> = {
  CHALLENGE_UNCORROBORATED_CLAIM: "an approval rests on a claim nothing corroborates",
  CHALLENGE_T1_UNCORROBORATED: "a tier T1 decision rests on a claim nothing corroborates",
};

const INTENT_WORDS: Record<string, string> = {
  approve: "approval",
  approve_with_conditions: "conditional approval",
  request_info: "information request",
  escalate: "escalation",
  decline: "decline",
};

export function modelLabel(event: TraceEvent): string {
  const meta = (event.provider_meta ?? {}) as Record<string, unknown>;
  const label = meta["winning_route.label"];
  if (typeof label === "string" && label) return label;
  return event.model ?? "the model";
}

function outcomeWords(code: string): string {
  return sentenceCase(code);
}

function backendWords(backend: string | null | undefined): string {
  if (backend === "zetaris") return "through Zetaris";
  if (backend === "duckdb") return "from the DuckDB mirror";
  return backend ? `through ${backend}` : "";
}

function queryLine(e: TraceEvent, registry: Registry | undefined): Line {
  const input = kv(e.input_summary);
  const out = kv(e.output_summary);
  const queryId = e.query_id ?? input.query_id ?? "";
  const rows = e.rows ?? int(out.rows) ?? 0;
  const all = registry ? targetsForQuery(registry, queryId) : [];
  // Name the specific system: a join through procurement is about the other system.
  const specificTargets = all.filter((t) => t.id !== "rec.procurement");
  const targets = specificTargets.length ? specificTargets : all;
  const labels = targets.map((t) => t.label);
  const where = labels.length ? (labels.length > 1 ? `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}` : labels[0]) : registry?.[queryId]?.description ?? "A registry query";
  const time = seconds(e.latency_ms);
  const via = backendWords(e.backend ?? out.backend);
  const failed = e.status !== "success";
  const text = failed
    ? `${where}: the query did not complete (${e.status}).`
    : `${where}: ${plural(rows, "row")}${time ? ` in ${time}` : ""}${via ? ` ${via}` : ""}.`;
  const request = out.zetaris_request_id ? `, request id ${out.zetaris_request_id.slice(0, 8)}…` : "";
  return { text, detail: `${queryId}${request}`, tone: failed ? "clash" : targets.some((t) => t.vendor) ? "claim" : "record", generic: false };
}

function modelCallLine(e: TraceEvent): Line {
  const who = agentWord(e.agent_name);
  const lane = e.route ?? kv(e.input_summary).route;
  if (e.status === "success") {
    const schema = /\((\w+)\)/.exec(e.output_summary)?.[1] ?? "";
    const result = SCHEMA_WORDS[schema] ?? "an answer";
    const time = seconds(e.latency_ms);
    const tokens = e.tokens_in && e.tokens_out ? `, ${e.tokens_in.toLocaleString("en-GB")} → ${e.tokens_out.toLocaleString("en-GB")} tokens` : "";
    const receipt = (e.provider_meta as Record<string, unknown> | null)?.receipt_id;
    return {
      text: `${modelLabel(e)} answered${time ? ` in ${time}` : ""} with ${result}.`,
      detail: `${lane ? `${lane} lane` : ""}${tokens}${typeof receipt === "string" ? `, receipt ${receipt}` : ""}`.replace(/^, /, ""),
      tone: "reason",
      generic: false,
    };
  }
  const http = /HTTP (\d{3})/.exec(e.output_summary)?.[1];
  const timeout = /timeout|timed out/i.test(e.output_summary);
  const cause = http ? `Nightshift returned an error (HTTP ${http})` : timeout ? "Nightshift did not answer in time" : "The model call failed";
  return { text: `${cause}, so ${who} used its deterministic fallback.`, detail: e.output_summary.slice(0, 160), tone: "clash", generic: false };
}

function transitionLine(e: TraceEvent): Line {
  const t = transition(e.output_summary);
  if (!t) return { text: `The run moved on: ${e.output_summary}.`, tone: "plain", generic: false };
  if (t.to === "SAFE_ESCALATE") return { text: "The run stopped safely and escalated to a person.", detail: e.output_summary, tone: "clash", generic: false };
  const from = stageFor(t.from);
  const to = stageFor(t.to);
  const fromWord = from ? STAGE_WORDS[from] : sentenceCase(t.from).toLowerCase();
  const toWord = to ? STAGE_WORDS[to] : sentenceCase(t.to).toLowerCase();
  const queries = /\((\d+) quer/.exec(t.rest)?.[1];
  if (e.status === "needs_revision") {
    const codes = /gaps:\s*([A-Z0-9,]+)/.exec(t.rest)?.[1];
    return { text: `Back to ${toWord} to fill the gaps the Evaluator found.`, detail: codes ? `Gaps: ${codes.split(",").join(", ")}` : undefined, tone: "clash", generic: false };
  }
  const suffix = queries ? ` with ${plural(Number(queries), "query", "queries")}` : "";
  const escalated = e.status === "escalated" ? ", carrying an escalation" : "";
  return { text: `Moved from ${fromWord} to ${toWord}${suffix}${escalated}.`, tone: "plain", generic: false };
}

function evaluateLine(e: TraceEvent, registry: Registry | undefined): Line {
  if (e.status === "needs_revision") {
    const pairs = gaps(e.output_summary);
    const words = registry ? [...new Set(pairs.flatMap((p) => queryEvidenceWords(registry, p.query)))] : [];
    const codes = [...new Set(pairs.map((p) => p.control))];
    const what = words.length ? `it needs evidence from ${words.join(", ")}` : "more evidence is needed";
    return { text: `The Evaluator sent the plan back: ${what}.`, detail: codes.length ? `Controls ${codes.join(", ")}` : undefined, tone: "clash", generic: false };
  }
  const facts = /(\d+) facts/.exec(e.output_summary)?.[1];
  const n = contradictionsIn(e.output_summary) ?? 0;
  const tier = /tier (T\d)/.exec(e.output_summary)?.[1];
  const parts = [facts ? plural(Number(facts), "fact") : null, plural(n, "contradiction"), tier ? `tier ${tier}` : null].filter(Boolean);
  return { text: `The Evaluator found the evidence sufficient: ${parts.join(", ")}.`, tone: n ? "clash" : "plain", generic: false };
}

function specific(e: TraceEvent, registry: Registry | undefined): Omit<Line, "generic"> | null {
  const input = kv(e.input_summary);
  const out = kv(e.output_summary);
  const who = agentWord(e.agent_name, true);
  switch (e.action) {
    case "start_run":
      return { text: `Started the assessment of ${input.case_id ?? "a case"}${out.budget ? ` with a ${out.budget.replace(/s$/, " s")} budget` : ""}.`, tone: "plain" };
    case "complete_run": {
      const done = completeSummary(e.output_summary);
      if (!done) return null;
      return { text: `Decided ${outcomeWords(done.outcome)}${done.seconds !== null ? ` in ${duration(done.seconds)}` : ""}.`, tone: "ink" };
    }
    case "transition":
      return transitionLine(e);
    case "query_run":
      return queryLine(e, registry);
    case "query_zetaris": {
      const rows = e.rows ?? int(out.rows) ?? 0;
      const time = seconds(e.latency_ms);
      return { text: `Zetaris answered with ${plural(rows, "row")}${time ? ` in ${time}` : ""}.`, detail: `${input.query_id ?? ""}${out.zetaris_request_id ? `, request id ${out.zetaris_request_id}` : ""}`, tone: "record" };
    }
    case "usl_catalogue":
      return { text: `${who} read the semantic layer's model (${out.tokens ?? "?"} tokens).`, detail: input.usl_model_sha256 ? `sha256 ${input.usl_model_sha256.slice(0, 12)}…` : undefined, tone: "record" };
    case "model_request": {
      const purpose = PURPOSE_WORDS[e.purpose ?? input.purpose ?? ""] ?? "an answer";
      const lane = e.route ?? input.route;
      return { text: `${who} asked Nightshift for ${purpose}${lane ? ` (${lane} lane)` : ""}.`, detail: input.prompt_chars ? `${input.prompt_chars} prompt characters` : undefined, tone: "reason" };
    }
    case "model_call":
      return modelCallLine(e);
    case "plan_corrected": {
      const added = list(out["re-added"] ?? /re-added=(\S+)/.exec(e.output_summary)?.[1]);
      const dropped = list(out.dropped);
      if (!added.length && !dropped.length) return { text: "The policy checked the model's plan and changed nothing.", tone: "plain" };
      const parts = [added.length ? `re-added ${plural(added.length, "required check")} the model left out` : null, dropped.length ? `dropped ${plural(dropped.length, "query", "queries")} the registry does not allow` : null].filter(Boolean);
      return { text: `The policy ${parts.join(" and ")}.`, detail: [...added, ...dropped].join(", "), tone: "plain" };
    }
    case "plan": {
      const n = int(/^(\d+) quer/.exec(e.output_summary)?.[1]) ?? 0;
      return { text: `The Planner sent ${plural(n, "query", "queries")} to Evidence.`, detail: e.output_summary.split(":")[1]?.trim(), tone: "plain" };
    }
    case "plan_fallback":
    case "critique_fallback":
    case "extract_fallback":
      return { text: `${who} fell back to its deterministic logic after the model call failed.`, detail: e.output_summary, tone: "clash" };
    case "guard_segment": {
      const segment = input.segment_id ?? "";
      const kind = segment.startsWith("doc-") ? "document" : "answer";
      const ref = segment.replace(/^(ans|doc)-/, "");
      if (e.status === "blocked" || out.level === "block") return { text: `The Scout guard blocked a ${kind} (score ${out.score ?? "?"}).`, detail: ref, tone: "clash" };
      return { text: `The Scout guard screened a ${kind}: it passed.`, detail: ref, tone: "claim" };
    }
    case "extract_claims": {
      const m = /^(\d+) claims from (\d+) answers/.exec(e.output_summary);
      if (!m) return { text: `Evidence extracted claims: ${e.output_summary}.`, tone: "claim" };
      return { text: `Evidence extracted ${plural(Number(m[1]), "claim")} from ${plural(Number(m[2]), "answer")}, each with a quote.`, detail: /\(([^)]+)\)/.exec(e.output_summary)?.[1], tone: "claim" };
    }
    case "critique": {
      const down = list(out.downgraded).length;
      const discarded = int(out.discarded) ?? 0;
      return { text: `The Evaluator critiqued ${plural(int(input.claims) ?? 0, "claim")}: ${down ? `${down} downgraded` : "none downgraded"}, ${discarded ? `${discarded} discarded` : "none discarded"}.`, tone: "plain" };
    }
    case "evaluate":
      return evaluateLine(e, registry);
    case "contradiction_found": {
      const where = systemLabel(out.system ?? "") || "the record";
      return { text: `The vendor says ${out.vendor ?? "?"}; ${where} says ${out.record ?? "?"}.`, detail: [input.control, out.record_key].filter(Boolean).join(", "), tone: "clash" };
    }
    case "decide": {
      const failing = list(out.failing);
      const unknown = list(out.unknown);
      const tail = failing.length ? `: ${plural(failing.length, "control")} failed` : "";
      return {
        text: `The policy ruled ${outcomeWords(out.outcome ?? "")}${out.tier ? ` at tier ${out.tier}` : ""}${tail}.`,
        detail: [failing.length ? `Failing ${failing.join(", ")}` : null, unknown.length ? `unknown ${unknown.join(", ")}` : null].filter(Boolean).join("; ") || undefined,
        tone: "ink",
      };
    }
    case "redecide":
      return { text: `The policy ruled again with ${plural(int(input.precedents) ?? 0, "precedent")}: ${outcomeWords(out.outcome ?? "")}.`, tone: "ink" };
    case "memory_check": {
      const n = int(out.candidates) ?? 0;
      return { text: n ? `Memory found ${plural(n, "candidate precedent")} for the failing controls.` : "Memory found no lead-approved precedent for this case.", detail: input.failing && input.failing !== "-" ? `Failing ${input.failing}` : undefined, tone: "plain" };
    }
    case "retrieve_precedents":
      return { text: `Memory looked for precedents and found ${int(out.found) ?? 0}.`, detail: input.failing ? `Failing ${input.failing}` : undefined, tone: "plain" };
    case "precedent_applied":
      return { text: "Memory applied a lead-approved precedent.", detail: e.input_summary, tone: "plain" };
    case "precedent_rejected":
      return { text: `Memory set a precedent aside (${sentenceCase(e.output_summary).toLowerCase()}).`, detail: e.input_summary, tone: "clash" };
    case "challenge":
    case "request_replan": {
      const code = /(CHALLENGE_[A-Z0-9_]+)/.exec(e.output_summary)?.[1];
      const reason = code ? (CHALLENGE_WORDS[code] ?? sentenceCase(code.replace(/^CHALLENGE_/, "")).toLowerCase()) : null;
      if (e.action === "request_replan") return { text: `The Challenger asked for a re-plan: ${reason ?? "the decision needs more support"}.`, detail: code, tone: "clash" };
      if (e.status === "escalated") return { text: `The Challenger escalated the case: ${reason ?? "a person must decide"}.`, detail: code, tone: "ink" };
      return { text: "The Challenger accepted the decision.", detail: /source=(\S+)/.exec(e.output_summary)?.[1], tone: "plain" };
    }
    case "report": {
      const n = int(out.sentences);
      return { text: `The Reporter wrote the brief${n !== null ? ` (${plural(n, "sentence")})` : ""}.`, detail: out.generator, tone: "plain" };
    }
    case "execute_action": {
      const contract = input.contract ?? "";
      const short = contract.length > 8 ? `${contract.slice(0, 8)}…` : contract;
      const intent = INTENT_WORDS[(input.intent ?? "").split(".").pop() ?? ""] ?? "action";
      if (e.status === "pending_approval") return { text: `The ${intent} waits for the TPRM lead under signed contract ${short}.`, detail: contract, tone: "plain" };
      if (e.status === "success") return { text: `The ${intent} was written to the outbox under signed contract ${short}.`, detail: contract, tone: "plain" };
      return { text: `The ${intent} under signed contract ${short} did not run (${e.status}).`, detail: contract, tone: "clash" };
    }
    default:
      return null;
  }
}

export function describe(event: TraceEvent, registry?: Registry): Line {
  try {
    const line = specific(event, registry);
    if (line) return { ...line, generic: false };
  } catch {
    // fall through to the generic form
  }
  return { text: `${agentShort(event.agent_name)} ${event.action}: ${event.output_summary}`, tone: event.status === "success" ? "plain" : "clash", generic: true };
}
