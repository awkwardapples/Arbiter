// Query id -> systems, from GET /registry/queries (P18-A). Which bench node a system lights up is the
// design §7.1 table: trust_portal is the vendor's word, everything else is a system of record.
import type { RegistryQuery } from "../api/types";

export interface RegistryEntry {
  id: string;
  description: string;
  systems: string[];
  controls: string[];
  sql: string | null;
}

export type Registry = Record<string, RegistryEntry>;

export function buildRegistry(rows: RegistryQuery[]): Registry {
  const out: Registry = {};
  for (const row of rows) {
    out[row.id] = {
      id: row.id,
      description: row.description,
      systems: [...row.systems],
      controls: [...(row.control_ids ?? [])],
      sql: row.sql ?? null,
    };
  }
  return out;
}

export const VENDOR_SYSTEM = "trust_portal";

/** System of record -> node id and the label an analyst understands. */
export const SOURCE_NODES: Record<string, { id: string; label: string; role: string }> = {
  procurement: { id: "rec.procurement", label: "Procurement", role: "System of record" },
  clm: { id: "rec.clm", label: "Contracts (CLM)", role: "System of record" },
  itsm: { id: "rec.itsm", label: "Service desk (ITSM)", role: "System of record" },
  grc_watchlist: { id: "rec.grc", label: "Watchlist (GRC)", role: "System of record" },
  cisa_kev: { id: "rec.kev", label: "CISA KEV", role: "Public catalogue" },
};

export const VENDOR_NODES = {
  answers: { id: "vendor.answers", label: "Questionnaire answers" },
  documents: { id: "vendor.documents", label: "Documents" },
  components: { id: "vendor.components", label: "Declared software" },
} as const;

export function sourceNode(system: string): { id: string; label: string; role: string } {
  return SOURCE_NODES[system] ?? { id: `rec.${system}`, label: system, role: "System of record" };
}

export function systemLabel(system: string): string {
  if (system === VENDOR_SYSTEM) return "Trust portal";
  return sourceNode(system).label;
}

/** Which of the vendor's-word nodes a trust-portal query reads, from what the query names. */
export function vendorNodeFor(queryId: string): (typeof VENDOR_NODES)[keyof typeof VENDOR_NODES] {
  if (/DOCUMENT/.test(queryId)) return VENDOR_NODES.documents;
  if (/COMPONENT|PRODUCT/.test(queryId)) return VENDOR_NODES.components;
  return VENDOR_NODES.answers;
}

export interface QueryTarget {
  id: string;
  label: string;
  role: string;
  vendor: boolean;
}

/** Bench nodes a query touches, derived from the registry's systems. Unknown query: none. */
export function targetsForQuery(registry: Registry, queryId: string | null | undefined): QueryTarget[] {
  if (!queryId) return [];
  const entry = registry[queryId];
  if (!entry) return [];
  const seen = new Set<string>();
  const out: QueryTarget[] = [];
  for (const system of entry.systems) {
    const node = system === VENDOR_SYSTEM ? { ...vendorNodeFor(queryId), role: "The vendor's word" } : sourceNode(system);
    if (seen.has(node.id)) continue;
    seen.add(node.id);
    out.push({ ...node, vendor: system === VENDOR_SYSTEM });
  }
  return out;
}

/** The systems of record a query is about, in words (procurement only when it is the only one). */
export function queryEvidenceWords(registry: Registry, queryId: string): string[] {
  const systems = registry[queryId]?.systems ?? [];
  const records = systems.filter((s) => s !== VENDOR_SYSTEM);
  const specific = records.filter((s) => s !== "procurement");
  const chosen = specific.length ? specific : records.length ? records : systems;
  return chosen.map(systemLabel);
}
