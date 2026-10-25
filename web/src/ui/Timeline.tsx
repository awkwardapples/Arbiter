// After Aceternity's Timeline: a real sequence down a line, one dot per entry (design §10, Case: Audit trail).
// Recoloured to tokens; each entry's dot takes its tone. No scroll-driven gradient.
import type { ReactNode } from "react";
import { cn } from "./lib/cn";

export type TimelineTone = "ink" | "record" | "claim" | "clash" | "reason";

const DOT: Record<TimelineTone, string> = {
  ink: "border-ink",
  record: "border-record",
  claim: "border-claim",
  clash: "border-clash",
  reason: "border-reason",
};

export interface TimelineEntry {
  id: string;
  when: ReactNode;
  title: ReactNode;
  body?: ReactNode;
  tone?: TimelineTone;
}

export function Timeline({ entries, className, ...props }: { entries: TimelineEntry[]; className?: string; "data-testid"?: string }) {
  return (
    <ol className={cn("relative ml-2 border-l border-hairline", className)} {...props}>
      {entries.map((entry) => (
        <li key={entry.id} className="relative pb-6 pl-6 last:pb-0">
          <span aria-hidden className={cn("absolute top-1.5 -left-[6px] size-[11px] rounded-full border-2 bg-sheet", DOT[entry.tone ?? "ink"])} />
          <p className="text-xs text-graphite">{entry.when}</p>
          <p className="text-sm font-semibold text-ink">{entry.title}</p>
          {entry.body ? <div className="mt-1 text-sm text-graphite">{entry.body}</div> : null}
        </li>
      ))}
    </ol>
  );
}
