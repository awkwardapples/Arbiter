// The signed contract for the next step: its state, and for pending_approval the approval form (rationale ≥ 30).
import { useId, useState } from "react";
import { ApiError } from "../../api/client";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { Identifier } from "../../ui/Identifier";
import { Input } from "../../ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../ui/select";
import { Textarea } from "../../ui/textarea";
import { toast } from "../../ui/toast";
import { liveContracts, useApproveContract } from "./queries";
import { fileName } from "./trace";
import type { Contract } from "./types";
import { capabilityWord, contractStateWord, roleWord } from "./words";

const MIN_RATIONALE = 30;
/** Roles the policy ranks (policy/arbiter_policy.v1.yaml `roles`), offered when a contract names none. */
const FALLBACK_ROLES = ["tprm_analyst", "tprm_lead"];

function rolesFor(contract: Contract, all: Contract[]): string[] {
  const named = [
    ...contract.risk.approvals_required.map((r) => r.role),
    ...all.flatMap((c) => c.risk.approvals.map((a) => a.role)),
  ];
  const unique = [...new Set(named.filter(Boolean))];
  return unique.length ? unique : FALLBACK_ROLES;
}

function Approval({ contract, all, caseId, onDone }: { contract: Contract; all: Contract[]; caseId: string; onDone: (id: string, file: string | null) => void }) {
  const roles = rolesFor(contract, all);
  const [role, setRole] = useState(contract.risk.approvals_required[0]?.role ?? roles[roles.length - 1]);
  const [name, setName] = useState("");
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mutation = useApproveContract(caseId);
  const ids = { name: useId(), rationale: useId(), role: useId() };
  const length = rationale.trim().length;
  const ready = length >= MIN_RATIONALE && name.trim().length > 0 && !mutation.isPending;
  const needed = contract.risk.approvals_required[0]?.role;

  const send = (decision: "approve" | "reject") => {
    if (!ready) return;
    setError(null);
    mutation.mutate(
      { contractId: contract.contract_id, by: name.trim(), role, decision, rationale: rationale.trim() },
      {
        onSuccess: (result) => {
          const file = result.artifact ? fileName(result.artifact) : null;
          onDone(result.contract_id, file);
          toast.success(decision === "approve" ? "Contract approved" : "Contract rejected", {
            description: file ? `Written to the outbox as ${file}.` : undefined,
          });
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "The approval could not be sent. Try again."),
      },
    );
  };

  return (
    <div data-testid="contract-approval" className="flex flex-col gap-3">
      <p className="text-sm text-ink">
        The {capabilityWord(contract)} waits for approval{needed ? ` from the ${roleWord(needed)}` : ""}.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor={ids.role} className="text-xs text-graphite">
            Approving as
          </label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger id={ids.role} aria-label="Approving as">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {roles.map((r) => (
                <SelectItem key={r} value={r}>
                  {roleWord(r).charAt(0).toUpperCase() + roleWord(r).slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor={ids.name} className="text-xs text-graphite">
            Your name
          </label>
          <Input id={ids.name} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex items-baseline justify-between">
          <label htmlFor={ids.rationale} className="text-xs text-graphite">
            Rationale (at least {MIN_RATIONALE} characters)
          </label>
          <span data-testid="rationale-count" className={length >= MIN_RATIONALE ? "text-xs text-record" : "text-xs text-graphite"} aria-live="polite">
            {length} / {MIN_RATIONALE}
          </span>
        </div>
        <Textarea id={ids.rationale} value={rationale} onChange={(e) => setRationale(e.target.value)} rows={3} />
      </div>
      <div className="flex gap-2">
        <Button disabled={!ready} onClick={() => send("approve")}>
          Approve contract
        </Button>
        <Button variant="secondary" disabled={!ready} onClick={() => send("reject")}>
          Reject contract
        </Button>
      </div>
      {error ? <Callout tone="error" title="The contract was not changed.">{error}</Callout> : null}
    </div>
  );
}

function approvalLine(contract: Contract): string | null {
  const last = contract.risk.approvals[contract.risk.approvals.length - 1];
  if (!last) return null;
  const verb = last.decision === "approve" ? "Approved" : "Rejected";
  return `${verb} by ${last.by} (${roleWord(last.role)}).`;
}

export function ContractBlock({
  contracts,
  caseId,
  outbox,
  onDone,
}: {
  contracts: Contract[];
  caseId: string;
  outbox: Record<string, string>;
  onDone: (id: string, file: string | null) => void;
}) {
  const live = liveContracts(contracts);
  return (
    <section data-testid="contract-block" className="rounded-panel border border-hairline bg-sheet p-5" aria-labelledby="contract-title">
      <h2 id="contract-title" className="mb-3 text-md font-semibold text-ink">
        Contract
      </h2>
      {!live.length ? <p className="text-sm text-graphite">No contracts were issued for this case.</p> : null}
      <div className="flex flex-col gap-4">
        {live.map((contract) => {
          const approved = approvalLine(contract);
          return (
            <div key={contract.contract_id} className="flex flex-col gap-2">
              <p className="text-sm text-graphite">
                Signed contract <Identifier value={contract.contract_id} />
              </p>
              {contract.state === "pending_approval" ? (
                <Approval contract={contract} all={contracts} caseId={caseId} onDone={onDone} />
              ) : contract.state === "executed" ? (
                <p className="text-sm text-ink">
                  {outbox[contract.contract_id] ? `Sent to the outbox: ${outbox[contract.contract_id]}` : `The ${capabilityWord(contract)} was sent to the outbox.`}
                </p>
              ) : (
                <p className="text-sm text-ink">
                  The {capabilityWord(contract)}: {contractStateWord(contract.state).toLowerCase()}.
                </p>
              )}
              {approved ? <p className="text-xs text-graphite">{approved}</p> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
