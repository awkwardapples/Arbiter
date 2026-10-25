// The brief: the ruling headline and the why-points, in Source Serif 4 (design §3.2), beside a Tracing Beam.
import { Serif } from "../../ui/Serif";
import { TracingBeam } from "../../ui/TracingBeam";
import { ClaimRecordPair } from "./ClaimRecordPair";
import type { CaseDetail } from "./types";

export function BriefColumn({ detail }: { detail: CaseDetail }) {
  const brief = detail.report.brief;
  return (
    <TracingBeam>
      <Serif as="h2" data-testid="brief-headline" className="text-lg leading-[30px] font-bold">
        {brief?.headline ?? detail.report.summary}
      </Serif>
      <ul className="mt-6 flex flex-col gap-6">
        {(brief?.why ?? []).map((point, index) => (
          <li key={index} data-testid="why-point" className="flex flex-col gap-3">
            <Serif>{point.text}</Serif>
            {point.claim && point.record ? <ClaimRecordPair claim={point.claim} record={point.record} decision={detail.record} /> : null}
          </li>
        ))}
      </ul>
    </TracingBeam>
  );
}
