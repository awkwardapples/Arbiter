// The timeline at the foot of the canvas (design §6): ticks for moments, red for send-backs and fallbacks.
import { FastForward, Pause, Play, SkipForward, StepForward } from "lucide-react";
import type { TraceEvent } from "../api/types";
import { isMoment, type PaceMode, type Speed } from "./pacer";
import { Button } from "../ui/button";
import { cn } from "../ui/lib/cn";

const RED = new Set(["needs_revision", "fallback", "blocked", "failed", "error"]);

export interface ScrubberProps {
  events: TraceEvent[];
  applied: number;
  mode: PaceMode;
  speed: Speed;
  playing: boolean;
  onPlay(): void;
  onPause(): void;
  onStep(): void;
  onSeek(index: number): void;
  onSkip(): void;
  onSpeed(speed: Speed): void;
}

export function Scrubber(p: ScrubberProps) {
  const total = p.events.length;
  const atEnd = total > 0 && p.applied >= total;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1">
        {p.playing ? (
          <Button variant="secondary" size="icon" aria-label="Pause" onClick={p.onPause}>
            <Pause />
          </Button>
        ) : (
          <Button variant="secondary" size="icon" aria-label="Play" onClick={p.onPlay} disabled={atEnd}>
            <Play />
          </Button>
        )}
        <Button variant="secondary" size="icon" aria-label="Step to the next moment" onClick={p.onStep} disabled={atEnd}>
          <StepForward />
        </Button>
      </div>
      <div className="relative min-w-[200px] flex-1">
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-2">
          {total > 1
            ? p.events.map((e, k) =>
                isMoment(e) ? (
                  <span
                    key={k}
                    className={cn("absolute top-0 h-2 w-px", RED.has(e.status) || e.action === "request_replan" ? "bg-clash" : "bg-graphite/50")}
                    style={{ left: `${(k / (total - 1)) * 100}%` }}
                  />
                ) : null,
              )
            : null}
        </div>
        <input
          type="range"
          aria-label="Timeline"
          min={0}
          max={total}
          value={Math.min(p.applied, total)}
          onChange={(event) => p.onSeek(Number(event.target.value))}
          className="mt-2 w-full accent-[var(--color-ink)]"
        />
      </div>
      <span className="font-mono text-xs text-graphite">
        {p.applied}/{total}
      </span>
      {p.mode === "recorded" ? (
        <div role="group" aria-label="Speed" className="flex items-center gap-1">
          <FastForward className="size-4 text-graphite" aria-hidden />
          {([1, 4, 16] as Speed[]).map((s) => (
            <Button key={s} variant={p.speed === s ? "primary" : "secondary"} size="sm" aria-pressed={p.speed === s} onClick={() => p.onSpeed(s)}>
              {s}×
            </Button>
          ))}
        </div>
      ) : null}
      <Button variant="secondary" size="sm" onClick={p.onSkip} disabled={atEnd}>
        <SkipForward />
        Skip to result
      </Button>
    </div>
  );
}
