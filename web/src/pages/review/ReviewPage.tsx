import { Link, useParams } from "react-router";
import { useCase } from "../../api/queries";
import { PageHeader } from "../../app/PageHeader";
import { Callout } from "../../ui/Callout";
import { OutcomeBadge } from "../../ui/OutcomeBadge";
import { ReviewForm } from "./ReviewForm";

export function ReviewPage() {
  const { caseId = "" } = useParams();
  const detail = useCase(caseId);
  return (
    <>
      <PageHeader title="Review">
        Record a reviewer's decision on a case. A TPRM lead can save an allowed exception as a precedent, so later cases are treated the same way.
      </PageHeader>
      <div className="flex flex-col gap-6 px-8 py-6">
        {detail.isError ? (
          <Callout tone="error" title={`Case ${caseId} did not load.`}>
            {detail.error.message} Open the case from <Link to="/cases" className="text-record underline">Cases</Link>.
          </Callout>
        ) : detail.data ? (
          <>
            <div className="flex flex-wrap items-center gap-3" data-testid="review-case">
              <Link to={`/cases/${encodeURIComponent(caseId)}`} className="font-mono text-xs text-record hover:underline">
                {caseId}
              </Link>
              <span className="text-md font-semibold text-ink">{detail.data.vendor}</span>
              <span className="text-sm text-graphite">The policy ruled</span>
              <OutcomeBadge outcome={detail.data.record.outcome} />
            </div>
            <ReviewForm key={caseId} caseId={caseId} machineOutcome={detail.data.record.outcome} />
          </>
        ) : (
          <p className="text-sm text-graphite">Loading the case…</p>
        )}
      </div>
    </>
  );
}
