import { Handle, type NodeProps, Position, type Node } from "@xyflow/react";
import { ChevronDown, ChevronRight, KeyRound, Table2 } from "lucide-react";
import { useState } from "react";
import { cn } from "../../ui/lib/cn";
import type { TableNodeData } from "./layout";

/** One USL table: name, description, primary key, and its columns on demand. */
export function TableNode({ data }: NodeProps<Node<TableNodeData>>) {
  const { table, selected, onSelect } = data;
  const [open, setOpen] = useState(false);
  return (
    <div
      data-testid={`usl-table-${table.name}`}
      onClick={() => onSelect(table.name)}
      onKeyDown={(e) => {
        if (e.key === "Enter") onSelect(table.name);
      }}
      className={cn(
        "w-[260px] cursor-pointer rounded-source border bg-sheet text-left",
        selected ? "border-record ring-2 ring-record/30" : "border-hairline",
      )}
    >
      <Handle type="target" position={Position.Left} className="!border-0 !bg-record" />
      <Handle type="source" position={Position.Right} className="!border-0 !bg-record" />
      <div className="flex items-center gap-2 border-l-4 border-record px-3 pt-2">
        <Table2 className="size-4 text-record" aria-hidden />
        <span className="font-mono text-xs font-semibold text-ink">{table.name}</span>
      </div>
      <p className="line-clamp-2 border-l-4 border-record px-3 text-xs text-graphite">{table.description}</p>
      <p className="flex items-center gap-1 border-l-4 border-record px-3 pt-1 text-xs text-ink">
        <KeyRound className="size-3 text-graphite" aria-hidden />
        <span className="sr-only">Primary key:</span>
        <span className="font-mono">{table.primary_key.join(", ") || "none"}</span>
      </p>
      <button
        type="button"
        className="nodrag flex w-full items-center gap-1 border-l-4 border-record px-3 pt-1 pb-2 text-xs text-graphite hover:text-ink"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        {open ? <ChevronDown className="size-3" aria-hidden /> : <ChevronRight className="size-3" aria-hidden />}
        {table.columns.length} columns
      </button>
      {open ? (
        <ul className="max-h-48 overflow-y-auto border-t border-hairline px-3 py-2 text-xs" data-testid={`usl-columns-${table.name}`}>
          {table.columns.map((column) => (
            <li key={column.name} className="flex justify-between gap-2">
              <span className="font-mono text-ink">{column.name}</span>
              <span className="font-mono text-graphite">{column.data_type}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
