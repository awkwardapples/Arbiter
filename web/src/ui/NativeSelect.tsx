import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "./lib/cn";

/** A native select styled like the kit's Select: for long forms, where a native control is quicker. */
export function NativeSelect({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <div className="relative">
      <select
        className={cn(
          "h-9 w-full appearance-none rounded-[6px] border border-hairline bg-sheet pr-8 pl-3 text-sm text-ink disabled:opacity-50 aria-[invalid=true]:border-clash",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute top-2.5 right-2.5 size-4 text-graphite" aria-hidden />
    </div>
  );
}
