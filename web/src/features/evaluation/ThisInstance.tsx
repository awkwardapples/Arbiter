import { useHealth } from "../../api/queries";
import { OUTCOME_CLASS } from "../../ui/outcome";
import { OutcomeBadge } from "../../ui/OutcomeBadge";
import { useCases } from "../usl/api";

/** Cases this API has decided, by outcome, and what it ran on. Not an evaluation: there are no labels here. */
export function ThisInstance() {
  const cases = useCases();
  const health = useHealth();
  const counts = new Map<string, number>();
  for (const c of cases.data ?? []) counts.set(c.outcome, (counts.get(c.outcome) ?? 0) + 1);
  const outcomes = [...Object.keys(OUTCOME_CLASS).filter((o) => counts.has(o)), ...[...counts.keys()].filter((o) => !(o in OUTCOME_CLASS))];
  const data = health.data?.mode?.data;
  const llm = (health.data?.provider as { provider_resolved?: string } | null | undefined)?.provider_resolved ?? health.data?.mode?.llm;
  const total = cases.data?.length ?? 0;
  return (
    <div className="flex flex-col gap-3" data-testid="eval-instance">
      <p className="text-sm text-ink">
        {cases.data
          ? total === 0
            ? "No cases on this instance yet. Start an assessment to add one."
            : `${total} ${total === 1 ? "case" : "cases"} decided on this instance.`
          : "Loading cases…"}
      </p>
      {outcomes.length ? (
        <ul className="flex flex-wrap gap-3">
          {outcomes.map((o) => (
            <li key={o} className="flex items-center gap-2 rounded-panel border border-hairline bg-sheet px-3 py-2 text-sm">
              <OutcomeBadge outcome={o} />
              <span className="font-semibold text-ink">{counts.get(o)}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <dl className="grid gap-x-6 gap-y-1 text-sm md:grid-cols-[max-content_1fr]">
        <dt className="text-graphite">Data backend</dt>
        <dd className="font-mono text-xs text-ink">{data ?? "unknown"}</dd>
        <dt className="text-graphite">Model provider</dt>
        <dd className="font-mono text-xs text-ink">{llm ?? "unknown"}</dd>
      </dl>
    </div>
  );
}
