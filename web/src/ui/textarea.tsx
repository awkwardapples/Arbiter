import type { ComponentProps } from "react";
import { cn } from "./lib/cn";

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-[6px] border border-hairline bg-sheet px-3 py-2 text-sm text-ink placeholder:text-graphite disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
