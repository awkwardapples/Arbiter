// Records real API payloads for the console's Vitest fixtures. Never hand-write a payload.
//
//   SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve      (another terminal)
//   node scripts/record-fixtures.mjs --lane 18d [--base http://localhost:8000]
//
// Each lane has its own route list, so lanes add entries without touching each other's.
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const BASE = flag("base", process.env.ARBITER_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const LANE = flag("lane", "");

async function call(method, path, body) {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: { accept: "application/json", ...(body ? { "content-type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  return { status: response.status, body: text ? JSON.parse(text) : null };
}

async function save(rel, value) {
  const path = join(WEB, rel);
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf-8");
  console.log(`recorded ${rel}`);
}

/** At least one case must exist; if none does, assess the first vendor the API lists. */
async function ensureCase() {
  let cases = (await call("GET", "/cases")).body ?? [];
  if (cases.length === 0) {
    const vendors = (await call("GET", "/vendors")).body ?? [];
    if (vendors.length === 0) throw new Error("the API lists no vendors");
    const run = await call("POST", "/run", { vendor_id: vendors[0].vendor_id });
    if (run.status !== 200) throw new Error(`POST /run answered ${run.status}`);
    cases = (await call("GET", "/cases")).body ?? [];
  }
  return cases;
}

const LANES = {
  "18d": async () => {
    const plain = [
      ["intake", "questions", "/questions"],
      ["usl", "usl_model", "/usl/model"],
      ["usl", "registry_queries", "/registry/queries"],
      ["usl", "evidence_parity", "/evidence/parity"],
      ["usl", "health", "/health"],
      ["usl", "evidence_nightshift", "/evidence/nightshift"],
      ["usl", "agents", "/agents"],
      ["audit", "audit_recent", "/audit/recent?limit=50"],
      ["audit", "audit_verify", "/audit/verify"],
      ["memory", "precedents", "/memory/precedents"],
      ["evaluation", "cases", "/cases"],
    ];
    const cases = await ensureCase();
    // Review dry runs on every case: keep one ineligible and, if the data has one, one eligible answer.
    // An eligible case is then reviewed for real, so precedents and the audit chain have rows to show.
    const review = (decision) => ({
      reviewer: "lead@example.com",
      role: "tprm_lead",
      decision,
      rationale: "Recorded by record-fixtures.mjs to capture the review shapes.",
      mitigations: ["assurance.bridge_letter_current"],
      conditions: ["SOC 2 Type II report within 60 days"],
      create_precedent: true,
    });
    // Seed reviews only once: a second recording on the same var/ adds no further precedents.
    const seeded = ((await call("GET", "/memory/precedents")).body ?? []).length > 0;
    const dryRuns = {};
    const tryReview = async (caseId) => {
      const request = review("APPROVE_WITH_CONDITIONS");
      const path = `/cases/${encodeURIComponent(caseId)}/review`;
      const dry = await call("POST", `${path}?dry_run=true`, request);
      const key = dry.body?.eligible ? "eligible" : "ineligible";
      if (dryRuns[key]) return;
      dryRuns[key] = { case_id: caseId, request, response: dry.body };
      if (key === "eligible" && !seeded) {
        const submitted = await call("POST", path, request);
        if (submitted.status !== 200) throw new Error(`POST ${path} answered ${submitted.status}`);
      }
    };
    for (const item of cases) await tryReview(item.case_id);
    // No eligible case yet: assess vendors in the API's order until one is (sample mode, ~1 s each).
    // Then keep assessing until a case considers that precedent, and review it with the machine's
    // outcome, so the precedent gets a real feedback entry.
    const vendors = (await call("GET", "/vendors")).body ?? [];
    let feedback = seeded;
    for (const vendor of vendors) {
      if (dryRuns.eligible && feedback) break;
      const run = await call("POST", "/run", { vendor_id: vendor.vendor_id });
      const caseId = run.body?.output?.case_id;
      if (!caseId) continue;
      if (!dryRuns.eligible) {
        await tryReview(caseId);
        continue;
      }
      const detail = (await call("GET", `/cases/${encodeURIComponent(caseId)}`)).body;
      if ((detail?.record?.precedents_considered ?? []).length === 0) continue;
      const request = { ...review(detail.record.outcome), mitigations: [], conditions: [], create_precedent: false };
      const done = await call("POST", `/cases/${encodeURIComponent(caseId)}/review`, request);
      feedback = done.status === 200;
    }
    await save("src/features/memory/__tests__/fixtures/review_dry_run.json", dryRuns);
    // A real review without a precedent. Only the fields the Review page reads are kept; the rest is
    // the full decision record and contract, which the Case page fixtures already cover.
    if (dryRuns.ineligible) {
      const path = `/cases/${encodeURIComponent(dryRuns.ineligible.case_id)}/review`;
      const request = { ...review("ESCALATE"), mitigations: [], conditions: [], create_precedent: false };
      const recorded = await call("POST", path, request);
      if (recorded.status !== 200) throw new Error(`POST ${path} answered ${recorded.status}`);
      await save("src/features/memory/__tests__/fixtures/review_submitted.json", {
        review_id: recorded.body.review_id,
        precedent: recorded.body.precedent,
        eligibility: recorded.body.eligibility,
      });
    }
    for (const [area, name, path] of plain) {
      const { status, body } = await call("GET", path);
      if (status !== 200) throw new Error(`GET ${path} answered ${status}`);
      if (name === "health") scrubModels(body);
      await save(`src/features/${area}/__tests__/fixtures/${name}.json`, body);
    }
    // POST /runs answers with the run id the form navigates to.
    const started = await call("POST", "/runs", { vendor_id: vendors[0].vendor_id });
    if (started.status !== 202) throw new Error(`POST /runs answered ${started.status}`);
    await save("src/features/intake/__tests__/fixtures/run_started.json", started.body);
    // /eval/latest: the published payload, and the 404 shape for the fallback test.
    const latest = await call("GET", "/eval/latest");
    await save("src/features/evaluation/__tests__/fixtures/eval_latest.json", latest.body);
    const missing = await call("GET", "/cases/CASE-does-not-exist");
    await save("src/features/evaluation/__tests__/fixtures/not_found.json", { status: missing.status, body: missing.body });
    // A sample-mode case trace, and one committed live recording, whose model calls carry receipts.
    const caseId = cases[0].case_id;
    const trace = await call("GET", `/cases/${encodeURIComponent(caseId)}/trace`);
    await save("src/features/usl/__tests__/fixtures/case_trace.json", trace.body);
    const recordings = (await call("GET", "/recordings")).body ?? [];
    const live = recordings.find((r) => r.kind === "live_example" && r.n_model_calls > 0);
    if (!live) throw new Error("no committed live recording with model calls");
    const recording = await call("GET", `/recordings/${live.run_id}`);
    await save("src/features/usl/__tests__/fixtures/live_recording.json", recording.body);
  },
};

/** The only edit to a recorded payload: models_seen keeps the Nemotron and Meterless routes, not the
 *  recording machine's other local models, which say nothing about Arbiter and are private. */
function scrubModels(health) {
  const meterless = health?.provider?.meterless;
  if (meterless && Array.isArray(meterless.models_seen)) {
    meterless.models_seen = meterless.models_seen.filter((m) => m.startsWith("nvidia/") || m.startsWith("meterless/"));
  }
}

if (!LANES[LANE]) {
  console.error(`usage: node scripts/record-fixtures.mjs --lane <${Object.keys(LANES).join("|")}>`);
  process.exit(2);
}
await LANES[LANE]();
