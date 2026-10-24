// The selected node, edge or event (design §7.5). Provider metadata is rendered from the whitelist only.
import { type ReactNode, useState } from "react";
import type { AgentInfo, TraceEvent } from "../api/types";
import { describe } from "./describe";
import { kv } from "./parse";
import type { Registry } from "./registry";
import type { RunState } from "./types";
import { filterProviderMeta, safeTraceLine } from "./whitelist";
import type { Selection } from "../graph/BenchGraph";
import { Button } from "../ui/button";
import { Identifier } from "../ui/Identifier";

const DEVIATIONS_URL = "https://github.com/awkwardapples/Arbiter/blob/main/docs/evidence/nightshift_deviations.md";

const TRACE_NAMES: Record<string, string> = {
  planner: "PlannerAgent",
  evidence: "EvidenceAgent",
  evaluator: "EvaluatorAgent",
  challenger: "ChallengerAgent",
  reporter: "ReporterAgent",
  policy: "PolicyEngine",
  memory: "MemoryKeeper",
  contract: "ActionExecutor",
  guard: "ScoutGuard",
};

const META_LABELS: Record<string, string> = {
  requested_model: "Model requested",
  routed_model: "Model routed",
  "winning_route.label": "Model served",
  "winning_route.model": "Served model id",
  "app_policy.requested_mode": "Lane requested",
  "app_policy.routed_mode": "Lane routed",
  "app_policy.mode_coerced": "Lane coerced",
  receipt_id: "Receipt id",
  decision_id: "Decision id",
  mode: "Nightshift mode",
  "cost.actual_usd": "Cost (USD)",
  no_think: "No-think",
};

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-2 py-0.5 text-[13px]">
      <dt className="text-graphite">{label}</dt>
      <dd className="min-w-0 break-words text-ink">{children}</dd>
    </div>
  );
}

function EventDetails({ event, registry }: { event: TraceEvent; registry: Registry }) {
  const line = describe(event, registry);
  const meta = filterProviderMeta(event.provider_meta);
  const queryId = event.query_id ?? kv(event.input_summary).query_id;
  const query = queryId ? registry[queryId] : undefined;
  const requestId = kv(event.output_summary).zetaris_request_id;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-ink">{line.text}</p>
      {line.detail ? <p className="text-[12px] text-graphite">{line.detail}</p> : null}
      <dl>
        <Field label="Agent">{event.agent_name}</Field>
        <Field label="Action">{event.action}</Field>
        <Field label="Status">{event.status}</Field>
        <Field label="Time (UTC)">{event.timestamp.replace("T", " ").slice(0, 23)}</Field>
        {event.latency_ms != null ? <Field label="Latency">{(event.latency_ms / 1000).toFixed(1)} s</Field> : null}
        {event.model ? <Field label="Model">{event.model}</Field> : null}
        {event.route ? <Field label="Lane">{event.route}</Field> : null}
        {event.tokens_in != null ? <Field label="Tokens">{`${event.tokens_in} in, ${event.tokens_out ?? "?"} out`}</Field> : null}
        {query ? (
          <>
            <Field label="Query">{query.description}</Field>
            <Field label="Systems">{query.systems.join(", ")}</Field>
            {event.rows != null || kv(event.output_summary).rows ? <Field label="Rows">{event.rows ?? kv(event.output_summary).rows}</Field> : null}
            {requestId ? (
              <Field label="Zetaris request id">
                <Identifier value={requestId} short={13} />
              </Field>
            ) : null}
            <Field label="Query id">
              <span className="font-mono text-xs">{queryId}</span>
            </Field>
          </>
        ) : null}
        {Object.entries(meta).map(([key, value]) => (
          <Field key={key} label={META_LABELS[key] ?? key}>
            {key === "receipt_id" || key === "decision_id" ? <Identifier value={value} /> : value}
          </Field>
        ))}
      </dl>
      {meta["app_policy.mode_coerced"] === "True" ? (
        <p className="text-[12px] text-graphite">
          Lane coerced to auto by a Nightshift app rule.{" "}
          <a className="text-record underline" href={DEVIATIONS_URL} target="_blank" rel="noreferrer">
            Read the recorded deviation
          </a>
        </p>
      ) : null}
      {query?.sql ? (
        <details className="text-[12px]">
          <summary className="cursor-pointer text-graphite">SQL resolved against the current layer</summary>
          <pre className="mt-1 overflow-x-auto rounded-[6px] bg-well p-2 font-mono text-[11px] text-ink">{query.sql}</pre>
        </details>
      ) : null}
    </div>
  );
}

