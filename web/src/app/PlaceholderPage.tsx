import { Callout } from "../ui/Callout";
import { PageHeader } from "./PageHeader";

/** Stand-in for a page another lane builds. It points to the classic console, which has the page today. */
export function PlaceholderPage({ title, classicPage }: { title: string; classicPage: string }) {
  return (
    <>
      <PageHeader title={title} />
      <div className="max-w-3xl px-8 py-6">
        <Callout title="This page is not in the web console yet.">
          The classic console has it today: run <code className="font-mono text-ink">python run.py ui</code> and open{" "}
          {classicPage} at http://localhost:8501.
        </Callout>
      </div>
    </>
  );
}
