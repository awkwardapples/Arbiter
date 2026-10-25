import { cn } from "../../ui/lib/cn";

export interface Chip {
  value: string;
  label: string;
  count: number;
}

/** Toggle chips with counts. Selected values live in the URL; an empty selection shows everything. */
export function FilterChips({
  name,
  label,
  chips,
  selected,
  onToggle,
}: {
  name: string;
  label: string;
  chips: Chip[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div data-testid={`cases-filter-${name}`} role="group" aria-label={label} className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-graphite">{label}</span>
      {chips.map((chip) => {
        const on = selected.includes(chip.value);
        return (
          <button
            key={chip.value}
            type="button"
            aria-pressed={on}
            onClick={() => onToggle(chip.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-medium transition-colors",
              on ? "border-ink bg-ink text-sheet" : "border-hairline bg-well text-ink hover:border-graphite",
            )}
          >
            {chip.label}
            <span className={cn("tabular-nums", on ? "text-sheet/80" : "text-graphite")}>{chip.count}</span>
          </button>
        );
      })}
    </div>
  );
}
