// Feeds one reducer from any of the three sources (design §6). The reducer is pure and cheap, so the
// state is a replay of the first `applied` events: seeking backwards is the same code path.
import { useEffect, useMemo, useRef, useState } from "react";
import { useRecording } from "../api/queries";
import type { RecordingMeta, TraceEvent } from "../api/types";
import { useRunEvents } from "../api/useRunEvents";
import { createPacer, type PaceMode, type Pacer, type Speed } from "./pacer";
import { replay } from "./reducer";
import type { Registry } from "./registry";
import type { RunState } from "./types";

export type RunSource =
  | { kind: "live"; runId: string }
  | { kind: "recorded"; runId: string }
  | { kind: "events"; events: TraceEvent[]; mode: PaceMode };

export interface Playback {
  state: RunState;
  events: TraceEvent[];
  applied: number;
  total: number;
  mode: PaceMode;
  speed: Speed;
  playing: boolean;
  loading: boolean;
  error: string | null;
  meta: RecordingMeta | null;
  doneCaseId: string | null;
  controls: {
    play(): void;
    pause(): void;
    step(): void;
    seek(index: number): void;
    skipToEnd(): void;
    restart(): void;
    setSpeed(speed: Speed): void;
  };
}

const NO_EVENTS: TraceEvent[] = [];

function sampleMode(event: TraceEvent | undefined): boolean {
  const mode = event?.mode as Record<string, string> | null | undefined;
  return mode?.data === "duckdb" && mode?.llm === "offline";
}

export function usePacer(source: RunSource, registry: Registry): Playback {
  const live = useRunEvents(source.kind === "live" ? source.runId : null);
  const recording = useRecording(source.kind === "recorded" ? source.runId : null);

  const events: TraceEvent[] =
    source.kind === "live" ? live.events : source.kind === "recorded" ? (recording.data?.events ?? NO_EVENTS) : source.events;
  const ready = source.kind !== "recorded" || Boolean(recording.data);
  const key = source.kind === "events" ? source.events : `${source.kind}:${source.runId}`;

  // A recording of a sample-mode run has millisecond gaps; it is paced like a sample run instead.
  const recordedSample = source.kind === "recorded" && sampleMode(events[0]);
  const baseMode: PaceMode = source.kind === "recorded" ? (recordedSample ? "paced" : "recorded") : source.kind === "events" ? source.mode : "live";
  const mode: PaceMode = source.kind === "live" && sampleMode(events[0]) ? "paced" : baseMode;

  const [applied, setApplied] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeedState] = useState<Speed>(baseMode === "recorded" ? 4 : 1);
  const pacer = useRef<Pacer | null>(null);
  const pushed = useRef(0);

  useEffect(() => {
    if (!ready) return;
    const initial = source.kind === "live" ? [] : events;
    const p = createPacer({ events: initial, mode: baseMode, speed: baseMode === "recorded" ? 4 : 1, onApply: setApplied });
    pacer.current = p;
    pushed.current = initial.length;
    p.start();
    return () => {
      p.stop();
      pacer.current = null;
      setApplied(0);
    };
    // The pacer is rebuilt only when the source changes, not on every new live event.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ready]);

  useEffect(() => {
    const p = pacer.current;
    if (!p || source.kind !== "live") return;
    if (events.length && pushed.current === 0) p.setMode(mode);
    for (let k = pushed.current; k < events.length; k++) p.push(events[k]);
    pushed.current = events.length;
  }, [events, mode, source.kind]);

  const state = useMemo(() => replay(events, registry, applied), [events, registry, applied]);

  const controls = useMemo(
    () => ({
      play() {
        pacer.current?.start();
        setPlaying(true);
      },
      pause() {
        pacer.current?.pause();
        setPlaying(false);
      },
      step() {
        pacer.current?.step();
        setPlaying(false);
      },
      seek(index: number) {
        pacer.current?.seek(index);
      },
      skipToEnd() {
        pacer.current?.skipToEnd();
      },
      restart() {
        pacer.current?.seek(0);
        pacer.current?.start();
        setPlaying(true);
      },
      setSpeed(next: Speed) {
        pacer.current?.setSpeed(next);
        setSpeedState(next);
      },
    }),
    [],
  );

  const error =
    source.kind === "live" ? live.error : source.kind === "recorded" && recording.isError ? (recording.error as Error).message : null;

  return {
    state,
    events,
    applied,
    total: events.length,
    mode,
    speed,
    playing: playing && applied < events.length,
    loading: source.kind === "recorded" ? recording.isLoading : source.kind === "live" ? events.length === 0 && !live.error : false,
    error,
    meta: recording.data?.meta ?? null,
    doneCaseId: live.done?.case_id ?? null,
    controls,
  };
}
