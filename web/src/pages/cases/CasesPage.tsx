import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { PageHeader } from "../../app/PageHeader";
import { PENDING_SCAN_LIMIT, useCases, usePendingApprovals } from "../../features/case/queries";
import type { QueueItem } from "../../features/case/types";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { EmptyState } from "../../ui/EmptyState";
import { OUTCOME_CLASS, outcomeWord } from "../../ui/outcome";
import { Tooltip } from "../../ui/tooltip";
import { CaseTable } from "./CaseTable";
import { type Chip, FilterChips } from "./FilterChips";
import { summarySentence } from "./summary";

const OUTCOME_ORDER = Object.keys(OUTCOME_CLASS);

function chipsFor(items: QueueItem[], pick: (i: QueueItem) => string, order: (values: string[]) => string[], label: (v: string) => string): Chip[] {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(pick(item), (counts.get(pick(item)) ?? 0) + 1);
  return order([...counts.keys()]).map((value) => ({ value, label: label(value), count: counts.get(value) ?? 0 }));
}

export function CasesPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const cases = useCases();
  const items = useMemo(() => cases.data ?? [], [cases.data]);
  const pending = usePendingApprovals(cases.data);
  const outcomes = params.getAll("outcome");
  const tiers = params.getAll("tier");

  const toggle = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    const current = next.getAll(name);
    next.delete(name);
    for (const v of current.includes(value) ? current.filter((c) => c !== value) : [...current, value]) next.append(name, v);
    setParams(next, { replace: true });
  };

  const shown = items.filter((i) => (!outcomes.length || outcomes.includes(i.outcome)) && (!tiers.length || tiers.includes(i.tier)));
  const outcomeChips = chipsFor(items, (i) => i.outcome, (v) => v.sort((a, b) => OUTCOME_ORDER.indexOf(a) - OUTCOME_ORDER.indexOf(b)), (v) => outcomeWord(v));
  const tierChips = chipsFor(items, (i) => i.tier, (v) => v.sort(), (v) => v);

  return (
    <>
      <PageHeader title="Cases" />
      <div className="flex max-w-6xl flex-col gap-5 px-8 py-6">
        {cases.isPending ? <p className="text-sm text-graphite">Loading cases…</p> : null}
        {cases.isError ? <Callout tone="error" title="The cases could not be loaded.">{cases.error.message}</Callout> : null}
        {cases.data && !items.length ? (
          <EmptyState
            title="No cases yet. Start an assessment to see the agents work."
            action={<Button onClick={() => navigate("/")}>Start an assessment</Button>}
          />
        ) : null}
        {items.length ? (
          <>
            <Tooltip content={`Approvals are counted from the first ${PENDING_SCAN_LIMIT} cases by residual risk.`}>
              <p data-testid="cases-summary" tabIndex={0} className="max-w-[72ch] text-md text-ink">
                {summarySentence(items, pending.done ? pending.count : null)}
              </p>
            </Tooltip>
            <div className="flex flex-col gap-2">
              <FilterChips name="outcome" label="Decision" chips={outcomeChips} selected={outcomes} onToggle={(v) => toggle("outcome", v)} />
              <FilterChips name="tier" label="Tier" chips={tierChips} selected={tiers} onToggle={(v) => toggle("tier", v)} />
            </div>
            <div className="rounded-panel border border-hairline bg-sheet">
              {shown.length ? (
                <CaseTable rows={shown} onOpen={(id) => navigate(`/cases/${encodeURIComponent(id)}`)} />
              ) : (
                <p className="px-4 py-6 text-sm text-graphite">No case matches these filters. Clear a chip to see more.</p>
              )}
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}
