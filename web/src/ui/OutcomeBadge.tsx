import { cn } from "./lib/cn";
import { outcomeClasses, outcomeWord } from "./outcome";

export function OutcomeBadge({ outcome, label, className }: { outcome: string | null | undefined; label?: string | null; className?: string }) {
  const c = outcomeClasses(outcome);
  return (
    <span
      data-outcome={outcome ?? ""}
      className={cn("inline-flex items-center rounded-full border bg-sheet px-2 text-xs font-semibold whitespace-nowrap", c.text, c.border, className)}
    >
      {outcomeWord(outcome, label)}
    </span>
  );
}
