import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export interface AuditEvent {
  seq: number;
  timestamp: string;
  case_id: string;
  event_type: string;
}

export interface AuditVerify {
  ok: boolean;
  first_bad_seq: number | null;
}

export const useAuditRecent = () =>
  useQuery({ queryKey: ["audit-recent"], queryFn: () => api.get<AuditEvent[]>("/audit/recent?limit=50") });

/** "review_recorded" → "Review recorded": the code in sentence case, so new kinds still read. */
export function eventWords(eventType: string): string {
  const words = eventType.split("_").join(" ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Event";
}

/** The verify result in words (design §4: say what happened). */
export function verifySentence(result: AuditVerify, entries: number | null | undefined): string {
  if (!result.ok) return `Chain breaks at entry ${result.first_bad_seq ?? "unknown"}.`;
  if (entries == null) return "Audit chain verified.";
  return `Audit chain verified: ${entries} ${entries === 1 ? "entry" : "entries"}.`;
}
