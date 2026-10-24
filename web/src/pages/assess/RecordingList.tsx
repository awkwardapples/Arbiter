// Committed traces this instance can replay (GET /recordings). Live kinds first, grouped by kind; a
// recording whose events say DuckDB and offline is listed apart, so nothing sample-mode passes as live.
import { useNavigate } from "react-router";
import { useRecordings } from "../../api/queries";
import type { RecordingMeta } from "../../api/types";
import { formatUtc } from "../../run/mode";
import { duration } from "../../run/parse";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { OutcomeBadge } from "../../ui/OutcomeBadge";

const KIND_ORDER = ["live_example", "live_eval", "live_session", "sample_example"];
const KIND_WORDS: Record<string, string> = {
  live_example: "Live examples",
  live_eval: "Live evaluation runs",
  live_session: "Live demo session",
  sample_example: "Sample-mode examples",
};

const isLive = (r: RecordingMeta) => r.mode?.data === "zetaris" && r.mode?.llm === "meterless";

function Row({ rec }: { rec: RecordingMeta }) {
  const navigate = useNavigate();
  const when = rec.recorded_at ? formatUtc(rec.recorded_at) : null;
  return (
    <li data-run-id={rec.run_id} className="flex items-center gap-4 px-4 py-2.5">
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="truncate font-medium text-ink">{rec.vendor_name ?? "Unknown vendor"}</span>
          <OutcomeBadge outcome={rec.outcome} />
        </span>
        <span className="block text-[13px] text-graphite">
          {[rec.duration_s !== null ? duration(rec.duration_s) : null, when, rec.n_model_calls ? `${rec.n_model_calls} model calls` : "no model calls", rec.n_fallbacks ? `${rec.n_fallbacks} fallbacks` : null]
            .filter(Boolean)
            .join(". ")}
        </span>
      </span>
      <Button variant="secondary" size="sm" onClick={() => navigate(`/recordings/${encodeURIComponent(rec.run_id)}`)} aria-label={`Watch ${rec.vendor_name ?? rec.run_id}, recorded ${when ?? ""}`}>
        Watch
      </Button>
    </li>
  );
}

function Groups({ list }: { list: RecordingMeta[] }) {
  const kinds = [...new Set(list.map((r) => r.kind))].sort((a, b) => (KIND_ORDER.indexOf(a) + 99) % 99 - (KIND_ORDER.indexOf(b) + 99) % 99);
  return (
    <div className="flex flex-col gap-4">
      {kinds.map((kind) => (
        <div key={kind}>
          <h3 className="mb-1.5 text-sm font-semibold text-graphite">{KIND_WORDS[kind] ?? kind}</h3>
          <ul className="divide-y divide-hairline rounded-panel border border-hairline bg-sheet">
            {list
              .filter((r) => r.kind === kind)
              .sort((a, b) => (b.recorded_at ?? "").localeCompare(a.recorded_at ?? ""))
              .map((rec) => (
                <Row key={rec.run_id} rec={rec} />
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function RecordingList() {
  const recordings = useRecordings();
  if (recordings.isError) {
    return <Callout tone="warn" title="Recordings did not load.">{(recordings.error as Error).message}</Callout>;
  }
  if (recordings.isLoading) return <p className="text-sm text-graphite">Loading recordings…</p>;
  const all = recordings.data ?? [];
  const live = all.filter(isLive);
  const other = all.filter((r) => !isLive(r));
  return (
    <div className="flex flex-col gap-4">
      {live.length ? <Groups list={live} /> : <p className="text-sm text-graphite">No recorded live runs are committed in this build.</p>}
      {other.length ? (
        <details>
          <summary className="cursor-pointer text-sm text-graphite">Recordings of sample-mode runs ({other.length})</summary>
          <div className="mt-3">
            <Groups list={other} />
          </div>
        </details>
      ) : null}
    </div>
  );
}
