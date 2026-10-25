// The case's own trace replayed on the bench (18b's RunCanvas), paced so it can be followed, and the workload.
import type { TraceEvent } from "../../api/types";
import { RunCanvas } from "../../run/RunCanvas";
import type { CaseDetail, TraceLine } from "./types";
import { workloadSentence } from "./words";

/** Sample traces arrive in under a second, so they are paced; a live trace replays with its real gaps. */
function paceFor(mode: Record<string, string> | null): "paced" | "recorded" {
  return mode?.data === "zetaris" || (mode?.llm && mode.llm !== "offline") ? "recorded" : "paced";
}

export function AgentActivityTab({ detail, trace, mode, traceError }: { detail: CaseDetail; trace: TraceLine[] | undefined; mode: Record<string, string> | null; traceError: string | null }) {
  return (
    <div data-testid="agent-activity-tab" className="flex flex-col gap-4">
      <div data-testid="agent-activity">
        {trace ? (
          <RunCanvas source={{ kind: "events", events: trace as TraceEvent[], mode: paceFor(mode) }} emptyText="Replaying this case's trace" />
        ) : traceError ? (
          <p className="text-sm text-clash">The trace for this case could not be read: {traceError}</p>
        ) : (
          <p className="text-sm text-graphite">Loading the trace…</p>
        )}
      </div>
      <p data-testid="workload" className="text-sm text-ink">
        {detail.workload ? workloadSentence(detail.workload) : "The workload was not recorded for this case."}
      </p>
    </div>
  );
}
