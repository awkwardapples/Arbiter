// Six counters that answer the judges' brief (design §7.5). Each one filters the Activity tab.
import type { CounterKey } from "./counters";
import type { RunState } from "./types";
import { NumberTicker } from "../ui/effects/NumberTicker";
import { cn } from "../ui/lib/cn";

export function BehaviourStrip({ state, filter, onFilter }: { state: RunState; filter: CounterKey | null; onFilter: (key: CounterKey | null) => void }) {
  const mirror = state.mode?.data === "duckdb";
  const items: { key: CounterKey; label: string; value: number; alert?: boolean }[] = [
    { key: "critiques", label: "Critiques", value: state.counters.critiques },
    { key: "sent_back", label: "Sent back", value: state.counters.sent_back, alert: state.counters.sent_back > 0 },
    { key: "retries_fallbacks", label: "Retries and fallbacks", value: state.counters.retries_fallbacks, alert: state.counters.retries_fallbacks > 0 },
    { key: "shared_context", label: "Shared context reads", value: state.counters.shared_context },
    { key: "model_calls", label: "Model calls on Nemotron", value: state.counters.model_calls },
    mirror
      ? { key: "mirror", label: "Mirror queries", value: state.counters.mirror }
      : { key: "zetaris", label: "Zetaris queries", value: state.counters.zetaris },
  ];
  return (
    <div role="group" aria-label="What the agents did" className="grid grid-cols-3 gap-2 lg:grid-cols-6">
      {items.map((item) => {
        const on = filter === item.key;
        return (
          <button
            key={item.key}
            type="button"
            aria-pressed={on}
            onClick={() => onFilter(on ? null : item.key)}
            className={cn("flex flex-col items-start rounded-panel border bg-sheet px-3 py-1 text-left hover:bg-well", on ? "border-ink" : "border-hairline")}
          >
            <NumberTicker value={item.value} className={cn("text-lg leading-6 font-semibold", item.alert ? "text-clash" : "text-ink")} />
            <span className="text-[12px] leading-4 text-graphite">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
