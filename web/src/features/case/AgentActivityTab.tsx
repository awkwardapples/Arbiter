// The case's own trace replayed on the bench, and the measured workload.
// The bench (<RunCanvas source={{kind:"events"}}>) comes from lane 18b part 2; until it lands this tab shows the
// workload only and says so.
import { Callout } from "../../ui/Callout";
import type { CaseDetail } from "./types";
import { workloadSentence } from "./words";

export function AgentActivityTab({ detail }: { detail: CaseDetail }) {
  return (
    <div data-testid="agent-activity-tab" className="flex flex-col gap-4">
      <div data-testid="agent-activity">
        <Callout title="The bench replay is not in this build yet.">
          It arrives with the live run view. The classic console shows this case's agent timeline today.
        </Callout>
      </div>
      <p data-testid="workload" className="text-sm text-ink">
        {detail.workload ? workloadSentence(detail.workload) : "The workload was not recorded for this case."}
      </p>
    </div>
  );
}
