import type { ReactNode } from "react";
import { cn } from "./lib/cn";

export function EmptyState({ title, children, action, className }: { title: string; children?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-start gap-2 rounded-panel border border-dashed border-hairline bg-sheet px-6 py-8", className)}>
      <p className="text-md font-semibold text-ink">{title}</p>
      {children ? <div className="max-w-prose text-sm text-graphite">{children}</div> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
