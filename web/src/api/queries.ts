// TanStack Query hooks, one per read route the console uses.
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { AgentInfo, CaseDetail, Health, Recording, RecordingMeta, RegistryQuery, Vendor } from "./types";

const MINUTE = 60_000;

export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: () => api.get<Health>("/health"), staleTime: MINUTE, retry: 1 });

export const useVendors = () =>
  useQuery({ queryKey: ["vendors"], queryFn: () => api.get<Vendor[]>("/vendors"), staleTime: 5 * MINUTE });

export const useRecordings = () =>
  useQuery({ queryKey: ["recordings"], queryFn: () => api.get<RecordingMeta[]>("/recordings"), staleTime: 5 * MINUTE });

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
