import type { HTMLAttributes } from "react";
import { cn } from "./lib/cn";

/** Source Serif 4: only where Arbiter rules or writes (design §3.2). Measure ≤ 72 characters. */
export function Serif({ className, as: Tag = "p", ...props }: HTMLAttributes<HTMLElement> & { as?: "p" | "h2" | "h3" | "div" | "blockquote" }) {
  return <Tag className={cn("max-w-[72ch] font-serif text-md leading-[28px] text-ink", className)} {...props} />;
}
