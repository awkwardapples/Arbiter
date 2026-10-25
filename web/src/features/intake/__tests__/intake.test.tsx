import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixture, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { PRESETS } from "../build";
import { NewVendorForm } from "../NewVendorForm";
import { caseInputSchema } from "../schema";

const questions = fixture("features/intake/__tests__/fixtures/questions.json");
const runStarted = fixture("features/intake/__tests__/fixtures/run_started.json");

const PAYROLL = PRESETS.find((p) => p.documents?.length && p.components?.length)!;

function setup() {
  const calls = stubApi({ "GET /questions": { body: questions }, "POST /runs": { status: 202, body: runStarted } });
  renderPage(<NewVendorForm />);
  return calls;
}

// The form re-renders 16 questions per keystroke; jsdom under a parallel run needs more than 5 s.
describe("New vendor questionnaire", { timeout: 30_000 }, () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T1: a preset fills all 16 questions; a missing legal name blocks the POST; a valid form posts a CaseInput", async () => {
    const user = userEvent.setup();
    const calls = setup();
    const preset = await screen.findByLabelText("Load an example vendor");
    await user.selectOptions(preset, PAYROLL.name);

    expect(questions).toHaveLength(16);
    for (const q of questions) {
      const entry = PAYROLL.answers[q.question_id];
      const card = screen.getByTestId(`question-${q.question_id}`);
      expect(within(card).getByTestId(`how-${q.question_id}`)).toHaveValue(entry.how ?? "");
      if (q.type === "yes_no") {
        const expected = entry.choice === "Yes" || entry.choice === "No" ? entry.choice : "Not answered";
        expect(within(card).getByRole("radio", { name: expected })).toHaveAttribute("aria-checked", "true");
      }
    }
    expect(screen.getByTestId("field-legal_name").querySelector("input")).toHaveValue(PAYROLL.legal_name);

    // Clear the legal name: the error sits by that field and nothing is posted.
    const legal = within(screen.getByTestId("field-legal_name")).getByRole("textbox");
    await user.clear(legal);
    await user.click(screen.getByRole("button", { name: "Start assessment" }));
    expect(within(screen.getByTestId("field-legal_name")).getByTestId("error-legal_name")).toHaveTextContent("Legal name is required.");
    expect(legal).toHaveAttribute("aria-invalid", "true");
    expect(calls.filter((c) => c.path === "/runs")).toHaveLength(0);

    // Put it back: one POST /runs whose body is a valid CaseInput, then the run view.
    await user.click(legal);
    await user.paste(PAYROLL.legal_name);
    await user.click(screen.getByRole("button", { name: "Start assessment" }));
    await screen.findByTestId("landed-run");
    const posts = calls.filter((c) => c.method === "POST" && c.path === "/runs");
    expect(posts).toHaveLength(1);
    const body = caseInputSchema.parse(posts[0].body);
    expect(body.submission.legal_name).toBe(PAYROLL.legal_name);
    expect(body.submission.documents).toHaveLength(1);
    expect(body.submission.documents[0].doc_id).toBe("D01");
    expect(body.submission.declared_components).toHaveLength(1);
    expect(body.submission.answers.length).toBeGreaterThan(0);
    for (const a of body.submission.answers) expect(a.answer_text.length).toBeGreaterThan(0);
  });

  it("names each problem next to its own field and row", async () => {
    const user = userEvent.setup();
    const calls = setup();
    await screen.findByLabelText("Load an example vendor");
    await user.click(screen.getByRole("button", { name: "Add a document" }));
    await user.click(screen.getByLabelText("Issued on, row 1"));
    await user.paste("March 2026");
    await user.click(screen.getByRole("button", { name: "Start assessment" }));
    expect(screen.getByTestId("error-requested_service")).toBeInTheDocument();
    expect(screen.getByTestId("error-data_categories")).toBeInTheDocument();
    expect(screen.getByTestId("error-processing_countries")).toBeInTheDocument();
    expect(screen.getByTestId("error-documents.0.issued_on")).toHaveTextContent("2026-03-01");
    expect(screen.getByTestId("error-documents.0.text")).toBeInTheDocument();
    await waitFor(() => expect(calls.some((c) => c.path === "/runs")).toBe(false));
  });

  it("Advanced JSON posts a pasted CaseInput and rejects one that is not", async () => {
    const user = userEvent.setup();
    const calls = setup();
    await screen.findByLabelText("Load an example vendor");
    const box = screen.getByLabelText("CaseInput JSON");
    await user.click(box);
    await user.paste('{"submission": {"legal_name": ""}}');
    await user.click(screen.getByRole("button", { name: "Start assessment from JSON" }));
    expect(within(screen.getByTestId("advanced-json")).getAllByRole("alert").length).toBeGreaterThan(0);
    expect(calls.some((c) => c.path === "/runs")).toBe(false);

    await user.clear(box);
    await user.paste('{"vendor_id": "from-the-vendor-list"}');
    await user.click(screen.getByRole("button", { name: "Start assessment from JSON" }));
    await screen.findByTestId("landed-run");
    expect(calls.find((c) => c.path === "/runs")?.body).toEqual({ vendor_id: "from-the-vendor-list" });
  });
});
