import { useHealth } from "../api/queries";
import { modeChipText } from "../run/mode";
import { ModeChip } from "../ui/ModeChip";

/** The mode chip for pages without a run: its text comes from GET /health (design §5). */
export function HealthModeChip() {
  const health = useHealth();
  if (health.isError) {
    return <span className="text-xs text-clash">The API is not answering. Start it with `python run.py serve`.</span>;
  }
  if (!health.data) return <span className="text-xs text-graphite">Checking the API…</span>;
  return <ModeChip chip={modeChipText({ kind: "mode", mode: health.data.mode })} />;
}
