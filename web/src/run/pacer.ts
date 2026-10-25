// When events reach the reducer (design §6). Live passes them through; paced holds each for a minimum
// dwell; recorded replays the real gaps, scaled by the speed and capped at 3 s each.
import type { TraceEvent } from "../api/types";

export type PaceMode = "live" | "paced" | "recorded";
export type Speed = 1 | 4 | 16;

export const RECORDED_GAP_CAP_MS = 3000;

export function dwellFor(event: TraceEvent): number {
  const a = event.action;
  if (a === "transition") return 350;
  if (a === "plan" || a === "evaluate" || a === "challenge" || a === "request_replan") return 700;
  if (a.startsWith("query")) return 250;
  if (a === "guard_segment") return 40;
  return 150;
}

function time(event: TraceEvent): number {
  const t = Date.parse(event.timestamp.endsWith("Z") || /[+-]\d\d:?\d\d$/.test(event.timestamp) ? event.timestamp : `${event.timestamp}Z`);
  return Number.isNaN(t) ? 0 : t;
}

export function recordedGap(prev: TraceEvent, next: TraceEvent, speed: Speed): number {
  const gap = Math.max(0, time(next) - time(prev));
  return Math.min(gap, RECORDED_GAP_CAP_MS) / speed;
}

/** A moment: worth stopping on when stepping (design §6). */
export function isMoment(event: TraceEvent): boolean {
  return (
    Boolean(event.target_agent) ||
    event.status !== "success" ||
    event.action === "contradiction_found" ||
    event.action === "decide" ||
    event.action === "complete_run"
  );
}

export interface PacerOptions {
  events: TraceEvent[];
  mode: PaceMode;
  speed: Speed;
  onApply: (applied: number) => void;
}

export interface Pacer {
  start(): void;
  pause(): void;
  stop(): void;
  step(): void;
  seek(index: number): void;
  skipToEnd(): void;
  setSpeed(speed: Speed): void;
  setMode(mode: PaceMode): void;
  push(event: TraceEvent): void;
  readonly applied: number;
  readonly playing: boolean;
  readonly length: number;
}

export function createPacer(options: PacerOptions): Pacer {
  const list = [...options.events];
  let mode = options.mode;
  let speed = options.speed;
  let applied = 0;
  let playing = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const clear = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  const emit = () => options.onApply(applied);

  const wait = (): number => {
    if (applied === 0) return 0;
    const prev = list[applied - 1];
    if (mode === "recorded") return recordedGap(prev, list[applied], speed);
    return dwellFor(prev);
  };

  const schedule = (): void => {
    if (!playing || timer !== null || applied >= list.length) return;
    if (mode === "live") {
      applied = list.length;
      emit();
      return;
    }
    timer = setTimeout(() => {
      timer = null;
      applied += 1;
      emit();
      schedule();
    }, wait());
  };

  const jump = (index: number) => {
    clear();
    applied = Math.max(0, Math.min(index, list.length));
    emit();
    schedule();
  };

  return {
    start() {
      playing = true;
      schedule();
    },
    pause() {
      playing = false;
      clear();
    },
    stop() {
      playing = false;
      clear();
    },
    step() {
      playing = false;
      clear();
      let k = applied;
      while (k < list.length && !isMoment(list[k])) k += 1;
      applied = Math.min(k + 1, list.length);
      emit();
    },
    seek: jump,
    skipToEnd() {
      jump(list.length);
    },
    setSpeed(next) {
      speed = next;
      if (timer !== null) {
        clear();
        schedule();
      }
    },
    setMode(next) {
      mode = next;
      if (timer !== null || mode === "live") {
        clear();
        schedule();
      }
    },
    push(event) {
      list.push(event);
      schedule();
    },
    get applied() {
      return applied;
    },
    get playing() {
      return playing;
    },
    get length() {
      return list.length;
    },
  };
}
