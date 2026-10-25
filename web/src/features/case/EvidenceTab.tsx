// Evidence in business terms: controls, what would change the decision, precedents and the facts behind them.
import type { ReactNode } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { cn } from "../../ui/lib/cn";
import { ProvenanceChip } from "./ProvenanceChip";
import { mergeCounterfactuals, valueWords } from "./evidence";
import type { CaseDetail, Question } from "./types";
import { criterionWord, factWords, roleWord, stateWord, systemLabel } from "./words";

const STATE_TONE: Record<string, string> = { TRUE: "text-record", FALSE: "text-clash", UNKNOWN: "text-claim" };
const capitalised = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

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

export function EvidenceTab({ detail, questions }: { detail: CaseDetail; questions: Question[] }) {
  const { record } = detail;
  const titles = new Map(record.controls.map((c) => [c.control_id, c.title]));
  const changes = mergeCounterfactuals(record.counterfactuals);
  const satisfy = new Map(changes.map((c) => [c.control_id, c.evidence_required]));
  const asked = new Map(questions.map((q) => [q.question_id, q.question]));
  const candidates = new Map((record.policy_inputs?.precedents ?? []).map((p) => [p.precedent_id, p]));
  const facts = new Map(record.facts.map((f) => [f.fact_id, f]));

  return (
    <div data-testid="evidence-tab" className="flex max-w-5xl flex-col gap-10">
      <Section id="evidence-controls" title="Controls">
        <div className="rounded-panel border border-hairline bg-sheet">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Control</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Required</TableHead>
                <TableHead>What would satisfy it</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {record.controls.map((control) => (
                <TableRow key={control.control_id}>
                  <TableCell className="font-medium">{control.title}</TableCell>
                  <TableCell className={cn("font-medium", STATE_TONE[control.state])}>{capitalised(stateWord(control.state))}</TableCell>
                  <TableCell>{control.required ? "Yes" : "No"}</TableCell>
                  <TableCell className="text-graphite">
                    {control.state === "TRUE" ? "Already verified" : (satisfy.get(control.control_id) ?? []).join("; ") || "No route to verify it is recorded"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>

      <Section id="evidence-changes" title="What would change this decision">
        {changes.length ? (
          <ul className="flex flex-col gap-4">
            {changes.map((change) => {
              const ask = (change.question_ids ?? []).map((q) => asked.get(q)).filter(Boolean);
              return (
                <li key={change.control_id} className="rounded-panel border border-hairline bg-sheet px-5 py-4">
                  <p className="font-semibold text-ink">{titles.get(change.control_id) ?? "A required control"}</p>
                  <p className="text-xs text-graphite">
                    From {stateWord(change.from_state)} to {stateWord(change.to_state)} with any of:
                  </p>
                  <ul className="mt-2 list-disc pl-5 text-sm text-ink">
                    {change.evidence_required.map((need) => (
                      <li key={need}>{need.replace(/^or\s+/i, "")}</li>
                    ))}
                  </ul>
                  {ask.length ? <p className="mt-2 text-sm text-graphite">Ask the vendor: {ask.join(" ")}</p> : null}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-graphite">Nothing further is needed: every required control is already verified.</p>
        )}
      </Section>

      <Section id="evidence-precedents" title="Precedents considered">
        {record.precedents_considered.length ? (
          <div className="rounded-panel border border-hairline bg-sheet">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Precedent</TableHead>
                  <TableHead>Signed off by</TableHead>
                  <TableHead>Conditions</TableHead>
                  <TableHead>Applied</TableHead>
                  <TableHead>Why</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {record.precedents_considered.map((ref) => {
                  const candidate = candidates.get(ref.precedent_id);
                  const failed = ref.failed_criteria ?? [];
                  return (
                    <TableRow key={ref.precedent_id}>
                      <TableCell className="font-mono text-xs">{ref.precedent_id}</TableCell>
                      <TableCell>{candidate ? capitalised(roleWord(candidate.reviewer_role)) : "Not recorded"}</TableCell>
                      <TableCell>{candidate?.mitigation ? factWords(candidate.mitigation) : "None recorded"}</TableCell>
                      <TableCell>{ref.applied ? "Yes" : "No"}</TableCell>
                      <TableCell className="text-graphite">
                        {ref.applied ? "Every criterion was met." : failed.length ? `Not applied: ${failed.map(criterionWord).join("; ")}.` : "Not applied."}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="text-sm text-graphite">No precedents were considered for this case.</p>
        )}
      </Section>

      <Section id="evidence-facts" title="Facts">
        <div className="rounded-panel border border-hairline bg-sheet">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Control</TableHead>
                <TableHead>Fact</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Provenance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...facts.values()].map((fact) => (
                <TableRow key={fact.fact_id}>
                  <TableCell>{titles.get(fact.control_id) ?? "Other"}</TableCell>
                  <TableCell>{capitalised(factWords(fact.key))}</TableCell>
                  <TableCell className="font-medium">{valueWords(fact.value)}</TableCell>
                  <TableCell className="text-graphite">{systemLabel(fact.provenance[0]?.system)}</TableCell>
                  <TableCell>
                    <ProvenanceChip provenance={fact.provenance[0]} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>
    </div>
  );
}
