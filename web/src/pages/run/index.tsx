import { useParams } from "react-router";
import { PageHeader } from "../../app/PageHeader";
import { Identifier } from "../../ui/Identifier";

function RunStub({ title }: { title: string }) {
  const { runId = "" } = useParams();
  return (
    <PageHeader title={title}>
      <Identifier value={runId} />
    </PageHeader>
  );
}

export function LiveRunPage() {
  return <RunStub title="Assessment" />;
}

export function RecordingPage() {
  return <RunStub title="Recorded run" />;
}
