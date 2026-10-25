// One bench node (design §7.1 anatomy): icon, label, role, a 4 px state ring and a count badge.
import { Handle, type NodeProps, Position } from "@xyflow/react";
import { createElement } from "react";
import { KIND_COLOR } from "../../run/nodes";
import type { BenchNode } from "../../run/types";
import { GlowingEffect } from "../../ui/effects/GlowingEffect";
import { cn } from "../../ui/lib/cn";
import { iconFor } from "./icons";

export interface BenchNodeData extends Record<string, unknown> {
  node: BenchNode;
  active: boolean;
  width: number;
  height: number;
}

const RADIUS: Record<BenchNode["kind"], number> = {
  agent: 10,
  source: 4,
  vendor: 4,
  gate: 10,
  engine: 999,
  model: 999,
  ruling: 8,
  clash: 8,
};

const TINT: Partial<Record<BenchNode["kind"], string>> = {
  source: "bg-record-tint",
  vendor: "bg-claim-tint",
  gate: "bg-claim-tint",
  engine: "bg-reason-tint",
  model: "bg-reason-tint",
};

function ringColor(node: BenchNode): string {
  if (node.ring === "idle") return "var(--color-hairline)";
  if (node.ring === "fallback") return "var(--color-claim)";
  if (node.ring === "failed") return "var(--color-clash)";
  if (node.id === "engine" && node.label.startsWith("Deterministic")) return "var(--color-graphite)";
  return KIND_COLOR[node.kind];
}

const hidden = "!h-1 !w-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

export function BenchNodeCard({ data }: NodeProps) {
  const { node, active, width, height } = data as BenchNodeData;
  const radius = RADIUS[node.kind];
  const still = node.id === "engine" && node.label.startsWith("Deterministic");
  const pill = radius > 100;
  const color = ringColor(node);
  return (
    <div
      data-node={node.id}
      data-ring={node.ring}
      data-active={active ? "true" : undefined}
      className={cn("relative flex items-center gap-2.5 border border-hairline bg-sheet pr-3 text-left", TINT[node.kind], still && "bg-well", pill ? "pl-4" : "pl-3")}
      style={{ width, height, borderRadius: pill ? height / 2 : radius }}
      aria-label={`${node.label}: ${node.role}${node.count ? `, ${node.count} ${node.countNoun}` : ""}${node.fellBack ? ", fell back" : ""}`}
    >
      {active && !still ? <GlowingEffect color={KIND_COLOR[node.kind]} radius={pill ? height / 2 : radius} /> : null}
      {!pill ? (
        <span
          aria-hidden
          className={cn("absolute top-2 bottom-2 left-0 w-1 rounded-r", node.ring === "active" && "animate-ring-pulse")}
          style={{ background: color }}
        />
      ) : null}
      {createElement(iconFor(node.id), {
        className: "size-4 shrink-0",
        style: { color: node.ring === "idle" ? "var(--color-graphite)" : color },
        "aria-hidden": true,
      })}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] leading-[18px] font-semibold text-ink">{node.label}</span>
        <span className="block truncate text-[12px] leading-[16px] text-graphite">{node.role}</span>
      </span>
      {node.count > 0 && node.countNoun ? (
        <span className="absolute -top-2 right-2 rounded-full border border-hairline bg-sheet px-1.5 text-[11px] leading-4 font-medium text-graphite">
          {node.count} {node.countNoun}
        </span>
      ) : null}
      {node.fellBack ? (
        <span className="absolute -bottom-2 left-3 rounded-full border border-claim/40 bg-sheet px-1.5 text-[11px] leading-4 font-medium text-claim">fell back</span>
      ) : node.note ? (
        <span className="absolute -bottom-2 left-3 max-w-[90%] truncate rounded-full border border-hairline bg-sheet px-1.5 text-[11px] leading-4 text-graphite">{node.note}</span>
      ) : null}
      <Handle type="target" position={Position.Left} className={hidden} isConnectable={false} />
      <Handle type="source" position={Position.Right} className={hidden} isConnectable={false} />
    </div>
  );
}
