import { CheckCircle2, XCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import type { Parity } from "./api";

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** The parity file's DQ rules grouped by table, with the invalid keys it recorded for each table. */
export function DataQuality({ parity }: { parity: Parity }) {
  const tables = [...new Set(parity.rules.map((r) => r.table))];
  const invalid = new Map(parity.invalid_by_table.map((i) => [i.table, i]));
  const q = parity.query_comparisons;
  const k = parity.kev_checks;
  return (
    <div className="flex flex-col gap-4" data-testid="usl-dq">
      <p className="flex items-center gap-2 text-sm text-ink" data-testid="usl-parity-summary">
        {parity.all_green ? <CheckCircle2 className="size-4 text-record" aria-hidden /> : <XCircle className="size-4 text-clash" aria-hidden />}
        {q.ok} of {q.total} registry comparisons matched; {k.ok} of {k.total} KEV checks.
      </p>
      <p className="text-xs text-graphite">
        Each rule runs in Zetaris and in the DuckDB mirror, and both must flag the same rows. From the parity run on the{" "}
        {parity.query_layer === "usl" ? "USL" : parity.query_layer} layer, recorded in <span className="font-mono">docs/passes/P1-B_parity.json</span>.
      </p>
      {tables.map((table) => {
        const rules = parity.rules.filter((r) => r.table === table);
        const flagged = invalid.get(table);
        const keys = flagged?.zetaris ?? [];
        return (
          <section key={table} className="rounded-panel border border-hairline bg-sheet" data-testid={`dq-table-${table}`}>
            <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-hairline px-4 py-2">
              <h4 className="text-sm font-semibold text-ink">
                <span className="font-mono">{table}</span> <span className="font-normal text-graphite">{plural(rules.length, "rule")}</span>
              </h4>
              <p className={keys.length ? "text-sm text-clash" : "text-sm text-graphite"}>
                {keys.length
                  ? `Invalid rows on ${table}: ${keys.join(", ")}${flagged?.ok ? " (Zetaris and mirror agree)" : " (Zetaris and mirror disagree)"}`
                  : flagged
                    ? `No invalid rows on ${table}${flagged.ok ? " (Zetaris and mirror agree)" : ""}`
                    : "Not checked in the parity run"}
              </p>
            </header>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>A row is valid when</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-mono text-xs text-graphite">{rule.id}</TableCell>
                    <TableCell className="font-mono text-xs text-ink">{rule.expr}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>
        );
      })}
    </div>
  );
}
