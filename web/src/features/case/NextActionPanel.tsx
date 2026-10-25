// The drafted next action: recipient, subject, an editable body, Copy and Download .txt.
import { useRef, useState } from "react";
import { Button } from "../../ui/button";
import { Textarea } from "../../ui/textarea";
import { toast } from "../../ui/toast";
import { copyText, downloadText } from "./download";
import type { Draft } from "./types";
import { roleWord } from "./words";

const capitalised = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function DraftEditor({ draft, fileName }: { draft: Draft; fileName: string }) {
  const [body, setBody] = useState(draft.body);
  const area = useRef<HTMLTextAreaElement>(null);
  const copy = async () => {
    const how = await copyText(body, area.current);
    if (how === "copied") toast.success("Copied to the clipboard");
    else toast("The text is selected. Press Ctrl+C or Cmd+C to copy it.");
  };
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-graphite">To</dt>
        <dd className="text-ink">{capitalised(roleWord(draft.to_role))}</dd>
        <dt className="text-graphite">Subject</dt>
        <dd className="text-ink">{draft.subject}</dd>
      </dl>
      <Textarea
        ref={area}
        aria-label="Message body"
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={12}
        className="font-serif text-sm leading-6"
      />
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={copy}>
          Copy
        </Button>
        <Button variant="secondary" size="sm" onClick={() => downloadText(fileName, `Subject: ${draft.subject}\n\n${body}\n`)}>
          Download .txt
        </Button>
      </div>
    </div>
  );
}

export function NextActionPanel({ drafts, caseId }: { drafts: Draft[]; caseId: string }) {
  return (
    <section data-testid="next-action" className="rounded-panel border border-hairline bg-sheet p-5" aria-labelledby="next-action-title">
      <h2 id="next-action-title" className="mb-3 text-md font-semibold text-ink">
        Next action
      </h2>
      {drafts.length ? (
        <div className="flex flex-col gap-6">
          {drafts.map((draft, index) => (
            <DraftEditor key={index} draft={draft} fileName={`${caseId}-draft-${index + 1}.txt`} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-graphite">No action was drafted for this case.</p>
      )}
    </section>
  );
}
