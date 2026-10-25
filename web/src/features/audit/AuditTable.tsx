import { Link } from "react-router";
import { formatUtc } from "../../run/mode";
import { Callout } from "../../ui/Callout";
import { EmptyState } from "../../ui/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { eventWords, useAuditRecent } from "./audit";

/** The 50 newest audit entries. The API serves sequence, time, case and kind; the payload stays in the log. */
export function AuditTable() {
  const recent = useAuditRecent();
  if (recent.isError) {
    return (
      <Callout tone="error" title="Recent audit entries did not load.">
        {recent.error.message}
      </Callout>
    );
  }
  if (!recent.data) return <p className="text-sm text-graphite">Loading the audit log…</p>;
  if (recent.data.length === 0) {
    return (
      <EmptyState title="No audit entries yet.">
        Reviews, approvals, precedents and their feedback are written here. Review a case to add the first entry.
      </EmptyState>
    );
  }
  return (
    <Table data-testid="audit-table">
      <TableHeader>
        <TableRow>
          <TableHead>Entry</TableHead>
          <TableHead>Time</TableHead>
          <TableHead>What happened</TableHead>
          <TableHead>Case</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {recent.data.map((event) => (
          <TableRow key={event.seq} data-testid="audit-row">
            <TableCell className="font-mono text-xs text-graphite">{event.seq}</TableCell>
            <TableCell className="text-xs text-graphite">{formatUtc(event.timestamp) ?? event.timestamp}</TableCell>
            <TableCell>
              {eventWords(event.event_type)}
              <span className="ml-2 font-mono text-xs text-graphite">{event.event_type}</span>
            </TableCell>
            <TableCell>
              <Link to={`/cases/${encodeURIComponent(event.case_id)}`} className="font-mono text-xs text-record hover:underline">
                {event.case_id}
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
