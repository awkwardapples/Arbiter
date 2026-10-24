import { Link } from "react-router";
import { PageHeader } from "../../app/PageHeader";
import { Callout } from "../../ui/Callout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../ui/tabs";
import { RecordingList } from "./RecordingList";
import { VendorList } from "./VendorList";

export function AssessPage() {
  return (
    <>
      <PageHeader title="Assess a vendor" />
      <div className="flex max-w-5xl flex-col gap-8 px-8 py-6">
        <Tabs defaultValue="existing">
          <TabsList>
            <TabsTrigger value="existing">Existing vendor</TabsTrigger>
            <TabsTrigger value="new">New vendor</TabsTrigger>
          </TabsList>
          <TabsContent value="existing" className="pt-4">
            <VendorList />
          </TabsContent>
          <TabsContent value="new" className="pt-4">
            <Callout title="The questionnaire form is not in the web console yet.">
              Open <Link className="text-record underline" to="/new">New vendor assessment</Link>, or use the classic console's questionnaire tab
              (<code className="font-mono text-ink">python run.py ui</code>).
            </Callout>
          </TabsContent>
        </Tabs>
        <section aria-labelledby="recordings-heading" className="flex flex-col gap-3">
          <div>
            <h2 id="recordings-heading" className="text-lg font-semibold text-ink">Recorded live runs</h2>
            <p className="text-sm text-graphite">Committed traces from real runs. Watching one replays its events; nothing is re-run.</p>
          </div>
          <RecordingList />
        </section>
      </div>
    </>
  );
}
