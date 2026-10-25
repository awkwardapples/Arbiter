import { cn } from "./lib/cn";
import { outcomeClasses, outcomeWord } from "./outcome";

/** The ruling stamp: the outcome word in its colour, 2 px radius (design §7.4). */
export function OutcomeStamp({ outcome, label, className }: { outcome: string | null | undefined; label?: string | null; className?: string }) {
  const c = outcomeClasses(outcome);
  return (
    <span
      data-testid="outcome-stamp"
      data-outcome={outcome ?? ""}
      className={cn("inline-block rounded-stamp border-2 bg-sheet px-3 py-1 text-lg font-bold tracking-wide", c.text, c.border, className)}
    >
      {outcomeWord(outcome, label)}
    </span>
  );
}
