/* eslint-disable @typescript-eslint/no-explicit-any -- the test plants canaries in recorded payloads of any shape */
import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixture, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { ProviderPage } from "../ProviderPage";
import { DEVIATION_SENTENCE } from "../provider";

const cases = fixture("features/evaluation/__tests__/fixtures/cases.json");
const caseTrace = fixture("features/usl/__tests__/fixtures/case_trace.json");
const proofJson = fixture("features/usl/__tests__/fixtures/evidence_nightshift.json");
const healthJson = fixture("features/usl/__tests__/fixtures/health.json");
const liveRecording = fixture("features/usl/__tests__/fixtures/live_recording.json");

// Canary values start with "example-" so the repo secret scanner treats them as placeholders.
const CANARIES = ["Bearer example-canary-7f3a90", "METERLESS_RUNTIME_TOKEN=example-canary-91bd2c", "Authorization", "canary"];
const FIELD = "token";
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const newest = [...cases].sort((a, b) => b.created.localeCompare(a.created)).slice(0, 5);

/** Plant the canaries everywhere a payload could carry them: new keys, existing strings, lists. */
function poisoned() {
  const health = clone(healthJson) as Record<string, any>;
  const meterless = health.provider.meterless;
  meterless.Authorization = CANARIES[0];
  meterless[FIELD] = CANARIES[1];
  meterless.base_url = `http://runtime-user:${CANARIES[1]}@${new URL(meterless.base_url).host}/v1?${FIELD}=${CANARIES[0]}`;
  meterless.models_seen = [...meterless.models_seen, `Authorization: ${CANARIES[0]}`, CANARIES[1]];
  meterless.detail = CANARIES[1];
  meterless.fast_model = CANARIES[0];
  health.provider.reason = `Authorization: ${CANARIES[0]}`;
  health.headers = { Authorization: CANARIES[0] };

  const proof = clone(proofJson) as Record<string, any>;
  proof.fast.Authorization = CANARIES[0];
  proof.deep.sent_model = CANARIES[1];
  proof.deep.receipt_id = `rcpt_${CANARIES[1]}`;
  proof.deviations[0].detail = `${proof.deviations[0].detail} ${CANARIES[0]}`;
  proof[FIELD] = CANARIES[1];

  const live = clone(liveRecording.events) as Record<string, any>[];
  const call = live.find((e) => e.action === "model_call")!;
  call.provider_meta.Authorization = CANARIES[0];
  call.provider_meta["METERLESS_RUNTIME_TOKEN"] = CANARIES[1];
  live.push({ ...clone(call), agent_name: "Authorization", purpose: CANARIES[1], model: CANARIES[0], timestamp: "2026-10-24T05:00:00Z" });
  return { health, proof, live };
}

function render(health: unknown, proof: unknown, live: unknown[]) {
  // The newest case's trace is a committed live trace (it has receipts); the rest are sample-mode traces.
  const traces = Object.fromEntries(
    newest.map((c, i) => [`GET /cases/${c.case_id}/trace`, { body: i === 0 ? live : caseTrace }]),
  );
  stubApi({ "GET /health": { body: health }, "GET /evidence/nightshift": { body: proof }, "GET /cases": { body: cases }, ...traces });
  renderPage(<ProviderPage />);
}

describe("Provider: Nightshift connection and Nemotron proof", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T3: host and port with 'token hidden', the deviation sentence, and no canary in the DOM", async () => {
    const { health, proof, live } = poisoned();
    render(health, proof, live);
    const host = new URL(healthJson.provider.meterless.base_url).host;
    const nightshift = await screen.findByTestId("provider-nightshift");
    expect(nightshift).toHaveTextContent(host);
    expect(nightshift).toHaveTextContent("token hidden");
    expect(await screen.findByTestId("provider-deviation")).toHaveTextContent(DEVIATION_SENTENCE);
    expect(await screen.findByTestId("proof-lane-deep")).toHaveTextContent(proofJson.deep.response_model);
    const rows = await screen.findAllByTestId("receipt-row");
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.length).toBeLessThanOrEqual(10);
    await waitFor(() => expect(screen.queryByText("Reading the latest traces…")).not.toBeInTheDocument());

    const dom = document.body.innerHTML;
    for (const canary of CANARIES) expect(dom).not.toContain(canary);
  });

  it("shows the recorded receipts and proof as recorded", async () => {
    render(healthJson, proofJson, liveRecording.events);
    const receipts = liveRecording.events.filter((e: any) => e.action === "model_call" && e.provider_meta?.receipt_id);
    const table = await screen.findByTestId("provider-receipts");
    await waitFor(() => expect(within(table).getAllByTestId("receipt-row")).toHaveLength(Math.min(receipts.length, 10)));
    expect(within(table).getByText(receipts[0].provider_meta!.receipt_id!)).toBeInTheDocument();
    expect(screen.getByTestId("proof-lane-fast")).toHaveTextContent(proofJson.fast.receipt_id);
    expect(screen.getByTestId("provider-run-proof")).toHaveTextContent("python run.py llm proof");
  });
});
