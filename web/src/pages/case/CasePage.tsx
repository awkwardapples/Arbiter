import { Tabs as TabsPrimitive } from "radix-ui";
import { useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { PageHeader } from "../../app/PageHeader";
import { AgentActivityTab } from "../../features/case/AgentActivityTab";
import { AuditTrailTab, type SessionReplay } from "../../features/case/AuditTrailTab";
import { DecisionTab } from "../../features/case/DecisionTab";
import { EvidenceTab } from "../../features/case/EvidenceTab";
import { useCaseDetail, useCaseTrace, useQuestions } from "../../features/case/queries";
import { TechnicalTab } from "../../features/case/TechnicalTab";
import { outboxFiles, traceMode } from "../../features/case/trace";
import { AnimatedTabsList } from "../../ui/AnimatedTabs";
import { Callout } from "../../ui/Callout";
import { CaseHeader } from "./CaseHeader";

const TABS = [
  { value: "decision", label: "Decision" },
  { value: "evidence", label: "Evidence" },
  { value: "activity", label: "Agent activity" },
  { value: "audit", label: "Audit trail" },
  { value: "technical", label: "Technical details" },
];

export function CasePage() {
  const { caseId } = useParams();
  const [params, setParams] = useSearchParams();
  const detail = useCaseDetail(caseId);
  const trace = useCaseTrace(caseId);
  const questions = useQuestions();
  const [approvedFiles, setApprovedFiles] = useState<Record<string, string>>({});
  const [replays, setReplays] = useState<SessionReplay[]>([]);
  const tab = TABS.some((t) => t.value === params.get("tab")) ? (params.get("tab") as string) : "decision";

  const setTab = (value: string) => {
    const next = new URLSearchParams(params);
    next.set("tab", value);
    setParams(next, { replace: true });
  };

  if (detail.isPending) {
    return (
      <>
        <PageHeader title="Case" />
        <p className="px-8 py-6 text-sm text-graphite">Loading the case…</p>
      </>
    );
  }
  if (detail.isError) {
    return (
      <>
        <PageHeader title="Case" />
        <div className="max-w-3xl px-8 py-6">
          <Callout tone="error" title="This case could not be opened.">
            {detail.error.message} Open it again from Cases.
          </Callout>
        </div>
      </>
    );
  }

  const data = detail.data;
  const outbox = { ...outboxFiles(trace.data), ...approvedFiles };
  return (
    <>
      <CaseHeader detail={data} mode={traceMode(trace.data)} />
      <TabsPrimitive.Root value={tab} onValueChange={setTab} className="px-8 pt-2 pb-12">
        <AnimatedTabsList tabs={TABS} value={tab} label="Case views" />
        <TabsPrimitive.Content value="decision" className="pt-6 outline-none">
          <DecisionTab detail={data} outbox={outbox} onApproved={(id, file) => file && setApprovedFiles((m) => ({ ...m, [id]: file }))} />
        </TabsPrimitive.Content>
        <TabsPrimitive.Content value="evidence" className="pt-6 outline-none">
          <EvidenceTab detail={data} questions={questions.data ?? []} />
        </TabsPrimitive.Content>
        <TabsPrimitive.Content value="activity" className="pt-6 outline-none">
          <AgentActivityTab detail={data} trace={trace.data} mode={traceMode(trace.data)} traceError={trace.isError ? trace.error.message : null} />
        </TabsPrimitive.Content>
        <TabsPrimitive.Content value="audit" className="pt-6 outline-none">
          <AuditTrailTab detail={data} replays={replays} onReplay={(r) => setReplays((list) => [...list, r])} />
        </TabsPrimitive.Content>
        <TabsPrimitive.Content value="technical" className="pt-6 outline-none">
          <TechnicalTab detail={data} />
        </TabsPrimitive.Content>
      </TabsPrimitive.Root>
    </>
  );
}
