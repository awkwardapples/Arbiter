// After Magic UI's Border Beam: one light runs once around the card (1.2 s), then stops (design §7.4).
// Recoloured to ink. Under reduced motion it renders nothing.
import { useEffect, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

export function BorderBeam({ color = "var(--color-ink)", duration = 1200, radius = 8 }: { color?: string; duration?: number; radius?: number }) {
  const reduced = useReducedMotion();
  const [running, setRunning] = useState(true);
  useEffect(() => {
    const id = setTimeout(() => setRunning(false), duration + 50);
    return () => clearTimeout(id);
  }, [duration]);
  if (reduced || !running) return null;
  return (
    <span aria-hidden data-beam className="pointer-events-none absolute inset-0 overflow-hidden" style={{ borderRadius: radius }}>
      <span
        className="arbiter-beam absolute size-10"
        style={{
          ["--beam-duration" as string]: `${duration}ms`,
          ["--beam-radius" as string]: `${radius}px`,
          background: `radial-gradient(closest-side, ${color}, transparent)`,
          opacity: 0.6,
        }}
      />
    </span>
  );
}
