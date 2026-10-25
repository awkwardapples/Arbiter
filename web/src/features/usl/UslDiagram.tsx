import { Background, Controls, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import type { RegistryQuery } from "../../api/types";
import { layoutGraph } from "./layout";
import { type UslModel, relationships } from "./model";
import { TableNode } from "./TableNode";

const NODE_TYPES = { table: TableNode };

/** The USL vendor_risk as an ERD: one node per table, solid declared keys, dashed query-only joins. */
export function UslDiagram({
  model,
  registry,
  rowCounts,
  selected,
  onSelect,
}: {
  model: UslModel;
  registry: RegistryQuery[];
  rowCounts?: Record<string, number>;
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const rels = useMemo(() => relationships(model, registry), [model, registry]);
  const { nodes, edges } = useMemo(
    () => layoutGraph(model.tables, rels, selected, onSelect, rowCounts),
    [model.tables, rels, selected, onSelect, rowCounts],
  );
  return (
    <div className="flex flex-col gap-3">
      <div className="h-[620px] overflow-hidden rounded-panel border border-hairline" data-testid="usl-diagram">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.04 }}
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => onSelect(node.id)}
          minZoom={0.3}
        >
          <Background gap={24} color="var(--color-hairline)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="flex flex-wrap gap-6 text-xs text-graphite">
        <span className="inline-flex items-center gap-2">
          <svg width="32" height="6" aria-hidden>
            <line x1="0" y1="3" x2="32" y2="3" stroke="var(--color-record)" strokeWidth="1.5" />
          </svg>
          Declared foreign key
        </span>
        <span className="inline-flex items-center gap-2">
          <svg width="32" height="6" aria-hidden>
            <line x1="0" y1="3" x2="32" y2="3" stroke="var(--color-record)" strokeWidth="1.5" strokeDasharray="6 4" />
          </svg>
          Joined in the query, not a declared key
        </span>
      </div>
      <details className="rounded-panel border border-hairline bg-sheet px-4 py-3">
        <summary className="cursor-pointer text-sm font-semibold text-ink">Keys and joins as a list ({rels.length})</summary>
        <ul className="mt-2 flex flex-col gap-1 text-sm" data-testid="usl-relationships">
          {rels.map((rel) => (
            <li key={rel.id} data-testid={`rel-${rel.kind}`}>
              <span className="font-mono text-xs text-ink">{rel.on}</span>{" "}
              <span className="text-graphite">
                {rel.kind === "declared" ? "declared foreign key" : `joined in the query, not a declared key (${rel.queryId})`}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
