// TanStack Query hooks, one per read route the console uses.
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { AgentInfo, CaseDetail, Health, Recording, RecordingMeta, RegistryQuery, Vendor } from "./types";

const MINUTE = 60_000;
// The API can answer 500 while a run holds the sample database (reported to lane 18a); retry reads a few times.
const READ_RETRY = { retry: 3, retryDelay: (attempt: number) => Math.min(500 * 2 ** attempt, 4000) };

export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: () => api.get<Health>("/health"), staleTime: MINUTE, ...READ_RETRY });

export const useVendors = () =>
  useQuery({ queryKey: ["vendors"], queryFn: () => api.get<Vendor[]>("/vendors"), staleTime: 5 * MINUTE, ...READ_RETRY });

export const useRecordings = () =>
  useQuery({ queryKey: ["recordings"], queryFn: () => api.get<RecordingMeta[]>("/recordings"), staleTime: 5 * MINUTE, ...READ_RETRY });

export const useRecording = (runId: string | null) =>
  useQuery({
    queryKey: ["recording", runId],
    queryFn: () => api.get<Recording>(`/recordings/${encodeURIComponent(runId ?? "")}`),
    enabled: Boolean(runId),
    staleTime: Infinity,
  });

export const useRegistry = () =>
  useQuery({
    queryKey: ["registry"],
    queryFn: () => api.get<RegistryQuery[]>("/registry/queries"),
    staleTime: Infinity,
    retry: 1,
  });

export const useAgents = () =>
  useQuery({ queryKey: ["agents"], queryFn: () => api.get<AgentInfo[]>("/agents"), staleTime: Infinity, retry: 1 });

export const useCase = (caseId: string | null, enabled = true) =>
  useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.get<CaseDetail>(`/cases/${encodeURIComponent(caseId ?? "")}`),
    enabled: Boolean(caseId) && enabled,
    retry: false,
  });
