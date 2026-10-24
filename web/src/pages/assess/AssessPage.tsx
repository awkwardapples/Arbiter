import { PageHeader } from "../../app/PageHeader";
import { EmptyState } from "../../ui/EmptyState";

export function AssessPage() {
  return (
    <>
      <PageHeader title="Assess a vendor" />
      <div className="px-8 py-6">
        <EmptyState title="Pick a vendor to start an assessment.">The vendor list arrives with the run view.</EmptyState>
      </div>
    </>
  );
}
