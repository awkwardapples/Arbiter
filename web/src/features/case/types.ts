// The case routes' shapes, mirroring app/api/routes_cases.py, routes_contracts.py, app/audit/replay.py and
// app/schemas/{decision,report,evidence,contract}.py. 18b's api/types.ts carries only the fields the run view reads.

export type TriState = "TRUE" | "FALSE" | "UNKNOWN";

export interface QueueItem {
  case_id: string;
  vendor: string;
  outcome: string;
  tier: string;
  residual_risk: number;
  status: string;
  created: string;
}

export interface Provenance {
  kind?: string | null;
  system?: string | null;
  query_id?: string | null;
  record_key?: string | null;
  field?: string | null;
  quote?: string | null;
  answer_ref?: string | null;
  backend?: string | null;
  zetaris_request_id?: string | null;
}

export interface Fact {
  fact_id: string;
  control_id: string;
  key: string;
  value: unknown;
  state: TriState;
  provenance: Provenance[];
  derived_from_claims?: string[];
  dq_flags?: string[];
}

export interface ControlResult {
  control_id: string;
  title: string;
  required: boolean;
  state: TriState;
  fact_ids: string[];
  rule_id: string;
  weight: number;
  hard_gate?: string | null;
  exception_applied?: string | null;
  conditional?: boolean;
  condition_text?: string | null;
}

export interface Contradiction {
  key: string;
  control_id: string;
  claim_id: string;
  claim_value: unknown;
  sor_value: unknown;
  sor_provenance: Provenance;
  severity: string;
  resolved?: boolean;
}

export interface Counterfactual {
  control_id: string;
  from_state: TriState;
  to_state: TriState;
  evidence_required: string[];
  question_ids?: string[];
}

export interface PrecedentRef {
  precedent_id: string;
  hmem_id: string;
  control_id: string;
  relevance: number;
  hmem_confidence: number;
  applied: boolean;
  failed_criteria?: string[];
}

export interface PrecedentCandidate {
  precedent_id: string;
  control_id: string;
  mitigation: string;
  reviewer_role: string;
  decision: string;
  created_as_of: string;
  tier: string;
}

export interface Confidence {
  value: number;
  gate: number;
  abstained: boolean;
  signals: Record<string, number>;
  unknown_controls?: string[];
}

export interface DecisionRecord {
  case_id: string;
  run_id: string;
  policy_version: string;
  policy_sha256: string;
  tier: string;
  facts: Fact[];
  controls: ControlResult[];
  contradictions: Contradiction[];
  outcome: string;
  outcome_reasons: string[];
  escalation_reasons?: string[];
  counterfactuals: Counterfactual[];
  precedents_considered: PrecedentRef[];
  exceptions_applied: string[];
  residual_risk: number;
  confidence: Confidence;
  conditions?: string[];
  as_of: string;
  policy_inputs?: { precedents?: PrecedentCandidate[] } & Record<string, unknown>;
  created_at: string;
  record_sha256: string;
}

export interface EvidenceRef {
  source_label: string;
  record_label: string;
  field_label: string;
  value: string;
  quote?: string | null;
  provenance_id?: string;
}

export interface BriefPoint {
  text: string;
  claim?: EvidenceRef | null;
  record?: EvidenceRef | null;
  citations?: string[];
}

export interface Draft {
  to_role: string;
  subject: string;
  body: string;
}

export interface Report {
  summary: string;
  drafts?: Draft[];
  clarification_email?: Draft | null;
  brief?: { headline: string; why: BriefPoint[]; next_steps?: unknown[]; generator?: string } | null;
  generator?: string;
}

export interface Approval {
  by: string;
  role: string;
  decision: string;
  rationale: string;
  at?: string;
}

export interface Contract {
  contract_id: string;
  parent_id: string | null;
  trace_id: string;
  case_id: string;
  intent: string;
  parameters: Record<string, unknown>;
  risk: { level?: string; approvals: Approval[]; approvals_required: Array<{ role: string }>; flags?: string[] };
  tool_plan: Array<{ capability: string; args?: Record<string, unknown> }>;
  issued_at: string;
  expires_at: string;
  signature: string;
  signed_by?: string;
  state: string;
}

export interface Review {
  review_id: string;
  reviewer: string;
  role: string;
  decision: string;
  rationale: string;
  at?: string;
}

export interface Workload {
  answers_read: number;
  documents_read: number;
  queries: number;
  contradictions: number;
  elapsed_seconds: number;
  model_calls: number;
  models: string[];
  systems_queried: string[];
}

export interface CaseDetail {
  case_id: string;
  vendor: string;
  status: string;
  record: DecisionRecord;
  report: Report;
  contracts: Contract[];
  reviews: Review[];
  trace_path: string;
  workload?: Workload | null;
}

export interface ApprovalResult {
  contract_id: string;
  parent_id: string | null;
  state: string;
  executed: boolean;
  artifact?: string | null;
}

export interface ReplayResult {
  match: boolean;
  diff: string[];
  checks: { policy_hash: boolean; record_hash: boolean; contract_signatures: boolean };
  human_override?: { reviewer: string; role: string; decision: string; rationale: string; review_id: string; at?: string | null } | null;
  machine_outcome?: string | null;
  machine_source?: string | null;
}

export interface Question {
  question_id: string;
  question: string;
}

export interface TraceLine {
  agent_name?: string | null;
  action?: string | null;
  input_summary?: string | null;
  output_summary?: string | null;
  mode?: Record<string, string> | null;
  timestamp?: string | null;
  status?: string | null;
}
