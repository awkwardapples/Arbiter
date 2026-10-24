// The run view as one reusable component (pass §4). 18c replays a case with {kind: "events"}.
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { useAgents, useRegistry } from "../api/queries";
import { ActivityPanel } from "./ActivityPanel";
import { BehaviourStrip } from "./BehaviourStrip";
import type { CounterKey } from "./counters";
import { agentShort } from "./describe";
import { Inspector } from "./Inspector";
import { modeChipText, type ModeChip } from "./mode";
import { nodeForAgent } from "./nodes";
import { buildRegistry, type Registry } from "./registry";
import { RulingCard } from "./RulingCard";
import { Scrubber } from "./Scrubber";
import { StageRail } from "./StageRail";
import type { RunState } from "./types";
import { type Playback, type RunSource, usePacer } from "./usePacer";
import { BenchGraph, type Selection } from "../graph/BenchGraph";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { Button } from "../ui/button";
import { Callout } from "../ui/Callout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

export type { RunSource } from "./usePacer";

export interface RunInfo {
  state: RunState;
  chip: ModeChip;
  elapsedSeconds: number | null;
  playback: Playback;
}

const EMPTY_REGISTRY: Registry = {};

function toMs(iso: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso.endsWith("Z") ? iso : `${iso}Z`);
  return Number.isNaN(t) ? null : t;
}

function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);
  return now;
}

export function RunCanvas({
  source,
  header,
  registryOverride,
  emptyText = "Pick a vendor to start an assessment",
}: {
  source: RunSource;
  header?: (info: RunInfo) => ReactNode;
  registryOverride?: Registry;
  emptyText?: string;
}) {
  const registryQuery = useRegistry();
  const agents = useAgents();
  const registry = useMemo(
    () => registryOverride ?? (registryQuery.data ? buildRegistry(registryQuery.data) : EMPTY_REGISTRY),
    [registryOverride, registryQuery.data],
  );
  const playback = usePacer(source, registry);
  const { state } = playback;
  const [selection, setSelection] = useState<Selection>(null);
  const [tab, setTab] = useState("activity");
  const [filter, setFilter] = useState<CounterKey | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);

  const realtime = playback.mode === "live" && !state.outcome && state.index > 0;
  const now = useNow(realtime);
  const clock = realtime ? now : (toMs(state.lastAt) ?? now);
  const started = toMs(state.startedAt);
  const elapsedSeconds = started !== null ? Math.max(0, (clock - started) / 1000) : null;

  const flight = state.inFlight[state.inFlight.length - 1];
  const waiting = flight
    ? {
        agent: nodeForAgent(flight.agent) ?? "",
        text: `${agentShort(flight.agent)} is waiting for Nightshift: ${Math.max(0, Math.round((clock - (toMs(flight.startedAt) ?? clock)) / 1000))} s`,
      }
    : null;

  const recorded = source.kind !== "live";
  const chip = recorded
    ? modeChipText({ kind: "recording", startedAt: playback.meta?.recorded_at ?? state.startedAt, fallbacks: state.fallbacks, mode: playback.meta?.mode ?? state.mode })
    : modeChipText({ kind: "mode", mode: state.mode, fallbacks: state.fallbacks, paced: playback.mode === "paced" && playback.applied < playback.total });

  const select = (next: Selection) => {
    setSelection(next);
    if (next) {
      setTab("inspector");
      setPanelOpen(true);
    }
  };

  return (
    <div className="flex min-h-screen flex-col gap-2.5 lg:h-screen">
      {header?.({ state, chip, elapsedSeconds, playback })}
      <div className="px-6">
        <StageRail state={state} />
      </div>
      {playback.error ? (
        <div className="px-6">
          <Callout tone="error" title="The run's events stopped.">
            {playback.error}
          </Callout>
        </div>
      ) : null}
      {!registryOverride && registryQuery.isError ? (
        <div className="px-6">
          <Callout tone="warn" title="The query registry did not load.">
            Data sources are not drawn on the bench. Check that the API serves GET /registry/queries.
          </Callout>
        </div>
      ) : null}
      <div className="flex min-h-0 flex-1 gap-3 px-6 max-lg:flex-col">
        <div className="relative min-h-[340px] min-w-0 flex-1 overflow-hidden rounded-panel border border-hairline bg-well max-lg:min-h-[420px]">
          <BenchGraph
            state={state}
            speed={playback.mode === "recorded" ? playback.speed : 1}
            emptyText={source.kind === "live" ? "Waiting for the first event of this run" : emptyText}
            waiting={waiting}
            onSelect={select}
          />
          <Button
            variant="secondary"
            size="sm"
            className="absolute top-2 right-2 z-10 max-lg:hidden"
            onClick={() => setPanelOpen((o) => !o)}
            aria-expanded={panelOpen}
          >
            {panelOpen ? <PanelRightClose /> : <PanelRightOpen />}
            {panelOpen ? "Hide panel" : "Show panel"}
          </Button>
          {state.outcome ? (
            <div className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-end px-3 [&>*]:pointer-events-auto">
              <RulingCard state={state} caseId={playback.doneCaseId} onWatchAgain={playback.controls.restart} />
            </div>
          ) : null}
        </div>
        <aside hidden={!panelOpen} className="flex min-h-0 w-[380px] shrink-0 flex-col rounded-panel border border-hairline bg-sheet max-lg:h-[420px] max-lg:w-full">
          <Tabs value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
            <TabsList className="px-2">
              <TabsTrigger value="activity">Activity{filter ? " (filtered)" : ""}</TabsTrigger>
              <TabsTrigger value="inspector">Inspector</TabsTrigger>
            </TabsList>
            <TabsContent value="activity" className="min-h-0 flex-1">
              <ActivityPanel
                state={state}
                registry={registry}
                filter={filter}
                selected={selection?.kind === "event" ? selection.index : null}
                onSelect={(index) => select({ kind: "event", index })}
              />
            </TabsContent>
            <TabsContent value="inspector" className="min-h-0 flex-1">
              <Inspector
                state={state}
                selection={selection}
                registry={registry}
                agents={agents.data ?? []}
                recordingPath={playback.meta?.path ?? null}
                onSelectEvent={(index) => select({ kind: "event", index })}
              />
            </TabsContent>
          </Tabs>
        </aside>
      </div>
      <div className="flex flex-col gap-2 px-6 pb-3">
        <BehaviourStrip
          state={state}
          filter={filter}
          onFilter={(key) => {
            setFilter(key);
            setTab("activity");
          }}
        />
        <Scrubber
          events={playback.events}
          applied={playback.applied}
          mode={playback.mode}
          speed={playback.speed}
          playing={playback.playing}
          onPlay={playback.controls.play}
          onPause={playback.controls.pause}
          onStep={playback.controls.step}
          onSeek={playback.controls.seek}
          onSkip={playback.controls.skipToEnd}
          onSpeed={playback.controls.setSpeed}
        />
      </div>
    </div>
  );
}
