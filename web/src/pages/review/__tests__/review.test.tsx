import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixture, fromRepo, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { ReviewPage } from "../ReviewPage";
import { reasonWords } from "../review";

// Dry runs recorded on two real cases (one ineligible, one eligible); only their answers are replayed here.
const dryRuns = fixture("features/memory/__tests__/fixtures/review_dry_run.json");
const submitted = fixture("features/memory/__tests__/fixtures/review_submitted.json");
// A case detail recorded by P14-B from a sample-mode API (the fixture rule in P18-C §4).
const caseDetail = fromRepo("tests/fixtures/ui/p14a_case_escalate.json");

function setup(dry: { response: unknown }) {
  const id = caseDetail.case_id as string;
  const calls = stubApi({
    [`GET /cases/${id}`]: { body: caseDetail },
    [`POST /cases/${id}/review?dry_run=true`]: { body: dry.response },
    [`POST /cases/${id}/review`]: { body: submitted },
  });
  renderPage(<ReviewPage />, { path: `/review/${id}`, pattern: "/review/:caseId" });
  return { calls, id };
}

describe("Review", { timeout: 30_000 }, () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T4: a rationale under 30 characters blocks submit; the dry run shows eligibility and why", async () => {
    const user = userEvent.setup();
    const { calls, id } = setup(dryRuns.ineligible);
    const form = await screen.findByTestId("review-form");
    await user.click(within(screen.getByTestId("field-reviewer")).getByRole("textbox"));
    await user.paste("lead@example.com");
    const rationale = within(screen.getByTestId("field-rationale")).getByRole("textbox");
    await user.click(rationale);
    await user.paste("x".repeat(29));
    const submit = within(form).getByRole("button", { name: "Submit review" });
    const check = within(form).getByRole("button", { name: "Check eligibility" });
    expect(submit).toBeDisabled();
    expect(check).toBeDisabled();
    expect(screen.getByTestId("error-rationale")).toHaveTextContent("at least 30 characters");
    await user.click(submit);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);

    await user.type(rationale, "y");
    expect(submit).toBeEnabled();
    await user.click(check);
    const result = await screen.findByTestId("review-eligibility");
    expect(result).toHaveTextContent("This review cannot become a precedent.");
    for (const code of dryRuns.ineligible.response.reasons as string[]) expect(result).toHaveTextContent(reasonWords(code));
    const post = calls.find((c) => c.method === "POST");
    expect(post?.path).toBe(`/cases/${id}/review?dry_run=true`);
    expect(post?.body).toMatchObject({ reviewer: "lead@example.com", role: "tprm_lead", rationale: `${"x".repeat(29)}y` });
    expect(screen.getByRole("checkbox", { name: /Save this exception/ })).toBeDisabled();
  });

  it("an eligible dry run unlocks the precedent; submit records it, shows the toast and links back to the case", async () => {
    const user = userEvent.setup();
    const { calls, id } = setup(dryRuns.eligible);
    await screen.findByTestId("review-form");
    await user.click(within(screen.getByTestId("field-reviewer")).getByRole("textbox"));
    await user.paste("lead@example.com");
    await user.click(within(screen.getByTestId("field-rationale")).getByRole("textbox"));
    await user.paste("Bridge letter accepted until the SOC 2 report arrives.");
    await user.click(screen.getByRole("button", { name: "Check eligibility" }));
    expect(await screen.findByTestId("review-eligibility")).toHaveTextContent("This review can become a precedent.");
    const save = screen.getByRole("checkbox", { name: /Save this exception/ });
    expect(save).toBeEnabled();
    await user.click(save);
    await user.click(screen.getByRole("button", { name: "Submit review" }));
    const done = await screen.findByTestId("review-done");
    expect(within(done).getByRole("link", { name: "Open the case" })).toHaveAttribute("href", `/cases/${id}`);
    const recorded = calls.find((c) => c.method === "POST" && c.path === `/cases/${id}/review`);
    expect(recorded?.body).toMatchObject({ create_precedent: true, mitigations: ["assurance.bridge_letter_current"] });
  });
});
