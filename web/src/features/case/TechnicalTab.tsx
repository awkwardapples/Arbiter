// The one tab where codes lead (design §4): reason codes, controls with evidence chips, raw lists and the record.
import type { ReactNode } from "react";
import { Identifier } from "../../ui/Identifier";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { JsonViewer } from "./JsonViewer";
import type { CaseDetail, Provenance } from "./types";
import { reasonMeaning, timeWords } from "./words";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section data-testid={id} aria-labelledby={`${id}-title`} className="flex flex-col gap-3">
      <h2 id={`${id}-title`} className="text-md font-semibold text-ink">
        {title}
      </h2>
      {children}
    </section>
  );
}

const raw = (value: unknown) => (typeof value === "string" ? value : JSON.stringify(value));

function chip(p: Provenance | undefined): string {
  if (!p) return "no provenance";
  return [p.system, p.query_id, p.record_key, p.field].filter(Boolean).join(" / ") || (p.kind ?? "evidence");
}

export function TechnicalTab({ detail }: { detail: CaseDetail }) {
  const { record } = detail;
  const facts = new Map(record.facts.map((f) => [f.fact_id, f]));
  const reasons = [...record.outcome_reasons, ...(record.escalation_reasons ?? [])];
  return (
    <div data-testid="technical-tab" className="flex max-w-6xl flex-col gap-10">
      <Section id="technical-reasons" title="Reason codes">
        <ul className="flex flex-col gap-1 text-sm">
          {reasons.map((code) => (
            <li key={code}>
              <span className="font-mono text-xs text-ink">{code}</span> <span className="text-graphite">{reasonMeaning(code)}</span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-graphite">
          Policy {record.policy_version}, hash <Identifier value={record.policy_sha256} short={16} />; record hash{" "}
          <Identifier value={record.record_sha256} short={16} />
        </p>
      </Section>

      <Section id="technical-controls" title="Controls and the facts behind them">
        <div className="rounded-panel border border-hairline bg-sheet">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Control</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Rule</TableHead>
                <TableHead>Hard gate</TableHead>
                <TableHead>Evidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {record.controls.map((control) => (
                <TableRow key={control.control_id}>
                  <TableCell>
                    <span className="font-mono text-xs">{control.control_id}</span> {control.title}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{control.state}</TableCell>
                  <TableCell className="font-mono text-xs">{control.rule_id}</TableCell>
                  <TableCell className="font-mono text-xs">{control.hard_gate ?? "none"}</TableCell>
                  <TableCell>
                    <ul className="flex flex-col gap-1">
                      {control.fact_ids.map((id) => (
                        <li key={id} className="flex flex-wrap items-center gap-2">
                          <Identifier value={id} />
                          <span className="font-mono text-xs text-graphite">{chip(facts.get(id)?.provenance[0])}</span>
                        </li>
                      ))}
                    </ul>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>

      <Section id="technical-contradictions" title="Contradictions">
        {record.contradictions.length ? (
          <ul className="flex flex-col gap-1 font-mono text-xs">
            {record.contradictions.map((c) => (
              <li key={`${c.key}-${c.claim_id}`}>
                {c.control_id} {c.key}: claim {raw(c.claim_value)} ({c.claim_id}) vs record {raw(c.sor_value)} ({chip(c.sor_provenance)}), {c.severity}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-graphite">No contradictions on this case.</p>
        )}
        <JsonViewer label="Contradictions (JSON)" value={record.contradictions} />
      </Section>

      <Section id="technical-counterfactuals" title="Counterfactuals">
        {record.counterfactuals.length ? (
          <ul className="flex flex-col gap-1 font-mono text-xs">
            {record.counterfactuals.map((c, index) => (
              <li key={index}>
                {c.control_id} {c.from_state} to {c.to_state}: {c.evidence_required.join("; ")}. Questions: {(c.question_ids ?? []).join(", ") || "none"}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-graphite">No counterfactuals: every required control is verified.</p>
        )}
      </Section>

      <Section id="technical-contracts" title="Signed contracts">
        {detail.contracts.length ? (
          <div className="rounded-panel border border-hairline bg-sheet">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contract</TableHead>
                  <TableHead>Parent</TableHead>
                  <TableHead>Intent</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Signature</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Expires</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.contracts.map((c) => (
                  <TableRow key={c.contract_id}>
                    <TableCell>
                      <Identifier value={c.contract_id} />
                    </TableCell>
                    <TableCell>{c.parent_id ? <Identifier value={c.parent_id} /> : <span className="text-graphite">none</span>}</TableCell>
                    <TableCell className="font-mono text-xs">{c.intent}</TableCell>
                    <TableCell className="font-mono text-xs">{c.state}</TableCell>
                    <TableCell>
                      <Identifier value={c.signature} short={12} />
                    </TableCell>
                    <TableCell className="text-xs">{timeWords(c.issued_at)}</TableCell>
                    <TableCell className="text-xs">{timeWords(c.expires_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="text-sm text-graphite">No contracts were issued for this case.</p>
        )}
      </Section>

      <section data-testid="technical-raw">
        <JsonViewer label="The raw case record (JSON)" value={detail} />
      </section>
    </div>
  );
}
