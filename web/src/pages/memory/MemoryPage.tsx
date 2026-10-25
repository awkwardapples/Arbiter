import { PageHeader } from "../../app/PageHeader";
import { PrecedentList } from "../../features/memory/PrecedentList";
import { MEMORY_RULE } from "../../features/memory/precedents";

export function MemoryPage() {
  return (
    <>
      <PageHeader title="Memory">Human exceptions saved to H-MEM, and how reviewers have rated them since.</PageHeader>
      <div className="flex max-w-5xl flex-col gap-6 px-8 py-6">
        <p className="font-serif text-md text-ink" data-testid="memory-rule">
          {MEMORY_RULE}
        </p>
        <PrecedentList />
      </div>
    </>
  );
}
