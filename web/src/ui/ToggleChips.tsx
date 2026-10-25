import { Check } from "lucide-react";
import { cn } from "./lib/cn";

/** Pick several from a short list. Each chip is a toggle button with aria-pressed. */
export function ToggleChips<T extends string>({
  options,
  value,
  onChange,
  words,
  label,
}: {
  options: readonly T[];
  value: readonly T[];
  onChange: (next: T[]) => void;
  words?: Partial<Record<T, string>>;
  label: string;
}) {
  const toggle = (option: T) =>
    onChange(value.includes(option) ? value.filter((v) => v !== option) : options.filter((o) => o === option || value.includes(o)));
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const on = value.includes(option);
        return (
          <button
            key={option}
            type="button"
            aria-pressed={on}
            onClick={() => toggle(option)}
            className={cn(
              "inline-flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors",
              on ? "border-ink bg-ink text-sheet" : "border-hairline bg-sheet text-ink hover:bg-well",
            )}
          >
            {on ? <Check className="size-3" aria-hidden /> : null}
            {words?.[option] ?? option}
          </button>
        );
      })}
    </div>
  );
}
