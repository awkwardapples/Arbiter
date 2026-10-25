// The run's sequence, from transition events (design §7.5). A safe escalation turns the rail red from there.
import type { RunState } from "./types";
import { cn } from "../ui/lib/cn";

export function StageRail({ state }: { state: RunState }) {
  const current = state.currentStage;
  let escalatedFrom = -1;
  if (state.safeEscalate) escalatedFrom = state.stages.findIndex((s) => s.escalated);
  return (
    <ol aria-label="Stages" className="flex flex-wrap items-center gap-1 text-[12px]">
      {state.stages.map((stage, k) => {
        const visited = stage.visits > 0 || stage.name === current;
        const isCurrent = stage.name === current && !state.outcome;
        const red = escalatedFrom >= 0 && k >= escalatedFrom;
        return (
          <li
            key={stage.name}
            aria-current={isCurrent ? "step" : undefined}
            className={cn(
              "flex items-center gap-1 rounded-full border px-2 py-0",
              visited ? "border-ink/25 bg-sheet text-ink" : "border-hairline bg-transparent text-graphite",
              isCurrent && "border-ink bg-ink text-sheet",
              red && "border-clash/50 text-clash",
            )}
          >
            <span className={cn("font-mono text-[11px]", isCurrent ? "text-sheet/80" : "text-graphite")}>{k + 1}</span>
            <span>{stage.name}</span>
            {stage.visits > 1 ? <span className={cn("text-[12px] font-semibold", isCurrent ? "text-sheet" : "text-clash")}>×{stage.visits}</span> : null}
          </li>
        );
      })}
    </ol>
  );
}
