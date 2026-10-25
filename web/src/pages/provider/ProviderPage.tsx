import { Link } from "react-router";
import { useHealth } from "../../api/queries";
import { PageHeader } from "../../app/PageHeader";
import { formatUtc } from "../../run/mode";
import { Badge } from "../../ui/badge";
import { Callout } from "../../ui/Callout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../ui/card";
import { CopyBlock } from "../../ui/CopyBlock";
import { DocLink } from "../../ui/DocLink";
import { Identifier } from "../../ui/Identifier";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { DEVIATION_SENTENCE, connection, proof, useNightshiftProof, useRecentReceipts } from "./provider";

const PROVIDER_WORDS: Record<string, string> = {
  meterless: "Meterless Nightshift",
  nvidia: "NVIDIA API, direct",
  offline: "Deterministic fallback (no model calls)",
  error: "Not configured correctly",
};

const seconds = (ms: number | null) => (ms == null ? "–" : `${(ms / 1000).toFixed(1)} s`);

function ConnectionCard() {
  const health = useHealth();
  const c = connection(health.data);
  const nemotron = c.modelsSeen.filter((m) => m.startsWith("nvidia/"));
  const others = c.modelsSeen.length - nemotron.length;
  return (
    <Card data-testid="provider-connection">
      <CardHeader>
        <CardTitle>Connection</CardTitle>
        <CardDescription>What this API resolved at start-up, from /health.</CardDescription>
      </CardHeader>
      <CardContent>
        {health.isError ? (
          <Callout tone="error" title="The API is not answering.">
            Start it with <span className="font-mono">python run.py serve</span>, then reload.
          </Callout>
        ) : !health.data ? (
          <p className="text-sm text-graphite">Checking the API…</p>
        ) : (
          <dl className="grid gap-x-6 gap-y-2 text-sm md:grid-cols-[max-content_1fr]">
            <dt className="text-graphite">Model calls go to</dt>
            <dd className="text-ink" data-testid="provider-resolved">
              {c.resolved ? (PROVIDER_WORDS[c.resolved] ?? c.resolved) : "Unknown"}
              {c.setting ? <span className="ml-2 font-mono text-xs text-graphite">LLM_PROVIDER={c.setting}</span> : null}
            </dd>
            <dt className="text-graphite">Nightshift</dt>
            <dd className="flex flex-wrap items-center gap-2" data-testid="provider-nightshift">
              {c.nightshiftStatus ? (
                <Badge tone={c.nightshiftStatus === "online" ? "record" : "clash"}>{c.nightshiftStatus === "online" ? "Online" : c.nightshiftStatus}</Badge>
              ) : null}
              {c.nightshiftHost ? <span className="font-mono text-xs text-ink">{c.nightshiftHost}</span> : <span className="text-graphite">No Runtime URL</span>}
              <span className="text-xs text-graphite">token hidden</span>
            </dd>
            <dt className="text-graphite">Lanes requested</dt>
            <dd className="font-mono text-xs text-ink">
              fast: {c.fastMode ?? "–"}, deep: {c.deepMode ?? "–"}
            </dd>
            <dt className="text-graphite">Nemotron models Nightshift offers</dt>
            <dd className="flex flex-wrap gap-1" data-testid="provider-models">
              {nemotron.length ? (
                nemotron.map((m) => (
                  <Badge key={m} tone="reason" className="font-mono">
                    {m}
                  </Badge>
                ))
              ) : (
                <span className="text-graphite">No Nemotron model seen.</span>
              )}
              {others > 0 ? (
                <span className="text-xs text-graphite">
                  and {others} other {others === 1 ? "route or model" : "routes and models"}
                </span>
              ) : null}
            </dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

function ProofCard() {
  const query = useNightshiftProof();
  const p = proof(query.data);
  return (
    <Card data-testid="provider-proof">
      <CardHeader>
        <CardTitle>Committed proof</CardTitle>
        <CardDescription>
          One call per lane through Nightshift to Nemotron, recorded in <span className="font-mono">docs/evidence/nightshift_proof.json</span>
          {p?.timestamp ? ` on ${formatUtc(p.timestamp)}` : ""}.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {query.isError ? (
          <Callout title="No proof is committed in this checkout.">Run the command below on a machine with Nightshift.</Callout>
        ) : !p ? (
          <p className="text-sm text-graphite">Loading the proof…</p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Lane</TableHead>
                  <TableHead>Sent as</TableHead>
                  <TableHead>Routed mode</TableHead>
                  <TableHead>Model served</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Receipt</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {p.lanes.map((l) => (
                  <TableRow key={l.lane} data-testid={`proof-lane-${l.lane}`}>
                    <TableCell className="font-semibold">{l.lane === "fast" ? "Fast" : "Deep"}</TableCell>
                    <TableCell className="font-mono text-xs">{l.sent ?? "–"}</TableCell>
                    <TableCell>
                      {l.routedMode ?? "–"}
                      {l.coerced ? (
                        <Badge tone="claim" className="ml-2">
                          coerced from {l.requestedMode ?? "the lane"}
                        </Badge>
                      ) : null}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-reason">{l.served ?? "–"}</TableCell>
                    <TableCell>{seconds(l.latencyMs)}</TableCell>
                    <TableCell>{l.receipt ? <Identifier value={l.receipt} /> : "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {p.host ? <p className="text-xs text-graphite">Runtime at {p.host}, token hidden.</p> : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function RecentReceipts() {
  const query = useRecentReceipts();
  return (
    <Card data-testid="provider-receipts">
      <CardHeader>
        <CardTitle>Recent receipts</CardTitle>
        <CardDescription>The last 10 model calls with a Nightshift receipt, across the 5 newest cases on this instance.</CardDescription>
      </CardHeader>
      <CardContent>
        {query.isError ? (
          <Callout tone="error" title="Recent receipts did not load.">
            {query.error.message}
          </Callout>
        ) : !query.data ? (
          <p className="text-sm text-graphite">Reading the latest traces…</p>
        ) : query.data.length === 0 ? (
          <p className="text-sm text-graphite">
            No model call on this instance has a receipt yet. In sample mode every step uses its deterministic fallback; a live run adds receipts here.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Purpose</TableHead>
                <TableHead>Lane</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Latency</TableHead>
                <TableHead>Receipt</TableHead>
                <TableHead>Case</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.map((r) => (
                <TableRow key={`${r.caseId}-${r.receipt}-${r.at}`} data-testid="receipt-row">
                  <TableCell>{r.agent}</TableCell>
                  <TableCell>{r.purpose ?? "–"}</TableCell>
                  <TableCell>{r.lane ?? "–"}</TableCell>
                  <TableCell className="font-mono text-xs text-reason">{r.model ?? "–"}</TableCell>
                  <TableCell>{seconds(r.latencyMs)}</TableCell>
                  <TableCell>
                    <Identifier value={r.receipt} />
                  </TableCell>
                  <TableCell>
                    <Link to={`/cases/${encodeURIComponent(r.caseId)}`} className="font-mono text-xs text-record hover:underline">
                      {r.caseId}
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function DeviationNote() {
  const p = proof(useNightshiftProof().data);
  const receipts = useRecentReceipts().data ?? [];
  if (!p?.coerced && !receipts.some((r) => r.coerced)) return null;
  return (
    <Callout tone="warn" title="Lane coerced to auto by a Nightshift app rule" className="max-w-4xl">
      <span data-testid="provider-deviation">{DEVIATION_SENTENCE}</span>{" "}
      <DocLink path="docs/evidence/nightshift_deviations.md">Read the deviation record</DocLink>.
    </Callout>
  );
}

export function ProviderPage() {
  return (
    <>
      <PageHeader title="Provider">Every model call goes through Meterless Nightshift to NVIDIA Nemotron. This page shows the proof.</PageHeader>
      <div className="flex max-w-6xl flex-col gap-6 px-8 py-6">
        <DeviationNote />
        <ConnectionCard />
        <ProofCard />
        <RecentReceipts />
        <Card data-testid="provider-run-proof">
          <CardHeader>
            <CardTitle>Run proof now</CardTitle>
            <CardDescription>
              From a terminal on a machine with Nightshift. It sends one call per lane and writes the proof file. The console does not run it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CopyBlock text="python run.py llm proof" />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
