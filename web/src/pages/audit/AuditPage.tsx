import { PageHeader } from "../../app/PageHeader";
import { AuditTable } from "../../features/audit/AuditTable";
import { VerifyChain } from "../../features/audit/VerifyChain";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../ui/card";

export function AuditPage() {
  return (
    <>
      <PageHeader title="Audit">An append-only hash chain of every review, approval, precedent and action.</PageHeader>
      <div className="flex max-w-5xl flex-col gap-6 px-8 py-6">
        <Card>
          <CardHeader>
            <CardTitle>Verify the chain</CardTitle>
            <CardDescription>Recomputes every entry's hash from the one before it. An edited or deleted entry breaks the chain there.</CardDescription>
          </CardHeader>
          <CardContent>
            <VerifyChain />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent entries</CardTitle>
            <CardDescription>The 50 newest, newest first. Each entry's content stays in the log.</CardDescription>
          </CardHeader>
          <CardContent>
            <AuditTable />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
