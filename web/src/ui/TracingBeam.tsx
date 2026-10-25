// After Aceternity's Tracing Beam: a line down the left of a long column, filled as you scroll past it, with a
// dot at the reading position (design §10, Case: Decision). Solid ink on hairline instead of the gradient.
import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { type ReactNode, useRef } from "react";
import { useReducedMotion } from "./effects/useReducedMotion";
import { cn } from "./lib/cn";

export function TracingBeam({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 30%", "end 70%"] });
  const smooth = useSpring(scrollYProgress, { stiffness: 300, damping: 40 });
  const progress = reduced ? scrollYProgress : smooth;
  const height = useTransform(progress, (p) => `${Math.round(Math.min(1, Math.max(0, p)) * 100)}%`);
  return (
    <div ref={ref} className={cn("relative pl-8", className)}>
      <div aria-hidden className="absolute top-2 bottom-2 left-2.5 w-px bg-hairline">
        <motion.div className="absolute top-0 left-0 w-px bg-ink" style={{ height }} />
        <motion.span className="absolute -left-[4px] size-[9px] -translate-y-1/2 rounded-full border-2 border-ink bg-sheet" style={{ top: height }} />
      </div>
      {children}
    </div>
  );
}
