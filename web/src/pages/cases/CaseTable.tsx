import { type KeyboardEvent, useRef } from "react";
import type { QueueItem } from "../../features/case/types";
import { relativeWords, timeWords } from "../../features/case/words";
import { Identifier } from "../../ui/Identifier";
import { OutcomeBadge } from "../../ui/OutcomeBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { Tooltip } from "../../ui/tooltip";

const STATUS_WORDS: Record<string, string> = { success: "Complete", error: "Failed", escalated: "Escalated safely" };

/** Cases in server order (residual risk, highest first). Arrow keys move between rows; Enter opens one. */
export function CaseTable({ rows, onOpen }: { rows: QueueItem[]; onOpen: (caseId: string) => void }) {
  const refs = useRef<Array<HTMLTableRowElement | null>>([]);

  const onKey = (event: KeyboardEvent<HTMLTableRowElement>, index: number) => {
    const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
    if (step) {
      event.preventDefault();
      refs.current[Math.min(rows.length - 1, Math.max(0, index + step))]?.focus();
    } else if (event.key === "Enter") {
      event.preventDefault();
      onOpen(rows[index].case_id);
    }
  };

  return (
    <Table data-testid="cases-table" aria-label="Cases, highest residual risk first">
      <TableHeader>
        <TableRow>
          <TableHead>Case</TableHead>
          <TableHead>Decision</TableHead>
          <TableHead>Tier</TableHead>
          <TableHead>Residual risk</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, index) => (
          <TableRow
            key={row.case_id}
            ref={(el) => {
              refs.current[index] = el;
            }}
            data-testid="case-row"
            data-case-id={row.case_id}
            tabIndex={index === 0 ? 0 : -1}
            onKeyDown={(event) => onKey(event, index)}
            onClick={() => onOpen(row.case_id)}
            className="cursor-pointer hover:bg-well focus-visible:bg-well"
          >
            <TableCell>
              <div className="font-medium text-ink">{row.vendor}</div>
              {/* Copying the id should not open the case. */}
              <span onClick={(event) => event.stopPropagation()}>
                <Identifier value={row.case_id} />
              </span>
            </TableCell>
            <TableCell>
              <OutcomeBadge outcome={row.outcome} />
            </TableCell>
            <TableCell>{row.tier}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <span className="w-8 text-right tabular-nums">{row.residual_risk}</span>
                <span className="h-1.5 w-16 overflow-hidden rounded-full bg-well" aria-hidden>
                  <span className="block h-full bg-ink" style={{ width: `${Math.max(0, Math.min(100, row.residual_risk))}%` }} />
                </span>
              </div>
            </TableCell>
            <TableCell className="text-graphite">{STATUS_WORDS[row.status] ?? row.status}</TableCell>
            <TableCell className="text-graphite">
              <Tooltip content={timeWords(row.created)}>
                <time dateTime={row.created}>{relativeWords(row.created)}</time>
              </Tooltip>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
