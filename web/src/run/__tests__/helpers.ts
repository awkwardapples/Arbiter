// Test fixtures come from committed files only: traces from the repo, the registry from app/data/queries.yaml.
import { globSync } from "glob";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "yaml";
import type { RegistryQuery, TraceEvent } from "../../api/types";
import { buildRegistry, type Registry } from "../registry";

export const REPO = resolve(__dirname, "../../../..");

export function loadTrace(relative: string): TraceEvent[] {
  return readFileSync(resolve(REPO, relative), "utf-8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as TraceEvent);
}

export function loadRegistry(): Registry {
  const doc = parse(readFileSync(resolve(REPO, "app/data/queries.yaml"), "utf-8")) as {
    queries: Record<string, { description: string; systems: string[]; control_ids?: string[]; params?: string[] }>;
  };
  const rows: RegistryQuery[] = Object.entries(doc.queries).map(([id, q]) => ({ id, ...q }));
  return buildRegistry(rows);
}

export function allTraceFiles(): string[] {
  return [
    ...globSync("logs/examples/**/trace-*.jsonl", { cwd: REPO }),
    ...globSync("eval/results_live/**/traces/trace-run-*.jsonl", { cwd: REPO }),
  ].sort();
}

export const LIVE = "logs/examples/live/history/trace-run-83de5da137c0.jsonl";
export const EVAL = "eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl";
export const SAMPLE = "logs/examples/sample_mode/history/trace-run-a90b795279e5.jsonl";
export const NEW_SCHEMA = "web/src/run/__tests__/fixtures/trace-run-5568c241c8e3.jsonl";
