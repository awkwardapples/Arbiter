// After Aceternity's Glowing Effect: a moving conic border, recoloured to the node's kind colour at
// 40% (design §7.1). Only the single active bench node uses it. Under reduced motion: a still ring.
import { cn } from "../lib/cn";
import { useReducedMotion } from "./useReducedMotion";

export function GlowingEffect({ color, radius = 10, className }: { color: string; radius?: number; className?: string }) {
  const reduced = useReducedMotion();
  const tint = `color-mix(in srgb, ${color} 40%, transparent)`;
  if (reduced) {
    return (
      <span
        aria-hidden
        data-glow="still"
        className={cn("pointer-events-none absolute -inset-[3px] border-2", className)}
        style={{ borderColor: tint, borderRadius: radius + 3 }}
      />
    );
  }
  return (
    <span
      aria-hidden
      data-glow="moving"
      className={cn("arbiter-glow pointer-events-none absolute -inset-[3px]", className)}
      style={{ borderRadius: radius + 3, ["--glow-color" as string]: tint }}
    />
  );
}
