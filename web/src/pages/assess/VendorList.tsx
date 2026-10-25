import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../../api/client";
import { useVendors } from "../../api/queries";
import type { RunStarted, Vendor } from "../../api/types";
import { Button } from "../../ui/button";
import { Callout } from "../../ui/Callout";
import { EmptyState } from "../../ui/EmptyState";
import { Input } from "../../ui/input";
import { toast } from "../../ui/toast";

function criticalityWords(v: Vendor): string {
  const parts = [v.category, v.criticality ? `${v.criticality} criticality` : null].filter(Boolean);
  return parts.join(", ");
}

export function VendorList() {
  const vendors = useVendors();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [starting, setStarting] = useState<string | null>(null);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = vendors.data ?? [];
    return q ? list.filter((v) => `${v.legal_name} ${v.category ?? ""} ${v.criticality ?? ""}`.toLowerCase().includes(q)) : list;
  }, [vendors.data, query]);

  const start = async (vendor: Vendor) => {
    setStarting(vendor.vendor_id);
    try {
      const run = await api.post<RunStarted>("/runs", { vendor_id: vendor.vendor_id });
      navigate(`/runs/${encodeURIComponent(run.run_id)}`, { state: { vendorName: vendor.legal_name } });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The assessment did not start.");
      setStarting(null);
    }
  };

  if (vendors.isError) {
    return (
      <Callout tone="error" title="The vendor list did not load.">
        {(vendors.error as Error).message}
      </Callout>
    );
  }
  if (vendors.isLoading) return <p className="py-4 text-sm text-graphite">Loading vendors…</p>;
  if (!vendors.data?.length) return <EmptyState title="No vendors found. Is the API running in sample mode?" />;

  return (
    <div className="flex flex-col gap-3">
      <label className="relative block max-w-sm">
        <span className="sr-only">Search vendors</span>
        <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-graphite" aria-hidden />
        <Input className="pl-9" placeholder="Search by name, category or criticality" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <ul className="max-h-[300px] divide-y divide-hairline overflow-y-auto rounded-panel border border-hairline bg-sheet" aria-label="Vendors">
        {shown.map((vendor) => (
          <li key={vendor.vendor_id} className="flex items-center gap-4 px-4 py-2.5">
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium text-ink">{vendor.legal_name}</span>
              <span className="block text-[13px] text-graphite">{criticalityWords(vendor)}</span>
            </span>
            <Button size="sm" onClick={() => start(vendor)} disabled={starting !== null} aria-label={`Start assessment of ${vendor.legal_name}`}>
              {starting === vendor.vendor_id ? "Starting…" : "Start assessment"}
            </Button>
          </li>
        ))}
        {!shown.length ? <li className="px-4 py-3 text-sm text-graphite">No vendor matches “{query}”.</li> : null}
      </ul>
    </div>
  );
}
