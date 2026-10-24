import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { cn } from "./lib/cn";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border px-2 py-0 text-xs font-medium whitespace-nowrap", {
  variants: {
    tone: {
      neutral: "border-hairline bg-well text-graphite",
      ink: "border-ink/20 bg-ink-tint text-ink",
      record: "border-record/30 bg-record-tint text-record",
      claim: "border-claim/30 bg-claim-tint text-claim",
      reason: "border-reason/30 bg-reason-tint text-reason",
      clash: "border-clash/30 bg-clash-tint text-clash",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends ComponentProps<"span">, VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span data-slot="badge" className={cn(badgeVariants({ tone }), className)} {...props} />;
}
