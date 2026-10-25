import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "./button";
import { cn } from "./lib/cn";

/** A command or other real text in mono, with a Copy button. */
export function CopyBlock({ text, label = "Copy", className }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className={cn("flex items-start gap-2 rounded-panel border border-hairline bg-well px-3 py-2", className)}>
      <pre className="min-w-0 flex-1 overflow-x-auto font-mono text-xs leading-6 whitespace-pre-wrap text-ink">{text}</pre>
      <Button type="button" variant="secondary" size="sm" onClick={copy}>
        {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
        {copied ? "Copied" : label}
      </Button>
    </div>
  );
}
