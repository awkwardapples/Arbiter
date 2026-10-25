// P18C-T3: the next action is editable and downloads as a .txt with the edited text.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { caseRoutes, load, mockApi, readBlob, renderAt, type Recorded } from "./helpers";

const detail = load<Recorded>("p14a_case_escalate.json");
const trace = load("p14a_trace_escalate.json");
const EDIT = "Please confirm the hosting region in writing.";

describe("P18C-T3 Next action", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("downloads the edited body as a .txt blob", async () => {
    mockApi(caseRoutes(detail, trace));
    let blob: Blob | null = null;
    let fileName = "";
    vi.stubGlobal("URL", Object.assign(URL, {
      createObjectURL: vi.fn((b: Blob) => {
        blob = b;
        return "blob:draft";
      }),
      revokeObjectURL: vi.fn(),
    }));
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      fileName = this.download;
    });

    renderAt(`/cases/${detail.case_id}`);
    const panel = await screen.findByTestId("next-action");
    expect(panel).toHaveTextContent("TPRM lead");
    const body = within(panel).getByRole("textbox", { name: "Message body" });
    await userEvent.clear(body);
    await userEvent.type(body, EDIT);
    await userEvent.click(within(panel).getByRole("button", { name: "Download .txt" }));

    expect(fileName).toMatch(/\.txt$/);
    expect(blob).not.toBeNull();
    const text = await readBlob(blob as unknown as Blob);
    expect(text).toContain(EDIT);
    expect((blob as unknown as Blob).type).toContain("text/plain");
  });

  it("copies the edited body", async () => {
    mockApi(caseRoutes(detail, trace));
    const writeText = vi.fn(async () => {});
    vi.stubGlobal("navigator", Object.assign(navigator, { clipboard: { writeText } }));
    renderAt(`/cases/${detail.case_id}`);
    const panel = await screen.findByTestId("next-action");
    const body = within(panel).getByRole("textbox", { name: "Message body" });
    await userEvent.clear(body);
    await userEvent.type(body, EDIT);
    await userEvent.click(within(panel).getByRole("button", { name: "Copy" }));
    expect(writeText).toHaveBeenCalledWith(EDIT);
  });
});
