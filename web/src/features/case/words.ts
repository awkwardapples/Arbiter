// Reader-facing words for the case pages (design §4).
//
// The blocks between `<labels:…>` markers mirror app/labels.py, which the API does not serve yet.
// scripts/gates/p18c.py parses them and fails if they drift. Keep one `KEY: "text",` entry per line.
import { outcomeWord } from "../../ui/outcome";
import type { Confidence, ControlResult, Workload } from "./types";

// <labels:outcomes> app/labels.py _OUTCOMES (meanings)
export const OUTCOME_MEANINGS: Record<string, string> = {
  APPROVE: "Every required control passed, so the vendor can be onboarded.",
  APPROVE_WITH_CONDITIONS: "Approval stands only if the stated conditions are met.",
  REQUEST_INFO: "Required evidence is missing, so the vendor must reply before a decision.",
  ESCALATE: "A person must decide; the policy will not approve this case as it stands.",
  DECLINE: "A hard gate failed. Do not onboard this vendor.",
};
// </labels:outcomes>

// <labels:reasons> app/labels.py _REASONS
export const REASON_MEANINGS: Record<string, string> = {
  HARD_GATE_DECLINE: "A control that requires a decline has failed.",
  UNTRUSTED_CONTENT_TAMPERING: "The vendor submission tried to change the assessment instructions.",
  CONTRADICTION: "The vendor's claim conflicts with a system of record.",
  HARD_GATE_ESCALATE: "A control that requires escalation has failed.",
  CONTROL_FAILED: "A required control failed.",
  EVIDENCE_MISSING: "A required control could not be verified.",
  LOW_CONFIDENCE_ABSTAIN: "The evidence is too thin to approve.",
  CONDITIONS: "Approval depends on a condition or a precedent exception.",
  ALL_REQUIRED_CONTROLS_MET: "Every required control passed.",
};
// </labels:reasons>

// <labels:systems> app/labels.py _SYSTEMS
export const SYSTEM_LABELS: Record<string, string> = {
  procurement: "Procurement (ERP)",
  clm: "Contract system (CLM)",
  itsm: "Service desk (ITSM)",
  grc_watchlist: "Sanctions watchlist (GRC)",
  trust_portal: "Vendor trust portal",
  cisa_kev: "CISA Known Exploited Vulnerabilities",
};
// </labels:systems>

// <labels:states> app/labels.py _STATE_WORDS
export const STATE_WORDS: Record<string, string> = {
  TRUE: "met",
  FALSE: "not met",
  UNKNOWN: "unverified",
};
// </labels:states>

const ROLE_WORDS: Record<string, string> = {
  tprm_analyst: "TPRM analyst",
  tprm_lead: "TPRM lead",
  business_owner: "business owner",
  vendor: "the vendor",
};

const CAPABILITY_WORDS: Record<string, string> = {
  "outbox.email.draft": "email draft",
  "itsm.ticket.create": "service-desk ticket",
  "procurement.status.update": "procurement status change",
};

const CONTRACT_STATE_WORDS: Record<string, string> = {
  issued: "Issued, not yet run",
  pending_approval: "Waiting for approval",
  approved: "Approved",
  executed: "Done",
  rejected: "Rejected",
  expired: "Expired",
};

// app/policy/engine.py _failed_criteria
const PRECEDENT_CRITERIA: Record<string, string> = {
  mitigation_fact: "the mitigation is not verified",
  reviewer_authority: "the reviewer's role is below the required authority",
  precedent_age: "the precedent is older than the 365-day window",
  retrieval_quality: "memory confidence or relevance is below the threshold",
  tier_risk: "this case's risk tier is higher than the precedent's",
};

const CHECK_WORDS: Record<string, string> = {
  policy_hash: "the policy file's hash",
  record_hash: "the decision record's hash",
  contract_signatures: "the contract signatures",
};

const REVIEW_DIFF_WORDS: Record<string, string> = {
  "review.record": "the reviewed record",
  "review.decision": "the review's decision",
  "review.run_id": "the review's run",
  "review.record_hash": "the reviewed record's hash",
  "review.role": "the reviewer's authority",
};

const spaced = (code: string) => code.replace(/[._]+/g, " ").trim();

