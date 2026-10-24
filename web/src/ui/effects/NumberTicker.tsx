// After Magic UI's Number Ticker: counts move from the old value to the new one. Plain under reduced motion.
import { animate } from "motion";
import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

export function NumberTicker({ value, className }: { value: number; className?: string }) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    if (reduced) {
      from.current = value;
      return;
    }
    const controls = animate(from.current, value, {
      duration: 0.4,
      ease: "easeOut",
      onUpdate: (v) => setShown(Math.round(v)),
    });
    from.current = value;
    return () => controls.stop();
  }, [value, reduced]);
  return (
    <span className={className} data-value={value}>
      {(reduced ? value : shown).toLocaleString("en-GB")}
    </span>
  );
}
