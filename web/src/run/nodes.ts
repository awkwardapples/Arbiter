// The bench nodes of design §7.1: label, second line and kind. Data-source nodes come from registry.ts.
import type { NodeKind } from "./types";

export interface NodeDef {
  kind: NodeKind;
  label: string;
  role: string;
  noun: string;
}

export const NODE_DEFS: Record<string, NodeDef> = {
  planner: { kind: "agent", label: "Planner", role: "Chooses what to check", noun: "plans" },
  evidence: { kind: "agent", label: "Evidence", role: "Gathers and extracts claims", noun: "claims" },
  evaluator: { kind: "agent", label: "Evaluator", role: "Checks claims against records", noun: "checks" },
  challenger: { kind: "agent", label: "Challenger", role: "Attacks the decision", noun: "challenges" },
  guard: { kind: "gate", label: "Scout guard", role: "Screens vendor text", noun: "screened" },
  usl: { kind: "source", label: "USL vendor_risk", role: "Zetaris semantic layer", noun: "queries" },
  engine: { kind: "engine", label: "Meterless Nightshift", role: "Routes every model call", noun: "calls" },
  policy: { kind: "ruling", label: "Policy engine", role: "Decides; never a model", noun: "rulings" },
  memory: { kind: "ruling", label: "Memory (H-MEM)", role: "Lead-approved precedents", noun: "lookups" },
  reporter: { kind: "ruling", label: "Reporter", role: "Writes the brief", noun: "briefs" },
  contract: { kind: "ruling", label: "Signed contract", role: "Scout execution contract", noun: "contracts" },
  outcome: { kind: "ruling", label: "The ruling", role: "", noun: "" },
  clash: { kind: "clash", label: "Contradiction", role: "Claim and record disagree", noun: "found" },
  "vendor.answers": { kind: "vendor", label: "Questionnaire answers", role: "The vendor's word", noun: "queries" },
  "vendor.documents": { kind: "vendor", label: "Documents", role: "The vendor's word", noun: "queries" },
  "vendor.components": { kind: "vendor", label: "Declared software", role: "The vendor's word", noun: "queries" },
};

const AGENT_NODES: Record<string, string> = {
  PlannerAgent: "planner",
  EvidenceAgent: "evidence",
  EvaluatorAgent: "evaluator",
  ChallengerAgent: "challenger",
  ReporterAgent: "reporter",
  PolicyEngine: "policy",
  MemoryKeeper: "memory",
  ActionExecutor: "contract",
  ScoutGuard: "guard",
};

export function nodeForAgent(name: string | null | undefined): string | null {
  return name ? (AGENT_NODES[name] ?? null) : null;
}

/** Kind colour as a CSS variable, for rings, edges and the glow. */
export const KIND_COLOR: Record<NodeKind, string> = {
  agent: "var(--color-ink)",
  source: "var(--color-record)",
  vendor: "var(--color-claim)",
  gate: "var(--color-claim)",
  engine: "var(--color-reason)",
  model: "var(--color-reason)",
  ruling: "var(--color-ink)",
  clash: "var(--color-clash)",
};
