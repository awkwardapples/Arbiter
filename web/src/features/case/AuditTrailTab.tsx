// What happened to this case, in order: created, contracts issued and signed, reviews, and replays this session.
import { Link } from "react-router";
import { ApiError } from "../../api/client";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { outcomeWord } from "../../ui/outcome";
import { Timeline, type TimelineEntry } from "../../ui/Timeline";
import { dossierUrl, useReplay } from "./queries";
import { replaySentence } from "./replay";
import { ReplayResultView } from "./ReplayResultView";
import type { CaseDetail, ReplayResult } from "./types";
import { capabilityWord, roleWord, timeWords } from "./words";

export interface SessionReplay {
  at: string;
  result: ReplayResult;
}

const capitalised = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function entriesFor(detail: CaseDetail, replays: SessionReplay[]): TimelineEntry[] {
  const entries: Array<TimelineEntry & { sort: string }> = [
    {
      id: "created",
      sort: detail.record.created_at,
      when: timeWords(detail.record.created_at),
      title: `Case created: the policy ruled ${outcomeWord(detail.record.outcome)}`,
      tone: "ink",
    },
  ];
  for (const contract of detail.contracts) {
    if (!contract.parent_id) {
      const waits = contract.risk.approvals_required.map((r) => roleWord(r.role));
      entries.push({
        id: `issued-${contract.contract_id}`,
        sort: contract.issued_at,
        when: timeWords(contract.issued_at),
        title: `Contract issued for the ${capabilityWord(contract)}`,
        body: waits.length ? `Needs approval from the ${waits.join(" and the ")}.` : "Needs no approval.",
        tone: "reason",
      });
    }
    for (const [index, approval] of contract.risk.approvals.entries()) {
      const approved = approval.decision === "approve";
      entries.push({
        id: `approval-${contract.contract_id}-${index}`,
        sort: approval.at ?? contract.issued_at,
        when: timeWords(approval.at ?? contract.issued_at),
        title: `${approved ? "Approved" : "Rejected"} by ${approval.by}, ${roleWord(approval.role)}`,
        body: approval.rationale,
        tone: approved ? "record" : "clash",
      });
    }
  }
  for (const review of detail.reviews) {
    entries.push({
      id: `review-${review.review_id}`,
      sort: review.at ?? "9999",
      when: review.at ? timeWords(review.at) : "Review",
      title: `${capitalised(roleWord(review.role))} ${review.reviewer} reviewed it: ${outcomeWord(review.decision)}`,
      body: review.rationale,
      tone: "claim",
    });
  }
  for (const [index, replay] of replays.entries()) {
    entries.push({
      id: `replay-${index}`,
      sort: replay.at,
      when: timeWords(replay.at),
      title: "Replayed in this session",
      body: replaySentence(replay.result),
      tone: replay.result.match ? "record" : "clash",
    });
  }
  return entries.sort((a, b) => a.sort.localeCompare(b.sort));
}

export function AuditTrailTab({ detail, replays, onReplay }: { detail: CaseDetail; replays: SessionReplay[]; onReplay: (r: SessionReplay) => void }) {
  const replay = useReplay(detail.case_id);
  const latest = replays[replays.length - 1];
  const run = () => replay.mutate(undefined, { onSuccess: (result) => onReplay({ at: new Date().toISOString(), result }) });

  return (
    <div data-testid="audit-trail-tab" className="grid max-w-5xl gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section aria-labelledby="audit-title">
        <h2 id="audit-title" className="mb-4 text-md font-semibold text-ink">
          Audit trail
        </h2>
        <Timeline data-testid="audit-timeline" entries={entriesFor(detail, replays)} />
      </section>
      <aside className="flex flex-col gap-6 self-start">
        <section className="flex flex-col gap-3">
          <Button data-testid="replay-button" onClick={run} disabled={replay.isPending}>
            {replay.isPending ? "Replaying…" : "Replay decision"}
          </Button>
          <p className="text-xs text-graphite">Re-runs the policy on the stored facts and checks every hash and signature.</p>
          {latest ? <ReplayResultView result={latest.result} /> : null}
          {replay.isError ? (
            <Callout tone="error" title="The replay did not run.">
              {replay.error instanceof ApiError ? replay.error.message : "Try again."}
            </Callout>
          ) : null}
        </section>
        <section data-testid="dossier-download" className="flex flex-col gap-2">
          <Button asChild variant="secondary">
            <a href={dossierUrl(detail.case_id, "html")} download={`${detail.case_id}-dossier.html`}>
              Download dossier (HTML)
            </a>
          </Button>
          <Button asChild variant="secondary">
            <a href={dossierUrl(detail.case_id, "md")} download={`${detail.case_id}-dossier.md`}>
              Download dossier (Markdown)
            </a>
          </Button>
        </section>
        <Button asChild variant="link" className="self-start">
          <Link to={`/review/${encodeURIComponent(detail.case_id)}`}>Open review</Link>
        </Button>
      </aside>
    </div>
  );
}
