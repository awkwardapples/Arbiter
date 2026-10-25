// Where a fact came from, behind a chip: record key, query and Zetaris request id, or the vendor's quote.
import { Popover, PopoverContent, PopoverTrigger } from "../../ui/popover";
import { Identifier } from "../../ui/Identifier";
import type { Provenance } from "./types";
import { systemLabel } from "./words";

const VENDOR_KINDS = new Set(["vendor_answer", "vendor_document", "document"]);

export function ProvenanceChip({ provenance }: { provenance: Provenance | undefined }) {
  if (!provenance) return <span className="text-xs text-graphite">No source recorded</span>;
  const vendor = VENDOR_KINDS.has(provenance.kind ?? "") || provenance.system === "trust_portal";
  const label = vendor ? (provenance.quote ? "Vendor's quote" : "Vendor's answer") : provenance.backend === "zetaris" ? "Record via Zetaris" : "Record";
  return (
    <Popover>
      <PopoverTrigger
        className={
          vendor
            ? "rounded-full border border-claim/40 bg-claim-tint px-2 py-0.5 text-xs font-medium text-claim"
            : "rounded-full border border-record/40 bg-record-tint px-2 py-0.5 text-xs font-medium text-record"
        }
      >
        {label}
      </PopoverTrigger>
      <PopoverContent>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-xs">
          <dt className="text-graphite">Source</dt>
          <dd>{systemLabel(provenance.system) || "Not recorded"}</dd>
          {provenance.record_key ? (
            <>
              <dt className="text-graphite">Record key</dt>
              <dd>
                <Identifier value={provenance.record_key} />
              </dd>
            </>
          ) : null}
          {provenance.field ? (
            <>
              <dt className="text-graphite">Field</dt>
              <dd className="font-mono">{provenance.field}</dd>
            </>
          ) : null}
          {provenance.query_id ? (
            <>
              <dt className="text-graphite">Query</dt>
              <dd>
                <Identifier value={provenance.query_id} />
              </dd>
            </>
          ) : null}
          {provenance.zetaris_request_id ? (
            <>
              <dt className="text-graphite">Zetaris request</dt>
              <dd>
                <Identifier value={provenance.zetaris_request_id} />
              </dd>
            </>
          ) : null}
        </dl>
        {provenance.quote ? <blockquote className="mt-3 border-l-2 border-claim/40 pl-2 font-serif text-sm">“{provenance.quote}”</blockquote> : null}
      </PopoverContent>
    </Popover>
  );
}
