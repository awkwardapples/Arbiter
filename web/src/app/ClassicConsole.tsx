import { MonitorCog } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "../ui/dialog";

/** The Streamlit console stays available (Release 3 README §4). This explains how to open it. */
export function ClassicConsoleLink() {
  return (
    <Dialog>
      <DialogTrigger className="flex w-full items-center gap-3 rounded-[6px] px-3 py-2 text-left text-xs text-graphite hover:bg-well hover:text-ink">
        <MonitorCog className="size-4 shrink-0" aria-hidden />
        <span className="max-lg:sr-only">Classic console</span>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>Classic console</DialogTitle>
        <DialogDescription>
          The Streamlit console has every page this console is replacing. Start it next to the API, then open it on port 8501.
        </DialogDescription>
        <pre className="mt-4 rounded-[6px] bg-well px-3 py-2 font-mono text-xs text-ink">python run.py ui</pre>
        <a className="mt-3 inline-block text-sm text-record underline" href="http://localhost:8501" target="_blank" rel="noreferrer">
          Open http://localhost:8501
        </a>
      </DialogContent>
    </Dialog>
  );
}
