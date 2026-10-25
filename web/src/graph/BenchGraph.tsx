// The bench (design §2, §7): React Flow with fixed positions. The graph grows as events touch nodes.
import { type Edge, type Node, Position, ReactFlow, ReactFlowProvider, useReactFlow, ViewportPortal } from "@xyflow/react";
import { type KeyboardEvent, type RefObject, useEffect, useMemo, useRef } from "react";
import type { RunState } from "../run/types";
import { useReducedMotion } from "../ui/effects/useReducedMotion";
import { BenchEdgeView, type BenchEdgeData } from "./edges/BenchEdgeView";
import { BANDS, CANVAS, edgeGeometry, rectFor } from "./layout";
import { BenchNodeCard } from "./nodes/BenchNodeCard";
import { ClashNode } from "./nodes/ClashNode";

const nodeTypes = {
  agent: BenchNodeCard,
  source: BenchNodeCard,
  vendor: BenchNodeCard,
  gate: BenchNodeCard,
  engine: BenchNodeCard,
  model: BenchNodeCard,
  ruling: BenchNodeCard,
  clash: ClashNode,
};
const edgeTypes = { forward: BenchEdgeView, sendback: BenchEdgeView, replan: BenchEdgeView, thread: BenchEdgeView };

export type Selection = { kind: "node"; id: string } | { kind: "edge"; id: string } | { kind: "event"; index: number } | null;

export interface BenchGraphProps {
  state: RunState;
  speed: number;
  emptyText: string;
  waiting: { agent: string; text: string } | null;
  onSelect: (selection: Selection) => void;
}

function Bands({ empty, emptyText }: { empty: boolean; emptyText: string }) {
  return (
    <ViewportPortal>
      {Object.entries(BANDS).map(([key, band]) => (
        <div
          key={key}
          aria-hidden
          className="pointer-events-none absolute rounded-panel border border-dashed border-hairline"
          style={{ left: band.x, top: band.y, width: band.w, height: band.h }}
        >
          <span className="absolute -top-2.5 left-3 bg-well px-1 text-[12px] leading-4 text-graphite">{band.label}</span>
        </div>
      ))}
      {empty ? (
        <p className="pointer-events-none absolute w-[400px] text-center text-md text-graphite" style={{ left: CANVAS.width / 2 - 200, top: 330 }}>
          {emptyText}
        </p>
      ) : null}
    </ViewportPortal>
  );
}

const BOUNDS = { x: -10, y: -14, width: CANVAS.width + 20, height: CANVAS.height + 28 };

/** Fits the whole fixed canvas into the container whenever the container's size changes. */
function Fit({ box }: { box: RefObject<HTMLDivElement | null> }) {
  const flow = useReactFlow();
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    let frame = 0;
    const fit = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => flow.fitBounds(BOUNDS, { padding: 0.02 }));
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(el);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [flow, box]);
  return null;
}

function Graph({ state, speed, emptyText, waiting, onSelect }: BenchGraphProps) {
  const reducedMotion = useReducedMotion();
  const modelOrder = useMemo(
    () =>
      Object.values(state.nodes)
        .filter((n) => n.kind === "model")
        .sort((a, b) => a.firstIndex - b.firstIndex)
        .map((n) => n.id),
    [state.nodes],
  );

  // Every size and handle is known from the layout, so React Flow never waits on measuring (the
  // server-render path): nodes and edges appear the moment an event creates them.
  const nodes: Node[] = useMemo(
    () =>
      Object.values(state.nodes).map((node) => {
        const r = rectFor(node.id, modelOrder);
        const sized = {
          position: { x: r.x, y: r.y },
          width: r.w,
          height: r.h,
          measured: { width: r.w, height: r.h },
          handles: [
            { type: "target" as const, position: Position.Left, x: 0, y: r.h / 2, width: 1, height: 1 },
            { type: "source" as const, position: Position.Right, x: r.w - 1, y: r.h / 2, width: 1, height: 1 },
          ],
          draggable: false,
          selectable: true,
        };
        if (node.kind === "clash") {
          return { id: node.id, type: "clash", ...sized, data: { items: state.clash, width: r.w, height: r.h }, ariaLabel: "Contradiction card. Press Enter to inspect." };
        }
        return {
          id: node.id,
          type: node.kind,
          ...sized,
          data: { node, active: state.activeNode === node.id, width: r.w, height: r.h },
          ariaLabel: `${node.label}. Press Enter to inspect.`,
        };
      }),
    [state.nodes, state.activeNode, state.clash, modelOrder],
  );

  const lastIndex = state.index - 1;
  const edges: Edge[] = useMemo(
    () =>
      Object.values(state.edges)
        .filter((edge) => state.nodes[edge.from] && state.nodes[edge.to])
        .map((edge) => {
          const geo = edgeGeometry(edge.type, rectFor(edge.from, modelOrder), rectFor(edge.to, modelOrder));
          const isWaiting = waiting !== null && edge.to === "engine" && edge.from === waiting.agent && edge.type === "forward";
          const data: BenchEdgeData = {
            edge,
            ...geo,
            travel: edge.lastIndex === lastIndex,
            travelMs: Math.min(edge.lastLatencyMs ?? 600, 1200) / Math.max(1, speed),
            reducedMotion,
            waiting: isWaiting ? waiting.text : null,
          };
          return { id: edge.id, source: edge.from, target: edge.to, type: edge.type, data, selectable: true, focusable: true };
        }),
    [state.edges, state.nodes, lastIndex, modelOrder, reducedMotion, speed, waiting],
  );

  const box = useRef<HTMLDivElement>(null);
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter") return;
    const target = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node, .react-flow__edge");
    const id = target?.dataset.id ?? target?.getAttribute("data-id") ?? null;
    if (!id) return;
    onSelect(target?.classList.contains("react-flow__edge") ? { kind: "edge", id } : { kind: "node", id });
  };

  return (
    <div ref={box} className="h-full w-full" onKeyDown={onKeyDown} data-testid="bench">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        nodesFocusable
        edgesFocusable
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnDoubleClick={false}
        minZoom={0.3}
        maxZoom={2}
        onNodeClick={(_, node) => onSelect({ kind: "node", id: node.id })}
        onEdgeClick={(_, edge) => onSelect({ kind: "edge", id: edge.id })}
        onPaneClick={() => onSelect(null)}
        proOptions={{ hideAttribution: false }}
      >
        <Bands empty={state.index === 0} emptyText={emptyText} />
        <Fit box={box} />
      </ReactFlow>
    </div>
  );
}

export function BenchGraph(props: BenchGraphProps) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}
