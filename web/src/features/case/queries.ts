// Reads and writes for the Cases and Case pages. 18b's api/queries.ts owns useCase; the rest live here.
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiUrl } from "../../api/client";
import type { ApprovalResult, CaseDetail, Contract, Question, QueueItem, ReplayResult, TraceLine } from "./types";

const MINUTE = 60_000;
/** Streamlit's limit for counting approvals waiting for sign-off (ui/portfolio.py). */
export const PENDING_SCAN_LIMIT = 40;

const enc = encodeURIComponent;

export const useCases = () => useQuery({ queryKey: ["cases"], queryFn: () => api.get<QueueItem[]>("/cases") });

export const useCaseDetail = (caseId: string | undefined) =>
  useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.get<CaseDetail>(`/cases/${enc(caseId ?? "")}`),
    enabled: Boolean(caseId),
    retry: false,
  });

export const useCaseTrace = (caseId: string | undefined) =>
  useQuery({
    queryKey: ["case-trace", caseId],
    queryFn: () => api.get<TraceLine[]>(`/cases/${enc(caseId ?? "")}/trace`),
    enabled: Boolean(caseId),
    retry: false,
    staleTime: 5 * MINUTE,
  });

export const useQuestions = () =>
  useQuery({ queryKey: ["questions"], queryFn: () => api.get<Question[]>("/questions"), staleTime: Infinity, retry: false });

/** A contract that a later approval or rejection replaced: another contract names it as its parent. */
export function liveContracts(contracts: Contract[]): Contract[] {
  const parents = new Set(contracts.map((c) => c.parent_id).filter(Boolean));
  return contracts.filter((c) => !parents.has(c.contract_id));
}

export function pendingCount(contracts: Contract[]): number {
  return liveContracts(contracts).filter((c) => c.state === "pending_approval").length;
}

/** Contracts waiting for sign-off across the first 40 cases. Cases that fail to load are skipped. */
export function usePendingApprovals(items: QueueItem[] | undefined) {
  const scanned = (items ?? []).slice(0, PENDING_SCAN_LIMIT);
  return useQueries({
    queries: scanned.map((item) => ({
      queryKey: ["case", item.case_id],
      queryFn: () => api.get<CaseDetail>(`/cases/${enc(item.case_id)}`),
      retry: false,
    })),
    combine: (results) => ({
      done: results.every((r) => !r.isPending),
      count: results.reduce((sum, r) => sum + (r.data ? pendingCount(r.data.contracts) : 0), 0),
    }),
  });
}

export interface ApprovalInput {
  contractId: string;
  by: string;
  role: string;
  decision: "approve" | "reject";
  rationale: string;
}

export function useApproveContract(caseId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ contractId, by, role, decision, rationale }: ApprovalInput) =>
      api.post<ApprovalResult>(`/contracts/${enc(contractId)}/approve`, { by, role, decision, rationale }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["case", caseId] });
      void client.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useReplay(caseId: string) {
  return useMutation({ mutationFn: () => api.post<ReplayResult>(`/cases/${enc(caseId)}/replay`, {}) });
}

export const dossierUrl = (caseId: string, format: "html" | "md") => apiUrl(`/cases/${enc(caseId)}/dossier?format=${format}`);
