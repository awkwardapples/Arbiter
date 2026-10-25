import { useCallback, useState } from "react";
import { useAgents, useHealth, useRegistry } from "../../api/queries";
import { PageHeader } from "../../app/PageHeader";
import { Callout } from "../../ui/Callout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../ui/card";
import { DocLink } from "../../ui/DocLink";
import { dataModeLine, tableCounts, useCaseTrace, useCases, useParity, useUslModel } from "../../features/usl/api";
import { Catalogue } from "../../features/usl/Catalogue";
import { DataQuality } from "../../features/usl/DataQuality";
import { QueriesForTable } from "../../features/usl/QueriesForTable";
import { agentsByQuery } from "../../features/usl/usage";
import { UslDiagram } from "../../features/usl/UslDiagram";

export function SourcesPage() {
  const health = useHealth();
  const model = useUslModel();
  const registry = useRegistry();
  const parity = useParity();
  const agents = useAgents();
  const cases = useCases();
  const latestCase = cases.data?.length
    ? [...cases.data].sort((a, b) => (b.created ?? "").localeCompare(a.created ?? ""))[0].case_id
    : null;
  const trace = useCaseTrace(latestCase);
  const [selected, setSelected] = useState<string | null>(null);
  const onSelect = useCallback((name: string) => setSelected(name), []);
  const usage = agentsByQuery(trace.data, agents.data);

  return (
    <>
      <PageHeader title="Sources and semantic layer">
        Where the evidence comes from: the company's systems and the CISA catalogue, behind one governed model.
      </PageHeader>
      <div className="flex max-w-7xl flex-col gap-6 px-8 py-6">
        <p className="text-sm text-ink" data-testid="sources-mode">
          <span className="text-graphite">Data mode: </span>
          <span className="font-semibold">{health.data ? dataModeLine(health.data.data, health.data.mode) : "Checking the API…"}</span>
        </p>

        <Card data-testid="sources-usl">
          <CardHeader>
            <CardTitle>The USL model{model.data ? `: ${model.data.tables.length} tables` : ""}</CardTitle>
            <CardDescription>
              Each system names a vendor differently. The semantic layer states the keys and joins once, with a description for every
              table, so agents plan against one model. Select a table to see the queries that read it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {model.isError || registry.isError ? (
              <Callout tone="error" title="The USL model did not load.">
                {(model.error ?? registry.error)?.message} Check that the API is running, then reload.
              </Callout>
            ) : model.data && registry.data ? (
              <div className="flex flex-col gap-6">
                <UslDiagram
                  model={model.data}
                  registry={registry.data}
                  rowCounts={tableCounts(health.data?.data)}
                  selected={selected}
                  onSelect={onSelect}
                />
                <aside className="min-w-0 max-w-4xl" aria-live="polite">
                  {selected ? (
                    <QueriesForTable table={selected} registry={registry.data} usage={usage} usageCase={latestCase} />
                  ) : (
                    <p className="text-sm text-graphite">Select a table in the diagram to list the registry queries that read it.</p>
                  )}
                </aside>
              </div>
            ) : (
              <p className="text-sm text-graphite">Loading the model…</p>
            )}
          </CardContent>
        </Card>

        <Card data-testid="sources-dq-card">
          <CardHeader>
            <CardTitle>Data quality and parity</CardTitle>
            <CardDescription>The five data-quality rules, and whether Zetaris and the DuckDB mirror return the same rows.</CardDescription>
          </CardHeader>
          <CardContent>
            {parity.isError ? (
              <Callout title="No parity run is committed in this checkout.">
                Run <span className="font-mono">python run.py zetaris parity</span> against Zetaris to produce one.
              </Callout>
            ) : parity.data ? (
              <DataQuality parity={parity.data} />
            ) : (
              <p className="text-sm text-graphite">Loading the parity run…</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>The catalogue the Planner reads</CardTitle>
          </CardHeader>
          <CardContent>{model.data ? <Catalogue model={model.data} /> : null}</CardContent>
        </Card>

        <p className="text-sm text-graphite">
          The full write-up, with measurements: <DocLink path="docs/ZETARIS_USL.md" />.
        </p>
      </div>
    </>
  );
}
