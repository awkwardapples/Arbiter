// Shows the result of Replay decision, with each verification check on its own line.
import { cn } from "../../ui/lib/cn";
import { replaySentence } from "./replay";
import type { ReplayResult } from "./types";
import { checkWord } from "./words";

export function ReplayResultView({ result }: { result: ReplayResult }) {
  return (
    <div
      data-testid="replay-result"
      role="status"
      className={cn(
        "rounded-panel border px-4 py-3 text-sm",
        result.match ? "border-record/30 bg-record-tint text-ink" : "border-clash/30 bg-clash-tint text-ink",
      )}
    >
      <p className="font-medium">{replaySentence(result)}</p>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-graphite">
        {Object.entries(result.checks ?? {}).map(([key, ok]) => (
          <li key={key} className={ok ? "" : "text-clash"}>
            {ok ? "Verified" : "Failed"}: {checkWord(key)}
          </li>
        ))}
      </ul>
    </div>
  );
}
