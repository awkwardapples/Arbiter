import { formatUtc } from "../../run/mode";
import { Badge } from "../../ui/badge";
import { DocLink } from "../../ui/DocLink";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { type EvalSummary, SYSTEM_WORDS, orderedSystems, publishedNotes, rateText, wilsonText } from "./evaluation";

const ms = (value: number | null | undefined) => (value == null ? "–" : `${(value / 1000).toFixed(1)} s`);

/** The published live evaluation: one row per system, the models seen, and the notes as written. */
export function LiveTable({ summary, markdown }: { summary: EvalSummary; markdown: string | null }) {
  const rows = orderedSystems(summary);
  const notes = publishedNotes(markdown);
  return (
    <div className="flex flex-col gap-4" data-testid="eval-live">
      <p className="text-sm text-graphite">
        Published {formatUtc(summary.generated_at) ?? summary.generated_at}. Data and models:{" "}
        <span className="font-mono text-xs">
          {summary.mode.data} / {summary.mode.llm}
        </span>
        {summary.synthetic ? ". Synthetic vendors." : "."}
      </p>
      <Table data-testid="eval-table">
        <TableHeader>
          <TableRow>
            <TableHead>System</TableHead>
            <TableHead>n</TableHead>
            <TableHead>Accuracy</TableHead>
            <TableHead>Unsafe approvals</TableHead>
            <TableHead>Abstention</TableHead>
            <TableHead>Contradiction recall</TableHead>
            <TableHead>p50</TableHead>
            <TableHead>p95</TableHead>
            <TableHead>Model calls per case</TableHead>
            <TableHead>Fallback rate</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(([key, s]) => (
            <TableRow key={key} data-testid={`eval-row-${key}`}>
              <TableCell>
                <span className="font-semibold text-ink">{SYSTEM_WORDS[key] ?? key}</span>
                <span className="block font-mono text-xs text-graphite">
                  {s.run.mode.data} / {s.run.mode.llm}
                </span>
              </TableCell>
              <TableCell>{s.run.n}</TableCell>
              <TableCell>{rateText(s.accuracy)}</TableCell>
              <TableCell>
                {s.unsafe_approvals.count}/{s.unsafe_approvals.n}
              </TableCell>
              <TableCell>{rateText(s.abstention_rate)}</TableCell>
              <TableCell>{rateText(s.contradiction_recall)}</TableCell>
              <TableCell className="whitespace-nowrap">{ms(s.run.latency_ms.p50)}</TableCell>
              <TableCell className="whitespace-nowrap">{ms(s.run.latency_ms.p95)}</TableCell>
              <TableCell>{s.run.model_calls_per_case.toFixed(1)}</TableCell>
              <TableCell>{rateText(s.run.fallback_rate)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <section className="rounded-panel border border-claim/30 bg-claim-tint px-4 py-3" data-testid="eval-small-n">
        <h3 className="text-sm font-semibold text-ink">n is small</h3>
        <p className="text-sm text-graphite">Accuracy with its Wilson 95% interval:</p>
        <ul className="mt-1 text-sm text-ink">
          {rows.map(([key, s]) => (
            <li key={key}>
              {SYSTEM_WORDS[key] ?? key}: {rateText(s.accuracy)}
              {wilsonText(s.accuracy) ? `, interval ${wilsonText(s.accuracy)}` : ""}
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-ink">Models that served the calls (from the traces)</h3>
        <div className="flex flex-wrap gap-2" data-testid="eval-models">
          {summary.model_ids.length ? (
            summary.model_ids.map((id) => (
              <Badge key={id} tone="reason" className="font-mono">
                {id}
              </Badge>
            ))
          ) : (
            <span className="text-sm text-graphite">No model calls in this run.</span>
          )}
        </div>
      </div>

      <section className="flex flex-col gap-2" data-testid="eval-notes">
        <h3 className="text-sm font-semibold text-ink">As published</h3>
        {summary.baseline_status ? (
          <p className="font-serif text-md text-ink" data-testid="eval-baseline-status">
            {summary.baseline_status}
          </p>
        ) : null}
        {notes.map((line) => (
          <p key={line} className="font-serif text-sm text-ink">
            {line}
          </p>
        ))}
        <p className="text-sm text-graphite">
          What the baseline result means, and why it is not a comparison yet: <DocLink path="docs/EVALUATION.md" anchor="discussion">the Discussion in docs/EVALUATION.md</DocLink>.
        </p>
      </section>
    </div>
  );
}
