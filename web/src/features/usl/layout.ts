// Dagre, left to right, for the USL ERD only (design §7: the bench keeps fixed positions).
import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";
import type { Relationship, UslTable } from "./model";

export const TABLE_WIDTH = 260;
export const TABLE_HEIGHT = 128;

export interface TableNodeData extends Record<string, unknown> {
  table: UslTable;
  selected: boolean;
  onSelect: (name: string) => void;
}

export interface RelationshipEdgeData extends Record<string, unknown> {
  relationship: Relationship;
}

export function layoutGraph(
  tables: UslTable[],
  rels: Relationship[],
  selected: string | null,
  onSelect: (name: string) => void,
): { nodes: Node<TableNodeData>[]; edges: Edge<RelationshipEdgeData>[] } {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 24, ranksep: 64, marginx: 16, marginy: 16 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const table of tables) g.setNode(table.name, { width: TABLE_WIDTH, height: TABLE_HEIGHT });
  // The referenced table sits to the right, so arrows read "this row belongs to that one".
  // Undeclared joins carry a label, so dagre reserves room for it between the ranks.
  for (const rel of rels) {
    g.setEdge(rel.from, rel.to, rel.kind === "undeclared" ? { width: 230, height: 16, labelpos: "c" } : {});
  }
  dagre.layout(g);

  const nodes: Node<TableNodeData>[] = tables.map((table) => {
    const pos = g.node(table.name);
    return {
      id: table.name,
      type: "table",
      position: { x: pos.x - TABLE_WIDTH / 2, y: pos.y - TABLE_HEIGHT / 2 },
      data: { table, selected: table.name === selected, onSelect },
      focusable: true,
    };
  });
  const edges: Edge<RelationshipEdgeData>[] = rels.map((rel) => {
    const undeclared = rel.kind === "undeclared";
    return {
      id: rel.id,
      source: rel.from,
      target: rel.to,
      type: "smoothstep",
      data: { relationship: rel },
      label: undeclared ? "joined in the query, not a declared key" : undefined,
      labelStyle: { fill: "var(--color-graphite)", fontSize: 12 },
      labelBgStyle: { fill: "var(--color-well)" },
      labelBgPadding: [4, 2] as [number, number],
      style: undeclared
        ? { stroke: "var(--color-record)", strokeWidth: 1.5, strokeDasharray: "6 4" }
        : { stroke: "var(--color-record)", strokeWidth: 1.5 },
      className: undeclared ? "usl-edge-undeclared" : "usl-edge-declared",
    };
  });
  return { nodes, edges };
}
