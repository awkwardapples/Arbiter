import { Database, Film, Radio } from "lucide-react";
import type { ModeChip as Chip } from "../run/mode";
import { cn } from "./lib/cn";

const TONE: Record<Chip["tone"], string> = {
  live: "border-record/40 bg-record-tint text-record",
  sample: "border-hairline bg-well text-graphite",
  recorded: "border-reason/40 bg-reason-tint text-reason",
  other: "border-hairline bg-sheet text-ink",
};

const ICON = { live: Radio, sample: Database, recorded: Film, other: Database };

/** The permanent honesty label (design §5). Its text is computed by run/mode.ts, never typed here. */
export function ModeChip({ chip, className }: { chip: Chip | null; className?: string }) {
  if (!chip) return null;
  const Icon = ICON[chip.tone];
  return (
    <span data-testid="mode-chip" className={cn("inline-flex items-center gap-2 text-xs", className)}>
      <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-medium", TONE[chip.tone])}>
        <Icon className="size-3.5" aria-hidden />
        {chip.text}
      </span>
      {chip.extra ? <span className="text-graphite">{chip.extra}</span> : null}
      {chip.fallbacks ? (
        <span className="rounded-full border border-clash/30 bg-clash-tint px-2 py-0.5 font-medium text-clash">{chip.fallbacks}</span>
      ) : null}
    </span>
  );
}
