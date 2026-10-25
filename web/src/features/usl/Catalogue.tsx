import { type UslModel, compactCatalogue } from "./model";

/** What the Planner reads before it plans: the compact catalogue and its token estimate. */
export function Catalogue({ model }: { model: UslModel }) {
  const text = compactCatalogue(model);
  return (
    <div className="flex flex-col gap-2" data-testid="usl-catalogue">
      <p className="text-sm text-ink">
        The Planner reads this one-line-per-table summary of the model, about {model.catalogue_tokens} tokens, instead of
        six schemas.
      </p>
      <pre className="overflow-x-auto rounded-panel border border-hairline bg-well px-4 py-3 font-mono text-xs leading-6 whitespace-pre-wrap text-ink">{text}</pre>
    </div>
  );
}
