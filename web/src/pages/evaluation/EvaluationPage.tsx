import { PageHeader } from "../../app/PageHeader";
import { useEvalLatest } from "../../features/evaluation/evaluation";
import { LiveTable } from "../../features/evaluation/LiveTable";
import { ThisInstance } from "../../features/evaluation/ThisInstance";
import { Callout } from "../../ui/Callout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../ui/card";
import { DocLink } from "../../ui/DocLink";

export function EvaluationPage() {
  const latest = useEvalLatest();
  return (
    <>
      <PageHeader title="Evaluation">The published live evaluation, and what this instance has decided so far.</PageHeader>
      <div className="flex max-w-7xl flex-col gap-6 px-8 py-6">
        <Card>
          <CardHeader>
            <CardTitle>Live evaluation</CardTitle>
            <CardDescription>
              Arbiter, a single-model baseline and Arbiter offline on the same labelled cases, as published in{" "}
              <DocLink path="docs/EVALUATION.md" />.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {latest.isError ? (
              <Callout tone="error" title="The evaluation did not load.">
                {latest.error.message}
              </Callout>
            ) : latest.data === null ? (
              <p className="text-sm text-ink" data-testid="eval-fallback">
                Evaluation results are published in <DocLink path="docs/EVALUATION.md">docs/EVALUATION.md</DocLink>.
              </p>
            ) : latest.data?.live ? (
              <LiveTable summary={latest.data.live} markdown={latest.data.live_markdown} />
            ) : latest.data ? (
              <p className="text-sm text-ink" data-testid="eval-fallback">
                No live evaluation is published in this checkout. Results are in <DocLink path="docs/EVALUATION.md">docs/EVALUATION.md</DocLink>.
              </p>
            ) : (
              <p className="text-sm text-graphite">Loading the evaluation…</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>This instance</CardTitle>
            <CardDescription>Cases decided by this API. These are not scored: there are no labels here.</CardDescription>
          </CardHeader>
          <CardContent>
            <ThisInstance />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
