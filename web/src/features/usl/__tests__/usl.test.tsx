import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RegistryQuery } from "../../../api/types";
import { SourcesPage } from "../../../pages/sources/SourcesPage";
import { fixture, renderPage, stubApi } from "../../../ui/__tests__/harness";
import { layoutGraph } from "../layout";
import { type UslModel, compactCatalogue, queriesForTable, relationships } from "../model";

const agents = fixture("features/usl/__tests__/fixtures/agents.json");
const caseTrace = fixture("features/usl/__tests__/fixtures/case_trace.json");
const parity = fixture("features/usl/__tests__/fixtures/evidence_parity.json");
const health = fixture("features/usl/__tests__/fixtures/health.json");
const registryJson = fixture("features/usl/__tests__/fixtures/registry_queries.json");
const modelJson = fixture("features/usl/__tests__/fixtures/usl_model.json");
const cases = fixture("features/evaluation/__tests__/fixtures/cases.json");

const model = modelJson as UslModel;
const registry = registryJson as RegistryQuery[];
const latest = [...cases].sort((a, b) => b.created.localeCompare(a.created))[0].case_id;

function renderSources() {
  stubApi({
    "GET /health": { body: health },
    "GET /usl/model": { body: model },
    "GET /registry/queries": { body: registry },
    "GET /evidence/parity": { body: parity },
    "GET /agents": { body: agents },
    "GET /cases": { body: cases },
    [`GET /cases/${latest}/trace`]: { body: caseTrace },
  });
  renderPage(<SourcesPage />);
}

describe("Sources: the USL diagram and data quality", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("P18D-T2: 10 table nodes, 5 declared foreign keys, 2 dashed undeclared joins, and CTR-30028 in DQ", async () => {
    const rels = relationships(model, registry);
    expect(rels.filter((r) => r.kind === "declared")).toHaveLength(5);
    const undeclared = rels.filter((r) => r.kind === "undeclared");
    expect(undeclared.map((r) => `${r.from}->${r.to}`).sort()).toEqual(["contract->vendor", "kev_vuln->vendor_component"]);

    const { nodes, edges } = layoutGraph(model.tables, rels, null, () => {});
    expect(nodes).toHaveLength(10);
    expect(edges.filter((e) => !e.style?.strokeDasharray)).toHaveLength(5);
    const dashed = edges.filter((e) => e.style?.strokeDasharray);
    expect(dashed).toHaveLength(2);
    for (const edge of dashed) expect(edge.label).toBe("joined in the query, not a declared key");
    // dagre lays the graph left to right: a referencing table sits left of the table it references.
    const x = new Map(nodes.map((n) => [n.id, n.position.x]));
    for (const rel of rels.filter((r) => r.kind === "declared")) expect(x.get(rel.from)!).toBeLessThan(x.get(rel.to)!);

    renderSources();
    for (const table of model.tables) expect(await screen.findByTestId(`usl-table-${table.name}`)).toBeInTheDocument();
    const list = screen.getByTestId("usl-relationships");
    expect(within(list).getAllByTestId("rel-declared")).toHaveLength(5);
    expect(within(list).getAllByTestId("rel-undeclared")).toHaveLength(2);
    expect(within(list).getByText("vendor.clm_supplier_ref = contract.supplier_ref")).toBeInTheDocument();

    const dq = await screen.findByTestId("usl-dq");
    expect(within(dq).getByTestId("dq-table-contract")).toHaveTextContent("Invalid rows on contract: CTR-30028 (Zetaris and mirror agree)");
    expect(within(dq).getByTestId("usl-parity-summary")).toHaveTextContent("416 of 416 registry comparisons matched; 32 of 32 KEV checks.");
    for (const rule of parity.rules) expect(within(dq).getByText(rule.id)).toBeInTheDocument();
    expect(screen.getByTestId("sources-mode")).toHaveTextContent("DuckDB mirror, sample mode");
  });

  it("lists the registry queries that read a selected table, with the agents that ran them", async () => {
    renderSources();
    // A plain click: React Flow's d3 pan handler needs a real window for the mousedown userEvent sends.
    fireEvent.click(await screen.findByTestId("usl-table-contract"));
    const panel = await screen.findByTestId("usl-queries");
    const expected = queriesForTable("contract", registry).map((q) => q.id);
    expect(expected).toContain("Q_VENDOR_CONTRACT");
    for (const id of expected) expect(within(panel).getByTestId(`usl-query-${id}`)).toBeInTheDocument();
    expect(await within(panel).findAllByText("Evidence")).not.toHaveLength(0);
  });

  it("the catalogue text is the one the Planner reads: its token estimate matches the API's", () => {
    expect(Math.floor(compactCatalogue(model).length / 4)).toBe(model.catalogue_tokens);
  });
});
