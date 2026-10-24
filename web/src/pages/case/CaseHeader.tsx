// The case header (design §12): vendor, the ruling stamp and its meaning, tier, residual risk, confidence in
// words, the mode chip from the case trace, and the case and run ids.
import { PageHeader } from "../../app/PageHeader";
import type { CaseDetail } from "../../features/case/types";
import { confidenceSentence, outcomeMeaning } from "../../features/case/words";
import { Identifier } from "../../ui/Identifier";
import { ModeChip } from "../../ui/ModeChip";
import { OutcomeStamp } from "../../ui/OutcomeStamp";
import { modeChipText } from "../../run/mode";

export function CaseHeader({ detail, mode }: { detail: CaseDetail; mode: Record<string, string> | null }) {
  const { record } = detail;
  return (
    <div data-testid="case-header">
      <PageHeader title={detail.vendor} chip={<ModeChip chip={modeChipText({ kind: "mode", mode })} />}>
        <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>
            Case <Identifier value={detail.case_id} />
          </span>
          <span>
            Run <Identifier value={record.run_id} />
          </span>
        </span>
      </PageHeader>
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-hairline bg-sheet px-8 py-4">
        <div className="flex items-center gap-4">
          <OutcomeStamp outcome={record.outcome} />
          <p data-testid="case-meaning" className="max-w-[48ch] text-sm text-ink">
            {outcomeMeaning(record.outcome)}
          </p>
        </div>
        <dl className="flex gap-8 text-sm">
          <div data-testid="case-tier">
            <dt className="text-xs text-graphite">Tier</dt>
            <dd className="font-semibold text-ink">{record.tier}</dd>
          </div>
          <div data-testid="case-risk">
            <dt className="text-xs text-graphite">Residual risk</dt>
            <dd className="font-semibold text-ink tabular-nums">{record.residual_risk}</dd>
          </div>
        </dl>
        <p data-testid="case-confidence" className="text-sm text-graphite">
          {confidenceSentence(record.confidence, record.controls)}
        </p>
      </div>
    </div>
  );
}
