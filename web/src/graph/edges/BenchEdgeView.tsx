// All four edge styles of design §7.2. Paths come from layout.ts; labels are a hover pill and a count.
import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from "@xyflow/react";
import { useState } from "react";
import type { BenchEdge } from "../../run/types";
import { TravelDot } from "../TravelDot";

export interface BenchEdgeData extends Record<string, unknown> {
  edge: BenchEdge;
  path: string;
  labelX: number;
  labelY: number;
  travel: boolean;
  travelMs: number;
  reducedMotion: boolean;
  waiting: string | null;
}

const TONE: Record<string, string> = {
  record: "var(--color-record)",
  claim: "var(--color-claim)",
  reason: "var(--color-reason)",
  clash: "var(--color-clash)",
  ink: "var(--color-ink)",
  plain: "var(--color-graphite)",
};

export function BenchEdgeView({ id, data }: EdgeProps) {
  const { edge, path, labelX, labelY, travel, travelMs, reducedMotion, waiting } = data as BenchEdgeData;
  const [hover, setHover] = useState(false);
  const color = TONE[edge.tone] ?? TONE.ink;
  const width = 1.5 + (Math.min(edge.count, 10) / 10) * 1.5;
  const dash = edge.type === "sendback" || edge.type === "replan" ? "6 5" : edge.type === "thread" ? "1.5 4" : undefined;
  const highlight = travel && reducedMotion;
  const back = edge.type === "sendback" || edge.type === "replan";
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        style={{ stroke: color, strokeWidth: highlight ? width + 1.5 : width, strokeDasharray: dash, strokeLinecap: "round", opacity: highlight ? 1 : 0.85 }}
        interactionWidth={14}
      />
      {travel && !reducedMotion ? <TravelDot key={`${edge.id}-${edge.count}`} path={path} color={color} durationMs={travelMs} /> : null}
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-auto absolute"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
        >
          {waiting ? (
            <span className="rounded-full border border-reason/40 bg-sheet px-2 py-0.5 text-[11px] font-medium whitespace-nowrap text-reason shadow-float">{waiting}</span>
          ) : back || edge.count > 1 || edge.type === "thread" ? (
            <span
              className="rounded-full border bg-sheet px-1.5 text-[11px] leading-4 font-medium whitespace-nowrap"
              style={{ borderColor: color, color }}
            >
              {back && edge.loopTotal ? `${edge.count} of ${edge.loopTotal}` : edge.type === "thread" ? "≠" : `×${edge.count}`}
            </span>
          ) : (
            <span className="block size-2 rounded-full" style={{ background: color, opacity: 0.4 }} />
          )}
          {hover ? (
            <span className="absolute top-full left-1/2 z-10 mt-1 w-max max-w-[280px] -translate-x-1/2 rounded-[6px] bg-ink px-2 py-1 text-[12px] leading-4 text-sheet shadow-float">
              {edge.lastLabel}
            </span>
          ) : null}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
