import type { ReactNode } from "react";
import { HealthModeChip } from "./HealthModeChip";

/** Page title on the left, the mode chip on the right. Pass `chip` to override the /health chip. */
export function PageHeader({ title, children, chip }: { title: ReactNode; children?: ReactNode; chip?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-hairline bg-sheet px-8 py-5">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        {children ? <div className="mt-1 text-sm text-graphite">{children}</div> : null}
      </div>
      <div className="pt-1">{chip ?? <HealthModeChip />}</div>
    </header>
  );
}
