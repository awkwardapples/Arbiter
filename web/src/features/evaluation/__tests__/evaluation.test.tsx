import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EvaluationPage } from "../../../pages/evaluation/EvaluationPage";
import { fixture, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { publishedNotes } from "../evaluation";

const latest = fixture("features/evaluation/__tests__/fixtures/eval_latest.json");
const notFound = fixture("features/evaluation/__tests__/fixtures/not_found.json");
const cases = fixture("features/evaluation/__tests__/fixtures/cases.json");
const health = fixture("features/usl/__tests__/fixtures/health.json");

function setup(evalReply: { status?: number; body: unknown }) {
  stubApi({ "GET /eval/latest": evalReply, "GET /cases": { body: cases }, "GET /health": { body: health } });
  renderPage(<EvaluationPage />);
}

describe("Evaluation", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T6: the three systems from /eval/latest, and the 404 fallback", async () => {
    setup({ body: latest });
    const table = await screen.findByTestId("eval-table");
    for (const key of ["arbiter", "baseline", "arbiter_offline"]) {
      const row = within(table).getByTestId(`eval-row-${key}`);
      expect(row).toHaveTextContent(String(latest.live.systems[key].run.n));
    }
    expect(within(table).getByTestId("eval-row-arbiter")).toHaveTextContent("1.000 (5/5)");
    expect(screen.getByTestId("eval-small-n")).toHaveTextContent("interval 0.57 to 1.00");
    for (const id of latest.live.model_ids) expect(within(screen.getByTestId("eval-models")).getByText(id)).toBeInTheDocument();
    // The published notes appear word for word.
    const notes = publishedNotes(latest.live_markdown);
    expect(notes.length).toBeGreaterThan(0);
    for (const line of notes) expect(within(screen.getByTestId("eval-notes")).getByText(line)).toBeInTheDocument();
    expect(await screen.findByTestId("eval-instance")).toHaveTextContent(`${cases.length} cases decided on this instance.`);

    vi.unstubAllGlobals();
    document.body.innerHTML = "";
    // The API's real 404 shape (recorded from another missing resource; /eval/latest is published here).
    setup({ status: notFound.status, body: notFound.body });
    expect(await screen.findByTestId("eval-fallback")).toHaveTextContent("Evaluation results are published in docs/EVALUATION.md");
    expect(screen.queryByTestId("eval-table")).not.toBeInTheDocument();
  });

  it("shows baseline_status exactly as published when the summary carries one", async () => {
    const status = latest.live.baseline_status ?? null;
    setup({ body: latest });
    await screen.findByTestId("eval-table");
    if (status) expect(screen.getByTestId("eval-baseline-status")).toHaveTextContent(status);
    else expect(screen.queryByTestId("eval-baseline-status")).not.toBeInTheDocument();
  });
});
