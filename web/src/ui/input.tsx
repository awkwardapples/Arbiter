import type { ComponentProps } from "react";
import { cn } from "./lib/cn";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-[6px] border border-hairline bg-sheet px-3 text-sm text-ink placeholder:text-graphite disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
