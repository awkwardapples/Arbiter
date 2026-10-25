// Small parsers for the key=value summaries the backend writes into trace events.

export function kv(summary: string | null | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  if (!summary) return out;
  const re = /([A-Za-z_]+)=(\[[^\]]*\]|\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(summary))) out[m[1]] = m[2];
  return out;
}

export function list(value: string | undefined): string[] {
  if (!value || value === "-") return [];
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}

export function int(value: string | undefined): number | null {
  if (value === undefined) return null;
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? n : null;
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export function seconds(ms: number | null | undefined): string | null {
  if (ms === null || ms === undefined) return null;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function duration(total: number): string {
  if (total < 60) return `${total.toFixed(1)} s`;
  const minutes = Math.floor(total / 60);
  const rest = Math.round(total - minutes * 60);
  return `${minutes} min ${rest} s`;
}

/** "ESCALATE in 131.444s" -> outcome and seconds. */
export function completeSummary(summary: string): { outcome: string; seconds: number | null } | null {
  const m = /^([A-Z_]+)\s+in\s+([\d.]+)s/.exec(summary.trim());
  if (m) return { outcome: m[1], seconds: Number.parseFloat(m[2]) };
  const word = /^([A-Z_]+)/.exec(summary.trim());
  return word ? { outcome: word[1], seconds: null } : null;
}

/** "INTAKE→PLAN (7 queries)" -> from, to. */
export function transition(summary: string): { from: string; to: string; rest: string } | null {
  const m = /^([A-Z_0-9]+)\s*(?:→|->)\s*([A-Z_0-9]+)\s*(.*)$/.exec(summary.trim());
  return m ? { from: m[1], to: m[2], rest: m[3] } : null;
}

/** "gaps: C06→Q_VENDOR_INCIDENTS; C09→Q_VENDOR_CONTRACT" -> pairs. */
export function gaps(summary: string): { control: string; query: string }[] {
  const out: { control: string; query: string }[] = [];
  const re = /([A-Z]\d+)\s*(?:→|->)\s*(Q_[A-Z0-9_]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(summary))) out.push({ control: m[1], query: m[2] });
  return out;
}

export function contradictionsIn(summary: string): number | null {
  const m = /(\d+)\s+contradictions?/.exec(summary);
  return m ? Number.parseInt(m[1], 10) : null;
}

export function sentenceCase(code: string): string {
  const words = code.toLowerCase().replace(/[_.]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
