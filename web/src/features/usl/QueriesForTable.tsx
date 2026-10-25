import type { RegistryQuery } from "../../api/types";
import { Badge } from "../../ui/badge";
import { queriesForTable } from "./model";

export function QueriesForTable({
  table,
  registry,
  usage,
  usageCase,
}: {
  table: string;
  registry: RegistryQuery[];
  usage: Map<string, string[]>;
  usageCase: string | null;
}) {
  const queries = queriesForTable(table, registry);
  return (
    <div className="flex flex-col gap-3" data-testid="usl-queries">
      <h3 className="text-md font-semibold text-ink">
        Queries that read <span className="font-mono text-sm">{table}</span>
      </h3>
      {queries.length === 0 ? (
        <p className="text-sm text-graphite">No registry query reads this table directly.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {queries.map((q) => {
            const agents = usage.get(q.id);
            return (
              <li key={q.id} className="rounded-panel border border-hairline bg-sheet px-3 py-2" data-testid={`usl-query-${q.id}`}>
                <p className="text-sm text-ink">{q.description}</p>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-graphite">
                  <span className="font-mono">{q.id}</span>
                  {agents?.length ? (
                    agents.map((a) => (
                      <Badge key={a} tone="ink">
                        {a}
                      </Badge>
                    ))
                  ) : (
                    <span>{usageCase ? `Not run in ${usageCase}.` : "No run on this instance yet."}</span>
                  )}
                </p>
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-xs text-graphite">
        The Planner chooses from these queries; it cannot write SQL.
        {usageCase ? ` Agents shown are those that ran each query in ${usageCase}, the latest case on this instance.` : ""}
      </p>
    </div>
  );
}
