import { BriefColumn } from "./BriefColumn";
import { ContractBlock } from "./ContractBlock";
import { NextActionPanel } from "./NextActionPanel";
import type { CaseDetail, Draft } from "./types";

function draftsOf(detail: CaseDetail): Draft[] {
  const drafts = detail.report.drafts ?? [];
  if (drafts.length) return drafts;
  return detail.report.clarification_email ? [detail.report.clarification_email] : [];
}

export function DecisionTab({ detail, outbox, onApproved }: { detail: CaseDetail; outbox: Record<string, string>; onApproved: (id: string, file: string | null) => void }) {
  return (
    <div data-testid="decision-tab" className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
      <BriefColumn detail={detail} />
      <aside className="flex flex-col gap-4 self-start lg:sticky lg:top-4">
        <NextActionPanel drafts={draftsOf(detail)} caseId={detail.case_id} />
        <ContractBlock contracts={detail.contracts} caseId={detail.case_id} outbox={outbox} onDone={onApproved} />
      </aside>
    </div>
  );
}
