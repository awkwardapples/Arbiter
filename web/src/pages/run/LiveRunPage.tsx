import { useLocation, useParams } from "react-router";
import { useCase } from "../../api/queries";
import { RunCanvas } from "../../run/RunCanvas";
import { RunHeader } from "./RunHeader";

export function LiveRunPage() {
  const { runId = "" } = useParams();
  const location = useLocation();
  const passed = (location.state as { vendorName?: string } | null)?.vendorName ?? null;
  return (
    <RunCanvas
      key={runId}
      source={{ kind: "live", runId }}
      header={({ state, chip, elapsedSeconds }) => (
        <LiveTitle runId={runId} caseId={state.outcome ? state.caseId : null} vendorName={passed} chip={chip} elapsedSeconds={elapsedSeconds} />
      )}
    />
  );
}

function LiveTitle({ runId, caseId, vendorName, chip, elapsedSeconds }: { runId: string; caseId: string | null; vendorName: string | null; chip: Parameters<typeof RunHeader>[0]["chip"]; elapsedSeconds: number | null }) {
  // The vendor's name comes from the Assess page, or from the case record once the run is done.
  const record = useCase(vendorName ? null : caseId);
  const name = vendorName ?? record.data?.vendor ?? null;
  return <RunHeader title={name ? `Assessing ${name}` : "Assessment"} chip={chip} elapsedSeconds={elapsedSeconds} runId={runId} />;
}