export const outcomeMeaning = (outcome: string) => OUTCOME_MEANINGS[outcome] ?? "";
export const reasonMeaning = (code: string) => REASON_MEANINGS[code] ?? spaced(code).toLowerCase();
export const systemLabel = (system: string | null | undefined) => (system ? (SYSTEM_LABELS[system] ?? spaced(system)) : "");
export const stateWord = (state: string) => STATE_WORDS[state] ?? "unverified";
export const roleWord = (role: string) => ROLE_WORDS[role] ?? spaced(role);
export const contractStateWord = (state: string) => CONTRACT_STATE_WORDS[state] ?? spaced(state);
export const criterionWord = (code: string) => PRECEDENT_CRITERIA[code] ?? spaced(code);
export const factWords = (key: string) => spaced(key);

export function capabilityWord(contract: { tool_plan?: Array<{ capability: string }> }): string {
  const capability = contract.tool_plan?.[0]?.capability ?? "";
  return CAPABILITY_WORDS[capability] ?? "action";
}

/** One replay diff entry in words: `outcome`, `facts.<key>` or `review.<field>` (app/audit/replay.py). */
export function diffWord(entry: string): string {
  if (entry === "outcome") return "the outcome";
  if (entry.startsWith("facts.")) return `the fact “${spaced(entry.slice(6))}”`;
  return REVIEW_DIFF_WORDS[entry] ?? spaced(entry);
}

export const checkWord = (key: string) => CHECK_WORDS[key] ?? spaced(key);

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export function listWords(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** "Confidence 75%: one control unverified (current SOC 2 or ISO 27001)". Controls by title, never by code. */
export function confidenceSentence(confidence: Confidence, controls: ControlResult[]): string {
  const pct = Math.round((confidence.value ?? 0) * 100);
  const unknown = confidence.unknown_controls ?? [];
  if (!unknown.length) return `Confidence ${pct}%: every required control is verified`;
  const titles = new Map(controls.map((c) => [c.control_id, c.title]));
  const named = unknown.map((id) => titles.get(id) ?? "an unnamed control");
  const count = unknown.length === 1 ? "one control" : `${unknown.length} controls`;
  return `Confidence ${pct}%: ${count} unverified (${listWords(named)})`;
}

/** The measured workload in one sentence, from the workload fields and nothing else (ui/labels_ui.py). */
export function workloadSentence(workload: Workload): string {
  const systems = workload.systems_queried?.length ?? 0;
  const found = workload.contradictions ? `${plural(workload.contradictions, "contradiction")} found` : "no contradictions found";
  const calls = workload.model_calls ?? 0;
  const family = (workload.models ?? []).some((m) => m.toLowerCase().includes("nemotron")) ? "Nemotron call" : "model call";
  const models = calls === 0 ? "no model calls (offline fallback)" : plural(calls, family);
  return (
    `Checked ${plural(systems, "system")}, ${plural(workload.queries ?? 0, "query", "queries")}, ` +
    `${plural(workload.answers_read ?? 0, "answer")}, ${plural(workload.documents_read ?? 0, "document")}, ` +
    `${found}, in ${Math.round(workload.elapsed_seconds ?? 0)} s with ${models}.`
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function parse(iso: string): Date | null {
  const date = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "24 Oct 2026" in UTC. */
export function dayWords(iso: string | null | undefined): string {
  const date = iso ? parse(iso) : null;
  if (!date) return "";
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

/** "24 Oct 2026 00:39 UTC". */
export function timeWords(iso: string | null | undefined): string {
  const date = iso ? parse(iso) : null;
  if (!date) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${dayWords(iso)} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

/** "3 hours ago", relative to `now`. */
export function relativeWords(iso: string, now: Date = new Date()): string {
  const date = parse(iso);
  if (!date) return "";
  const seconds = Math.round((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const steps: Array<[number, string]> = [
    [60, "minute"],
    [3600, "hour"],
    [86400, "day"],
    [604800, "week"],
  ];
  let unit = steps[0];
  for (const step of steps) if (seconds >= step[0]) unit = step;
  if (seconds >= 30 * 86400) return dayWords(iso);
  return `${plural(Math.floor(seconds / unit[0]), unit[1])} ago`;
}

export function outcomeWords(outcome: string): string {
  return outcomeWord(outcome);
}
