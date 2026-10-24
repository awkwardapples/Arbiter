// A 6 px dot that travels once along an edge when its event fires (design §7.2).
export function TravelDot({ path, color, durationMs }: { path: string; color: string; durationMs: number }) {
  return (
    <circle data-travel r={3} fill={color}>
      <animateMotion dur={`${Math.max(120, durationMs)}ms`} repeatCount="1" fill="freeze" path={path} />
    </circle>
  );
}
