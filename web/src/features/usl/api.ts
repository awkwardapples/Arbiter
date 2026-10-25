import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { TraceEvent } from "../../api/types";
import type { UslModel } from "./model";

export interface ParityRule {
  id: string;
  table: string;
  expr: string;
  pk: string;
}

export interface ParityInvalid {
  table: string;
  zetaris: string[];
  mirror: string[];
  ok: boolean;
}

export interface Parity {
  query_layer: string;
  source_mode: string;
  all_green: boolean;
  table_counts: { table: string; expected: number; zetaris: number; ok: boolean }[];
  rules: ParityRule[];
  invalid_by_table: ParityInvalid[];
  query_comparisons: { total: number; ok: number };
  kev_checks: { total: number; ok: number };
}

export interface CaseRow {
  case_id: string;
  vendor: string;
  outcome: string;
  tier: string;
  residual_risk: number;
  status: string;
  created: string;
}

export const useUslModel = () =>
  useQuery({ queryKey: ["usl-model"], queryFn: () => api.get<UslModel>("/usl/model"), staleTime: Infinity });

export const useParity = () =>
  useQuery({ queryKey: ["evidence-parity"], queryFn: () => api.get<Parity>("/evidence/parity"), staleTime: Infinity, retry: false });

export const useCases = () => useQuery({ queryKey: ["cases"], queryFn: () => api.get<CaseRow[]>("/cases") });

export const useCaseTrace = (caseId: string | null | undefined) =>
  useQuery({
    queryKey: ["case-trace", caseId],
    queryFn: () => api.get<TraceEvent[]>(`/cases/${encodeURIComponent(caseId ?? "")}/trace`),
    enabled: Boolean(caseId),
    staleTime: Infinity,
  });

/** Data mode in words, from /health only. */
export function dataModeLine(data: Record<string, unknown> | null | undefined, mode: Record<string, string> | undefined): string {
  const backend = (data?.backend as string | undefined) ?? mode?.data;
  if (backend === "zetaris") {
    const layer = (data?.zetaris as { query_layer?: string } | undefined)?.query_layer;
    return layer === "usl" ? "Zetaris USL vendor_risk, live" : "Zetaris views, live";
  }
  if (backend === "duckdb") return "DuckDB mirror, sample mode";
  return "Unknown";
}
