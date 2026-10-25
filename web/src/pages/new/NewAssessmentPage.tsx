import { PageHeader } from "../../app/PageHeader";
import { NewVendorForm } from "../../features/intake/NewVendorForm";

export function NewAssessmentPage() {
  return (
    <>
      <PageHeader title="Assess a new vendor">
        Enter what the vendor told you. Arbiter treats every answer as a claim and checks it against the company's records.
      </PageHeader>
      <div className="px-8 py-6">
        <NewVendorForm />
      </div>
    </>
  );
}
