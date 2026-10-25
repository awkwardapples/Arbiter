// Mode chip text (design §5). It comes only from an event's `mode`, /health, or a recording's metadata.

export type ModeSource =
  | { kind: "mode"; mode: Record<string, string> | null | undefined; fallbacks?: number; paced?: boolean }
  | { kind: "recording"; startedAt: string | null | undefined; fallbacks?: number; mode?: Record<string, string> | null; modelIds?: string[] };

export interface ModeChip {
  text: string;
  tone: "live" | "sample" | "recorded" | "other";
  fallbacks: string | null;
  extra: string | null;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatUtc(iso: string): string | null {
  const date = new Date(iso.endsWith("Z") || /[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) return null;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

// Counts trace steps marked fallback: a failed model call and the deterministic step that replaced it
// count once each. The behaviour strip's "Retries and fallbacks" counts calls and queries instead.
export function fallbackText(count: number | undefined): string | null {
  if (!count) return null;
  return count === 1 ? "1 fallback step" : `${count} fallback steps`;
}

/**
 * A recording is live when Zetaris served the data and Nightshift served the models. `llm: "auto"`
 * (the memory session) counts only when a model call carried a model id, which only a Nightshift
 * completion records.
 */
export function recordedLive(mode: Record<string, string> | null | undefined, modelIds?: string[]): boolean {
  if (!mode) return false;
  if (mode.data !== "zetaris") return false;
  return mode.llm === "meterless" || (mode.llm === "auto" && (modelIds ?? []).length > 0);
}

const DATA_WORDS: Record<string, string> = { zetaris: "Zetaris USL", duckdb: "DuckDB mirror" };
const LLM_WORDS: Record<string, string> = {
  meterless: "Meterless Nightshift",
  nvidia: "NVIDIA direct",
  offline: "deterministic fallback",
  auto: "automatic provider choice",
};

export function modeChipText(source: ModeSource): ModeChip {
  if (source.kind === "recording") {
    const when = source.startedAt ? formatUtc(source.startedAt) : null;
    // A recording is called live only when its events say Zetaris and Nightshift served it.
    const live = !source.mode || recordedLive(source.mode, source.modelIds);
    const what = live ? "Recorded live run" : source.mode?.data === "duckdb" ? "Recorded sample-mode run" : "Recorded run";
    return {
      text: when ? `${what}, ${when}` : what,
      tone: "recorded",
      fallbacks: fallbackText(source.fallbacks),
      extra: null,
    };
  }
  const data = source.mode?.data ?? "";
  const llm = source.mode?.llm ?? "";
  if (data === "zetaris" && llm === "meterless") {
    return { text: "Live: Zetaris USL and Meterless Nightshift", tone: "live", fallbacks: fallbackText(source.fallbacks), extra: null };
  }
  if (data === "duckdb" && llm === "offline") {
    return {
      text: "Sample mode: DuckDB mirror, deterministic fallback",
      tone: "sample",
      fallbacks: null,
      extra: source.paced ? "Paced for viewing" : null,
    };
  }
  if (!data && !llm) return { text: "Mode unknown", tone: "other", fallbacks: null, extra: null };
  const dataWord = DATA_WORDS[data] ?? (data || "unknown data");
  const llmWord = LLM_WORDS[llm] ?? (llm || "unknown models");
  return { text: `Data: ${dataWord}. Models: ${llmWord}`, tone: "other", fallbacks: fallbackText(source.fallbacks), extra: null };
}
