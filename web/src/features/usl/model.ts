// The USL model as GET /usl/model serves it, and what the Sources page derives from it.
import type { RegistryQuery } from "../../api/types";

export interface UslColumn {
  name: string;
  data_type: string;
  nullable?: boolean;
  description?: string;
}

export interface UslForeignKey {
  columns: string[];
  target_table: string;
  target_columns: string[];
}

export interface UslTable {
  name: string;
  description: string;
  primary_key: string[];
  columns: UslColumn[];
  foreign_keys: UslForeignKey[];
}

export interface UslModel {
  name: string;
  namespace: string;
  tables: UslTable[];
  catalogue_tokens: number;
}

export interface Relationship {
  id: string;
  kind: "declared" | "undeclared";
  from: string;
  to: string;
  /** Plain words: which columns match. */
  on: string;
  /** For undeclared joins, the registry query that makes the match. */
  queryId?: string;
}

/**
 * Joins the model does not declare as keys, as documented in docs/ZETARIS_USL.md ("contract joins
 * procurement on clm_supplier_ref = supplier_ref … kev_vuln has no foreign key; Q_VENDOR_360 matches it
 * in the query"). Each is drawn only if both tables exist and the named query's SQL reads both.
 */
const DOCUMENTED_JOINS: Omit<Relationship, "id" | "kind">[] = [
  { from: "contract", to: "vendor", on: "vendor.clm_supplier_ref = contract.supplier_ref", queryId: "Q_VENDOR_360" },
  {
    from: "kev_vuln",
    to: "vendor_component",
    on: "vendor_project, and product contains the declared product",
    queryId: "Q_VENDOR_360",
  },
];

/** True if the resolved SQL names the table, under its USL name or a qualified mirror name. */
export function sqlReadsTable(sql: string | null | undefined, table: string): boolean {
  if (!sql) return false;
  const pattern = new RegExp(`\\b(?:FROM|JOIN)\\s+(?:[\\w.]*\\.)?${table}(?:_v)?\\b`, "i");
  return pattern.test(sql);
}

export function relationships(model: UslModel, registry: RegistryQuery[]): Relationship[] {
  const names = new Set(model.tables.map((t) => t.name));
  const declared: Relationship[] = model.tables.flatMap((table) =>
    table.foreign_keys
      .filter((fk) => names.has(fk.target_table))
      .map((fk) => ({
        id: `fk:${table.name}.${fk.columns.join("+")}->${fk.target_table}`,
        kind: "declared" as const,
        from: table.name,
        to: fk.target_table,
        on: `${table.name}.${fk.columns.join(", ")} = ${fk.target_table}.${fk.target_columns.join(", ")}`,
      })),
  );
  const byId = new Map(registry.map((q) => [q.id, q]));
  const undeclared: Relationship[] = DOCUMENTED_JOINS.filter((join) => {
    const sql = join.queryId ? byId.get(join.queryId)?.sql : null;
    return names.has(join.from) && names.has(join.to) && sqlReadsTable(sql, join.from) && sqlReadsTable(sql, join.to);
  }).map((join) => ({ ...join, id: `join:${join.from}->${join.to}`, kind: "undeclared" as const }));
  return [...declared, ...undeclared];
}

/** Registry queries whose resolved SQL reads the table. Handler queries (no SQL) never match. */
export function queriesForTable(table: string, registry: RegistryQuery[]): RegistryQuery[] {
  return registry.filter((q) => sqlReadsTable(q.sql, table));
}

/** The text the Planner reads: a port of app/data/usl_model.py compact_catalogue(). */
export function compactCatalogue(model: UslModel): string {
  return model.tables
    .map((table) => {
      const parts = table.primary_key.map((column) => `${column} pk`);
      for (const fk of table.foreign_keys) {
        parts.push(`${fk.columns.join(", ")} fk→${fk.target_table}.${fk.target_columns[0] ?? ""}`);
      }
      return `${table.name}(${parts.join(", ")}): ${table.description}`;
    })
    .join("\n");
}
