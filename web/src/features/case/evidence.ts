// Evidence-tab helpers: counterfactuals merged by control, and fact values in words.
import type { Counterfactual } from "./types";

/** One entry per control: evidence and question ids merged, in first-seen order. */
export function mergeCounterfactuals(items: Counterfactual[]): Counterfactual[] {
  const merged = new Map<string, Counterfactual>();
  for (const item of items) {
    const seen = merged.get(item.control_id);
    if (!seen) {
      merged.set(item.control_id, { ...item, evidence_required: [...new Set(item.evidence_required)], question_ids: [...new Set(item.question_ids ?? [])] });
      continue;
    }
    seen.evidence_required = [...new Set([...seen.evidence_required, ...item.evidence_required])];
    seen.question_ids = [...new Set([...(seen.question_ids ?? []), ...(item.question_ids ?? [])])];
  }
  return [...merged.values()];
}

export function valueWords(value: unknown): string {
  if (value === null || value === undefined) return "Not recorded";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(String).join(", ") : "None";
  return String(value);
}
