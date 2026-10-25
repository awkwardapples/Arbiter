// What the Provider page may show. Every value passes a shape check before it reaches the DOM, so a
// token or header that ever lands in a payload is dropped, not rendered (design §11).
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { Health, TraceEvent } from "../../api/types";
import { filterProviderMeta } from "../../run/whitelist";

const MODEL_ID = /^[a-z0-9][a-z0-9._-]*\/[A-Za-z0-9._:-]+$/;
const WORD = /^[a-z][a-z_-]{0,31}$/;
const RECEIPT = /^rcpt_[A-Za-z0-9_-]{1,64}$/;
const HOST_PORT = /^[A-Za-z0-9.-]{1,253}(:\d{1,5})?$/;
const AGENT = /^[A-Z][A-Za-z]{0,30}Agent$/;

export const modelId = (v: unknown): string | null => (typeof v === "string" && MODEL_ID.test(v) ? v : null);
export const word = (v: unknown): string | null => (typeof v === "string" && WORD.test(v) ? v : null);
export const receiptId = (v: unknown): string | null => (typeof v === "string" && RECEIPT.test(v) ? v : null);

/** host:port from a URL, or null. The path, query, user info and anything else are never kept. */
export function hostPort(url: unknown): string | null {
  if (typeof url !== "string" || !url) return null;
  try {
    const parsed = new URL(url.includes("://") ? url : `http://${url}`);
    const value = parsed.port ? `${parsed.hostname}:${parsed.port}` : parsed.hostname;
    return HOST_PORT.test(value) ? value : null;
  } catch {
    return null;
  }
}

export const safeHost = (v: unknown): string | null => (typeof v === "string" && HOST_PORT.test(v) ? v : null);

export interface Connection {
  resolved: string | null;
  setting: string | null;
  nightshiftStatus: string | null;
  nightshiftHost: string | null;
  modelsSeen: string[];
  fastMode: string | null;
  deepMode: string | null;
}

export function connection(health: Health | undefined): Connection {
  const provider = (health?.provider ?? {}) as Record<string, unknown>;
  const meterless = (provider.meterless ?? {}) as Record<string, unknown>;
  const seen = Array.isArray(meterless.models_seen) ? meterless.models_seen : [];
  return {
    resolved: word(provider.provider_resolved),
    setting: word(provider.llm_provider_setting),
    nightshiftStatus: word(meterless.status),
    nightshiftHost: hostPort(meterless.base_url),
    modelsSeen: seen.map(modelId).filter((m): m is string => m !== null),
    fastMode: modelId(meterless.fast_model),
    deepMode: modelId(meterless.deep_model),
  };
}

export interface ProofLane {
  lane: string;
  sent: string | null;
  requestedMode: string | null;
  routedMode: string | null;
  coerced: boolean;
  served: string | null;
  receipt: string | null;
  latencyMs: number | null;
}

export interface Proof {
  timestamp: string | null;
  host: string | null;
  lanes: ProofLane[];
  coerced: boolean;
}

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);

export function proof(raw: unknown): Proof | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const lanes: ProofLane[] = ["fast", "deep"].flatMap((lane) => {
    const l = r[lane];
    if (!l || typeof l !== "object") return [];
    const v = l as Record<string, unknown>;
    return [
      {
        lane,
        sent: modelId(v.sent_model),
        requestedMode: word(v.requested_mode),
        routedMode: word(v.routed_mode),
        coerced: v.mode_coerced === true,
        served: modelId(v.response_model) ?? modelId(v.routed_model),
        receipt: receiptId(v.receipt_id),
        latencyMs: num(v.latency_ms),
      },
    ];
  });
  const ts = typeof r.timestamp === "string" && !Number.isNaN(Date.parse(r.timestamp)) ? r.timestamp : null;
  return { timestamp: ts, host: safeHost(r.base_url_host), lanes, coerced: lanes.some((l) => l.coerced) };
}

export interface Receipt {
  caseId: string;
  at: string;
  agent: string;
  purpose: string | null;
  lane: string | null;
  model: string | null;
  latencyMs: number | null;
  receipt: string;
  coerced: boolean;
}

/** Model calls that carry a receipt, newest first. Provider metadata goes through the whitelist. */
export function receiptsFrom(caseId: string, events: TraceEvent[]): Receipt[] {
  return events.flatMap((event) => {
    if (event.action !== "model_call") return [];
    const meta = filterProviderMeta(event.provider_meta);
    const receipt = receiptId(meta.receipt_id);
    if (!receipt) return [];
    return [
      {
        caseId,
        at: event.timestamp,
        agent: AGENT.test(event.agent_name) ? event.agent_name.replace(/Agent$/, "") : "Agent",
        purpose: word(event.purpose),
        lane: word(event.route),
        model: modelId(event.model) ?? modelId(meta.routed_model),
        latencyMs: num(event.latency_ms),
        receipt,
        coerced: meta["app_policy.mode_coerced"] === "True",
      },
    ];
  });
}

export const useNightshiftProof = () =>
  useQuery({ queryKey: ["evidence-nightshift"], queryFn: () => api.get<unknown>("/evidence/nightshift"), staleTime: Infinity, retry: false });

/** The last 10 receipts across the 5 most recent cases (GET /cases, then each case's trace). */
export const useRecentReceipts = () =>
  useQuery({
    queryKey: ["recent-receipts"],
    queryFn: async () => {
      const cases = await api.get<{ case_id: string; created?: string }[]>("/cases");
      const recent = [...cases].sort((a, b) => (b.created ?? "").localeCompare(a.created ?? "")).slice(0, 5);
      const traces = await Promise.all(
        recent.map(async (c) => receiptsFrom(c.case_id, await api.get<TraceEvent[]>(`/cases/${encodeURIComponent(c.case_id)}/trace`))),
      );
      return traces
        .flat()
        .sort((a, b) => b.at.localeCompare(a.at))
        .slice(0, 10);
    },
  });

export const DEVIATION_SENTENCE =
  "Nightshift's app rule coerced the requested lane to auto, so the model that served each call was chosen by Nightshift, not by the lane Arbiter asked for.";
