import { useParams } from "react-router";
import { RunCanvas } from "../../run/RunCanvas";
import { RunHeader } from "./RunHeader";

export function RecordingPage() {
  const { runId = "" } = useParams();
  return (
    <RunCanvas
      key={runId}
      source={{ kind: "recorded", runId }}
      emptyText="Press play to replay this recording"
      header={({ chip, elapsedSeconds, playback }) => (
        <RunHeader
          title={playback.meta?.vendor_name ? `Recorded run: ${playback.meta.vendor_name}` : "Recorded run"}
          chip={chip}
          elapsedSeconds={elapsedSeconds}
          runId={runId}
        />
      )}
    />
  );
}
