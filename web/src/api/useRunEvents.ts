// EventSource hook for GET /runs/{run_id}/events (P18-A §3.2). The browser reconnects by itself and
// sends Last-Event-ID, so the server replays only what was missed.
import { useEffect, useState } from "react";
import { apiUrl } from "./client";
import { type DoneEvent, parseDone, parseError, parseTraceEvent } from "./events";
import type { TraceEvent } from "./types";

export interface RunEvents {
  events: TraceEvent[];
  done: DoneEvent | null;
  error: string | null;
  connected: boolean;
}

const EMPTY: RunEvents = { events: [], done: null, error: null, connected: false };

export function useRunEvents(runId: string | null): RunEvents {
  // State is tagged with its run id, so switching runs starts from empty without a reset in the effect.
  const [tagged, setTagged] = useState<{ runId: string | null; value: RunEvents }>({ runId: null, value: EMPTY });

  useEffect(() => {
    if (!runId) return;
    const setState = (update: (s: RunEvents) => RunEvents) =>
      setTagged((prev) => ({ runId, value: update(prev.runId === runId ? prev.value : EMPTY) }));
    const source = new EventSource(apiUrl(`/runs/${encodeURIComponent(runId)}/events`));
    const seen = new Set<string>();

    source.onopen = () => setState((s) => ({ ...s, connected: true, error: null }));
    source.addEventListener("trace", (message) => {
      const id = (message as MessageEvent).lastEventId;
      if (id && seen.has(id)) return;
      if (id) seen.add(id);
      let data: unknown;
      try {
        data = JSON.parse((message as MessageEvent<string>).data);
      } catch {
        return;
      }
      const event = parseTraceEvent(data);
      if (event) setState((s) => ({ ...s, events: [...s.events, event] }));
    });
    source.addEventListener("done", (message) => {
      let done: DoneEvent | null = null;
      try {
        done = parseDone(JSON.parse((message as MessageEvent<string>).data));
      } catch {
        done = null;
      }
      setState((s) => ({ ...s, done, connected: false }));
      source.close();
    });
    source.addEventListener("error", (message) => {
      const raw = (message as MessageEvent<string>).data;
      if (typeof raw === "string" && raw) {
        let text: string | null = null;
        try {
          text = parseError(JSON.parse(raw));
        } catch {
          text = null;
        }
        setState((s) => ({ ...s, error: text ?? "The run stopped with an error.", connected: false }));
        source.close();
        return;
      }
      // A transport error: EventSource retries by itself unless the server closed for good.
      if (source.readyState === EventSource.CLOSED) {
        setState((s) => (s.done ? s : { ...s, connected: false, error: "Lost the connection to the run's event stream." }));
      } else {
        setState((s) => ({ ...s, connected: false }));
      }
    });
    return () => source.close();
  }, [runId]);

  return runId && tagged.runId === runId ? tagged.value : EMPTY;
}
