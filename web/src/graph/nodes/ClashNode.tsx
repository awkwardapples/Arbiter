// The clash card (design §7.3): hangs under the Evaluator; red threads come in from both sides.
import { Handle, type NodeProps, Position } from "@xyflow/react";
import { systemLabel } from "../../run/registry";
import type { ClashItem } from "../../run/types";

export interface ClashNodeData extends Record<string, unknown> {
  items: ClashItem[];
  width: number;
  height: number;
}

const hidden = "!h-1 !w-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

export function ClashNode({ data }: NodeProps) {
  const { items, width, height } = data as ClashNodeData;
  return (
    <div
      data-testid="clash-card"
      className="relative overflow-hidden rounded-panel border border-clash/50 bg-sheet px-3 py-2 text-left shadow-float"
      style={{ width, minHeight: height }}
    >
      <p className="text-[13px] leading-[18px] font-semibold text-clash">{items.length === 1 ? "Claim and record disagree" : `${items.length} contradictions`}</p>
      <ul className="mt-1 flex flex-col gap-1.5">
        {items.map((item) => (
          <li key={`${item.key ?? "summary"}-${item.fromEvent}`} className="text-[12px] leading-[16px] text-ink">
            {item.vendorValue !== undefined ? (
              <>
                <span className="block">
                  <span className="text-claim">Vendor says</span> {item.vendorValue}
                  <span className="text-graphite"> (questionnaire answer)</span>
                </span>
                <span className="block">
                  <span className="text-record">{systemLabel(item.system ?? "") || "The record"} says</span> {item.recordValue}
                  {item.recordKey ? <span className="font-mono text-[11px] text-graphite"> {item.recordKey.split("=").pop()}</span> : null}
                </span>
                {item.control ? <span className="block text-[11px] text-graphite">Affects control {item.control}</span> : null}
              </>
            ) : (
              <span>{item.text}</span>
            )}
          </li>
        ))}
      </ul>
      <Handle type="target" position={Position.Left} className={hidden} isConnectable={false} />
      <Handle type="source" position={Position.Right} className={hidden} isConnectable={false} />
    </div>
  );
}
