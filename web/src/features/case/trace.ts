// Facts the Case page reads from the case's own trace: its mode, and where each executed contract was written.
import type { TraceLine } from "./types";

export function traceMode(trace: TraceLine[] | undefined): Record<string, string> | null {
  return trace?.find((e) => e.mode && Object.keys(e.mode).length)?.mode ?? null;
}

/** contract id → outbox file name, from `ActionExecutor execute_action` lines ("executed: ok → <path>"). */
export function outboxFiles(trace: TraceLine[] | undefined): Record<string, string> {
  const files: Record<string, string> = {};
  for (const event of trace ?? []) {
    if (event.action !== "execute_action" || event.status !== "success") continue;
    const contract = /contract=(\S+)/.exec(event.input_summary ?? "")?.[1];
    const path = /→\s*(\S+)\s*$/.exec(event.output_summary ?? "")?.[1];
    if (contract && path) files[contract] = path.split(/[\\/]/).pop() ?? path;
  }
  return files;
}

export const fileName = (path: string) => path.split(/[\\/]/).pop() ?? path;