function TraceLine({ event }: { event: TraceEvent }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-hairline pt-2">
      <Button variant="ghost" size="sm" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "Hide the trace line" : "Show the trace line"}
      </Button>
      {open ? (
        <pre data-testid="trace-line" className="mt-1 max-h-72 overflow-auto rounded-[6px] bg-well p-2 font-mono text-[11px] leading-4 text-ink">
          {JSON.stringify(safeTraceLine(event as Record<string, unknown>), null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export interface InspectorProps {
  state: RunState;
  selection: Selection;
  registry: Registry;
  agents: AgentInfo[];
  recordingPath: string | null;
  onSelectEvent?: (index: number) => void;
}

export function Inspector({ state, selection, registry, agents, recordingPath, onSelectEvent }: InspectorProps) {
  if (!selection) {
    return (
      <div className="px-4 py-6 text-sm text-graphite">
        <p>Select a node, an edge or an activity line to see what happened there.</p>
        {recordingPath ? (
          <p className="mt-3 text-[12px]">
            Recording: <span className="font-mono">{recordingPath}</span>
          </p>
        ) : null}
      </div>
    );
  }
  let title = "";
  let role = "";
  let indices: number[] = [];
  let focus: number | null = null;
  if (selection.kind === "event") {
    focus = selection.index;
    const event = state.events[focus];
    title = event ? describe(event, registry).text : "Event";
  } else if (selection.kind === "node") {
    const node = state.nodes[selection.id];
    title = node?.label ?? selection.id;
    role = node?.role ?? "";
    indices = node?.eventIdx ?? [];
    focus = indices.length ? indices[indices.length - 1] : null;
  } else {
    const edge = state.edges[selection.id];
    title = edge?.lastLabel ?? selection.id;
    role = edge ? `${edge.count} ${edge.count === 1 ? "time" : "times"}` : "";
    indices = edge?.eventIdx ?? [];
    focus = indices.length ? indices[indices.length - 1] : null;
  }
  const agent = selection.kind === "node" ? agents.find((a) => a.trace_name === TRACE_NAMES[selection.id]) : undefined;
  const event = focus !== null ? state.events[focus] : undefined;
  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto px-4 py-3">
      <div>
        <h3 className="text-md font-semibold text-ink">{title}</h3>
        {role ? <p className="text-[13px] text-graphite">{role}</p> : null}
      </div>
      {agent ? (
        <dl className="rounded-panel border border-hairline px-3 py-2">
          <Field label="Can">{agent.can}</Field>
          <Field label="Cannot">{agent.cannot}</Field>
          <Field label="Kind">{agent.kind}</Field>
        </dl>
      ) : null}
      {selection.kind === "node" && selection.id === "policy" && state.policy ? (
        <dl className="rounded-panel border border-hairline px-3 py-2">
          <Field label="Outcome">{state.policy.outcome}</Field>
          <Field label="Tier">{state.policy.tier ?? "not recorded"}</Field>
          <Field label="Failing controls">{state.policy.failing.join(", ") || "none"}</Field>
          <Field label="Unknown controls">{state.policy.unknown.join(", ") || "none"}</Field>
        </dl>
      ) : null}
      {selection.kind === "node" && selection.id === "clash" ? (
        <ul className="flex flex-col gap-1 text-[13px]">
          {state.clash.map((c) => (
            <li key={c.fromEvent}>{c.text}</li>
          ))}
        </ul>
      ) : null}
      {indices.length > 1 ? (
        <ol className="flex flex-col gap-0.5" aria-label="Events here">
          {indices.map((k) => (
            <li key={k}>
              <button
                type="button"
                className="w-full rounded-[4px] px-2 py-0.5 text-left text-[12px] text-ink hover:bg-well"
                onClick={() => onSelectEvent?.(k)}
              >
                {describe(state.events[k], registry).text}
              </button>
            </li>
          ))}
        </ol>
      ) : null}
      {event ? <EventDetails event={event} registry={registry} /> : null}
      {event ? <TraceLine key={focus ?? -1} event={event} /> : null}
    </div>
  );
}
