// One plain sentence per event, grouped under stage headings, newest at the bottom (design §7.5).
import { useEffect, useMemo, useRef } from "react";
import { type CounterKey, countersFor } from "./counters";
import { describe, type Line } from "./describe";
import type { Registry } from "./registry";
import type { RunState, StageName } from "./types";
import { cn } from "../ui/lib/cn";

interface Row {
  heading: StageName | null;
  index: number;
  last: number;
  line: Line;
  stage: StageName | null;
}

const TONE: Record<string, string> = {
  record: "border-record",
  claim: "border-claim",
  reason: "border-reason",
  clash: "border-clash",
  ink: "border-ink",
  plain: "border-hairline",
};

function rows(state: RunState, registry: Registry, filter: CounterKey | null): Row[] {
  const out: Row[] = [];
  state.events.forEach((event, index) => {
    if (filter && !countersFor(event).includes(filter)) return;
    // Zetaris' own line repeats the agent's query line that follows it; it shows under its counter.
    if (!filter && event.action === "query_zetaris") return;
    const stage = state.stageOf[index] ?? null;
    const prev = out[out.length - 1];
    if (event.action === "guard_segment" && prev && state.events[prev.index].action === "guard_segment" && !filter) {
      const batch = state.events.slice(prev.index, index + 1).filter((e) => e.action === "guard_segment");
      const blocked = batch.filter((e) => e.status === "blocked").length;
      const docs = batch.filter((e) => (e.input_summary ?? "").includes("segment_id=doc-")).length;
      const noun = docs === batch.length ? "documents" : docs ? "items" : "answers";
      prev.line = {
        text: blocked ? `The Scout guard screened ${batch.length} ${noun}: ${blocked} blocked.` : `The Scout guard screened ${batch.length} ${noun}: all passed.`,
        tone: blocked ? "clash" : "claim",
        generic: false,
      };
      prev.last = index;
      return;
    }
    out.push({ heading: null, index, last: index, line: describe(event, registry), stage });
  });
  let lastStage: StageName | null | undefined;
  for (const row of out) {
    row.heading = row.stage !== lastStage ? row.stage : null;
    lastStage = row.stage;
  }
  return out;
}

export function ActivityPanel({
  state,
  registry,
  filter,
  selected,
  onSelect,
}: {
  state: RunState;
  registry: Registry;
  filter: CounterKey | null;
  selected: number | null;
  onSelect: (index: number) => void;
}) {
  const list = useMemo(() => rows(state, registry, filter), [state, registry, filter]);
  const box = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);

  useEffect(() => {
    const el = box.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [list.length]);

  if (!list.length) {
    return <p className="px-4 py-6 text-sm text-graphite">{filter ? "No events of this kind yet." : "Nothing has happened yet."}</p>;
  }
  return (
    <div
      ref={box}
      className="h-full overflow-y-auto px-3 py-2"
      onScroll={(e) => {
        const el = e.currentTarget;
        pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      }}
    >
      <ol className="flex flex-col gap-1" aria-label="Activity">
        {list.map((row) => {
          const heading = row.heading;
          return (
            <li key={row.index}>
              {heading ? <p className="mt-2 mb-1 text-xs font-semibold text-graphite">{heading}</p> : null}
              <button
                type="button"
                onClick={() => onSelect(row.last)}
                className={cn(
                  "w-full rounded-[4px] border-l-2 py-1 pr-2 pl-2.5 text-left text-[13px] leading-[19px] text-ink hover:bg-well",
                  TONE[row.line.tone],
                  selected !== null && selected >= row.index && selected <= row.last && "bg-well",
                )}
              >
                {row.line.text}
                {row.line.detail ? <span className="block truncate text-[12px] text-graphite">{row.line.detail}</span> : null}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
