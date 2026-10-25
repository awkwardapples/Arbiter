import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, ShieldCheck, XCircle } from "lucide-react";
import { api } from "../../api/client";
import { useHealth } from "../../api/queries";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { type AuditVerify, verifySentence } from "./audit";

/** Verify chain: recompute every hash in the audit log and say where it breaks, if it does. */
export function VerifyChain() {
  const health = useHealth();
  const verify = useMutation({ mutationFn: () => api.get<AuditVerify>("/audit/verify") });
  const result = verify.data;
  return (
    <div className="flex flex-col gap-3" data-testid="audit-verify">
      <div>
        <Button type="button" onClick={() => verify.mutate()} disabled={verify.isPending}>
          <ShieldCheck aria-hidden />
          {verify.isPending ? "Verifying…" : "Verify chain"}
        </Button>
      </div>
      {result ? (
        <p
          role="status"
          data-testid="audit-verify-result"
          className={`flex items-center gap-2 text-sm font-semibold ${result.ok ? "text-record" : "text-clash"}`}
        >
          {result.ok ? <CheckCircle2 className="size-4" aria-hidden /> : <XCircle className="size-4" aria-hidden />}
          {verifySentence(result, health.data?.audit_chain_length)}
        </p>
      ) : null}
      {verify.isError ? (
        <Callout tone="error" title="The chain could not be checked.">
          {verify.error.message} Try again once the API is running.
        </Callout>
      ) : null}
    </div>
  );
}
