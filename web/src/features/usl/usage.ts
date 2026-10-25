import type { AgentInfo, TraceEvent } from "../../api/types";

/** The agents that ran each query in one real run: query events that are not the data layer's own. */
export function agentsByQuery(trace: TraceEvent[] | undefined, roster: AgentInfo[] | undefined): Map<string, string[]> {
  const names = new Map((roster ?? []).map((a) => [a.trace_name, a.name]));
  const out = new Map<string, Set<string>>();
  for (const event of trace ?? []) {
    if (!event.query_id || event.agent_name === "data") continue;
    const set = out.get(event.query_id) ?? new Set<string>();
    set.add(names.get(event.agent_name) ?? event.agent_name);
    out.set(event.query_id, set);
  }
  return new Map([...out].map(([k, v]) => [k, [...v].sort()]));
}
