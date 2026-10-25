// GET /eval/latest (P19): the published live evaluation and the offline benchmark, read as published.
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../api/client";

export interface Rate {
  rate: number | null;
  n?: number;
  count?: number;
  correct?: number;
  found?: number;
  expected?: number;
  wilson_95?: [number, number];
}

export interface SystemSummary {
  accuracy: Rate;
  unsafe_approvals: { count: number; n: number };
  abstention_rate: Rate;
  contradiction_recall: Rate;
  run: {
    n: number;
    mode: Record<string, string>;
    latency_ms: { p50: number | null; p95: number | null };
    model_calls_per_case: number;
    fallback_rate: Rate;
    model_ids: string[];
  };
}

export interface EvalSummary {
  generated_at: string;
  mode: Record<string, string>;
  model_ids: string[];
  n: number;
  synthetic: boolean;
  systems: Record<string, SystemSummary>;
  /** Added by P20 if it publishes one; shown exactly as written. */
  baseline_status?: string;
}

export interface EvalLatest {
  live: EvalSummary | null;
  offline: EvalSummary | null;
  live_markdown: string | null;
  offline_markdown: string | null;
}

/** null means the API has no published results (HTTP 404), which the page explains. */
export const useEvalLatest = () =>
  useQuery({
    queryKey: ["eval-latest"],
    queryFn: async () => {
      try {
        return await api.get<EvalLatest>("/eval/latest");
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    retry: false,
  });

/** Systems in the order the page shows them: Arbiter, the baseline, then Arbiter offline. */
export const SYSTEM_ORDER = ["arbiter", "baseline", "arbiter_offline"];
export const SYSTEM_WORDS: Record<string, string> = {
  arbiter: "Arbiter",
  baseline: "Single-model baseline",
  arbiter_offline: "Arbiter offline (deterministic fallback)",
};

export function orderedSystems(summary: EvalSummary): [string, SystemSummary][] {
  const known = SYSTEM_ORDER.filter((k) => summary.systems[k]).map((k) => [k, summary.systems[k]] as [string, SystemSummary]);
  const rest = Object.entries(summary.systems).filter(([k]) => !SYSTEM_ORDER.includes(k));
  return [...known, ...rest];
}

/** "1.000 (5/5)", as the published summary writes a rate. */
export function rateText(rate: Rate | undefined, numerator?: number, denominator?: number): string {
  if (!rate || rate.rate == null) return "–";
  const num = numerator ?? rate.correct ?? rate.found ?? rate.count;
  const den = denominator ?? rate.n ?? rate.expected;
  return num != null && den != null ? `${rate.rate.toFixed(3)} (${num}/${den})` : rate.rate.toFixed(3);
}

export function wilsonText(rate: Rate | undefined): string | null {
  if (!rate?.wilson_95) return null;
  const [lo, hi] = rate.wilson_95;
  return `${lo.toFixed(2)} to ${hi.toFixed(2)}`;
}

/** The published notes, word for word: the summary's prose lines, without its title, tables or list. */
export function publishedNotes(markdown: string | null | undefined): string[] {
  if (!markdown) return [];
  return markdown
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#") && !line.startsWith("|") && !line.startsWith("- "));
}
