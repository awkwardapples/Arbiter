import type { ModeChip as Chip } from "../../run/mode";
import { duration } from "../../run/parse";
import { Identifier } from "../../ui/Identifier";
import { ModeChip } from "../../ui/ModeChip";

export function RunHeader({ title, chip, elapsedSeconds, runId }: { title: string; chip: Chip; elapsedSeconds: number | null; runId: string }) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-hairline bg-sheet px-6 py-3">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold text-ink">{title}</h1>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-sm text-graphite">
          <span>{elapsedSeconds !== null ? `Elapsed ${duration(elapsedSeconds)}` : "Not started yet"}</span>
          <Identifier value={runId} />
        </p>
      </div>
      <div className="pt-1">
        <ModeChip chip={chip} />
      </div>
    </header>
  );
}
