import { Popover as PopoverPrimitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "./lib/cn";

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;

export function PopoverContent({ className, ...props }: ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        sideOffset={6}
        align="start"
        className={cn("z-50 w-80 rounded-panel border border-hairline bg-sheet p-4 text-sm text-ink shadow-float outline-none", className)}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}
