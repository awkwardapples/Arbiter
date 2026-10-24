// After Aceternity's Animated Tabs: the active tab's marker slides to the tab you pick (design §10, Case page only).
// Recoloured to tokens: an ink underline on sheet, no gradient. Under reduced motion the marker jumps.
import { motion } from "motion/react";
import { Tabs as TabsPrimitive } from "radix-ui";
import { useId } from "react";
import { useReducedMotion } from "./effects/useReducedMotion";
import { cn } from "./lib/cn";

export interface AnimatedTab {
  value: string;
  label: string;
}

export function AnimatedTabsList({ tabs, value, label, className }: { tabs: AnimatedTab[]; value: string; label: string; className?: string }) {
  const reduced = useReducedMotion();
  const layoutId = useId();
  return (
    <TabsPrimitive.List aria-label={label} className={cn("flex items-center gap-1 border-b border-hairline", className)}>
      {tabs.map((tab) => (
        <TabsPrimitive.Trigger
          key={tab.value}
          value={tab.value}
          className="relative px-3 pt-2 pb-2.5 text-sm font-medium text-graphite transition-colors hover:text-ink data-[state=active]:text-ink"
        >
          {tab.label}
          {tab.value === value ? (
            <motion.span
              layoutId={layoutId}
              aria-hidden
              className="absolute inset-x-1 -bottom-px h-0.5 rounded-full bg-ink"
              transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 36 }}
            />
          ) : null}
        </TabsPrimitive.Trigger>
      ))}
    </TabsPrimitive.List>
  );
}
