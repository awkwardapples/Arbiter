// GET /memory/precedents, and what the Memory page reads from each precedent's H-MEM ledger.
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export interface LedgerEntry {
  memory_id: string;
  action: string;
  actor: string;
  timestamp: number;
  previous_state: Record<string, unknown> | null;
  new_state: Record<string, unknown> | null;
  details: Record<string, unknown> | null;
}

export interface Precedent {
  precedent_id: string;
  hmem_id: string;
  confidence: number | null;
  control_id: string | null;
  ledger: LedgerEntry[];
}

export interface FeedbackItem {
  kind: string;
  delta: number | null;
  at: Date;
}

export interface PrecedentView {
  id: string;
  controlId: string | null;
  confidence: number | null;
  fromCase: string | null;
  approvedBy: string | null;
  createdAt: Date | null;
  reads: number;
  feedback: FeedbackItem[];
}

export const usePrecedents = () =>
  useQuery({ queryKey: ["precedents"], queryFn: () => api.get<Precedent[]>("/memory/precedents") });

export const MEMORY_EMPTY = "No precedents yet. A TPRM lead creates one by reviewing a case.";
export const MEMORY_RULE =
  "A precedent changes a decision only where the policy allows an exception, and only if a TPRM lead approved it.";

const REVIEW_SOURCE = /^human_review:(.+)$/;

/** Only fields the ledger really holds: the creating review's case and reviewer, reads and feedback. */
export function precedentView(p: Precedent): PrecedentView {
  const created = p.ledger.find((e) => e.action === "create");
  const state = created?.new_state ?? {};
  const source = typeof state.source === "string" ? REVIEW_SOURCE.exec(state.source) : null;
  return {
    id: p.precedent_id,
    controlId: p.control_id,
    confidence: p.confidence,
    fromCase: typeof state.taskId === "string" ? state.taskId : null,
    approvedBy: source ? source[1] : null,
    createdAt: created ? new Date(created.timestamp) : null,
    reads: p.ledger.filter((e) => e.action === "read").length,
    feedback: p.ledger
      .filter((e) => e.action === "feedback")
      .map((e) => ({
        kind: typeof e.details?.kind === "string" ? e.details.kind : "feedback",
        delta: typeof e.details?.delta === "number" ? e.details.delta : null,
        at: new Date(e.timestamp),
      })),
  };
}
