import { ThumbsDown, ThumbsUp } from "lucide-react";
import { Link } from "react-router";
import { formatUtc } from "../../run/mode";
import { Badge } from "../../ui/badge";
import { Callout } from "../../ui/Callout";
import { EmptyState } from "../../ui/EmptyState";
import { Identifier } from "../../ui/Identifier";
import { useCases } from "../usl/api";
import { MEMORY_EMPTY, precedentView, usePrecedents } from "./precedents";

function when(date: Date | null): string {
  return date ? (formatUtc(date.toISOString()) ?? "") : "";
}

/** Every precedent H-MEM holds, with where it came from and how reviewers have rated it since. */
export function PrecedentList() {
  const precedents = usePrecedents();
  const cases = useCases();
  if (precedents.isError) {
    return (
      <Callout tone="error" title="Precedents did not load.">
        {precedents.error.message}
      </Callout>
    );
  }
  if (!precedents.data) return <p className="text-sm text-graphite">Loading precedents…</p>;
  if (precedents.data.length === 0) return <EmptyState title={MEMORY_EMPTY} />;
  const vendorOf = new Map((cases.data ?? []).map((c) => [c.case_id, c.vendor]));
  return (
    <ul className="flex flex-col gap-4" data-testid="memory-list">
      {precedents.data.map((raw) => {
        const p = precedentView(raw);
        const helpful = p.feedback.filter((f) => f.kind === "helpful").length;
        const wrong = p.feedback.filter((f) => f.kind === "wrong").length;
        return (
          <li key={p.id} className="rounded-panel border border-hairline bg-sheet" data-testid={`precedent-${p.id}`}>
            <header className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-3">
              <div className="flex items-center gap-3">
                <Identifier value={p.id} />
                {p.controlId ? <Badge tone="record">Exception for control {p.controlId}</Badge> : null}
              </div>
              {p.confidence != null ? (
                <span className="text-sm text-graphite">Memory confidence {Math.round(p.confidence * 100)}%</span>
              ) : null}
            </header>
            <dl className="grid gap-x-6 gap-y-2 px-5 py-3 text-sm md:grid-cols-[max-content_1fr]">
              <dt className="text-graphite">From</dt>
              <dd>
                {p.fromCase ? (
                  <>
                    <Link to={`/cases/${encodeURIComponent(p.fromCase)}`} className="font-mono text-xs text-record hover:underline">
                      {p.fromCase}
                    </Link>
                    {vendorOf.get(p.fromCase) ? <span className="ml-2 text-ink">{vendorOf.get(p.fromCase)}</span> : null}
                  </>
                ) : (
                  <span className="text-graphite">Not recorded</span>
                )}
              </dd>
              <dt className="text-graphite">Approved by</dt>
              <dd>
                {p.approvedBy ?? <span className="text-graphite">Not recorded</span>}
                {p.createdAt ? <span className="ml-2 text-xs text-graphite">{when(p.createdAt)}</span> : null}
              </dd>
              <dt className="text-graphite">Used since</dt>
              <dd>{p.reads === 0 ? "Not yet retrieved for another case." : `Retrieved for ${p.reads} later ${p.reads === 1 ? "case" : "cases"}.`}</dd>
              <dt className="text-graphite">Feedback</dt>
              <dd data-testid="precedent-feedback">
                {p.feedback.length === 0 ? (
                  <span className="text-graphite">No feedback yet.</span>
                ) : (
                  <>
                    <p>
                      {helpful} helpful, {wrong} wrong.
                    </p>
                    <ul className="mt-1 flex flex-col gap-1 text-xs text-graphite">
                      {p.feedback.map((f, i) => (
                        <li key={i} className="flex items-center gap-2">
                          {f.kind === "wrong" ? (
                            <ThumbsDown className="size-3 text-clash" aria-hidden />
                          ) : (
                            <ThumbsUp className="size-3 text-record" aria-hidden />
                          )}
                          {f.kind === "wrong" ? "Marked wrong" : "Marked helpful"}
                          {f.delta != null ? ` (confidence ${f.delta > 0 ? "+" : ""}${f.delta.toFixed(2)})` : ""}, {when(f.at)}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </dd>
            </dl>
          </li>
        );
      })}
    </ul>
  );
}
