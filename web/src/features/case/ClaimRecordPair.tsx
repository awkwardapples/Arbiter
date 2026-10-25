// A claim card beside a record card (design §2: the vendor's word against the company's records).
import { Identifier } from "../../ui/Identifier";
import { cn } from "../../ui/lib/cn";
import type { DecisionRecord, EvidenceRef } from "./types";

const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

/** The Zetaris request id behind a record ref, when the record was read through Zetaris. */
function requestId(ref: EvidenceRef, record: DecisionRecord): string | null {
  const key = ref.provenance_id ?? "";
  if (!key) return null;
  const sources = [...record.contradictions.map((c) => c.sor_provenance), ...record.facts.flatMap((f) => f.provenance)];
  return sources.find((p) => p?.record_key === key && p.zetaris_request_id)?.zetaris_request_id ?? null;
}

function Value({ value, clash }: { value: string; clash: boolean }) {
  return (
    <p data-clash={clash ? "true" : "false"} className={cn("text-lg font-semibold", clash ? "text-clash" : "text-ink")}>
      {value}
    </p>
  );
}

export function ClaimRecordPair({ claim, record, decision }: { claim: EvidenceRef; record: EvidenceRef; decision: DecisionRecord }) {
  const clash = !same(claim.value, record.value);
  const zetaris = requestId(record, decision);
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-3">
      <div data-testid="claim-card" className="rounded-source border border-claim/30 bg-claim-tint px-4 py-3">
        <p className="text-xs font-semibold text-claim">The vendor's word</p>
        <p className="text-sm font-medium text-ink">{claim.source_label}</p>
        <p className="text-xs text-graphite">
          {claim.field_label}, from {claim.record_label}
        </p>
        <Value value={claim.value} clash={clash} />
        {claim.quote ? <blockquote className="mt-1 border-l-2 border-claim/40 pl-2 font-serif text-sm text-ink">“{claim.quote}”</blockquote> : null}
      </div>
      <div className="flex items-center text-xl font-semibold" aria-label={clash ? "does not match" : "matches"}>
        <span className={clash ? "text-clash" : "text-graphite"}>{clash ? "≠" : "="}</span>
      </div>
      <div data-testid="record-card" className="rounded-source border border-record/30 bg-record-tint px-4 py-3">
        <p className="text-xs font-semibold text-record">The company's records</p>
        <p className="text-sm font-medium text-ink">{record.source_label}</p>
        <p className="text-xs text-graphite">
          {record.field_label}, in <span className="font-mono text-ink">{record.record_label}</span>
        </p>
        <Value value={record.value} clash={clash} />
        {zetaris ? (
          <p className="mt-1 text-xs text-graphite">
            Read through Zetaris, request <Identifier value={zetaris} short={12} />
          </p>
        ) : null}
      </div>
    </div>
  );
}
